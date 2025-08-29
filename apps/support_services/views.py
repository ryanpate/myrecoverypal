# apps/support_services/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
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
        meetings = meetings.filter(
            Q(name__icontains=search_query) |
            Q(group__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(notes__icontains=search_query)
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

    # If address provided, geocode it
    if address and not (lat and lng):
        # Use Google Geocoding API or similar
        if hasattr(settings, 'GOOGLE_API_KEY'):
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': settings.GOOGLE_API_KEY
            }
            response = requests.get(geocode_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK' and data['results']:
                    location = data['results'][0]['geometry']['location']
                    lat = location['lat']
                    lng = location['lng']

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
