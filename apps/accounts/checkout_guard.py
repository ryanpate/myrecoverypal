"""One Stripe Checkout Session per click.

The one-off checkouts (gift, keepsake, medallion pack, court report) create an
order row and then a Checkout Session. A double-click or a retried POST would
otherwise leave two of each. `once_per_minute` lets the first request through
and sends an identical repeat to the same Stripe page.
"""
import hashlib
import json
import time
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse

PENDING = 'pending'
WINDOW_SECONDS = 60
WAIT_SECONDS = 5


def _key(kind, request):
    if request.user.is_authenticated:
        who = f'u{request.user.pk}'
    else:
        who = request.COOKIES.get('csrftoken') or request.META.get('REMOTE_ADDR', '')
    form = sorted((k, v) for k, v in request.POST.lists() if k != 'csrfmiddlewaretoken')
    digest = hashlib.sha256(json.dumps([kind, who, form]).encode()).hexdigest()
    return f'checkout_once:{digest}'


def once_per_minute(kind):
    """Decorate a view (first argument `request`) that answers a successful
    checkout start with a 303 to Stripe. Anything else it returns (an error
    redirect, a free unlock) is not remembered, so the visitor can try again."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            key = _key(kind, request)
            if not cache.add(key, PENDING, WINDOW_SECONDS):
                # An identical request got here first. Wait for its Stripe URL.
                deadline = time.monotonic() + WAIT_SECONDS
                while True:
                    url = cache.get(key)
                    if url and url != PENDING:
                        response = HttpResponse(status=303)
                        response['Location'] = url
                        return response
                    if url is None or time.monotonic() > deadline:
                        break  # the first one failed or is stuck: carry on normally
                    time.sleep(0.2)
            try:
                response = view(request, *args, **kwargs)
            except Exception:
                cache.delete(key)
                raise
            if response.status_code == 303:
                cache.set(key, response['Location'], WINDOW_SECONDS)
            else:
                cache.delete(key)
            return response
        return wrapper
    return decorator
