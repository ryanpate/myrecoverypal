# apps/support_services/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from apps.support_services.hubs import hub_cities, hub_states, resolve_city
from apps.support_services.coverage import record_coverage_gap
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
import json
import requests
from datetime import datetime, timedelta
import logging

from .models import Meeting, SupportService, ServiceSubmission, UserBookmark
from .forms import MeetingSubmissionForm, SupportServiceSubmissionForm

logger = logging.getLogger(__name__)


def support_services_home(request):
    """Main support services page with search"""
    context = {
        'featured_services': SupportService.objects.filter(
            is_approved=True,
            is_active=True,
            is_featured=True
        )[:6],
        'recent_meetings': Meeting.objects.filter(
            is_approved=True,
            is_active=True
        ).select_related('submitted_by')[:10],
        'helplines': SupportService.objects.filter(
            is_approved=True,
            is_active=True,
            type='helpline'
        )[:5],
    }
    return render(request, 'support_services/home.html', context)


def meeting_finder(request):
    """
    TSML UI Meeting Finder - comprehensive meeting search interface
    """
    context = {
        # You can pass configuration from Django settings if needed
        'tsml_data_source': getattr(settings, 'TSML_DATA_SOURCE', None),
    }
    return render(request, 'support_services/meeting_finder.html', context)


def meeting_list(request):
    """List and search meetings"""
    meetings = Meeting.objects.filter(is_approved=True, is_active=True)

    # Search filters
    search_query = request.GET.get('q', '')
    day = request.GET.get('day', '')
    city = request.GET.get('city', '')
    state = request.GET.get('state', '')
    attendance = request.GET.get('attendance', '')
    meeting_type = request.GET.get('type', '')

    if search_query:
        # Location fields matter as much as the name: people search a ZIP
        # or a city, not a group name. Without these a ZIP returned nothing
        # even for ZIPs we hold data for.
        # state is iexact, not icontains — a 2-letter query like "in" would
        # otherwise match Indiana plus every name containing "in".
        meetings = meetings.filter(
            Q(name__icontains=search_query) |
            Q(group__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(formatted_address__icontains=search_query) |
            Q(address__icontains=search_query) |
            Q(postal_code__istartswith=search_query) |
            Q(state__iexact=search_query)
        )

    if day:
        meetings = meetings.filter(day=day)

    if city:
        meetings = meetings.filter(city__icontains=city)

    if state:
        meetings = meetings.filter(state=state)

    if attendance:
        meetings = meetings.filter(attendance_option=attendance)

    if meeting_type:
        meetings = meetings.filter(types__contains=meeting_type)

    # Get today's day of week (0=Monday, 6=Sunday)
    today = datetime.now().weekday()
    # Convert to Meeting model format (0=Sunday, 6=Saturday)
    today_meeting_day = (today + 1) % 7

    # Sort meetings - today's meetings first, then by day and time
    meetings = meetings.extra(
        select={'is_today': f"day = {today_meeting_day}"}
    ).order_by('-is_today', 'day', 'time')

    # Pagination
    paginator = Paginator(meetings, 20)
    page = request.GET.get('page')
    meetings_page = paginator.get_page(page)

    # A search that found nothing is a coverage gap worth ranking. A
    # day/attendance filter finding nothing is not — that is the filter
    # working. See apps/support_services/coverage.py.
    if search_query and not meetings_page.object_list:
        record_coverage_gap(search_query)

    context = {
        'meetings': meetings_page,
        'search_query': search_query,
        'selected_day': day,
        'selected_city': city,
        'selected_state': state,
        'selected_attendance': attendance,
        'selected_type': meeting_type,
        'today_day': today_meeting_day,
        'days': Meeting.DAY_CHOICES,
        'meeting_types': Meeting.MEETING_TYPES,
        'attendance_options': Meeting.ATTENDANCE_CHOICES,

        # SEO: override the site-wide defaults from
        # apps.core.context_processors.seo_defaults. These keys drive
        # <title>, meta description, og: and twitter: tags together.
        # seo_url is pinned to the bare hub URL so filtered permutations
        # (?day=, ?city=, ...) canonicalise here instead of competing.
        'states': hub_states(),
        # The in-person directory only covers the metros we hold feeds for,
        # so a miss needs to say why and point at the online meetings, which
        # work from anywhere. Only computed when there is nothing to show.
        'online_total': (
            Meeting.objects.filter(
                is_approved=True, is_active=True,
                attendance_option__in=('online', 'hybrid'),
            ).count()
            if not meetings_page.object_list else 0
        ),
        # The directory is sourced entirely from AA intergroup feeds. The
        # previous copy claimed NA and SMART meetings it does not carry, and
        # "1,500+" understated the count by 4x.
        'seo_title': 'AA Meeting Finder — Search Local & Online AA Meetings',
        'seo_description': (
            'Search thousands of free AA meetings by day, city, state or '
            'online. Times, addresses and Zoom links, updated weekly from '
            'local AA intergroups. No signup.'
        ),
        'seo_keywords': (
            'aa meetings near me, aa meeting finder, aa meeting directory, '
            'online aa meetings, aa meeting schedule, alcoholics anonymous '
            'meetings, find aa meetings'
        ),
        'seo_url': request.build_absolute_uri(reverse('support_services:meeting_list')),
    }

    return render(request, 'support_services/meeting_list.html', context)


def meeting_detail(request, slug):
    """Meeting detail page"""
    meeting = get_object_or_404(
        Meeting, slug=slug, is_approved=True, is_active=True)

    # Get nearby meetings (same city or within 10 miles if coordinates available)
    nearby_meetings = Meeting.objects.filter(
        is_approved=True,
        is_active=True
    ).exclude(id=meeting.id)

    if meeting.city:
        nearby_meetings = nearby_meetings.filter(
            city=meeting.city,
            state=meeting.state
        )[:5]

    context = {
        'meeting': meeting,
        'nearby_meetings': nearby_meetings,
        'is_bookmarked': False,

        # SEO: all 1,565 detail pages previously shared the site-wide
        # boilerplate title/description, which is why they sat in GSC
        # "Crawled - currently not indexed".
        'seo_title': meeting.seo_title,
        'seo_description': meeting.seo_description,
    }

    if request.user.is_authenticated:
        context['is_bookmarked'] = UserBookmark.objects.filter(
            user=request.user,
            meeting=meeting
        ).exists()

    return render(request, 'support_services/meeting_detail.html', context)


def service_list(request):
    """List and search support services"""
    services = SupportService.objects.filter(is_approved=True, is_active=True)

    # Search filters
    search_query = request.GET.get('q', '')
    service_type = request.GET.get('type', '')
    category = request.GET.get('category', '')
    cost = request.GET.get('cost', '')

    if search_query:
        services = services.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(organization__icontains=search_query)
        )

    if service_type:
        services = services.filter(type=service_type)

    if category:
        services = services.filter(category=category)

    if cost:
        services = services.filter(cost=cost)

    # Group services by type for better display
    services = services.order_by('type', 'category', 'name')

    # Pagination
    paginator = Paginator(services, 20)
    page = request.GET.get('page')
    services_page = paginator.get_page(page)

    context = {
        'services': services_page,
        'search_query': search_query,
        'selected_type': service_type,
        'selected_category': category,
        'selected_cost': cost,
        'service_types': SupportService.SERVICE_TYPES,
        'categories': SupportService.CATEGORY_CHOICES,
        'cost_options': SupportService.COST_CHOICES,
    }

    return render(request, 'support_services/service_list.html', context)


