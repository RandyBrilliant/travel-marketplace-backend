"""Booking state changes shared by views and Celery tasks."""
from django.db import transaction

from .models import Booking, BookingStatus, SeatSlotStatus


def cancel_booking(booking):
    """
    Cancel a booking: mark it CANCELLED, drop its commissions, release its
    seats and wipe the previous passengers' details (passport files are
    deleted after the transaction commits).

    Returns False (and changes nothing) if the booking is no longer PENDING,
    e.g. it was confirmed or cancelled by someone else in the meantime.
    """
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if booking.status != BookingStatus.PENDING:
            return False

        booking.status = BookingStatus.CANCELLED
        booking.save()

        # Resellers do not earn commission on cancelled bookings.
        booking.commissions.all().delete()

        passport_files = [slot.passport for slot in booking.seat_slots.all() if slot.passport]
        booking.seat_slots.update(
            status=SeatSlotStatus.AVAILABLE,
            booking=None,
            passenger_name="",
            passport=None,
            visa_required=False,
            special_requests="",
        )

        def _delete_passport_files():
            for passport in passport_files:
                passport.delete(save=False)

        transaction.on_commit(_delete_passport_files)
    return True
