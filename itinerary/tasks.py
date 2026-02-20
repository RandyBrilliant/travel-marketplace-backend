from celery import shared_task
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from .models import ItineraryTransaction, ItineraryTransactionStatus
from account.tasks import send_email_with_backend_detection
from account.models import UserRole
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


@shared_task
def send_itinerary_creation_emails(transaction_id):
    """
    Send itinerary creation emails to customer and supplier ONLY.
    Admin will be notified when payment is uploaded.
    
    Args:
        transaction_id: The ID of the itinerary transaction that was created
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        transaction = ItineraryTransaction.objects.select_related(
            'customer',
            'board__created_by',
            'promo_code'
        ).get(id=transaction_id)
    except ItineraryTransaction.DoesNotExist:
        return f"ItineraryTransaction with ID {transaction_id} does not exist"
    
    # Check if board has a creator
    if not transaction.board.created_by:
        return f"ItineraryTransaction {transaction_id} has no board creator"
    
    # Common context for all emails
    common_context = {
        'transaction_number': transaction.transaction_number or f"IT-{transaction.id:06d}",
        'itinerary_title': transaction.board.title,
        'purchase_date': transaction.created_at.strftime('%d %B %Y %H:%M'),
        'departure_date': transaction.departure_date.strftime('%d %B %Y') if transaction.departure_date else 'Belum ditentukan',
        'arrival_date': transaction.arrival_date.strftime('%d %B %Y') if transaction.arrival_date else 'Belum ditentukan',
        'total_amount_formatted': f"Rp {transaction.amount:,.0f}",
        'company_name': getattr(settings, 'COMPANY_NAME', 'GoHoliday Travel Marketplace'),
        'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Indonesia'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@goholiday.id'),
        'support_phone': getattr(settings, 'SUPPORT_PHONE', '+62 xxx xxxx xxxx'),
    }
    
    # Add promo code info if used
    if transaction.promo_code:
        common_context['promo_code'] = transaction.promo_code
        common_context['promo_discount_formatted'] = f"Rp {transaction.promo_discount_amount:,.0f}"
    
    # 1. Send confirmation email to customer
    customer_context = {
        **common_context,
        'customer_name': transaction.customer.get_full_name() or transaction.customer.email,
        'site_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'transaction_id': transaction.id,
    }
    
    customer_html = render_to_string('itinerary/transaction_created_customer.html', customer_context)
    send_email_with_backend_detection(
        subject=f"Pembelian Itinerary Diterima #{common_context['transaction_number']}",
        plain_message=f"Pembelian itinerary {transaction.board.title} telah diterima.",
        html_message=customer_html,
        recipient_list=[transaction.customer.email],
        email_type="itinerary_created_customer"
    )
    
    # 2. Send notification email to supplier (itinerary owner)
    supplier_context = {
        **common_context,
        'supplier_name': transaction.board.created_by.get_full_name() or transaction.board.created_by.email,
        'customer_name': transaction.customer.get_full_name() or transaction.customer.email,
        'customer_email': transaction.customer.email,
        'supplier_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'transaction_id': transaction.id,
    }
    
    supplier_html = render_to_string('itinerary/transaction_created_supplier.html', supplier_context)
    send_email_with_backend_detection(
        subject=f"Pembelian Baru Itinerary: {transaction.board.title}",
        plain_message=f"Itinerary Anda {transaction.board.title} telah dibeli.",
        html_message=supplier_html,
        recipient_list=[transaction.board.created_by.email],
        email_type="itinerary_created_supplier"
    )
    
    return f"Itinerary creation emails sent for transaction ID {transaction_id}"


@shared_task
def send_itinerary_payment_uploaded_emails(transaction_id):
    """
    Send email to admin when payment proof is uploaded.
    
    Args:
        transaction_id: The ID of the transaction with payment proof
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        transaction = ItineraryTransaction.objects.select_related(
            'customer',
            'board__created_by'
        ).get(id=transaction_id)
    except ItineraryTransaction.DoesNotExist:
        return f"ItineraryTransaction with ID {transaction_id} does not exist"
    
    # Context for admin
    admin_context = {
        'transaction_number': transaction.transaction_number or f"IT-{transaction.id:06d}",
        'itinerary_title': transaction.board.title,
        'customer_name': transaction.customer.get_full_name() or transaction.customer.email,
        'customer_email': transaction.customer.email,
        'payment_amount_formatted': f"Rp {transaction.payment_amount:,.0f}" if transaction.payment_amount else 'Rp 0',
        'transfer_date': transaction.payment_transfer_date.strftime('%d %B %Y') if transaction.payment_transfer_date else 'Tidak tersedia',
        'payment_status': 'Menunggu Verifikasi',
        'admin_url': getattr(settings, 'ADMIN_FRONTEND_URL', 'https://goholiday.id/admin'),
        'transaction_id': transaction.id,
        'company_name': getattr(settings, 'COMPANY_NAME', 'GoHoliday Travel Marketplace'),
    }
    
    admin_html = render_to_string('itinerary/payment_uploaded_admin.html', admin_context)
    
    admin_emails = list(User.objects.filter(role=UserRole.STAFF, is_active=True).values_list('email', flat=True))
    
    if admin_emails:
        send_email_with_backend_detection(
            subject=f"Bukti Pembayaran Itinerary Baru - {transaction.transaction_number}",
            plain_message=f"Bukti pembayaran telah diupload untuk transaksi itinerary {transaction.transaction_number}",
            html_message=admin_html,
            recipient_list=admin_emails,
            email_type="itinerary_payment_uploaded_admin"
        )
    
    return f"Payment uploaded email sent for transaction ID {transaction_id}"