def service_detail(request, service_id):
    """Service detail page"""
    service = get_object_or_404(
        SupportService,
        service_id=service_id,
        is_approved=True,
        is_active=True
    )

    # Get related services
    related_services = SupportService.objects.filter(
        is_approved=True,
        is_active=True,
        type=service.type
    ).exclude(id=service.id)[:5]

    context = {
        'service': service,
        'related_services': related_services,
        'is_bookmarked': False,
    }

    if request.user.is_authenticated:
        context['is_bookmarked'] = UserBookmark.objects.filter(
            user=request.user,
            service=service
        ).exists()

    return render(request, 'support_services/service_detail.html', context)


@login_required
def submit_meeting(request):
    """Submit a new meeting for review"""
    if request.method == 'POST':
        form = MeetingSubmissionForm(request.POST)
        if form.is_valid():
            # Create submission for review
            submission_data = form.cleaned_data

            # Generate slug
            submission_data['slug'] = slugify(
                submission_data['name']) + '-' + str(timezone.now().timestamp())[:10]

            # Convert time fields to string for JSON storage
            if submission_data.get('time'):
                submission_data['time'] = submission_data['time'].strftime(
                    '%H:%M')
            if submission_data.get('end_time'):
                submission_data['end_time'] = submission_data['end_time'].strftime(
                    '%H:%M')

            submission = ServiceSubmission.objects.create(
                submission_type='meeting',
                submission_data=submission_data,
                submitted_by=request.user if request.user.is_authenticated else None,
                submitted_email=form.cleaned_data.get('contact_email', ''),
                submitted_phone=form.cleaned_data.get('contact_phone', ''),
            )

            messages.success(
                request, 'Thank you! Your meeting submission has been received and will be reviewed shortly.')

            # If user is staff, auto-approve
            if request.user.is_staff:
                submission.approve(request.user)
                messages.info(
                    request, 'As a staff member, your submission has been auto-approved.')

            return redirect('support_services:meeting_list')
    else:
        form = MeetingSubmissionForm()

    return render(request, 'support_services/submit_meeting.html', {'form': form})


