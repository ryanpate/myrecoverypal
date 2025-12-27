"""
A/B Testing Framework for MyRecoveryPal

Simple but effective A/B testing system focused on onboarding optimization.
Tracks variant assignments, conversions, and provides analytics.

Usage:
    from apps.accounts.ab_testing import ABTestingService

    # Assign user to a variant
    variant = ABTestingService.get_variant(user, 'onboarding_flow')

    # Track conversion
    ABTestingService.track_conversion(user, 'onboarding_flow', 'completed_onboarding')

    # Get test results
    results = ABTestingService.get_test_results('onboarding_flow')
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
import random
import hashlib


class ABTest(models.Model):
    """Defines an A/B test with multiple variants"""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Test status
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    # Traffic allocation (percentage of users to include, 0-100)
    traffic_percentage = models.IntegerField(default=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ab_tests'
        ordering = ['-created_at']

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status})"

    def is_running(self):
        """Check if test is currently running"""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.end_date and now > self.end_date:
            return False
        return now >= self.start_date


class ABTestVariant(models.Model):
    """A variant within an A/B test"""

    test = models.ForeignKey(ABTest, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=50)  # e.g., 'control', 'variant_a', 'variant_b'
    description = models.TextField(blank=True)

    # Weight for random assignment (higher = more likely)
    weight = models.IntegerField(default=1)

    # Variant configuration (JSON for flexibility)
    config = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ab_test_variants'
        unique_together = ['test', 'name']

    def __str__(self):
        return f"{self.test.name}: {self.name}"


class ABTestAssignment(models.Model):
    """Tracks which user is assigned to which variant"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ab_test_assignments'
    )
    test = models.ForeignKey(ABTest, on_delete=models.CASCADE, related_name='assignments')
    variant = models.ForeignKey(ABTestVariant, on_delete=models.CASCADE, related_name='assignments')

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ab_test_assignments'
        unique_together = ['user', 'test']

    def __str__(self):
        return f"{self.user.username} -> {self.variant.name}"


class ABTestConversion(models.Model):
    """Tracks conversion events for A/B tests"""

    CONVERSION_TYPES = [
        ('started_onboarding', 'Started Onboarding'),
        ('completed_step_1', 'Completed Step 1'),
        ('completed_step_2', 'Completed Step 2'),
        ('completed_step_3', 'Completed Step 3'),
        ('completed_step_4', 'Completed Step 4'),
        ('completed_step_5', 'Completed Step 5'),
        ('completed_onboarding', 'Completed Onboarding'),
        ('followed_user', 'Followed a User'),
        ('first_post', 'Made First Post'),
        ('first_checkin', 'First Check-in'),
        ('day_1_return', 'Returned Day 1'),
        ('day_7_return', 'Returned Day 7'),
    ]

    assignment = models.ForeignKey(
        ABTestAssignment,
        on_delete=models.CASCADE,
        related_name='conversions'
    )
    conversion_type = models.CharField(max_length=50, choices=CONVERSION_TYPES)
    converted_at = models.DateTimeField(auto_now_add=True)

    # Optional metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'ab_test_conversions'
        unique_together = ['assignment', 'conversion_type']

    def __str__(self):
        return f"{self.assignment.user.username}: {self.conversion_type}"