@shared_task
def send_itinerary_payment_approved_emails(transaction_id):
    """
    Send emails when payment is approved and access is granted.
    - Customer: Access granted notification with itinerary link
    - Supplier: Payment received notification
    
    Args:
        transaction_id: The ID of the transaction with approved payment
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        transaction = ItineraryTransaction.objects.select_related(
            'customer',
            'board__created_by'
        ).get(id=transaction_id)
    except ItineraryTransaction.DoesNotExist:
        return f"ItineraryTransaction with ID {transaction_id} does not exist"
    
    if not transaction.board.created_by:
        return f"ItineraryTransaction {transaction_id} has no board creator"
    
    # Common context
    common_context = {
        'transaction_number': transaction.transaction_number or f"IT-{transaction.id:06d}",
        'itinerary_title': transaction.board.title,
        'payment_amount_formatted': f"Rp {transaction.payment_amount:,.0f}" if transaction.payment_amount else f"Rp {transaction.amount:,.0f}",
        'transfer_date': transaction.payment_transfer_date.strftime('%d %B %Y') if transaction.payment_transfer_date else 'Tidak tersedia',
        'company_name': getattr(settings, 'COMPANY_NAME', 'GoHoliday Travel Marketplace'),
        'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Indonesia'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@goholiday.id'),
        'support_phone': getattr(settings, 'SUPPORT_PHONE', '+62 xxx xxxx xxxx'),
    }
    
    # 1. Send access granted email to customer
    customer_context = {
        **common_context,
        'customer_name': transaction.customer.get_full_name() or transaction.customer.email,
        'site_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'itinerary_url': f"{getattr(settings, 'FRONTEND_URL', 'https://goholiday.id')}/itinerary/{transaction.board.id}",
        'expires_at': transaction.expires_at.strftime('%d %B %Y %H:%M') if transaction.expires_at else 'Tidak terbatas',
        'transaction_id': transaction.id,
    }
    
    customer_html = render_to_string('itinerary/payment_approved_customer.html', customer_context)
    send_email_with_backend_detection(
        subject=f"Akses Itinerary Diberikan - {transaction.transaction_number}",
        plain_message=f"Pembayaran Anda telah disetujui. Akses itinerary {transaction.board.title} sekarang tersedia.",
        html_message=customer_html,
        recipient_list=[transaction.customer.email],
        email_type="itinerary_payment_approved_customer"
    )
    
    # 2. Send payment received email to supplier
    supplier_context = {
        **common_context,
        'supplier_name': transaction.board.created_by.get_full_name() or transaction.board.created_by.email,
        'customer_name': transaction.customer.get_full_name() or transaction.customer.email,
        'supplier_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'transaction_id': transaction.id,
    }
    
    supplier_html = render_to_string('itinerary/payment_approved_supplier.html', supplier_context)
    send_email_with_backend_detection(
        subject=f"Pembayaran Diterima - Itinerary {transaction.board.title}",
        plain_message=f"Pembayaran untuk itinerary {transaction.board.title} telah disetujui.",
        html_message=supplier_html,
        recipient_list=[transaction.board.created_by.email],
        email_type="itinerary_payment_approved_supplier"
    )
    
    return f"Payment approved emails sent for transaction ID {transaction_id}"


@shared_task
def send_itinerary_payment_rejected_emails(transaction_id):
    """
    Send email to customer when payment is rejected.
    
    Args:
        transaction_id: The ID of the transaction with rejected payment
    """
    try:
        transaction = ItineraryTransaction.objects.select_related(
            'customer',
            'board'
        ).get(id=transaction_id)
    except ItineraryTransaction.DoesNotExist:
        return f"ItineraryTransaction with ID {transaction_id} does not exist"
    
    # Context for customer
    customer_context = {
        'transaction_number': transaction.transaction_number or f"IT-{transaction.id:06d}",
        'itinerary_title': transaction.board.title,
        'customer_name': transaction.customer.get_full_name() or transaction.customer.email,
        'payment_amount_formatted': f"Rp {transaction.payment_amount:,.0f}" if transaction.payment_amount else f"Rp {transaction.amount:,.0f}",
        'site_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'transaction_url': f"{getattr(settings, 'FRONTEND_URL', 'https://goholiday.id')}/itinerary/transactions/{transaction.id}",
        'company_name': getattr(settings, 'COMPANY_NAME', 'GoHoliday Travel Marketplace'),
        'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Indonesia'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@goholiday.id'),
        'support_phone': getattr(settings, 'SUPPORT_PHONE', '+62 xxx xxxx xxxx'),
    }
    
    customer_html = render_to_string('itinerary/payment_rejected_customer.html', customer_context)
    send_email_with_backend_detection(
        subject=f"Pembayaran Ditolak - {transaction.transaction_number}",
        plain_message=f"Pembayaran untuk transaksi {transaction.transaction_number} ditolak. Silakan upload ulang bukti pembayaran.",
        html_message=customer_html,
        recipient_list=[transaction.customer.email],
        email_type="itinerary_payment_rejected_customer"
    )
    
    return f"Payment rejected email sent for transaction ID {transaction_id}"


@shared_task
def send_itinerary_expiring_soon_emails():
    """
    Send reminder emails to customers whose itinerary access is expiring soon (within 2 days).
    This task should be run daily via cron/celery beat.
    """
    from datetime import timedelta
    
    now = timezone.now()
    two_days_later = now + timedelta(days=2)
    
    # Find ACTIVE transactions expiring in the next 2 days
    expiring_transactions = ItineraryTransaction.objects.filter(
        status=ItineraryTransactionStatus.ACTIVE,
        payment_status='APPROVED',
        expires_at__gte=now,
        expires_at__lte=two_days_later
    ).select_related('customer', 'board')
    
    count = 0
    for transaction in expiring_transactions:
        # Context for customer
        customer_context = {
            'transaction_number': transaction.transaction_number or f"IT-{transaction.id:06d}",
            'itinerary_title': transaction.board.title,
            'customer_name': transaction.customer.get_full_name() or transaction.customer.email,
            'expires_at': transaction.expires_at.strftime('%d %B %Y %H:%M'),
            'days_remaining': (transaction.expires_at - now).days,
            'itinerary_url': f"{getattr(settings, 'FRONTEND_URL', 'https://goholiday.id')}/itinerary/{transaction.board.id}",
            'company_name': getattr(settings, 'COMPANY_NAME', 'GoHoliday Travel Marketplace'),
            'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Indonesia'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@goholiday.id'),
            'support_phone': getattr(settings, 'SUPPORT_PHONE', '+62 xxx xxxx xxxx'),
        }
        
        customer_html = render_to_string('itinerary/expiring_soon_reminder.html', customer_context)
        send_email_with_backend_detection(
            subject=f"Pengingat: Akses Itinerary Akan Berakhir - {transaction.transaction_number}",
            plain_message=f"Akses Anda ke itinerary {transaction.board.title} akan berakhir dalam {customer_context['days_remaining']} hari.",
            html_message=customer_html,
            recipient_list=[transaction.customer.email],
            email_type="itinerary_expiring_soon"
        )
        count += 1
    
    logger.info(f"Sent {count} expiration reminder email(s)")
    return f"Sent {count} expiration reminder emails"


# Keep the old function name for backward compatibility, but redirect to new one
@shared_task
def send_itinerary_transaction_confirmation_emails(transaction_id):
    """
    Deprecated: Use send_itinerary_creation_emails instead.
    Kept for backward compatibility.
    """
    return send_itinerary_creation_emails(transaction_id)
