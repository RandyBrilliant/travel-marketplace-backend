from celery import shared_task
from django.template.loader import render_to_string
from django.conf import settings
from account.tasks import send_email_with_backend_detection


@shared_task
def send_booking_confirmation_emails(booking_id):
    """
    Send booking confirmation emails to customer/reseller, admin, and supplier.
    
    Args:
        booking_id: The ID of the booking that was created
    """
    from travel.models import Booking
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        booking = Booking.objects.select_related(
            'reseller__user',
            'customer__user',
            'tour_date__package__supplier'
        ).get(id=booking_id)
    except Booking.DoesNotExist:
        return f"Booking with ID {booking_id} does not exist"
    
    # Get the user who made the booking
    booked_by_user = booking.reseller.user if booking.reseller else booking.customer.user
    tour_package = booking.tour_date.package
    
    # Common context for all emails
    common_context = {
        'booking_number': booking.booking_number,
        'tour_package_name': tour_package.name,
        'departure_date': booking.tour_date.departure_date.strftime('%d %B %Y'),
        'seats_booked': booking.seats_booked,
        'total_amount_formatted': f"Rp {booking.total_amount:,.0f}",
        'company_name': getattr(settings, 'COMPANY_NAME', 'GoHoliday Travel Marketplace'),
        'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Indonesia'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@goholiday.id'),
        'support_phone': getattr(settings, 'SUPPORT_PHONE', '+62 xxx xxxx xxxx'),
    }
    
    # Add promo code info if used
    if booking.promo_code:
        common_context['promo_code'] = booking.promo_code
        common_context['promo_discount_formatted'] = f"Rp {booking.promo_discount_amount:,.0f}"
    
    # Calculate platform fee and supplier earnings
    platform_fee = booking.platform_fee if hasattr(booking, 'platform_fee') else 50000
    supplier_earnings = booking.total_amount - platform_fee
    
    common_context['platform_fee_formatted'] = f"Rp {platform_fee:,.0f}"
    common_context['supplier_earnings_formatted'] = f"Rp {supplier_earnings:,.0f}"
    
    # 1. Send confirmation email to customer/reseller
    customer_context = {
        **common_context,
        'customer_name': booked_by_user.get_full_name() or booked_by_user.email,
        'site_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'booking_id': booking.id,
    }
    
    customer_html = render_to_string('travel/booking_confirmation.html', customer_context)
    send_email_with_backend_detection(
        subject=f"Konfirmasi Pemesanan #{common_context['booking_number']}",
        plain_message=f"Pemesanan Anda untuk {tour_package.name} telah berhasil dibuat.",
        html_message=customer_html,
        recipient_list=[booked_by_user.email],
        email_type="booking_confirmation"
    )
    
    # 2. Send notification email to admin
    booked_by_type = "Customer" if booking.customer else "Reseller"
    
    admin_context = {
        **common_context,
        'booked_by_name': booked_by_user.get_full_name() or booked_by_user.email,
        'booked_by_type': booked_by_type,
        'booked_by_email': booked_by_user.email,
        'supplier_name': tour_package.supplier.get_full_name() or tour_package.supplier.email,
        'admin_url': getattr(settings, 'ADMIN_FRONTEND_URL', 'https://goholiday.id/admin'),
        'booking_id': booking.id,
    }
    
    admin_html = render_to_string('travel/booking_notification_admin.html', admin_context)
    
    # Get all admin emails
    admin_emails = list(User.objects.filter(role='admin', is_active=True).values_list('email', flat=True))
    
    if admin_emails:
        send_email_with_backend_detection(
            subject=f"Pemesanan Baru #{common_context['booking_number']} - {tour_package.name}",
            plain_message=f"Pemesanan baru dari {booked_by_user.get_full_name() or booked_by_user.email}",
            html_message=admin_html,
            recipient_list=admin_emails,
            email_type="booking_admin_notification"
        )
    
    # 3. Send notification email to supplier
    supplier_context = {
        **common_context,
        'supplier_name': tour_package.supplier.get_full_name() or tour_package.supplier.email,
        'booked_by_name': booked_by_user.get_full_name() or booked_by_user.email,
        'booked_by_email': booked_by_user.email,
        'supplier_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'booking_id': booking.id,
    }
    
    supplier_html = render_to_string('travel/booking_notification_supplier.html', supplier_context)
    send_email_with_backend_detection(
        subject=f"Pemesanan Baru untuk {tour_package.name}",
        plain_message=f"Anda mendapat pemesanan baru untuk paket {tour_package.name}",
        html_message=supplier_html,
        recipient_list=[tour_package.supplier.email],
        email_type="booking_supplier_notification"
    )
    
    return f"Booking confirmation emails sent for booking ID {booking_id}"
