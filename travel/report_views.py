"""
Report views for admin and supplier analytics and reporting.

This module provides comprehensive reporting endpoints for both admin and supplier dashboards:

Admin Reports:
- Sales reports with commission tracking
- Passenger (PAX) statistics
- Total revenue tracking
- Commission payout status

Supplier Reports:
- Sales reports for their own packages
- Passenger statistics for their bookings
- Total revenue for their packages
- Commission payout status for their payouts
"""

from django.utils import timezone
from django.views.decorators.cache import cache_page
from datetime import timedelta, datetime, date
from django.db.models import Sum, Count, Q
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_status

from travel.models import Booking, BookingStatus, ResellerCommission, WithdrawalRequest, WithdrawalRequestStatus, SeatSlot
from account.models import SupplierProfile


class IsStaff(IsAuthenticated):
    """
    Permission class to check if user is a staff member (admin).
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        # Check if user has STAFF role
        return hasattr(request.user, 'role') and request.user.role == 'STAFF'


class IsSupplier(IsAuthenticated):
    """
    Permission class to check if user is a supplier.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        # Check if user has SUPPLIER role
        return hasattr(request.user, 'role') and request.user.role == 'SUPPLIER'


def parse_date_range(request, default_days=30):
    """
    Parse start_date and end_date from request query parameters.
    Returns a tuple of (start_date, end_date) as date objects.
    
    Args:
        request: Django request object
        default_days: Number of days to look back if dates not provided (default: 30)
    
    Returns:
        tuple: (start_date, end_date) as date objects
        
    Raises:
        ValueError: If date format is invalid or start_date > end_date
    """
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid start_date format. Use YYYY-MM-DD")
    else:
        start_date = (timezone.now() - timedelta(days=default_days)).date()
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid end_date format. Use YYYY-MM-DD")
    else:
        end_date = timezone.now().date()
    
    if start_date > end_date:
        raise ValueError("start_date must be before end_date")
    
    return start_date, end_date


