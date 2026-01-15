# apps/accounts/email_service.py
"""
Email service using Resend HTTP API for reliable email delivery.

This service provides a consistent interface for sending emails via Resend's
HTTP API, which is more reliable than SMTP on cloud platforms like Railway.
Falls back to Django's SMTP backend if the API call fails.
"""

import logging
import os
import time
import requests
from django.conf import settings
from django.core.mail import send_mail as django_send_mail

logger = logging.getLogger(__name__)


def send_email(
    subject: str,
    plain_message: str,
    html_message: str,
    recipient_email: str,
    from_email: str = None,
    max_retries: int = 3,
    use_smtp_fallback: bool = True
) -> tuple:
    """
    Send an email using Resend HTTP API with optional SMTP fallback.

    Args:
        subject: Email subject line
        plain_message: Plain text version of the email
        html_message: HTML version of the email
        recipient_email: Recipient's email address
        from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
        max_retries: Number of retry attempts for transient errors
        use_smtp_fallback: Whether to fall back to SMTP if API fails

    Returns:
        Tuple of (success: bool, error_message: str or None)
        - (True, None) if email was sent successfully
        - (False, "error description") if email failed
    """
    if from_email is None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'MyRecoveryPal <noreply@myrecoverypal.com>')

    # Get Resend API key
    resend_api_key = os.environ.get('RESEND_API_KEY', getattr(settings, 'EMAIL_HOST_PASSWORD', ''))

    if not resend_api_key:
        logger.warning("RESEND_API_KEY not set, attempting SMTP fallback")
        if use_smtp_fallback:
            return _send_via_smtp(subject, plain_message, html_message, recipient_email, from_email, max_retries)
        return (False, "RESEND_API_KEY not configured and SMTP fallback disabled")

    last_error = None

    # Try Resend HTTP API
    for attempt in range(max_retries):
        try:
            response = requests.post(
                'https://api.resend.com/emails',
                headers={
                    'Authorization': f'Bearer {resend_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'from': from_email,
                    'to': [recipient_email],
                    'subject': subject,
                    'html': html_message,
                    'text': plain_message
                },
                timeout=15
            )

            if response.status_code in [200, 201]:
                logger.info(f"Email sent successfully to {recipient_email} via Resend API")
                return (True, None)

            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 5))
                logger.warning(f"Rate limited by Resend, waiting {retry_after}s before retry")
                time.sleep(retry_after)
                last_error = f"Rate limited (429), retried {attempt + 1} times"
                continue

            # Parse error details
            error_data = response.json() if response.content else {}
            error_message = error_data.get('message', response.text)
            last_error = f"Resend API error ({response.status_code}): {error_message}"
            logger.error(last_error)

            # Don't retry on client errors (4xx) except rate limits
            if 400 <= response.status_code < 500:
                break

        except requests.exceptions.Timeout:
            last_error = f"Resend API timeout after {attempt + 1} attempts"
            logger.warning(f"Resend API timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # Exponential backoff
                continue

        except requests.exceptions.RequestException as e:
            last_error = f"Resend API request error: {str(e)}"
            logger.warning(f"Resend API request error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue

    # API failed, try SMTP fallback
    if use_smtp_fallback:
        logger.info("Resend API failed, attempting SMTP fallback")
        smtp_result = _send_via_smtp(subject, plain_message, html_message, recipient_email, from_email, max_retries)
        if smtp_result[0]:
            return smtp_result
        # Both failed - include both error messages
        return (False, f"Resend: {last_error}; SMTP: {smtp_result[1]}")

    return (False, last_error or "Unknown error")


def _send_via_smtp(
    subject: str,
    plain_message: str,
    html_message: str,
    recipient_email: str,
    from_email: str,
    max_retries: int = 3
) -> tuple:
    """
    Send email via Django's SMTP backend as a fallback.

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            django_send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Email sent successfully to {recipient_email} via SMTP")
            return (True, None)

        except Exception as e:
            last_error = str(e)
            error_msg = last_error.lower()
            # Retry on transient connection errors
            if any(x in error_msg for x in ['connection', 'timeout', 'closed', 'reset', 'refused']):
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"SMTP error (attempt {attempt + 1}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue

            logger.error(f"SMTP send failed for {recipient_email}: {e}")
            return (False, f"SMTP error: {last_error}")

    return (False, f"SMTP failed after {max_retries} retries: {last_error}")


def send_email_batch(
    emails: list,
    delay_between: float = 0.5
) -> dict:
    """
    Send multiple emails with a delay between each to avoid rate limiting.

    Args:
        emails: List of dicts with keys: subject, plain_message, html_message, recipient_email
        delay_between: Seconds to wait between emails

    Returns:
        Dict with 'sent', 'failed' counts and 'errors' list
    """
    sent = 0
    failed = 0
    errors = []

    for email_data in emails:
        try:
            success, error = send_email(
                subject=email_data['subject'],
                plain_message=email_data['plain_message'],
                html_message=email_data['html_message'],
                recipient_email=email_data['recipient_email'],
                from_email=email_data.get('from_email'),
            )
            if success:
                sent += 1
            else:
                failed += 1
                errors.append({'email': email_data.get('recipient_email'), 'error': error})
        except Exception as e:
            logger.error(f"Error sending email to {email_data.get('recipient_email')}: {e}")
            failed += 1
            errors.append({'email': email_data.get('recipient_email'), 'error': str(e)})

        # Delay between emails
        if delay_between > 0:
            time.sleep(delay_between)

    return {'sent': sent, 'failed': failed, 'errors': errors}
