from celery import shared_task
from django.template.loader import render_to_string
from django.conf import settings
from account.tasks import send_email_with_backend_detection
from account.models import UserRole


@shared_task
def send_booking_creation_emails(booking_id):
    """
    Send booking creation emails to customer/reseller and supplier ONLY.
    Admin will be notified when the booking is confirmed.
    
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
            'tour_date__package__supplier__user'
        ).get(id=booking_id)
    except Booking.DoesNotExist:
        return f"Booking with ID {booking_id} does not exist"
    
    # Get the user who made the booking
    if booking.reseller:
        booked_by_user = booking.reseller.user
    elif booking.customer:
        booked_by_user = booking.customer.user
    else:
        return f"Booking {booking_id} has no reseller or customer associated"
    
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
    
    # 2. Send notification email to supplier
    supplier_context = {
        **common_context,
        'supplier_name': tour_package.supplier.user.get_full_name() or tour_package.supplier.user.email,
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
        recipient_list=[tour_package.supplier.user.email],
        email_type="booking_supplier_notification"
    )
    
    return f"Booking creation emails sent for booking ID {booking_id}"


@shared_task
def send_booking_confirmed_emails(booking_id):
    """
    Send emails when booking status changes to CONFIRMED.
    - Customer/Reseller: Payment request with link to make payment
    - Admin: Notification about booking confirmation
    
    Args:
        booking_id: The ID of the booking that was confirmed
    """
    from travel.models import Booking
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        booking = Booking.objects.select_related(
            'reseller__user',
            'customer__user',
            'tour_date__package__supplier__user'
        ).get(id=booking_id)
    except Booking.DoesNotExist:
        return f"Booking with ID {booking_id} does not exist"
    
    # Get the user who made the booking
    if booking.reseller:
        booked_by_user = booking.reseller.user
        booked_by_type = "Reseller"
    elif booking.customer:
        booked_by_user = booking.customer.user
        booked_by_type = "Customer"
    else:
        return f"Booking {booking_id} has no reseller or customer associated"
    
    tour_package = booking.tour_date.package
    
    # Common context
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
    
    # 1. Send payment request email to customer/reseller
    customer_context = {
        **common_context,
        'customer_name': booked_by_user.get_full_name() or booked_by_user.email,
        'site_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'booking_id': booking.id,
        'payment_url': f"{getattr(settings, 'FRONTEND_URL', 'https://goholiday.id')}/bookings/{booking.id}",
    }
    
    customer_html = render_to_string('travel/booking_payment_request.html', customer_context)
    send_email_with_backend_detection(
        subject=f"Pembayaran Diperlukan - Booking #{common_context['booking_number']}",
        plain_message=f"Booking Anda untuk {tour_package.name} telah dikonfirmasi. Silakan lakukan pembayaran.",
        html_message=customer_html,
        recipient_list=[booked_by_user.email],
        email_type="booking_payment_request"
    )
    
    # 2. Send notification to admin
    admin_context = {
        **common_context,
        'booked_by_name': booked_by_user.get_full_name() or booked_by_user.email,
        'booked_by_type': booked_by_type,
        'booked_by_email': booked_by_user.email,
        'supplier_name': tour_package.supplier.user.get_full_name() or tour_package.supplier.user.email,
        'admin_url': getattr(settings, 'ADMIN_FRONTEND_URL', 'https://goholiday.id/admin'),
        'booking_id': booking.id,
    }
    
    admin_html = render_to_string('travel/booking_confirmed_admin.html', admin_context)
    
    admin_emails = list(User.objects.filter(role=UserRole.STAFF, is_active=True).values_list('email', flat=True))
    
    if admin_emails:
        send_email_with_backend_detection(
            subject=f"Booking Dikonfirmasi #{common_context['booking_number']} - {tour_package.name}",
            plain_message=f"Booking {common_context['booking_number']} telah dikonfirmasi oleh supplier.",
            html_message=admin_html,
            recipient_list=admin_emails,
            email_type="booking_confirmed_admin"
        )
    
    return f"Booking confirmed emails sent for booking ID {booking_id}"


@shared_task
def send_payment_created_emails(payment_id):
    """
    Send email to admin when a payment is created/uploaded.
    
    Args:
        payment_id: The ID of the payment that was created
    """
    from travel.models import Payment
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        payment = Payment.objects.select_related(
            'booking__reseller__user',
            'booking__customer__user',
            'booking__tour_date__package__supplier__user'
        ).get(id=payment_id)
    except Payment.DoesNotExist:
        return f"Payment with ID {payment_id} does not exist"
    
    booking = payment.booking
    
    # Get the user who made the booking
    if booking.reseller:
        booked_by_user = booking.reseller.user
        booked_by_type = "Reseller"
    elif booking.customer:
        booked_by_user = booking.customer.user
        booked_by_type = "Customer"
    else:
        return f"Booking {booking.id} has no reseller or customer associated"
    
    tour_package = booking.tour_date.package
    
    # Context for admin
    admin_context = {
        'booking_number': booking.booking_number,
        'tour_package_name': tour_package.name,
        'departure_date': booking.tour_date.departure_date.strftime('%d %B %Y'),
        'payment_amount_formatted': f"Rp {payment.amount:,.0f}",
        'transfer_date': payment.transfer_date.strftime('%d %B %Y'),
        'booked_by_name': booked_by_user.get_full_name() or booked_by_user.email,
        'booked_by_type': booked_by_type,
        'booked_by_email': booked_by_user.email,
        'payment_status': payment.get_status_display(),
        'admin_url': getattr(settings, 'ADMIN_FRONTEND_URL', 'https://goholiday.id/admin'),
        'booking_id': booking.id,
        'payment_id': payment.id,
        'company_name': getattr(settings, 'COMPANY_NAME', 'GoHoliday Travel Marketplace'),
    }
    
    admin_html = render_to_string('travel/payment_created_admin.html', admin_context)
    
    admin_emails = list(User.objects.filter(role=UserRole.STAFF, is_active=True).values_list('email', flat=True))
    
    if admin_emails:
        send_email_with_backend_detection(
            subject=f"Pembayaran Baru - Booking #{booking.booking_number}",
            plain_message=f"Pembayaran baru telah diupload untuk booking {booking.booking_number}",
            html_message=admin_html,
            recipient_list=admin_emails,
            email_type="payment_created_admin"
        )
    
    return f"Payment created email sent for payment ID {payment_id}"


@shared_task
def send_payment_approved_emails(payment_id):
    """
    Send emails when payment status changes to APPROVED.
    - Customer/Reseller: Payment approved confirmation
    - Supplier: Payment approved notification
    
    Args:
        payment_id: The ID of the payment that was approved
    """
    from travel.models import Payment
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        payment = Payment.objects.select_related(
            'booking__reseller__user',
            'booking__customer__user',
            'booking__tour_date__package__supplier__user'
        ).get(id=payment_id)
    except Payment.DoesNotExist:
        return f"Payment with ID {payment_id} does not exist"
    
    booking = payment.booking
    
    # Get the user who made the booking
    if booking.reseller:
        booked_by_user = booking.reseller.user
    elif booking.customer:
        booked_by_user = booking.customer.user
    else:
        return f"Booking {booking.id} has no reseller or customer associated"
    
    tour_package = booking.tour_date.package
    
    # Common context
    common_context = {
        'booking_number': booking.booking_number,
        'tour_package_name': tour_package.name,
        'departure_date': booking.tour_date.departure_date.strftime('%d %B %Y'),
        'payment_amount_formatted': f"Rp {payment.amount:,.0f}",
        'transfer_date': payment.transfer_date.strftime('%d %B %Y'),
        'company_name': getattr(settings, 'COMPANY_NAME', 'GoHoliday Travel Marketplace'),
        'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Indonesia'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@goholiday.id'),
        'support_phone': getattr(settings, 'SUPPORT_PHONE', '+62 xxx xxxx xxxx'),
    }
    
    # 1. Send approval confirmation to customer/reseller
    customer_context = {
        **common_context,
        'customer_name': booked_by_user.get_full_name() or booked_by_user.email,
        'site_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'booking_id': booking.id,
    }
    
    customer_html = render_to_string('travel/payment_approved_customer.html', customer_context)
    send_email_with_backend_detection(
        subject=f"Pembayaran Disetujui - Booking #{booking.booking_number}",
        plain_message=f"Pembayaran Anda untuk booking {booking.booking_number} telah disetujui.",
        html_message=customer_html,
        recipient_list=[booked_by_user.email],
        email_type="payment_approved_customer"
    )
    
    # 2. Send notification to supplier
    supplier_context = {
        **common_context,
        'supplier_name': tour_package.supplier.user.get_full_name() or tour_package.supplier.user.email,
        'booked_by_name': booked_by_user.get_full_name() or booked_by_user.email,
        'supplier_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'booking_id': booking.id,
    }
    
    supplier_html = render_to_string('travel/payment_approved_supplier.html', supplier_context)
    send_email_with_backend_detection(
        subject=f"Pembayaran Diterima - Booking #{booking.booking_number}",
        plain_message=f"Pembayaran untuk booking {booking.booking_number} telah disetujui.",
        html_message=supplier_html,
        recipient_list=[tour_package.supplier.user.email],
        email_type="payment_approved_supplier"
    )
    
    return f"Payment approved emails sent for payment ID {payment_id}"

