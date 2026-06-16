# apps/support_services/tasks.py
"""Celery tasks for support services.

Monthly online-meeting refresh: refresh_online_meetings_task (1st of month, 4am UTC).
Re-imports the online subset of the source TSML feed so conference links stay current.
"""
import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,  # 60s, 120s, 240s
    retry_kwargs={'max_retries': 3},
)
def refresh_online_meetings_task(self):
    """Re-import online meetings from the source feed to keep join links fresh.

    The seed command upserts on a namespaced slug, so this refreshes existing
    rows rather than creating duplicates.
    """
    call_command('seed_online_meetings')
    logger.info('Online meetings refresh task complete')