@api_view(['GET'])
@permission_classes([IsStaff])
def sales_report_view(request):
    """
    Get sales and commission report for a specified date range.
    
    Query Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of daily sales and commission data:
        [
            {
                "period": "2025-01-15",
                "sales": 10000000,
                "commission": 500000
            },
            ...
        ]
    """
    try:
        start_date, end_date = parse_date_range(request)
        
        # Optimized query: single aggregation query instead of multiple
        bookings = Booking.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED]
        ).values('created_at__date').annotate(
            total_sales=Sum('total_amount'),
            total_commission=Sum('commissions__amount')
        ).order_by('created_at__date')
        
        # Format response
        data = [
            {
                "period": booking['created_at__date'].isoformat(),
                "sales": int(booking['total_sales'] or 0),
                "commission": int(booking['total_commission'] or 0)
            }
            for booking in bookings
        ]
        
        return Response(data)
    
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsStaff])
def pax_report_view(request):
    """
    Get passenger (PAX) statistics and distribution for a date range.
    
    Query Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
    
    Returns:
        {
            "total_pax": 250,
            "confirmed_pax": 180,
            "pending_pax": 50,
            "completed_pax": 120
        }
    """
    try:
        start_date, end_date = parse_date_range(request)
        
        # Optimized: single query with multiple annotations instead of separate queries
        pax_stats = SeatSlot.objects.filter(
            booking__created_at__date__gte=start_date,
            booking__created_at__date__lte=end_date
        ).aggregate(
            total_pax=Count('id'),
            confirmed_pax=Count('id', filter=Q(booking__status=BookingStatus.CONFIRMED)),
            pending_pax=Count('id', filter=Q(booking__status=BookingStatus.PENDING)),
            completed_pax=Count('id', filter=Q(booking__status=BookingStatus.CONFIRMED))
        )
        
        data = {
            "total_pax": pax_stats['total_pax'] or 0,
            "confirmed_pax": pax_stats['confirmed_pax'] or 0,
            "pending_pax": pax_stats['pending_pax'] or 0,
            "completed_pax": pax_stats['completed_pax'] or 0
        }
        
        return Response(data)
    
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsStaff])
def total_amount_report_view(request):
    """
    Get total revenue report with daily breakdown for a date range.
    
    Query Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
    
    Returns:
        {
            "total_amount": 125000000,
            "average_daily_amount": 4166666,
            "max_amount": 15000000,
            "daily_amounts": [
                {
                    "period": "2025-01-01",
                    "amount": 5000000
                },
                ...
            ]
        }
    """
    try:
        start_date, end_date = parse_date_range(request)
        
        # Optimized: single query for daily aggregation
        daily_data = Booking.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED]
        ).values('created_at__date').annotate(
            amount=Sum('total_amount')
        ).order_by('created_at__date')
        
        daily_amounts = [
            {
                "period": item['created_at__date'].isoformat(),
                "amount": int(item['amount'] or 0)
            }
            for item in daily_data
        ]
        
        # Calculate statistics efficiently
        amounts = [item['amount'] for item in daily_amounts]
        total_amount = sum(amounts)
        
        data = {
            "total_amount": int(total_amount),
            "average_daily_amount": int(total_amount / len(amounts)) if amounts else 0,
            "max_amount": max(amounts) if amounts else 0,
            "daily_amounts": daily_amounts
        }
        
        return Response(data)
    
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsStaff])
def commission_payout_report_view(request):
    """
    Get commission payout status and breakdown for a date range.
    
    Query Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
    
    Returns:
        {
            "total_commission_earned": 5000000,
            "total_commission_paid": 2000000,
            "pending_amount": 1000000,
            "pending_count": 10,
            "approved_amount": 2000000,
            "approved_count": 15,
            "paid_amount": 2000000,
            "paid_count": 12
        }
    """
    try:
        start_date, end_date = parse_date_range(request)
        
        # Optimized: single query for total earned commissions
        total_earned = ResellerCommission.objects.filter(
            booking__created_at__date__gte=start_date,
            booking__created_at__date__lte=end_date
        ).aggregate(amount=Sum('amount'))
        total_commission_earned = int(total_earned['amount'] or 0)
        
        # Optimized: single query with multiple status annotations instead of separate queries
        withdrawal_stats = WithdrawalRequest.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).aggregate(
            pending_amount=Sum('amount', filter=Q(status=WithdrawalRequestStatus.PENDING)),
            pending_count=Count('id', filter=Q(status=WithdrawalRequestStatus.PENDING)),
            approved_amount=Sum('amount', filter=Q(status=WithdrawalRequestStatus.APPROVED)),
            approved_count=Count('id', filter=Q(status=WithdrawalRequestStatus.APPROVED)),
            paid_amount=Sum('amount', filter=Q(status=WithdrawalRequestStatus.COMPLETED)),
            paid_count=Count('id', filter=Q(status=WithdrawalRequestStatus.COMPLETED))
        )
        
        data = {
            "total_commission_earned": total_commission_earned,
            "total_commission_paid": int(withdrawal_stats['paid_amount'] or 0),
            "pending_amount": int(withdrawal_stats['pending_amount'] or 0),
            "pending_count": withdrawal_stats['pending_count'] or 0,
            "approved_amount": int(withdrawal_stats['approved_amount'] or 0),
            "approved_count": withdrawal_stats['approved_count'] or 0,
            "paid_amount": int(withdrawal_stats['paid_amount'] or 0),
            "paid_count": withdrawal_stats['paid_count'] or 0
        }
        
        return Response(data)
    
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )

# ============================================================================
# SUPPLIER REPORTS - Filtered by authenticated supplier
# ============================================================================

