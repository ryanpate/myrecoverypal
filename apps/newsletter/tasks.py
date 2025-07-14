from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from .models import Newsletter, Subscriber, EmailLog
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_newsletter_task(newsletter_id):
    """Send newsletter to all active subscribers"""
    try:
        newsletter = Newsletter.objects.get(id=newsletter_id)
        
        # Get active, confirmed subscribers
        subscribers = Subscriber.objects.filter(
            is_active=True,
            is_confirmed=True
        )
        
        # Filter by category if specified
        if newsletter.category:
            subscribers = subscribers.filter(categories=newsletter.category)
        
        sent_count = 0
        site_url = settings.SITE_URL.rstrip('/')
        
        for subscriber in subscribers:
            try:
                # Check if already sent
                email_log, created = EmailLog.objects.get_or_create(
                    newsletter=newsletter,
                    subscriber=subscriber
                )
                
                if not created:
                    continue  # Already sent
                
                # Render email
                html_message = render_to_string('newsletter/emails/newsletter.html', {
                    'newsletter': newsletter,
                    'subscriber': subscriber,
                    'site_url': site_url,
                    'tracking_id': email_log.tracking_id,
                    'current_year': timezone.now().year,
                })
                
                plain_message = strip_tags(html_message)
                
                # Send email
                send_mail(
                    subject=newsletter.subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[subscriber.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                # Update subscriber stats
                subscriber.last_email_sent = timezone.now()
                subscriber.emails_received += 1
                subscriber.save()
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Error sending to {subscriber.email}: {str(e)}")
                continue
        
        # Update newsletter status
        newsletter.is_sent = True
        newsletter.sent_at = timezone.now()
        newsletter.sent_count = sent_count
        newsletter.status = 'sent'
        newsletter.save()
        
        logger.info(f"Newsletter '{newsletter.title}' sent to {sent_count} subscribers")
        return f"Newsletter sent to {sent_count} subscribers"
        
    except Newsletter.DoesNotExist:
        logger.error(f"Newsletter {newsletter_id} not found")
        return "Newsletter not found"

@shared_task
def send_scheduled_newsletters():
    """Check and send scheduled newsletters"""
    now = timezone.now()
    scheduled = Newsletter.objects.filter(
        status='scheduled',
        scheduled_for__lte=now,
        is_sent=False
    )
    
    for newsletter in scheduled:
        send_newsletter_task.delay(newsletter.id)
        logger.info(f"Scheduled newsletter '{newsletter.title}' queued for sending")

@shared_task
def update_subscriber_stats():
    """Update subscriber engagement stats"""
    # This would integrate with email tracking
    pass