class ABTestingService:
    """Service class for A/B testing operations"""

    @classmethod
    def get_variant(cls, user, test_name, create_if_missing=True):
        """
        Get the variant for a user in a specific test.
        If user isn't assigned yet, assigns them randomly.

        Returns: variant name (string) or None if test not running
        """
        # Check if user already has an assignment
        try:
            assignment = ABTestAssignment.objects.select_related('variant').get(
                user=user,
                test__name=test_name
            )
            return assignment.variant.name
        except ABTestAssignment.DoesNotExist:
            pass

        # Get the test
        try:
            test = ABTest.objects.get(name=test_name)
        except ABTest.DoesNotExist:
            return None

        # Check if test is running
        if not test.is_running():
            return None

        # Check traffic percentage (deterministic based on user id)
        if test.traffic_percentage < 100:
            hash_input = f"{user.id}:{test_name}:traffic"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            if (hash_value % 100) >= test.traffic_percentage:
                return None  # User not included in test

        if not create_if_missing:
            return None

        # Assign user to a variant
        variants = list(test.variants.all())
        if not variants:
            return None

        # Weighted random selection (deterministic based on user id)
        hash_input = f"{user.id}:{test_name}:variant"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

        total_weight = sum(v.weight for v in variants)
        selection = hash_value % total_weight

        cumulative = 0
        selected_variant = variants[0]
        for variant in variants:
            cumulative += variant.weight
            if selection < cumulative:
                selected_variant = variant
                break

        # Create assignment
        ABTestAssignment.objects.create(
            user=user,
            test=test,
            variant=selected_variant
        )

        return selected_variant.name

    @classmethod
    def get_variant_config(cls, user, test_name):
        """Get the configuration for a user's variant"""
        try:
            assignment = ABTestAssignment.objects.select_related('variant').get(
                user=user,
                test__name=test_name
            )
            return assignment.variant.config
        except ABTestAssignment.DoesNotExist:
            return {}

    @classmethod
    def track_conversion(cls, user, test_name, conversion_type, metadata=None):
        """
        Track a conversion event for a user in a test.
        Only tracks if user is assigned to a variant.

        Returns: True if tracked, False otherwise
        """
        try:
            assignment = ABTestAssignment.objects.get(
                user=user,
                test__name=test_name
            )
        except ABTestAssignment.DoesNotExist:
            return False

        # Create conversion (ignore if already exists)
        try:
            ABTestConversion.objects.create(
                assignment=assignment,
                conversion_type=conversion_type,
                metadata=metadata or {}
            )
            return True
        except Exception:
            # Already converted
            return False

    @classmethod
    def get_test_results(cls, test_name):
        """
        Get aggregated results for an A/B test.

        Returns dict with variant statistics:
        {
            'variant_name': {
                'total_users': 100,
                'conversions': {
                    'completed_onboarding': {'count': 75, 'rate': 0.75},
                    ...
                }
            }
        }
        """
        try:
            test = ABTest.objects.get(name=test_name)
        except ABTest.DoesNotExist:
            return {}

        results = {}

        for variant in test.variants.all():
            assignments = ABTestAssignment.objects.filter(variant=variant)
            total_users = assignments.count()

            conversions = {}
            for conv_type, conv_label in ABTestConversion.CONVERSION_TYPES:
                count = ABTestConversion.objects.filter(
                    assignment__variant=variant,
                    conversion_type=conv_type
                ).count()

                rate = (count / total_users) if total_users > 0 else 0
                conversions[conv_type] = {
                    'label': conv_label,
                    'count': count,
                    'rate': round(rate, 4),
                    'percentage': round(rate * 100, 1)
                }

            results[variant.name] = {
                'description': variant.description,
                'total_users': total_users,
                'conversions': conversions
            }

        return results

    @classmethod
    def create_onboarding_test(cls):
        """
        Helper to create the default onboarding A/B test.
        Call this once to set up the test.
        """
        test, created = ABTest.objects.get_or_create(
            name='onboarding_flow',
            defaults={
                'description': 'Test different onboarding flows to optimize completion rate',
                'is_active': True,
                'traffic_percentage': 100
            }
        )

        if created:
            # Control: Current 5-step flow
            ABTestVariant.objects.create(
                test=test,
                name='control',
                description='Current 5-step onboarding flow',
                weight=1,
                config={
                    'steps': 5,
                    'show_progress_bar': True,
                    'skip_allowed': False
                }
            )

            # Variant A: 3-step simplified flow
            ABTestVariant.objects.create(
                test=test,
                name='simplified',
                description='Simplified 3-step onboarding (profile, privacy, connect)',
                weight=1,
                config={
                    'steps': 3,
                    'show_progress_bar': True,
                    'skip_allowed': True,
                    'skip_steps': [1, 2]  # Skip recovery stage and interests
                }
            )

            # Variant B: Progressive disclosure
            ABTestVariant.objects.create(
                test=test,
                name='progressive',
                description='Progressive 5-step with ability to skip and complete later',
                weight=1,
                config={
                    'steps': 5,
                    'show_progress_bar': True,
                    'skip_allowed': True,
                    'complete_later_prompt': True
                }
            )

        return test


# Register models for admin
def register_ab_models():
    """Call this from admin.py to register A/B testing models"""
    from django.contrib import admin

    @admin.register(ABTest)
    class ABTestAdmin(admin.ModelAdmin):
        list_display = ['name', 'is_active', 'start_date', 'end_date', 'traffic_percentage']
        list_filter = ['is_active']
        search_fields = ['name', 'description']

    @admin.register(ABTestVariant)
    class ABTestVariantAdmin(admin.ModelAdmin):
        list_display = ['test', 'name', 'weight']
        list_filter = ['test']

    @admin.register(ABTestAssignment)
    class ABTestAssignmentAdmin(admin.ModelAdmin):
        list_display = ['user', 'test', 'variant', 'assigned_at']
        list_filter = ['test', 'variant']
        search_fields = ['user__username', 'user__email']

    @admin.register(ABTestConversion)
    class ABTestConversionAdmin(admin.ModelAdmin):
        list_display = ['assignment', 'conversion_type', 'converted_at']
        list_filter = ['conversion_type', 'assignment__test']
