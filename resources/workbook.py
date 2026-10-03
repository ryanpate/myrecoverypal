""""My Recovery Workbook": one Premium PDF of a member's own recovery work.

It combines check-in trends, the relapse prevention plan, saved worksheets,
milestones and (opt-in) slips, for a member to bring to a therapist,
counselor, sponsor or IOP. Everything here is the requesting member's own
data. Journal entries are never included: the journal stays private even
from exports like this one.

WeasyPrint is imported lazily (same pattern as apps/accounts/plan_service.py).
"""
from collections import OrderedDict
from datetime import timedelta
from io import BytesIO

from django.db.models import Avg, Count, Q
from django.template.loader import render_to_string
from django.utils import timezone

from .models import WorksheetEntry
from .worksheets import build_sections

# key -> (label, description, included by default)
SECTIONS = OrderedDict([
    ('reasons', ('My reasons & goals', 'Your pledge reason, recovery goals and pledge streak.', True)),
    ('checkins', ('Check-in trends', 'Mood, craving and energy averages, weekly charts and gratitude highlights.', True)),
    ('plan', ('Relapse prevention plan', 'Triggers, warning signs, coping strategies and support contacts.', True)),
    ('worksheets', ('Saved worksheets', 'Every worksheet you saved in this period, with your answers.', True)),
    ('milestones', ('Milestones', 'The milestones you recorded.', True)),
    ('slips', ('Slips', 'Any slips you logged, with notes and triggers. Off by default.', False)),
])

# Choice value -> (label, days back or None for all time)
RANGES = OrderedDict([
    ('30', ('Last 30 days', 30)),
    ('90', ('Last 90 days', 90)),
    ('365', ('Last 12 months', 365)),
    ('all', ('All time', None)),
])
DEFAULT_RANGE = '90'

GRATITUDE_HIGHLIGHTS = 8
CHART_GAP_DAYS = 21


def default_sections():
    return [k for k, (_, _, on) in SECTIONS.items() if on]


def parse_options(params):
    """(sections, range_key) from GET params; unknown values are ignored.

    `sections` is a list of keys in SECTIONS order. Nothing selected falls
    back to the defaults, so a bare URL still produces a useful workbook.
    """
    chosen = set(params.getlist('section')) if hasattr(params, 'getlist') else set()
    sections = [k for k in SECTIONS if k in chosen] or default_sections()
    range_key = params.get('range', DEFAULT_RANGE)
    if range_key not in RANGES:
        range_key = DEFAULT_RANGE
    return sections, range_key


def _start_date(range_key):
    days = RANGES[range_key][1]
    if days is None:
        return None
    return timezone.localdate() - timedelta(days=days - 1)


def _date_label(d):
    return f"{d:%b} {d.day}"


def line_chart_svg(points, y_min, y_max, y_labels, color, width=480, height=150):
    """Small inline SVG line chart for WeasyPrint.

    `points` is a list of (date, value), oldest first. Points are spaced by
    date, so a gap of weeks without check-ins shows as a gap. Only numbers
    and formatted dates reach the markup, so it's safe to render unescaped.
    """
    pad_l, pad_r, pad_t, pad_b = 58, 10, 10, 22
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    n = len(points)
    first = points[0][0].toordinal() if points else 0
    span = (points[-1][0].toordinal() - first) if n > 1 else 0

    def x(d):
        return pad_l + (plot_w * (d.toordinal() - first) / span if span else plot_w / 2)

    def y(v):
        return pad_t + plot_h * (1 - (v - y_min) / (y_max - y_min))

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">']
    for value, label in y_labels:
        yy = y(value)
        parts.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width - pad_r}" y2="{yy:.1f}" '
                     f'stroke="#e2e8f0" stroke-width="0.75"/>')
        parts.append(f'<text x="{pad_l - 5}" y="{yy + 3:.1f}" font-size="7.5" fill="#667" '
                     f'text-anchor="end">{label}</text>')
    # Break the line across gaps of more than three weeks without check-ins.
    runs, run = [], []
    for d, v in points:
        if run and (d - run[-1][0]).days > CHART_GAP_DAYS:
            runs.append(run)
            run = []
        run.append((d, v))
    if run:
        runs.append(run)
    for run in runs:
        if len(run) > 1:
            coords = ' '.join(f'{x(d):.1f},{y(v):.1f}' for d, v in run)
            parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>')
    for d, v in points:
        parts.append(f'<circle cx="{x(d):.1f}" cy="{y(v):.1f}" r="2.6" fill="{color}"/>')
    # Label the first and last weeks only; more would collide.
    if points:
        parts.append(f'<text x="{x(points[0][0]):.1f}" y="{height - 6}" font-size="7.5" fill="#667" '
                     f'text-anchor="start">{_date_label(points[0][0])}</text>')
    if n > 1:
        parts.append(f'<text x="{x(points[-1][0]):.1f}" y="{height - 6}" font-size="7.5" fill="#667" '
                     f'text-anchor="end">{_date_label(points[-1][0])}</text>')
    parts.append('</svg>')
    return ''.join(parts)