@login_required
def submit_service(request):
    """Submit a new support service for review"""
    if request.method == 'POST':
        form = SupportServiceSubmissionForm(request.POST)
        if form.is_valid():
            # Create submission for review
            submission_data = form.cleaned_data

            # Generate service_id
            submission_data['service_id'] = slugify(
                submission_data['name']) + '-' + str(timezone.now().timestamp())[:10]

            submission = ServiceSubmission.objects.create(
                submission_type='service',
                submission_data=submission_data,
                submitted_by=request.user if request.user.is_authenticated else None,
                submitted_email=form.cleaned_data.get('email', ''),
                submitted_phone=form.cleaned_data.get('phone', ''),
            )

            messages.success(
                request, 'Thank you! Your service submission has been received and will be reviewed shortly.')

            # If user is staff, auto-approve
            if request.user.is_staff:
                submission.approve(request.user)
                messages.info(
                    request, 'As a staff member, your submission has been auto-approved.')

            return redirect('support_services:service_list')
    else:
        form = SupportServiceSubmissionForm()

    return render(request, 'support_services/submit_service.html', {'form': form})


@login_required
def bookmark_toggle(request, item_type, item_id):
    """Toggle bookmark for a meeting or service"""
    if request.method == 'POST':
        if item_type == 'meeting':
            item = get_object_or_404(Meeting, id=item_id)
            bookmark, created = UserBookmark.objects.get_or_create(
                user=request.user,
                meeting=item
            )
        elif item_type == 'service':
            item = get_object_or_404(SupportService, id=item_id)
            bookmark, created = UserBookmark.objects.get_or_create(
                user=request.user,
                service=item
            )
        else:
            return JsonResponse({'error': 'Invalid item type'}, status=400)

        if not created:
            bookmark.delete()
            return JsonResponse({'bookmarked': False, 'message': 'Bookmark removed'})

        return JsonResponse({'bookmarked': True, 'message': 'Bookmarked successfully'})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def my_bookmarks(request):
    """View user's bookmarked meetings and services"""
    bookmarks = UserBookmark.objects.filter(
        user=request.user).select_related('meeting', 'service')

    context = {
        'bookmarks': bookmarks,
    }

    return render(request, 'support_services/my_bookmarks.html', context)


def meeting_guide_json(request):
    """Export meetings in Meeting Guide API format"""
    meetings = Meeting.objects.filter(is_approved=True, is_active=True)

    # Apply filters if provided
    day = request.GET.get('day')
    if day:
        meetings = meetings.filter(day=day)

    city = request.GET.get('city')
    if city:
        meetings = meetings.filter(city__icontains=city)

    state = request.GET.get('state')
    if state:
        meetings = meetings.filter(state=state)

    # Convert to Meeting Guide format
    meetings_data = [meeting.to_meeting_guide_format() for meeting in meetings]

    return JsonResponse(meetings_data, safe=False)


def support_services_json(request):
    """Export support services as JSON"""
    services = SupportService.objects.filter(is_approved=True, is_active=True)

    # Apply filters if provided
    service_type = request.GET.get('type')
    if service_type:
        services = services.filter(type=service_type)

    category = request.GET.get('category')
    if category:
        services = services.filter(category=category)

    # Convert to JSON format
    services_data = [service.to_json() for service in services]

    return JsonResponse({
        'services': services_data,
        'metadata': {
            'total': len(services_data),
            'generated': timezone.now().isoformat(),
        }
    })


