"""
Django signals for:
1. Automatically optimizing images to WebP format
2. Sending email notifications on booking/payment status changes
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import TourPackage, TourImage, Payment, Booking, BookingStatus, PaymentStatus
from .utils import optimize_image_to_webp


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


@receiver(post_save, sender=TourImage)
def optimize_tour_image(sender, instance, created, **kwargs):
    """Optimize image when TourImage is saved."""
    _optimize_image_field(instance, 'image')


@receiver(post_save, sender=Payment)
def optimize_payment_proof_image(sender, instance, created, **kwargs):
    """Optimize proof_image when Payment is saved."""
    _optimize_image_field(instance, 'proof_image')


# ============================================================================
# Email Notification Signals
# ============================================================================

@receiver(pre_save, sender=Booking)
def track_booking_status_change(sender, instance, **kwargs):
    """
    Track booking status changes using pre_save to compare old vs new status.
    Store the old status in instance._old_status for use in post_save.
    """
    if instance.pk:  # Only for existing bookings (updates)
        try:
            old_booking = Booking.objects.get(pk=instance.pk)
            instance._old_status = old_booking.status
        except Booking.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Booking)
def send_booking_status_change_notifications(sender, instance, created, **kwargs):
    """
    Send email notifications when booking status changes to CONFIRMED.
    Notifies customer/reseller with payment request and admin with confirmation notice.
    """
    if not created and hasattr(instance, '_old_status'):
        # Check if status changed to CONFIRMED
        if instance._old_status != BookingStatus.CONFIRMED and instance.status == BookingStatus.CONFIRMED:
            from .tasks import send_booking_confirmed_emails
            send_booking_confirmed_emails.delay(instance.id)


@receiver(pre_save, sender=Payment)
def track_payment_status_change(sender, instance, **kwargs):
    """
    Track payment status changes using pre_save to compare old vs new status.
    Store the old status in instance._old_status for use in post_save.
    """
    if instance.pk:  # Only for existing payments (updates)
        try:
            old_payment = Payment.objects.get(pk=instance.pk)
            instance._old_status = old_payment.status
        except Payment.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Payment)
def send_payment_notifications(sender, instance, created, **kwargs):
    """
    Send email notifications for payment events:
    - When payment is created: notify admin to review
    - When payment status changes to APPROVED: notify customer/reseller and supplier
    """
    # 1. Payment created - notify admin
    if created:
        from .tasks import send_payment_created_emails
        send_payment_created_emails.delay(instance.id)
    
    # 2. Payment approved - notify customer/reseller and supplier
    elif hasattr(instance, '_old_status'):
        if instance._old_status != PaymentStatus.APPROVED and instance.status == PaymentStatus.APPROVED:
            from .tasks import send_payment_approved_emails
            send_payment_approved_emails.delay(instance.id)

