"""One-time $9.99 court reports for people without the Court subscription."""
import logging

from django.db import transaction
from django.utils import timezone

from .court_models import CourtReportPurchase
from .court_service import generate_court_report

logger = logging.getLogger(__name__)

SINGLE_REPORT_PRICE_CENTS = 999
COURT_REPORT_KIND = 'court_report'


def fulfil_court_report_session(session):
    """Generate the paid-for report exactly once (success page and webhook both call this)."""
    metadata = session.get('metadata') or {}
    if metadata.get('kind') != COURT_REPORT_KIND or session.get('payment_status') != 'paid':
        return None
    with transaction.atomic():
        try:
            purchase = CourtReportPurchase.objects.select_for_update().select_related('user').get(
                pk=metadata.get('purchase_id'))
        except (CourtReportPurchase.DoesNotExist, ValueError, TypeError):
            logger.error('Court report session %s has no matching purchase', session.get('id'))
            return None
        if purchase.status == 'pending':
            purchase.status = 'paid'
            purchase.paid_at = timezone.now()
            purchase.stripe_payment_intent_id = session.get('payment_intent') or ''
        if purchase.status == 'paid' and not purchase.report_id:
            purchase.report = generate_court_report(
                purchase.user, purchase.period_start, purchase.period_end)
        purchase.save()
    return purchase


def refund_court_report(payment_intent_id):
    """Mark a refunded single report. The PDF stays verifiable: a PO may already hold it."""
    if not payment_intent_id:
        return False
    return CourtReportPurchase.objects.filter(
        stripe_payment_intent_id=payment_intent_id).update(status='refunded') > 0
