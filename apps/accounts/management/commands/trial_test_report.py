"""Results of the card-trial vs. no-card-trial A/B test.

    python manage.py trial_test_report
"""
from django.core.management.base import BaseCommand, CommandError

from apps.accounts import trial_experiment as t

LABELS = {
    t.STARTED_TRIAL: 'Started a trial',
    t.BEGAN_CHECKOUT: 'Opened checkout',
    t.SUBSCRIBED: 'Subscribed',
    t.CONVERTED_PAID: 'Paid (first real payment)',
}


class Command(BaseCommand):
    help = 'Show results for the premium_trial_type A/B test.'

    def handle(self, *args, **opts):
        r = t.report()
        if r is None:
            raise CommandError('The test has not been created. Run: python manage.py init_trial_test')
        status = 'RUNNING' if r['test'].is_running() else 'STOPPED'
        self.stdout.write(f"{t.TEST_NAME} ({status}, started {r['test'].start_date:%Y-%m-%d})\n")
        c, v = r['rows'][t.CONTROL], r['rows'][t.VARIANT]
        self.stdout.write(f"{'':28}{'card trial':>18}{'no-card trial':>18}")
        self.stdout.write(f"{'Members in test':28}{c['users']:>18}{v['users']:>18}")
        for e in t.FUNNEL:
            self.stdout.write(f"{LABELS[e]:28}{self._cell(c, e):>18}{self._cell(v, e):>18}")
        self.stdout.write(f"{'Active in week 2':28}{self._week2(c):>18}{self._week2(v):>18}")
        self.stdout.write('')
        if not r['enough_data']:
            self.stdout.write('Too early to call: wait for at least 100 members in each group.')
        elif r['significant']:
            better = t.VARIANT if v['rates'][t.CONVERTED_PAID] > c['rates'][t.CONVERTED_PAID] else t.CONTROL
            self.stdout.write(self.style.SUCCESS(
                f"Paid conversion differs significantly (p={r['p_paid']:.3f}); {better} is ahead. "
                f"Check week-2 retention before switching everyone."))
        else:
            p = f"p={r['p_paid']:.2f}" if r['p_paid'] is not None else 'no payments yet'
            self.stdout.write(f'No significant difference in paid conversion yet ({p}).')
        self.stdout.write('Apple purchases count as "Subscribed"; "Paid" counts Stripe payments only.')

    @staticmethod
    def _cell(row, event):
        return f"{row['events'][event]} ({row['rates'][event] * 100:.1f}%)"

    @staticmethod
    def _week2(row):
        if not row['week2_eligible']:
            return 'n/a yet'
        return f"{row['week2_retained']}/{row['week2_eligible']} ({row['week2_rate'] * 100:.0f}%)"
