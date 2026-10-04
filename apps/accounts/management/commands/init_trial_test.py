"""Start (or stop) the card-trial vs. no-card-trial A/B test.

    python manage.py init_trial_test          # create + start: new signups split 50/50
    python manage.py init_trial_test --stop   # stop assigning; everyone gets the card trial again

Stopping never touches anyone already in a trial. See apps/accounts/trial_experiment.py.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.trial_experiment import NO_CARD_TRIAL_DAYS, TEST_NAME, setup_test


class Command(BaseCommand):
    help = 'Start or stop the premium_trial_type A/B test.'

    def add_arguments(self, parser):
        parser.add_argument('--stop', action='store_true')

    def handle(self, *args, **opts):
        test = setup_test()
        if opts['stop']:
            test.is_active = False
            test.end_date = timezone.now()
            test.save(update_fields=['is_active', 'end_date'])
            self.stdout.write(self.style.SUCCESS(
                f'Stopped {TEST_NAME}. New signups get the card trial; existing trials run their course.'))
            return
        if not test.is_active or test.end_date:
            test.is_active, test.end_date = True, None
            test.save(update_fields=['is_active', 'end_date'])
        self.stdout.write(self.style.SUCCESS(
            f'{TEST_NAME} is running: new signups split 50/50 between the card trial (control) and '
            f'a {NO_CARD_TRIAL_DAYS}-day no-card trial. Results: python manage.py trial_test_report'))
