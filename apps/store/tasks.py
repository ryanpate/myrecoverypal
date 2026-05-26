# apps/store/tasks.py
"""Celery tasks for the shop emails.

Friday weekly digest: weekly_shop_digest_task (Fridays 10am UTC)
Daily milestone scan: daily_milestone_celebration_task (Daily 9am UTC)
"""
import logging

from celery import shared_task

from apps.store.email_service import (
    find_users_hitting_milestone_today,
    send_milestone_celebration_email,
    send_weekly_shop_digest,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,  # 30s, 60s, 120s, ...
    retry_kwargs={'max_retries': 3},
)
def weekly_shop_digest_task(self):
    """Send the Friday weekly shop digest to all opted-in users."""
    sent = send_weekly_shop_digest()
    logger.info('Weekly shop digest task: %d emails sent', sent)
    return sent


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_kwargs={'max_retries': 3},
)
def daily_milestone_celebration_task(self):
    """Daily scan for users hitting a milestone today and send each a celebration email."""
    pairs = find_users_hitting_milestone_today()
    sent = 0
    for user, milestone_days in pairs:
        if send_milestone_celebration_email(user, milestone_days):
            sent += 1
    logger.info(
        'Milestone celebration task: %d/%d emails sent',
        sent, len(pairs),
    )
    return sent
