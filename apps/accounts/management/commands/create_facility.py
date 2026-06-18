"""Provision a treatment-center facility + a staff login (manual B2B onboarding)."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.accounts.facility_models import Facility, FacilityStaff

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a Facility and attach a staff user (creating the user if needed).'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True)
        parser.add_argument('--staff-email', required=True, dest='staff_email')
        parser.add_argument('--slug', default=None)
        parser.add_argument('--role', default='admin', choices=['admin', 'coordinator'])

    def handle(self, *args, **opts):
        slug = opts['slug'] or slugify(opts['name'])
        facility, created = Facility.objects.get_or_create(
            slug=slug, defaults={'name': opts['name']})
        verb = 'Created' if created else 'Found'
        self.stdout.write(f'{verb} facility: {facility.name} ({facility.slug})')

        email = opts['staff_email']
        user = User.objects.filter(email=email).first()
        if not user:
            username = email.split('@')[0]
            base, i = username, 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'
                i += 1
            user = User.objects.create_user(username=username, email=email)
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.WARNING(
                f'Created staff user {username} ({email}) — send a password reset.'))

        staff, s_created = FacilityStaff.objects.get_or_create(
            facility=facility, user=user, defaults={'role': opts['role']})
        if not s_created:
            raise CommandError('That user is already staff of this facility.')
        self.stdout.write(self.style.SUCCESS(
            f'Attached {user.email} as {staff.role} of {facility.name}.'))
