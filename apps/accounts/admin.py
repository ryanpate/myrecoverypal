from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Milestone, SupportMessage, ActivityFeed, DailyCheckIn, ActivityComment
from .models import GroupChallenge, ChallengeParticipant, ChallengeCheckIn, ChallengeComment, ChallengeBadge, UserChallengeBadge
# Add to apps/accounts/admin.py
from .admin_invite import *
from .payment_models import Subscription, SubscriptionPlan, Transaction, PaymentMethod, Invoice

class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active',
                    'sobriety_date', 'get_days_sober', 'is_sponsor']
    list_filter = ['is_active', 'is_staff',
                   'is_sponsor', 'newsletter_subscriber']

    fieldsets = UserAdmin.fieldsets + (
        ('Recovery Information', {
            'fields': ('sobriety_date', 'recovery_goals', 'is_sponsor')
        }),
        ('Profile', {
            'fields': ('bio', 'location', 'avatar')
        }),
        ('Privacy Settings', {
            'fields': ('is_profile_public', 'show_sobriety_date', 'allow_messages')
        }),
        ('Email Preferences', {
            'fields': ('email_notifications', 'newsletter_subscriber')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'sobriety_date')
        }),
    )


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'milestone_type',
                    'date_achieved', 'days_sober']
    list_filter = ['milestone_type', 'date_achieved']
    search_fields = ['user__username', 'title', 'description']
    date_hierarchy = 'date_achieved'


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username',
                     'recipient__username', 'subject', 'message']
    date_hierarchy = 'created_at'


@admin.register(ActivityFeed)
class ActivityFeedAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'title', 'is_public', 'created_at', 'likes_count']
    list_filter = ['activity_type', 'is_public', 'created_at']
    search_fields = ['user__username', 'title', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'likes_count']
    
    def likes_count(self, obj):
        return obj.likes_count
    likes_count.short_description = 'Likes'


@admin.register(DailyCheckIn)
class DailyCheckInAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'mood', 'craving_level', 'energy_level', 'is_shared', 'likes_count']
    list_filter = ['mood', 'craving_level', 'energy_level', 'is_shared', 'date']
    search_fields = ['user__username', 'gratitude', 'challenge', 'goal']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'likes_count']
    
    def likes_count(self, obj):
        return obj.likes_count
    likes_count.short_description = 'Likes'


