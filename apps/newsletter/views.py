from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from .models import Newsletter, Subscriber, EmailLog, NewsletterCategory
from .forms import SubscribeForm, UnsubscribeForm, NewsletterForm, PreferencesForm
import uuid

def subscribe_view(request):
    """Newsletter subscription page"""
    if request.method == 'POST':
        form = SubscribeForm(request.POST)
        if form.is_valid():
            subscriber = form.save(commit=False)
            
            # Link to user account if logged in
            if request.user.is_authenticated:
                subscriber.user = request.user
                if not subscriber.first_name and request.user.first_name:
                    subscriber.first_name = request.user.first_name
                if not subscriber.last_name and request.user.last_name:
                    subscriber.last_name = request.user.last_name
            
            subscriber.source = 'newsletter_page'
            subscriber.save()
            
            # Send confirmation email
            send_confirmation_email(subscriber)
            
            messages.success(request, 'Please check your email to confirm your subscription!')
            return redirect('newsletter:subscribe_success')
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }
        form = SubscribeForm(initial=initial_data)
    
    return render(request, 'newsletter/subscribe.html', {
        'form': form,
        'categories': NewsletterCategory.objects.all()
    })

def subscribe_success_view(request):
    """Subscription success page"""
    return render(request, 'newsletter/subscribe_success.html')

def confirm_subscription_view(request, token):
    """Confirm email subscription"""
    try:
        subscriber = Subscriber.objects.get(confirmation_token=token)
        if not subscriber.is_confirmed:
            subscriber.is_confirmed = True
            subscriber.confirmed_at = timezone.now()
            subscriber.save()
            
            # Send welcome email
            send_welcome_email(subscriber)
            
            messages.success(request, 'Your subscription has been confirmed!')
        else:
            messages.info(request, 'Your subscription was already confirmed.')
        
        return redirect('newsletter:preferences', token=token)
    except Subscriber.DoesNotExist:
        messages.error(request, 'Invalid confirmation link.')
        return redirect('newsletter:subscribe')

def preferences_view(request, token):
    """Manage subscription preferences"""
    try:
        subscriber = Subscriber.objects.get(confirmation_token=token)
    except Subscriber.DoesNotExist:
        messages.error(request, 'Invalid preferences link.')
        return redirect('newsletter:subscribe')
    
    if request.method == 'POST':
        form = PreferencesForm(request.POST, instance=subscriber)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your preferences have been updated!')
            return redirect('newsletter:preferences', token=token)
    else:
        form = PreferencesForm(instance=subscriber)
    
    return render(request, 'newsletter/preferences.html', {
        'form': form,
        'subscriber': subscriber
    })

def unsubscribe_view(request, token):
    """Unsubscribe from newsletter"""
    try:
        subscriber = Subscriber.objects.get(confirmation_token=token)
    except Subscriber.DoesNotExist:
        # Show generic unsubscribe form
        if request.method == 'POST':
            form = UnsubscribeForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                try:
                    subscriber = Subscriber.objects.get(email=email)
                    subscriber.is_active = False
                    subscriber.unsubscribed_at = timezone.now()
                    subscriber.save()
                    messages.success(request, 'You have been unsubscribed.')
                except Subscriber.DoesNotExist:
                    messages.error(request, 'Email not found in our newsletter list.')
                return redirect('core:index')
        else:
            form = UnsubscribeForm()
        
        return render(request, 'newsletter/unsubscribe.html', {'form': form})
    
    # Direct unsubscribe with token
    if request.method == 'POST':
        subscriber.is_active = False
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save()
        messages.success(request, 'You have been unsubscribed from our newsletter.')
        return redirect('core:index')
    
    return render(request, 'newsletter/unsubscribe_confirm.html', {
        'subscriber': subscriber
    })

def newsletter_preview_view(request, pk):
    """Preview a newsletter"""
    newsletter = get_object_or_404(Newsletter, pk=pk)
    
    # Only allow staff or preview for sent newsletters
    if not newsletter.is_sent and not request.user.is_staff:
        raise Http404
    
    # Create a dummy subscriber for preview
    subscriber = Subscriber(
        email='preview@example.com',
        first_name='Preview',
        last_name='User'
    )
    
    html_content = render_to_string('newsletter/emails/newsletter.html', {
        'newsletter': newsletter,
        'subscriber': subscriber,
        'is_preview': True,
        'site_url': request.build_absolute_uri('/')[:-1],
    })
    
    return HttpResponse(html_content)

class NewsletterListView(ListView):
    """Public archive of sent newsletters"""
    model = Newsletter
    template_name = 'newsletter/archive.html'
    context_object_name = 'newsletters'
    paginate_by = 12
    
    def get_queryset(self):
        return Newsletter.objects.filter(is_sent=True).order_by('-sent_at')

@staff_member_required
def newsletter_dashboard_view(request):
    """Admin dashboard for newsletters"""
    context = {
        'total_subscribers': Subscriber.objects.filter(is_active=True).count(),
        'confirmed_subscribers': Subscriber.objects.filter(is_active=True, is_confirmed=True).count(),
        'recent_newsletters': Newsletter.objects.order_by('-created_at')[:5],
        'scheduled_newsletters': Newsletter.objects.filter(status='scheduled', scheduled_for__gt=timezone.now()),
        'draft_newsletters': Newsletter.objects.filter(status='draft'),
    }
    return render(request, 'newsletter/dashboard.html', context)

# Helper functions
def send_confirmation_email(subscriber):
    """Send confirmation email to new subscriber"""
    subject = 'Confirm your subscription to Journey to Recovery Newsletter'
    
    html_message = render_to_string('newsletter/emails/confirm.html', {
        'subscriber': subscriber,
        'confirmation_url': f"{settings.SITE_URL}/newsletter/confirm/{subscriber.confirmation_token}/",
    })
    
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [subscriber.email],
        html_message=html_message,
    )

def send_welcome_email(subscriber):
    """Send welcome email to confirmed subscriber"""
    subject = 'Welcome to Journey to Recovery Newsletter!'
    
    html_message = render_to_string('newsletter/emails/welcome.html', {
        'subscriber': subscriber,
        'preferences_url': f"{settings.SITE_URL}/newsletter/preferences/{subscriber.confirmation_token}/",
    })
    
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [subscriber.email],
        html_message=html_message,
    )