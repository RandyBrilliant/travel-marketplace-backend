from celery import shared_task
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from .models import ItineraryTransaction, ItineraryTransactionStatus
from account.tasks import send_email_with_backend_detection
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
def send_itinerary_transaction_confirmation_emails(transaction_id):
    """
    Send itinerary transaction confirmation emails to buyer, admin, and supplier.
    
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
    
    # Common context for all emails
    common_context = {
        'transaction_number': f"IT-{transaction.id:06d}",
        'itinerary_title': transaction.board.title,
        'purchase_date': transaction.created_at.strftime('%d %B %Y %H:%M'),
        'status': transaction.get_status_display(),
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
    
    # Calculate platform fee and supplier earnings
    platform_fee_percentage = getattr(settings, 'PLATFORM_FEE_PERCENTAGE', 10)
    platform_fee = (transaction.amount * platform_fee_percentage) / 100
    supplier_earnings = transaction.amount - platform_fee
    
    common_context['platform_fee_formatted'] = f"Rp {platform_fee:,.0f}"
    common_context['supplier_earnings_formatted'] = f"Rp {supplier_earnings:,.0f}"
    
    # 1. Send confirmation email to buyer (customer/reseller)
    buyer_context = {
        **common_context,
        'customer_name': transaction.customer.get_full_name() or transaction.customer.email,
        'site_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'itinerary_id': transaction.board.id,
    }
    
    buyer_html = render_to_string('itinerary/transaction_confirmation.html', buyer_context)
    send_email_with_backend_detection(
        subject=f"Konfirmasi Pembelian Itinerary #{common_context['transaction_number']}",
        plain_message=f"Pembelian itinerary {transaction.board.title} telah berhasil.",
        html_message=buyer_html,
        recipient_list=[transaction.customer.email],
        email_type="itinerary_confirmation"
    )
    
    # 2. Send notification email to admin
    buyer_type = "Customer" if transaction.customer.role == 'customer' else "Reseller"
    
    admin_context = {
        **common_context,
        'buyer_name': transaction.customer.get_full_name() or transaction.customer.email,
        'buyer_type': buyer_type,
        'buyer_email': transaction.customer.email,
        'supplier_name': transaction.board.created_by.get_full_name() or transaction.board.created_by.email,
        'admin_url': getattr(settings, 'ADMIN_FRONTEND_URL', 'https://goholiday.id/admin'),
        'transaction_id': transaction.id,
    }
    
    admin_html = render_to_string('itinerary/transaction_notification_admin.html', admin_context)
    
    # Get all admin emails
    admin_emails = list(User.objects.filter(role='admin', is_active=True).values_list('email', flat=True))
    
    if admin_emails:
        send_email_with_backend_detection(
            subject=f"Transaksi Itinerary Baru #{common_context['transaction_number']} - {transaction.board.title}",
            plain_message=f"Transaksi itinerary baru dari {transaction.customer.get_full_name() or transaction.customer.email}",
            html_message=admin_html,
            recipient_list=admin_emails,
            email_type="itinerary_admin_notification"
        )
    
    # 3. Send notification email to supplier (itinerary owner)
    supplier_context = {
        **common_context,
        'supplier_name': transaction.board.created_by.get_full_name() or transaction.board.created_by.email,
        'buyer_name': transaction.customer.get_full_name() or transaction.customer.email,
        'buyer_email': transaction.customer.email,
        'supplier_url': getattr(settings, 'FRONTEND_URL', 'https://goholiday.id'),
        'transaction_id': transaction.id,
    }
    
    supplier_html = render_to_string('itinerary/transaction_notification_supplier.html', supplier_context)
    send_email_with_backend_detection(
        subject=f"Itinerary Anda Terjual: {transaction.board.title}",
        plain_message=f"Itinerary Anda {transaction.board.title} telah dibeli.",
        html_message=supplier_html,
        recipient_list=[transaction.board.created_by.email],
        email_type="itinerary_supplier_notification"
    )
    
    return f"Itinerary transaction confirmation emails sent for transaction ID {transaction_id}"