@admin.register(ActivityComment)
class ActivityCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'content', 'activity__title']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(GroupChallenge)
class GroupChallengeAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'challenge_type', 'group', 'status', 'participant_count',
        'completion_rate', 'start_date', 'end_date', 'creator'
    ]
    list_filter = [
        'status', 'challenge_type', 'is_public', 'enable_leaderboard',
        'allow_pal_system', 'enable_daily_check_in', 'created_at'
    ]
    search_fields = ['title', 'description',
                     'group__name', 'creator__username']
    readonly_fields = ['created_at', 'updated_at',
                       'participant_count', 'completion_rate']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'challenge_type', 'group', 'creator')
        }),
        ('Timeline', {
            'fields': ('duration_days', 'start_date', 'end_date', 'status')
        }),
        ('Challenge Details', {
            'fields': ('daily_goal_description', 'rules_and_guidelines')
        }),
        ('Settings', {
            'fields': (
                'is_public', 'max_participants', 'enable_daily_check_in',
                'enable_leaderboard', 'allow_pal_system'
            )
        }),
        ('Completion', {
            'fields': ('completion_badge_name', 'completion_message')
        }),
        ('Statistics', {
            'fields': ('participant_count', 'completion_rate'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def participant_count(self, obj):
        return obj.participant_count
    participant_count.short_description = 'Participants'

    def completion_rate(self, obj):
        return f"{obj.completion_rate}%"
    completion_rate.short_description = 'Completion Rate'

    actions = ['activate_challenges', 'complete_challenges']

    def activate_challenges(self, request, queryset):
        updated = queryset.filter(status='draft').update(status='upcoming')
        self.message_user(request, f'{updated} challenges were activated.')
    activate_challenges.short_description = "Activate selected challenges"

    def complete_challenges(self, request, queryset):
        updated = queryset.filter(status='active').update(status='completed')
        self.message_user(
            request, f'{updated} challenges were marked as completed.')
    complete_challenges.short_description = "Mark selected challenges as completed"


class ChallengeCheckInInline(admin.TabularInline):
    model = ChallengeCheckIn
    extra = 0
    readonly_fields = ['date', 'created_at']
    fields = [
        'date', 'completed_daily_goal', 'mood', 'progress_note',
        'is_shared_with_group', 'created_at'
    ]


@admin.register(ChallengeParticipant)
class ChallengeParticipantAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'challenge', 'status', 'days_completed', 'current_streak',
        'longest_streak', 'completion_percentage', 'joined_date'
    ]
    list_filter = [
        'status', 'challenge__challenge_type', 'challenge__group',
        'joined_date', 'completion_date'
    ]
    search_fields = [
        'user__username', 'user__email', 'challenge__title',
        'personal_goal', 'motivation_note'
    ]
    readonly_fields = ['joined_date', 'updated_at', 'completion_percentage']

    fieldsets = (
        ('Participation Info', {
            'fields': ('user', 'challenge', 'status', 'joined_date', 'completion_date')
        }),
        ('Progress', {
            'fields': ('days_completed', 'current_streak', 'longest_streak', 'completion_percentage')
        }),
        ('Personal Goals', {
            'fields': ('personal_goal', 'motivation_note')
        }),
        ('Pal System', {
            'fields': ('accountability_partner',)
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    inlines = [ChallengeCheckInInline]

    def completion_percentage(self, obj):
        return f"{obj.completion_percentage}%"
    completion_percentage.short_description = 'Completion %'

    actions = ['mark_completed', 'reset_streak']

    def mark_completed(self, request, queryset):
        updated = queryset.filter(status='active').update(status='completed')
        self.message_user(
            request, f'{updated} participants were marked as completed.')
    mark_completed.short_description = "Mark selected participants as completed"

    def reset_streak(self, request, queryset):
        updated = queryset.update(current_streak=0)
        self.message_user(
            request, f'Reset streaks for {updated} participants.')
    reset_streak.short_description = "Reset current streak for selected participants"


@admin.register(ChallengeCheckIn)
class ChallengeCheckInAdmin(admin.ModelAdmin):
    list_display = [
        'participant', 'date', 'completed_daily_goal', 'mood',
        'is_shared_with_group', 'encouragement_count', 'created_at'
    ]
    list_filter = [
        'completed_daily_goal', 'mood', 'is_shared_with_group',
        'participant__challenge__challenge_type', 'date', 'created_at'
    ]
    search_fields = [
        'participant__user__username', 'participant__challenge__title',
        'progress_note'
    ]
    readonly_fields = ['created_at', 'encouragement_count']

    fieldsets = (
        ('Check-in Info', {
            'fields': ('participant', 'date', 'completed_daily_goal', 'mood')
        }),
        ('Progress Details', {
            'fields': ('progress_note', 'custom_metric_1', 'custom_metric_2')
        }),
        ('Social', {
            'fields': ('is_shared_with_group', 'encouragement_received', 'encouragement_count')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def encouragement_count(self, obj):
        return obj.encouragement_count
    encouragement_count.short_description = 'Encouragements'

    date_hierarchy = 'date'


@admin.register(ChallengeComment)
class ChallengeCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'check_in', 'is_encouragement',
                    'created_at', 'content_preview']
    list_filter = ['is_encouragement', 'created_at']
    search_fields = ['user__username', 'content',
                     'check_in__participant__user__username']
    readonly_fields = ['created_at']

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(ChallengeBadge)
class ChallengeBadgeAdmin(admin.ModelAdmin):
    list_display = [
        'icon', 'name', 'badge_type', 'challenge_type', 'rarity_level',
        'points_value', 'required_completions', 'required_streak_days'
    ]
    list_filter = ['badge_type', 'challenge_type', 'rarity_level']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Badge Info', {
            'fields': ('name', 'description', 'icon', 'badge_type')
        }),
        ('Requirements', {
            'fields': (
                'challenge_type', 'required_completions', 'required_streak_days'
            )
        }),
        ('Rarity & Points', {
            'fields': ('rarity_level', 'points_value')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserChallengeBadge)
class UserChallengeBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'challenge', 'earned_date']
    list_filter = ['badge__badge_type', 'badge__rarity_level', 'earned_date']
    search_fields = ['user__username', 'badge__name', 'challenge__title']
    readonly_fields = ['earned_date']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'badge', 'challenge'
        )


# Payment and Subscription Admin
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'tier', 'status', 'billing_period',
        'current_period_end', 'created_at'
    ]
    list_filter = ['tier', 'status', 'billing_period', 'created_at']
    search_fields = [
        'user__username', 'user__email',
        'stripe_customer_id', 'stripe_subscription_id'
    ]
    readonly_fields = ['created_at', 'updated_at', 'stripe_customer_id', 'stripe_subscription_id']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('User & Plan', {
            'fields': ('user', 'tier', 'status', 'billing_period')
        }),
        ('Stripe Information', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id', 'stripe_price_id')
        }),
        ('Billing Dates', {
            'fields': ('current_period_start', 'current_period_end', 'trial_end', 'canceled_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'tier', 'billing_period', 'price',
        'currency', 'is_active', 'sort_order'
    ]
    list_filter = ['tier', 'billing_period', 'is_active', 'currency']
    search_fields = ['name', 'description', 'stripe_price_id', 'stripe_product_id']
    ordering = ['sort_order', 'tier', 'billing_period']

    fieldsets = (
        ('Plan Details', {
            'fields': ('name', 'tier', 'billing_period', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'currency')
        }),
        ('Stripe Integration', {
            'fields': ('stripe_price_id', 'stripe_product_id')
        }),
        ('Features', {
            'fields': ('features',),
            'description': 'Enter features as a JSON array, e.g., ["Feature 1", "Feature 2"]'
        }),
        ('Display Settings', {
            'fields': ('is_active', 'sort_order')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'transaction_type', 'status', 'amount',
        'currency', 'payment_method_brand', 'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'currency', 'created_at']
    search_fields = [
        'user__username', 'user__email', 'stripe_payment_intent_id',
        'stripe_charge_id', 'stripe_invoice_id', 'description'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'stripe_payment_intent_id',
        'stripe_charge_id', 'stripe_invoice_id'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Transaction Info', {
            'fields': ('user', 'subscription', 'transaction_type', 'status')
        }),
        ('Amount', {
            'fields': ('amount', 'currency', 'description')
        }),
        ('Payment Method', {
            'fields': ('payment_method_brand', 'payment_method_last4')
        }),
        ('Stripe Information', {
            'fields': ('stripe_payment_intent_id', 'stripe_charge_id', 'stripe_invoice_id')
        }),
        ('Additional Data', {
            'fields': ('metadata', 'failure_reason'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'card_brand', 'card_last4',
        'card_exp_month', 'card_exp_year', 'is_default', 'is_active'
    ]
    list_filter = ['card_brand', 'is_default', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'stripe_payment_method_id', 'card_last4']
    readonly_fields = ['created_at', 'updated_at', 'stripe_payment_method_id']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Card Details', {
            'fields': ('card_brand', 'card_last4', 'card_exp_month', 'card_exp_year')
        }),
        ('Stripe Information', {
            'fields': ('stripe_payment_method_id',)
        }),
        ('Status', {
            'fields': ('is_default', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'user', 'status', 'amount_due',
        'amount_paid', 'currency', 'invoice_date', 'paid_at'
    ]
    list_filter = ['status', 'currency', 'invoice_date', 'paid_at']
    search_fields = [
        'user__username', 'user__email', 'invoice_number',
        'stripe_invoice_id', 'description'
    ]
    readonly_fields = ['created_at', 'updated_at', 'stripe_invoice_id', 'stripe_invoice_pdf']
    date_hierarchy = 'invoice_date'

    fieldsets = (
        ('Invoice Info', {
            'fields': ('user', 'subscription', 'invoice_number', 'status')
        }),
        ('Amounts', {
            'fields': ('amount_due', 'amount_paid', 'currency')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date', 'paid_at')
        }),
        ('Stripe Information', {
            'fields': ('stripe_invoice_id', 'stripe_invoice_pdf')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Register the custom user admin
admin.site.register(User, CustomUserAdmin)