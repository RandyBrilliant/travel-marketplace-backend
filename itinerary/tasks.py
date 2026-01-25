from celery import shared_task
from django.utils import timezone
from .models import ItineraryTransaction, ItineraryTransactionStatus
import logging

logger = logging.getLogger(__name__)


@shared_task
def expire_old_itinerary_transactions():
    """
    Check for ACTIVE itinerary transactions that have passed their expiry date
    and update their status to EXPIRED.
    
    This task should be run periodically (e.g., daily or hourly).
    """
    now = timezone.now()
    
    # Find ACTIVE transactions where expires_at has passed
    expired_transactions = ItineraryTransaction.objects.filter(
        status=ItineraryTransactionStatus.ACTIVE,
        expires_at__lt=now
    )
    
    count = expired_transactions.count()
    
    if count > 0:
        # Update all expired transactions to EXPIRED status
        expired_transactions.update(
            status=ItineraryTransactionStatus.EXPIRED
        )
        logger.info(f"Expired {count} itinerary transaction(s)")
    else:
        logger.info("No itinerary transactions to expire")
    
    return {
        'expired_count': count,
        'timestamp': now.isoformat()
    }
