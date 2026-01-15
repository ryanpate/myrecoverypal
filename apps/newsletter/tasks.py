from celery import shared_task
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from .models import Newsletter, Subscriber, EmailLog
from apps.accounts.email_service import send_email
import logging
import time

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

                # Send email using Resend API
                success, error = send_email(
                    subject=newsletter.subject,
                    plain_message=plain_message,
                    html_message=html_message,
                    recipient_email=subscriber.email,
                )

                if not success:
                    logger.warning(f"Failed to send newsletter to {subscriber.email}: {error}")
                    continue

                # Small delay between emails to avoid rate limiting
                time.sleep(0.5)

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
        try:
            send_newsletter_task.delay(newsletter.id)
            logger.info(f"Scheduled newsletter '{newsletter.title}' queued for sending")
        except Exception as e:
            # If we can't queue, send directly (we're already in a Celery task)
            logger.warning(f"Could not queue newsletter '{newsletter.title}', sending directly: {e}")
            try:
                send_newsletter_task(newsletter.id)
            except Exception as direct_error:
                logger.error(f"Failed to send newsletter '{newsletter.title}': {direct_error}")

@shared_task
def update_subscriber_stats():
    """Update subscriber engagement stats"""
    # This would integrate with email tracking
    pass