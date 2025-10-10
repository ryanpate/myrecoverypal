from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_invite_email_task(self, invite_code_id):
    """
    Celery task to send invite email asynchronously
    """
    from .invite_models import InviteCode
    
    try:
        invite_code = InviteCode.objects.get(id=invite_code_id)
        success = invite_code.send_invite_email()
        
        if success:
            logger.info(f"Successfully sent invite email to {invite_code.email}")
        else:
            logger.warning(f"Failed to send invite email to {invite_code.email}")
            
        return success
    except InviteCode.DoesNotExist:
        logger.error(f"InviteCode {invite_code_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error sending invite email: {e}")
        # Retry after 60 seconds
        raise self.retry(exc=e, countdown=60)