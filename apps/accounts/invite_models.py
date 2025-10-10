# apps/accounts/invite_models.py
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string

class WaitlistRequest(models.Model):
    """
    Stores requests from users who want to join the platform
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    # Request Information
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, blank=True)
    reason = models.TextField(
        help_text="Why do you want to join MyRecoveryPal?",
        blank=True
    )
    
    # Status
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # Admin notes
    admin_notes = models.TextField(blank=True)
    
    # Tracking
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_waitlist_requests'
    )
    
    # Referral tracking (optional)
    referral_source = models.CharField(
        max_length=100, 
        blank=True,
        help_text="How did you hear about us?"
    )
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Waitlist Request'
        verbose_name_plural = 'Waitlist Requests'
    
    def __str__(self):
        return f"{self.email} - {self.get_status_display()}"
    
    def approve(self, admin_user=None):
        """Approve the waitlist request and generate an invite code"""
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.reviewed_by = admin_user
        self.save()
        
        # Generate invite code
        invite_code = InviteCode.objects.create(
            email=self.email,
            created_by=admin_user,
            notes=f"Generated from waitlist request"
        )
        
        return invite_code
    
    def reject(self, admin_user=None, reason=''):
        """Reject the waitlist request"""
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.reviewed_by = admin_user
        if reason:
            self.admin_notes = reason
        self.save()


class InviteCode(models.Model):
    """
    Unique invite codes that allow users to register
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    )
    
    # The actual invite code
    code = models.CharField(
        max_length=32, 
        unique=True, 
        db_index=True,
        editable=False
    )
    
    # Who can use this code
    email = models.EmailField(
        null=True, 
        blank=True,
        help_text="If specified, only this email can use the code"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='active'
    )
    
    # Usage tracking
    used_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invite_codes'
    )
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Creation tracking
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invite_codes'
    )
    
    # Optional expiration
    expires_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Leave blank for no expiration"
    )
    
    # Max uses (for codes that can be reused)
    max_uses = models.IntegerField(
        default=1,
        help_text="Number of times this code can be used"
    )
    uses_remaining = models.IntegerField(default=1)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invite Code'
        verbose_name_plural = 'Invite Codes'
    
    def __str__(self):
        return f"{self.code} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.uses_remaining:
            self.uses_remaining = self.max_uses
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_code():
        """Generate a unique random invite code"""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(12))
            # Format as XXXX-XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:8]}-{code[8:12]}"
            if not InviteCode.objects.filter(code=formatted_code).exists():
                return formatted_code
    
    def is_valid(self, email=None):
        """Check if the invite code is valid and can be used"""
        # Check status
        if self.status != 'active':
            return False, f"This invite code is {self.get_status_display().lower()}"
        
        # Check expiration
        if self.expires_at and timezone.now() > self.expires_at:
            self.status = 'expired'
            self.save()
            return False, "This invite code has expired"
        
        # Check uses remaining
        if self.uses_remaining <= 0:
            self.status = 'used'
            self.save()
            return False, "This invite code has been fully used"
        
        # Check email restriction
        if self.email and email and self.email.lower() != email.lower():
            return False, "This invite code is not valid for your email address"
        
        return True, "Valid"
    
    def mark_as_used(self, user):
        """Mark the invite code as used by a specific user"""
        self.uses_remaining -= 1
        if self.uses_remaining <= 0:
            self.status = 'used'
        
        if not self.used_by:  # Record first user
            self.used_by = user
            self.used_at = timezone.now()
        
        self.save()
    

    def send_invite_email(self):
        """Send invite email using SendGrid API (with SMTP fallback)"""
        if not self.email:
            return False

        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.conf import settings
        import logging

        logger = logging.getLogger('apps.accounts')

        # Prepare context
        context = {
            'email': self.email,
            'invite_code': self.code,
            'registration_url': f"{settings.SITE_URL}/accounts/register/?invite={self.code}",
            'site_url': settings.SITE_URL,
            'uses_remaining': self.uses_remaining,
            'expires_at': self.expires_at,
        }

        html_message = render_to_string('emails/invite_code.html', context)
        plain_message = strip_tags(html_message)
        subject = '🌟 Welcome to MyRecoveryPal - Your Invite Code'

        # Try SendGrid HTTP API first (more reliable on Railway)
        try:
            import requests

            sendgrid_api_key = settings.EMAIL_HOST_PASSWORD

            response = requests.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers={
                    'Authorization': f'Bearer {sendgrid_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'personalizations': [{
                        'to': [{'email': self.email}],
                        'subject': subject
                    }],
                    'from': {'email': settings.DEFAULT_FROM_EMAIL},
                    'content': [
                        {'type': 'text/plain', 'value': plain_message},
                        {'type': 'text/html', 'value': html_message}
                    ]
                },
                timeout=10
            )

            if response.status_code in [200, 202]:
                logger.info(f"✅ SendGrid API: Email sent to {self.email}")
                return True
            else:
                logger.error(
                    f"❌ SendGrid API failed: {response.status_code} - {response.text}")
                raise Exception(f"SendGrid API error: {response.status_code}")

        except Exception as api_error:
            logger.warning(
                f"⚠️ SendGrid API failed: {api_error}, trying SMTP fallback...")

            # Fallback to SMTP (less reliable on Railway)
            try:
                from django.core.mail import EmailMultiAlternatives

                email = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[self.email]
                )
                email.attach_alternative(html_message, "text/html")
                email.send(fail_silently=False)

                logger.info(f"✅ SMTP: Email sent to {self.email}")
                return True

            except Exception as smtp_error:
                logger.error(
                    f"❌ Both SendGrid API and SMTP failed for {self.email}: {smtp_error}")
                return False

class SystemSettings(models.Model):
    """
    Global settings for the invite system
    """
    invite_only_mode = models.BooleanField(
        default=True,
        help_text="When enabled, registration requires an invite code"
    )
    
    waitlist_enabled = models.BooleanField(
        default=True,
        help_text="When enabled, users can request access via waitlist"
    )
    
    waitlist_message = models.TextField(
        default="We're currently in beta! Request access to join our community.",
        help_text="Message shown to users on the waitlist page"
    )
    
    registration_closed_message = models.TextField(
        default="Registration is currently closed. Please check back later!",
        help_text="Message shown when both invite mode and waitlist are disabled"
    )
    
    auto_approve_waitlist = models.BooleanField(
        default=False,
        help_text="Automatically approve all waitlist requests"
    )
    
    max_users = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of registered users (optional limit)"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return "Invite System Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
    
    def save(self, *args, **kwargs):
        self.pk = 1  # Enforce singleton
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        pass  # Prevent deletion