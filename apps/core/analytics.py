"""Server-queued GA4 events.

GA4 showed `Key events: 0` and `Total revenue: 0` on every row because the
site fired no conversion events at all — only page_view and one
`daily_pledge`. There was no way to tell which pages produced a signup or
a subscription.

Most conversions finish with a redirect (register -> onboarding, Stripe ->
payment_success), so an inline `gtag('event', ...)` in the view's own
template would never render. Queue the event on the session instead; the
`ga_events` context processor pops it onto the next rendered page and
base.html fires it.

Usage:

    from apps.core.analytics import queue_ga_event

    queue_ga_event(request, 'sign_up', method='email')

Events fire once and only once — popping is what clears them.
"""
SESSION_KEY = 'ga_events'

# Cap the queue so a redirect loop or a bug can't grow the session cookie
# without bound. Conversions come in ones and twos; 10 is already generous.
MAX_QUEUED = 10


def queue_ga_event(request, name, **params):
    """Queue a GA4 event to fire on the next page this user renders."""
    session = getattr(request, 'session', None)
    if session is None:
        return
    events = session.get(SESSION_KEY) or []
    if len(events) >= MAX_QUEUED:
        return
    events.append({'name': name, 'params': params})
    session[SESSION_KEY] = events


def pop_ga_events(request):
    """Return and clear the queued events."""
    session = getattr(request, 'session', None)
    if not session:
        return []
    return session.pop(SESSION_KEY, []) or []