@api_view(['GET'])
@permission_classes([IsSupplier])
def supplier_sales_report_view(request):
    """
    Get sales and commission report for supplier's own packages.
    
    Query Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of daily sales data for supplier's packages
    """
    try:
        start_date, end_date = parse_date_range(request)
        
        # Get supplier profile
        supplier_profile = SupplierProfile.objects.get(user=request.user)
        
        # Optimized query: get bookings for this supplier's packages only
        bookings = Booking.objects.filter(
            tour_date__package__supplier=supplier_profile,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED]
        ).values('created_at__date').annotate(
            total_sales=Sum('total_amount'),
            total_commission=Sum('commissions__amount')
        ).order_by('created_at__date')
        
        data = [
            {
                "period": booking['created_at__date'].isoformat(),
                "sales": int(booking['total_sales'] or 0),
                "commission": int(booking['total_commission'] or 0)
            }
            for booking in bookings
        ]
        
        return Response(data)
    
    except SupplierProfile.DoesNotExist:
        return Response(
            {"error": "Supplier profile not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsSupplier])
def supplier_pax_report_view(request):
    """
    Get passenger statistics for supplier's own packages.
    
    Query Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
    """
    try:
        start_date, end_date = parse_date_range(request)
        
        # Get supplier profile
        supplier_profile = SupplierProfile.objects.get(user=request.user)
        
        # Optimized: single query with multiple annotations for supplier's packages
        pax_stats = SeatSlot.objects.filter(
            booking__tour_date__package__supplier=supplier_profile,
            booking__created_at__date__gte=start_date,
            booking__created_at__date__lte=end_date
        ).aggregate(
            total_pax=Count('id'),
            confirmed_pax=Count('id', filter=Q(booking__status=BookingStatus.CONFIRMED)),
            pending_pax=Count('id', filter=Q(booking__status=BookingStatus.PENDING)),
            completed_pax=Count('id', filter=Q(booking__status=BookingStatus.CONFIRMED))
        )
        
        data = {
            "total_pax": pax_stats['total_pax'] or 0,
            "confirmed_pax": pax_stats['confirmed_pax'] or 0,
            "pending_pax": pax_stats['pending_pax'] or 0,
            "completed_pax": pax_stats['completed_pax'] or 0
        }
        
        return Response(data)
    
    except SupplierProfile.DoesNotExist:
        return Response(
            {"error": "Supplier profile not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsSupplier])
def supplier_total_amount_report_view(request):
    """
    Get total revenue report for supplier's own packages.
    
    Query Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
    """
    try:
        start_date, end_date = parse_date_range(request)
        
        # Get supplier profile
        supplier_profile = SupplierProfile.objects.get(user=request.user)
        
        # Optimized: single query for daily aggregation for supplier's packages
        daily_data = Booking.objects.filter(
            tour_date__package__supplier=supplier_profile,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED]
        ).values('created_at__date').annotate(
            amount=Sum('total_amount')
        ).order_by('created_at__date')
        
        daily_amounts = [
            {
                "period": item['created_at__date'].isoformat(),
                "amount": int(item['amount'] or 0)
            }
            for item in daily_data
        ]
        
        # Calculate statistics efficiently
        amounts = [item['amount'] for item in daily_amounts]
        total_amount = sum(amounts)
        
        data = {
            "total_amount": int(total_amount),
            "average_daily_amount": int(total_amount / len(amounts)) if amounts else 0,
            "max_amount": max(amounts) if amounts else 0,
            "daily_amounts": daily_amounts
        }
        
        return Response(data)
    
    except SupplierProfile.DoesNotExist:
        return Response(
            {"error": "Supplier profile not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsSupplier])
def supplier_commission_report_view(request):
    """
    Get commission payout report for supplier's own payouts.
    
    Query Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
    """
    try:
        start_date, end_date = parse_date_range(request)
        
        # Get supplier profile
        supplier_profile = SupplierProfile.objects.get(user=request.user)
        
        # Optimized: single query for total earned commissions for supplier's packages
        total_earned = ResellerCommission.objects.filter(
            booking__tour_date__package__supplier=supplier_profile,
            booking__created_at__date__gte=start_date,
            booking__created_at__date__lte=end_date
        ).aggregate(amount=Sum('amount'))
        total_commission_earned = int(total_earned['amount'] or 0)
        
        # Note: Supplier withdrawal requests are filtered by the withdrawal's user (reseller)
        # For supplier commission, we show their commission from bookings on their packages
        # There's no separate withdrawal system for suppliers in the current model
        # So we show earned vs paid differently
        
        data = {
            "total_commission_earned": total_commission_earned,
            "total_commission_paid": 0,  # Suppliers don't have a withdrawal system yet
            "pending_amount": total_commission_earned,  # All commission is pending payment to supplier
            "pending_count": 1,
            "approved_amount": 0,
            "approved_count": 0,
            "paid_amount": 0,
            "paid_count": 0
        }
        
        return Response(data)
    
    except SupplierProfile.DoesNotExist:
        return Response(
            {"error": "Supplier profile not found"},
            status=http_status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST
        )