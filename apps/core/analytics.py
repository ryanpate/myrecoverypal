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


def queue_one_off_purchase(request, transaction_id, amount_cents, item_id, item_name):
    """Queue a GA4 `purchase` for a single one-off item.

    transaction_id dedupes the purchase in GA4 and `items` fills the item
    reports; without them a sale shows as Transaction ID "(not set)".
    """
    price = amount_cents / 100
    queue_ga_event(request, 'purchase', transaction_id=transaction_id, value=price,
                   currency='USD',
                   items=[{'item_id': item_id, 'item_name': item_name,
                           'price': price, 'quantity': 1}])


def queue_begin_checkout(request, amount_cents, item_id, item_name, **item_extra):
    """Queue a GA4 `begin_checkout` before a server-side redirect to Stripe.

    The redirect renders no page of ours, so the event fires on the next one
    the visitor sees: the success page, or wherever they land after backing
    out. A visitor who closes the tab on Stripe and never returns is missed.
    """
    price = amount_cents / 100
    queue_ga_event(request, 'begin_checkout', value=price, currency='USD',
                   items=[{'item_id': item_id, 'item_name': item_name,
                           'price': price, 'quantity': 1, **item_extra}])


def pop_ga_events(request):
    """Return and clear the queued events."""
    session = getattr(request, 'session', None)
    if not session:
        return []
    return session.pop(SESSION_KEY, []) or []
