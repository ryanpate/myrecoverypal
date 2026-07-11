# apps/support_services/tasks.py
"""Celery tasks for support services.

Weekly online-meeting sync: refresh_online_meetings_task (Mondays, 4am UTC).
Re-imports every configured TSML feed so conference links stay current and
deactivates meetings that vanished from their source feed.
"""
import logging

from celery import shared_task

from apps.support_services.meeting_sync import sync_all

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,  # 60s, 120s, 240s
    retry_kwargs={'max_retries': 3},
)
def refresh_online_meetings_task(self):
    """Weekly re-sync of online meetings from all configured feeds.

    Per-source failures are isolated inside sync_all (a down feed never
    deactivates its own meetings); sync_all only raises — triggering
    autoretry — when every source fails.
    """
    results = sync_all()
    logger.info('Online meetings sync complete: %s', results)