def _weekly_averages(checkins):
    """[(week_start, avg_mood, avg_craving, avg_energy)] oldest first."""
    weeks = OrderedDict()
    for c in sorted(checkins, key=lambda c: c.date):
        start = c.date - timedelta(days=c.date.weekday())
        weeks.setdefault(start, []).append(c)
    out = []
    for start, rows in weeks.items():
        n = len(rows)
        out.append((start,
                    sum(r.mood for r in rows) / n,
                    sum(r.craving_level for r in rows) / n,
                    sum(r.energy_level for r in rows) / n))
    return out


def _checkins_context(user, start):
    qs = user.daily_checkins.all()
    if start:
        qs = qs.filter(date__gte=start)
    stats = qs.aggregate(
        count=Count('id'), avg_mood=Avg('mood'), avg_craving=Avg('craving_level'),
        avg_energy=Avg('energy_level'),
        tough_days=Count('id', filter=Q(mood__lte=2) | Q(craving_level__gte=3)),
    )
    checkins = list(qs.only('date', 'mood', 'craving_level', 'energy_level'))
    weekly = _weekly_averages(checkins)
    charts = None
    if len(weekly) >= 2:
        charts = {
            'mood': line_chart_svg(
                [(w[0], w[1]) for w in weekly], 1, 6,
                [(1, 'Struggling'), (3, 'Okay'), (6, 'Amazing')], '#1e4d8b'),
            'craving': line_chart_svg(
                [(w[0], w[2]) for w in weekly], 0, 4,
                [(0, 'None'), (2, 'Moderate'), (4, 'Intense')], '#c2410c'),
        }
    gratitude = list(
        qs.exclude(gratitude='').order_by('-date').values('date', 'gratitude')[:GRATITUDE_HIGHLIGHTS])
    return {
        'stats': stats,
        'weekly': weekly,
        'charts': charts,
        'gratitude': gratitude,
        'streak': user.get_checkin_streak(),
    }


def build_workbook_context(user, sections, range_key):
    start = _start_date(range_key)
    ctx = {
        'owner': user,
        'sections': sections,
        'range_label': RANGES[range_key][0],
        'start': start,
        'today': timezone.localdate(),
        'generated': timezone.now(),
        'days_sober': user.get_days_sober() if user.sobriety_date else None,
        'scale_points': range(11),
        'filled': True,
    }
    if 'reasons' in sections:
        pledges = user.daily_pledges.all()
        if start:
            pledges = pledges.filter(date__gte=start)
        ctx['pledge_count'] = pledges.count()
        ctx['pledge_streak'] = user.get_pledge_streak()
    if 'checkins' in sections:
        ctx['checkins'] = _checkins_context(user, start)
    if 'plan' in sections:
        from apps.accounts.plan_models import RelapsePreventionPlan
        # filter().first(): exporting must not create an empty plan row.
        ctx['plan'] = RelapsePreventionPlan.objects.filter(user=user).first()
    if 'worksheets' in sections:
        entries = WorksheetEntry.objects.filter(user=user).order_by('created_at')
        if start:
            entries = entries.filter(created_at__date__gte=start)
        ctx['worksheet_entries'] = [
            {'entry': e, 'worksheet': e.worksheet,
             'sections': build_sections(e.worksheet, e.data)}
            for e in entries if e.worksheet is not None
        ]
    if 'milestones' in sections:
        milestones = user.milestones.all()
        if start:
            milestones = milestones.filter(date_achieved__gte=start)
        ctx['milestones'] = list(milestones)
    if 'slips' in sections:
        slips = user.relapse_logs.all()
        if start:
            slips = slips.filter(relapse_date__gte=start)
        ctx['slips'] = list(slips)
    return ctx


def render_workbook_html(user, sections, range_key):
    return render_to_string(
        'resources/workbook/pdf.html', build_workbook_context(user, sections, range_key))


def render_workbook_pdf(user, sections, range_key):
    from weasyprint import HTML

    buf = BytesIO()
    HTML(string=render_workbook_html(user, sections, range_key)).write_pdf(target=buf)
    return buf.getvalue()


def section_counts(user):
    """Rough all-time counts shown next to each checkbox on the builder."""
    from apps.accounts.plan_models import RelapsePreventionPlan
    plan = RelapsePreventionPlan.objects.filter(user=user).first()
    return {
        'reasons': 1 if (user.pledge_reason or user.recovery_goals) else 0,
        'checkins': user.daily_checkins.count(),
        'plan': plan.filled_section_count if plan else 0,
        'worksheets': WorksheetEntry.objects.filter(user=user).count(),
        'milestones': user.milestones.count(),
        'slips': user.relapse_logs.count(),
    }
