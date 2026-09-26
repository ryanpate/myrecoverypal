"""Minimal Printify API client for keepsake orders."""
import httpx
from django.conf import settings

BASE_URL = 'https://api.printify.com/v1'


class PrintifyError(Exception):
    pass


def _request(method, path, json=None):
    if not settings.PRINTIFY_API_KEY:
        raise PrintifyError('PRINTIFY_API_KEY is not configured')
    try:
        response = httpx.request(
            method, f'{BASE_URL}/shops/{settings.PRINTIFY_SHOP_ID}/{path}', json=json,
            headers={'Authorization': f'Bearer {settings.PRINTIFY_API_KEY}',
                     'User-Agent': 'MyRecoveryPal'},
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise PrintifyError(f'{method} {path}: {exc}') from exc
    if response.status_code >= 400:
        raise PrintifyError(f'{method} {path}: HTTP {response.status_code} {response.text[:500]}')
    return response.json() if response.content else {}


def create_order(payload):
    """Create an order (it starts on hold). Returns the Printify order id."""
    return _request('POST', 'orders.json', payload)['id']


def get_order(order_id):
    return _request('GET', f'orders/{order_id}.json')


def send_to_production(order_id):
    return _request('POST', f'orders/{order_id}/send_to_production.json', {})


def cancel_order(order_id):
    """Cancel an order that hasn't been paid/sent to production yet."""
    return _request('POST', f'orders/{order_id}/cancel.json', {})


def list_webhooks():
    return _request('GET', 'webhooks.json')


def create_webhook(topic, url, secret):
    return _request('POST', 'webhooks.json', {'topic': topic, 'url': url, 'secret': secret})
