"""
Django signals for:
1. Automatically optimizing itinerary images to WebP format
2. Sending email notifications on transaction/payment status changes
3. Auto-activating transactions when payment is approved
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import ItineraryCard, ItineraryBoard, ItineraryTransaction, ItineraryTransactionStatus
from travel.utils import optimize_image_to_webp


# Flag to prevent infinite recursion
_optimizing = set()


def _optimize_image_field(instance, field_name):
    """Helper function to optimize an image field without causing recursion."""
    # Skip if instance doesn't have a primary key yet (new instance)
    if not instance.pk:
        return
    
    # Create a unique identifier for this instance and field
    instance_id = f"{instance.__class__.__name__}_{instance.pk}_{field_name}"
    
    # Skip if already optimizing this instance
    if instance_id in _optimizing:
        return
    
    image_field = getattr(instance, field_name, None)
    if image_field and image_field.name:
        # Check if already WebP to avoid unnecessary processing
        if not image_field.name.lower().endswith('.webp'):
            _optimizing.add(instance_id)
            try:
                if optimize_image_to_webp(image_field):
                    # Save the instance with the optimized image
                    # Using update_fields to only save this field
                    instance.save(update_fields=[field_name])
            finally:
                _optimizing.discard(instance_id)


@receiver(post_save, sender=ItineraryCard)
def optimize_card_cover_image(sender, instance, created, **kwargs):
    """Optimize cover image when ItineraryCard is saved."""
    _optimize_image_field(instance, 'cover_image')


@receiver(post_save, sender=ItineraryBoard)
def optimize_board_package_image(sender, instance, created, **kwargs):
    """Optimize package image when ItineraryBoard is saved."""
    _optimize_image_field(instance, 'package_image')


# ============================================================================
# Email Notification Signals for ItineraryTransaction
# ============================================================================

@receiver(pre_save, sender=ItineraryTransaction)
def track_itinerary_payment_changes(sender, instance, **kwargs):
    """
    Track payment-related changes using pre_save.
    Store old values for comparison in post_save.
    """
    if instance.pk:  # Only for existing transactions (updates)
        try:
            old_transaction = ItineraryTransaction.objects.get(pk=instance.pk)
            instance._old_payment_status = old_transaction.payment_status
            instance._old_payment_proof = old_transaction.payment_proof_image
            instance._has_old_payment_proof = bool(old_transaction.payment_proof_image)
        except ItineraryTransaction.DoesNotExist:
            instance._old_payment_status = None
            instance._old_payment_proof = None
            instance._has_old_payment_proof = False
    else:
        instance._old_payment_status = None
        instance._old_payment_proof = None
        instance._has_old_payment_proof = False


@receiver(post_save, sender=ItineraryTransaction)
def handle_itinerary_payment_notifications(sender, instance, created, **kwargs):
    """
    Handle email notifications and auto-activation for itinerary transactions.
    
    Events handled:
    1. Payment uploaded (proof image added) → Email admin
    2. Payment approved → Auto-activate + Email customer & supplier
    3. Payment rejected → Email customer
    """
    # Skip if this is being called from within another signal to prevent recursion
    if hasattr(instance, '_skip_payment_signals'):
        return
    
    if not created and hasattr(instance, '_old_payment_status'):
        # 1. Payment proof uploaded (new proof added when there wasn't one before)
        has_new_payment_proof = bool(instance.payment_proof_image)
        payment_just_uploaded = (
            not instance._has_old_payment_proof and 
            has_new_payment_proof and 
            instance.payment_amount and 
            instance.payment_transfer_date
        )
        
        if payment_just_uploaded:
            from .tasks import send_itinerary_payment_uploaded_emails
            send_itinerary_payment_uploaded_emails.delay(instance.id)
        
        # 2. Payment approved → Auto-activate and send emails
        if instance._old_payment_status != 'APPROVED' and instance.payment_status == 'APPROVED':
            # Auto-activate transaction if not already active
            if instance.status == ItineraryTransactionStatus.PENDING:
                # Set the skip flag to prevent recursion in post_save signal
                instance._skip_payment_signals = True
                try:
                    # Use the model's activate() method which correctly sets
                    # expires_at to end-of-day (23:59:59) via time(23, 59, 59).
                    # Previously this block manually used timezone.datetime.min.time()
                    # which resolves to midnight (00:00:00), causing expires_at to land
                    # at the very START of (arrival_date + 2 days). When arrival_date
                    # is in the past, expires_at ends up already expired, so Celery's
                    # expire_old_itinerary_transactions task immediately flips the status
                    # back to EXPIRED and customers lose access right after approval.
                    instance.activate()
                finally:
                    # Always remove the flag even if activate() raises an exception
                    if hasattr(instance, '_skip_payment_signals'):
                        delattr(instance, '_skip_payment_signals')
            
            # Send approval emails
            from .tasks import send_itinerary_payment_approved_emails
            send_itinerary_payment_approved_emails.delay(instance.id)
        
        # 3. Payment rejected → Send rejection email
        elif instance._old_payment_status != 'REJECTED' and instance.payment_status == 'REJECTED':
            from .tasks import send_itinerary_payment_rejected_emails
            send_itinerary_payment_rejected_emails.delay(instance.id)

