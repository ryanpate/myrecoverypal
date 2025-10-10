# apps/accounts/admin_invite.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .invite_models import WaitlistRequest, InviteCode, SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Invite System', {
            'fields': ('invite_only_mode', 'waitlist_enabled', 'auto_approve_waitlist')
        }),
        ('User Limits', {
            'fields': ('max_users',)
        }),
        ('Messages', {
            'fields': ('waitlist_message', 'registration_closed_message')
        }),
    )

    def has_add_permission(self, request):
        # Singleton - only one instance allowed
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Can't delete settings
        return False


@admin.register(WaitlistRequest)
class WaitlistRequestAdmin(admin.ModelAdmin):
    list_display = (
        'email', 'first_name', 'last_name', 'status',
        'requested_at', 'action_buttons'
    )
    list_filter = ('status', 'requested_at', 'referral_source')
    search_fields = ('email', 'first_name', 'last_name', 'reason')
    readonly_fields = ('requested_at', 'reviewed_at', 'reviewed_by')

    fieldsets = (
        ('Request Information', {
            'fields': ('email', 'first_name', 'last_name', 'reason', 'referral_source')
        }),
        ('Status', {
            'fields': ('status', 'admin_notes')
        }),
        ('Review Information', {
            'fields': ('requested_at', 'reviewed_at', 'reviewed_by'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_requests', 'reject_requests']

    def action_buttons(self, obj):
        if obj.status == 'pending':
            approve_url = reverse(
                'accounts:admin_approve_waitlist', args=[obj.id])
            return format_html(
                '<a class="button" href="{}">Approve & Generate Code</a>',
                approve_url
            )
        elif obj.status == 'approved':
            # Find the associated invite code
            try:
                invite = InviteCode.objects.filter(
                    email=obj.email).latest('created_at')
                return format_html(
                    '<span style="color: green;">✓ Code: {}</span>',
                    invite.code
                )
            except InviteCode.DoesNotExist:
                return format_html('<span style="color: orange;">Approved (no code)</span>')
        return format_html('<span style="color: gray;">{}</span>', obj.get_status_display())

    action_buttons.short_description = 'Actions'

    def approve_requests(self, request, queryset):
        count = 0
        emails_sent = 0
        for waitlist_request in queryset.filter(status='pending'):
            invite_code = waitlist_request.approve(admin_user=request.user)
            count += 1

            # Automatically send email
            if invite_code.send_invite_email():
                emails_sent += 1

        self.message_user(
            request,
            f'{count} request(s) approved. {emails_sent} invite email(s) sent successfully.'
        )
    approve_requests.short_description = 'Approve selected requests and send emails'

    def reject_requests(self, request, queryset):
        queryset.filter(status='pending').update(
            status='rejected',
            reviewed_at=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, 'Selected requests have been rejected.')
    reject_requests.short_description = 'Reject selected requests'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Show pending requests first
        return qs.order_by('-status', '-requested_at')


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'email', 'status', 'uses_remaining',
        'created_at', 'expires_at', 'used_by'
    )
    list_filter = ('status', 'created_at', 'expires_at')
    search_fields = ('code', 'email', 'notes')
    readonly_fields = ('code', 'used_by', 'used_at', 'created_at')

    fieldsets = (
        ('Code Information', {
            'fields': ('code', 'email', 'status')
        }),
        ('Usage Settings', {
            'fields': ('max_uses', 'uses_remaining', 'expires_at')
        }),
        ('Usage Tracking', {
            'fields': ('used_by', 'used_at'),
            'classes': ('collapse',)
        }),
        ('Administrative', {
            'fields': ('created_at', 'created_by', 'notes'),
            'classes': ('collapse',)
        }),
    )

    actions = ['revoke_codes', 'send_invite_emails']

    def revoke_codes(self, request, queryset):
        queryset.update(status='revoked')
        self.message_user(request, 'Selected codes have been revoked.')
    revoke_codes.short_description = 'Revoke selected codes'

    def send_invite_emails(self, request, queryset):
        count = 0
        for invite in queryset.filter(status='active', email__isnull=False):
            if invite.send_invite_email():
                count += 1

        self.message_user(
            request,
            f'Invite emails sent successfully to {count} recipient(s).'
        )
    send_invite_emails.short_description = 'Send invite emails'

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new invite
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
