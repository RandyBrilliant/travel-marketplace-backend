from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from account.models import ResellerProfile, UserRole
from .models import WithdrawalRequest, WithdrawalRequestStatus
from .serializers import (
    WithdrawalRequestSerializer,
    WithdrawalRequestCreateSerializer,
    WithdrawalRequestUpdateSerializer,
)


class IsReseller(permissions.BasePermission):
    """
    Permission check for reseller profile.
    Allows any authenticated user who has a reseller profile (supports dual roles).
    """
    
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_reseller  # Checks if user has reseller_profile
        )


class ResellerWithdrawalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for resellers to create and view their withdrawal requests.
    Resellers can only see and create their own withdrawal requests.
    """
    
    permission_classes = [IsReseller]
    serializer_class = WithdrawalRequestSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "amount"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """Return only withdrawal requests for the authenticated reseller."""
        if not self.request.user.is_authenticated:
            return WithdrawalRequest.objects.none()
        
        try:
            reseller_profile = ResellerProfile.objects.get(user=self.request.user)
            return WithdrawalRequest.objects.filter(
                reseller=reseller_profile
            ).select_related(
                "reseller", "reseller__user", "approved_by"
            ).all()
        except ResellerProfile.DoesNotExist:
            return WithdrawalRequest.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for create vs other actions."""
        if self.action == "create":
            return WithdrawalRequestCreateSerializer
        return WithdrawalRequestSerializer
    
    def perform_create(self, serializer):
        """Set the reseller when creating a withdrawal request."""
        try:
            reseller_profile = ResellerProfile.objects.get(user=self.request.user)
            serializer.save(reseller=reseller_profile)
        except ResellerProfile.DoesNotExist:
            raise ValidationError(
                {"detail": "Profil reseller tidak ditemukan. Silakan lengkapi pengaturan profil Anda."}
            )
    
    @action(detail=False, methods=["get"], url_path="balance")
    def get_balance(self, request):
        """Get commission balance information for the reseller."""
        try:
            reseller_profile = ResellerProfile.objects.get(user=request.user)
            
            total_earned = reseller_profile.get_total_commission_earned()
            total_withdrawn = reseller_profile.get_total_withdrawn()
            pending_withdrawals = reseller_profile.get_pending_withdrawal_amount()
            available_balance = reseller_profile.get_available_commission_balance()
            commission_breakdown = reseller_profile.get_commission_breakdown()
            
            return Response({
                "total_earned": total_earned,
                "total_withdrawn": total_withdrawn,
                "pending_withdrawals": pending_withdrawals,
                "available_balance": available_balance,
                "commission_breakdown": {
                    "from_booking": commission_breakdown['from_booking'],
                    "from_downline": commission_breakdown['from_downline'],
                    "pending_commission": commission_breakdown['pending_commission'],
                },
                "bank_account": {
                    "bank_name": reseller_profile.bank_name or None,
                    "bank_account_name": reseller_profile.bank_account_name or None,
                    "bank_account_number": reseller_profile.bank_account_number or None,
                },
            })
        except ResellerProfile.DoesNotExist:
            return Response(
                {"detail": "Profil reseller tidak ditemukan."},
                status=status.HTTP_404_NOT_FOUND
            )


class AdminWithdrawalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to view and manage all withdrawal requests.
    Admin can approve, reject, or mark withdrawals as completed.
    """
    
    permission_classes = [IsAdminUser]
    serializer_class = WithdrawalRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "reseller"]
    search_fields = [
        "reseller__full_name",
        "reseller__user__email",
    ]
    ordering_fields = ["created_at", "amount", "status"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """Return all withdrawal requests with optimized queries."""
        return WithdrawalRequest.objects.select_related(
            "reseller", "reseller__user", "approved_by"
        ).all()
    
    def get_serializer_class(self):
        """Use different serializers for update vs other actions."""
        if self.action in ["update", "partial_update"]:
            return WithdrawalRequestUpdateSerializer
        return WithdrawalRequestSerializer
    
    def perform_update(self, serializer):
        """Set approved_by and approved_at when status changes."""
        instance = serializer.instance
        old_status = instance.status
        new_status = serializer.validated_data.get("status", old_status)
        
        # If status is being changed to APPROVED or REJECTED, set approved_by and approved_at
        if old_status == WithdrawalRequestStatus.PENDING and new_status in [WithdrawalRequestStatus.APPROVED, WithdrawalRequestStatus.REJECTED]:
            serializer.save(
                approved_by=self.request.user,
                approved_at=timezone.now()
            )
        # If status is being changed to COMPLETED, set completed_at
        elif old_status == WithdrawalRequestStatus.APPROVED and new_status == WithdrawalRequestStatus.COMPLETED:
            serializer.save(completed_at=timezone.now())
        else:
            serializer.save()
    
    @action(detail=True, methods=["post"], url_path="approve")
    def approve_withdrawal(self, request, pk=None):
        """Approve a withdrawal request."""
        withdrawal = self.get_object()
        
        if withdrawal.status != WithdrawalRequestStatus.PENDING:
            return Response(
                {"detail": f"Hanya permintaan dengan status PENDING yang dapat disetujui. Status saat ini: {withdrawal.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        withdrawal.status = WithdrawalRequestStatus.APPROVED
        withdrawal.approved_by = request.user
        withdrawal.approved_at = timezone.now()
        withdrawal.save()
        
        serializer = self.get_serializer(withdrawal)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"], url_path="reject")
    def reject_withdrawal(self, request, pk=None):
        """Reject a withdrawal request."""
        withdrawal = self.get_object()
        
        if withdrawal.status != WithdrawalRequestStatus.PENDING:
            return Response(
                {"detail": f"Hanya permintaan dengan status PENDING yang dapat ditolak. Status saat ini: {withdrawal.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        admin_notes = request.data.get("admin_notes", "")
        
        withdrawal.status = WithdrawalRequestStatus.REJECTED
        withdrawal.approved_by = request.user
        withdrawal.approved_at = timezone.now()
        if admin_notes:
            withdrawal.admin_notes = admin_notes
        withdrawal.save()
        
        serializer = self.get_serializer(withdrawal)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"], url_path="complete")
    def complete_withdrawal(self, request, pk=None):
        """Mark a withdrawal as completed (payment sent)."""
        withdrawal = self.get_object()
        
        if withdrawal.status != WithdrawalRequestStatus.APPROVED:
            return Response(
                {"detail": f"Hanya permintaan dengan status APPROVED yang dapat diselesaikan. Status saat ini: {withdrawal.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        withdrawal.status = WithdrawalRequestStatus.COMPLETED
        withdrawal.completed_at = timezone.now()
        withdrawal.save()
        
        serializer = self.get_serializer(withdrawal)
        return Response(serializer.data)