def nearby_meetings(request):
    """Find meetings near a location using coordinates or address"""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    address = request.GET.get('address')
    radius = float(request.GET.get('radius', 10))  # Default 10 miles

    if not (lat and lng) and not address:
        return JsonResponse({'error': 'Please provide coordinates or address'}, status=400)

    # If address provided, geocoding would be needed here
    # Note: Geocoding functionality has been removed
    if address and not (lat and lng):
        return JsonResponse({
            'error': 'Address geocoding is not currently supported. Please provide coordinates.'
        }, status=400)

    if lat and lng:
        # Find nearby meetings using Haversine formula
        # This is a simplified version - in production, use GeoDjango
        meetings = Meeting.objects.filter(
            is_approved=True,
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False
        )

        nearby = []
        for meeting in meetings:
            # Calculate distance (simplified)
            distance = calculate_distance(
                float(lat), float(lng),
                float(meeting.latitude), float(meeting.longitude)
            )
            if distance <= radius:
                meeting_data = meeting.to_meeting_guide_format()
                meeting_data['distance'] = round(distance, 1)
                nearby.append(meeting_data)

        # Sort by distance
        nearby.sort(key=lambda x: x['distance'])

        return JsonResponse({
            'meetings': nearby[:50],  # Limit to 50 results
            'center': {'lat': float(lat), 'lng': float(lng)},
            'radius': radius
        })

    return JsonResponse({'error': 'Could not geocode address'}, status=400)


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in miles (simplified Haversine)"""
    from math import radians, sin, cos, sqrt, atan2

    R = 3959  # Earth's radius in miles

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c


@require_http_methods(["GET"])
def crisis_resources(request):
    """Display crisis resources and helplines"""
    crisis_services = SupportService.objects.filter(
        is_approved=True,
        is_active=True,
        type='helpline'
    ).order_by('-is_featured', 'name')

    context = {
        'crisis_services': crisis_services,
    }

    return render(request, 'support_services/crisis_resources.html', context)


US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut',
    'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida',
    'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois',
    'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky',
    'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
    'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
    'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire',
    'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
    'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
    'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming',
}


def city_hub(request, state, city_slug):
    """Directory of every meeting in one city — the page that answers
    "aa meetings in <city>". Detail pages cannot rank for that query."""
    state = state.upper()
    city = resolve_city(state, city_slug)
    if not city:
        raise Http404('No meeting hub for that city')

    meetings = list(
        Meeting.objects
        .filter(is_approved=True, is_active=True, state=state, city=city)
        .order_by('day', 'time', 'name')
    )
    by_day = {}
    for m in meetings:
        label = m.get_day_display() if m.day is not None else 'Schedule varies'
        by_day.setdefault(label, []).append(m)

    state_name = US_STATES.get(state, state)
    total = len(meetings)
    online = sum(1 for m in meetings if m.attendance_option != 'in_person')

    return render(request, 'support_services/city_hub.html', {
        'city': city,
        'state': state,
        'state_name': state_name,
        'meetings': meetings,
        'by_day': by_day,
        'total': total,
        'online_count': online,
        'in_person_count': total - online,
        'seo_title': f'AA Meetings in {city}, {state} \u2014 {total} Local Meeting Times',
        'seo_description': (
            f'{total} AA meetings in {city}, {state}. Browse by day with '
            f'times, addresses and online options \u2014 free, no signup, '
            f'updated weekly from the local AA intergroup.'
        ),
        'seo_keywords': (
            f'aa meetings {city.lower()}, aa meetings in {city.lower()} {state.lower()}, '
            f'alcoholics anonymous {city.lower()}, aa meeting schedule {city.lower()}, '
            f'{city.lower()} recovery meetings'
        ),
        'seo_url': request.build_absolute_uri(
            reverse('support_services:city_hub',
                    kwargs={'state': state.lower(), 'city_slug': city_slug.lower()})),
    })


def state_hub(request, state):
    """Index of the cities in one state that have their own hub."""
    state = state.upper()
    cities = hub_cities(state)
    if not cities:
        raise Http404('No meeting hub for that state')

    state_name = US_STATES.get(state, state)
    total = sum(c['count'] for c in cities)

    return render(request, 'support_services/state_hub.html', {
        'state': state,
        'state_name': state_name,
        'cities': sorted(cities, key=lambda c: c['city']),
        'cities_by_size': cities,
        'total': total,
        'seo_title': f'AA Meetings in {state_name} \u2014 {total} Meetings in {len(cities)} Cities',
        'seo_description': (
            f'Find AA meetings across {state_name}. {total} meetings in '
            f'{len(cities)} cities with times, addresses and online options '
            f'\u2014 free and updated weekly.'
        ),
        'seo_keywords': (
            f'aa meetings {state_name.lower()}, alcoholics anonymous '
            f'{state_name.lower()}, aa meeting directory {state_name.lower()}'
        ),
        'seo_url': request.build_absolute_uri(
            reverse('support_services:state_hub', kwargs={'state': state.lower()})),
    })
