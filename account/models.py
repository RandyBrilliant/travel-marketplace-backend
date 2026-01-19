from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class UserRole(models.TextChoices):
    SUPPLIER = "SUPPLIER", _("Supplier")
    RESELLER = "RESELLER", _("Reseller")
    STAFF = "STAFF", _("Admin staff")
    CUSTOMER = "CUSTOMER", _("Customer")


class CustomUser(AbstractUser):
    email = models.EmailField(verbose_name="Email Address", unique=True)
    role = models.CharField(
        max_length=8,
        choices=UserRole.choices,
        verbose_name="Role",
        help_text=_("High-level role used for permissions and routing."),
    )
    email_verified = models.BooleanField(
        default=False,
        verbose_name="Email Verified",
        help_text=_("Whether the email address has been verified."),
    )
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Email Verified At",
        help_text=_("Timestamp when email was verified."),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        editable=False,
        related_name="user_created_by",
        verbose_name="Created By",
    )
    updated_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        editable=False,
        related_name="user_updated_by",
        verbose_name="Updated By",
    )
    
    # We use email as the unique identifier instead of username/first/last name.
    username = None
    first_name = None
    last_name = None

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        roles_display = self.get_roles_display()
        return f"{self.email} | ({roles_display})"

    @property
    def is_supplier(self) -> bool:
        """
        Check if user has supplier profile (supports dual roles).
        Users can now have both supplier and reseller profiles.
        """
        return hasattr(self, 'supplier_profile')

    @property
    def is_reseller(self) -> bool:
        """
        Check if user has reseller profile (supports dual roles).
        Users can now have both supplier and reseller profiles.
        """
        return hasattr(self, 'reseller_profile')

    @property
    def is_customer(self) -> bool:
        """
        Check if user has customer profile.
        Customers are end-users who book tours.
        """
        return hasattr(self, 'customer_profile')

    @property
    def is_admin_staff(self) -> bool:
        """
        Convenience flag for your code to distinguish marketplace staff.
        Note: Django's `is_staff` is still used for admin-site access.
        """
        return self.role == UserRole.STAFF
    
    @property
    def has_supplier_role(self) -> bool:
        """
        Check if user's primary role is SUPPLIER (for backward compatibility).
        """
        return self.role == UserRole.SUPPLIER
    
    @property
    def has_reseller_role(self) -> bool:
        """
        Check if user's primary role is RESELLER (for backward compatibility).
        """
        return self.role == UserRole.RESELLER
    
    def get_roles_display(self) -> str:
        """
        Get a human-readable string of all roles this user has.
        Example: "Supplier, Reseller" or "Supplier" or "Reseller"
        """
        roles = []
        if self.is_supplier:
            roles.append("Supplier")
        if self.is_reseller:
            roles.append("Reseller")
        if self.is_customer:
            roles.append("Customer")
        if self.is_admin_staff:
            roles.append("Admin Staff")
        return ", ".join(roles) if roles else "No roles"
    

    class Meta:
        ordering = ["-is_active", "email"]
        verbose_name = "User"
        verbose_name_plural = "User List"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["email_verified"]),
            models.Index(fields=["is_active", "role", "email_verified"]),
        ]


class SupplierApprovalStatus(models.TextChoices):
    """Approval status for supplier accounts."""
    PENDING = "PENDING", _("Pending Approval")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class SupplierProfile(models.Model):
    """
    Additional business data for supplier accounts.

    Keeps authentication concerns in `CustomUser` and supplier-specific
    fields here, following the "user + profile" pattern.
    """

    user = models.OneToOneField(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="supplier_profile",
        # Removed limit_choices_to to allow users to have both supplier and reseller profiles
    )
    company_name = models.CharField(
        max_length=255,
        help_text=_("Official company/business name."),
    )
    contact_person = models.CharField(
        max_length=255,
        help_text=_("Primary contact person name."),
    )
    contact_phone = models.CharField(
        max_length=50,
        help_text=_("Primary contact phone number."),
    )
    address = models.TextField(
        blank=True,
        help_text=_("Business address."),
    )
    photo = models.ImageField(
        upload_to="profile_photos/suppliers/",
        blank=True,
        null=True,
        verbose_name="Profile Photo",
        help_text=_("Supplier profile photo."),
    )
    approval_status = models.CharField(
        max_length=20,
        choices=SupplierApprovalStatus.choices,
        default=SupplierApprovalStatus.PENDING,
        help_text=_("Approval status for supplier account. Suppliers need admin approval to access dashboard."),
    )
    approved_by = models.ForeignKey(
        "CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_suppliers",
        help_text=_("Admin user who approved this supplier."),
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the supplier was approved."),
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text=_("Reason for rejection (if rejected)."),
    )
    bank_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Bank Name",
        help_text=_("Bank name for commission payouts."),
    )
    bank_account_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Bank Account Name",
        help_text=_("Account holder name for commission payouts."),
    )
    bank_account_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Bank Account Number",
        help_text=_("Bank account number for commission payouts."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Supplier Profile"
        verbose_name_plural = "Supplier Profiles"
        indexes = [
            models.Index(fields=["company_name"]),
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["approval_status"]),
            models.Index(fields=["approval_status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.company_name} ({self.user.email})"
    
    @property
    def is_approved(self) -> bool:
        """Check if supplier is approved."""
        return self.approval_status == SupplierApprovalStatus.APPROVED
    
    @property
    def is_pending(self) -> bool:
        """Check if supplier is pending approval."""
        return self.approval_status == SupplierApprovalStatus.PENDING
    
    @property
    def is_rejected(self) -> bool:
        """Check if supplier is rejected."""
        return self.approval_status == SupplierApprovalStatus.REJECTED


class ResellerProfile(models.Model):
    """
    Reseller-specific data, including simple multi-level marketing (MLM)
    relationships and referral / verification code.
    """

    user = models.OneToOneField(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="reseller_profile",
        # Removed limit_choices_to to allow users to have both supplier and reseller profiles
    )
    full_name = models.CharField(
        max_length=255,
        help_text=_("Full name of the reseller."),
    )
    contact_phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(
        blank=True,
        help_text=_("Business address."),
    )

    # Verification / referral code used to invite new resellers into a group.
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_(
            "Code this reseller can share so new members join under them "
            "in the same group / team."
        ),
    )

    # MLM hierarchy: sponsor (direct upline) and group_root (top leader of tree).
    sponsor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_downlines",
        help_text=_("Direct upline / leader who invited this reseller."),
    )
    group_root = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="group_members",
        editable=False,
        help_text=_("Top-most leader in this reseller's tree. Set automatically."),
    )

    # Commission settings for this reseller (their own sales).
    base_commission = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_(
            "Base commission amount per seat (per passenger) for each sale made directly "
            "by this reseller. The actual commission will be multiplied by the number of seats in the booking."
        ),
    )
    
    # Banking information for commission payouts
    bank_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Bank Name",
        help_text=_("Bank name for commission payouts."),
    )
    bank_account_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Bank Account Name",
        help_text=_("Account holder name for commission payouts."),
    )
    bank_account_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Bank Account Number",
        help_text=_("Bank account number for commission payouts."),
    )
    photo = models.ImageField(
        upload_to="profile_photos/resellers/",
        blank=True,
        null=True,
        verbose_name="Profile Photo",
        help_text=_("Reseller profile photo."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reseller Profile"
        verbose_name_plural = "Reseller Profiles"
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["referral_code"]),
            models.Index(fields=["user"]),
            models.Index(fields=["sponsor"]),
            models.Index(fields=["group_root"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["sponsor", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.user.email})"

    def save(self, *args, **kwargs):
        """
        Automatically maintain group_root:
        - If there is no sponsor, this reseller is the root of their own group.
        - If there is a sponsor, inherit the sponsor's group_root (or sponsor themselves).
        """
        # Determine group_root based on sponsor
        if self.sponsor:
            # If sponsor exists, inherit their group_root (or use sponsor if no group_root)
            self.group_root = self.sponsor.group_root or self.sponsor
        # else: group_root will be set after save if this is a new instance
        
        # Save the instance first
        super().save(*args, **kwargs)
        
        # If no sponsor, this reseller is their own group root
        # Set it after save to avoid self-reference issues with new instances
        if not self.sponsor and not self.group_root:
            # Update only the group_root field using queryset to avoid recursion
            type(self).objects.filter(pk=self.pk).update(group_root_id=self.pk)
            # Refresh from DB to get updated group_root
            self.refresh_from_db()

    @property
    def direct_downline_count(self) -> int:
        """Convenience helper for dashboards."""
        return self.direct_downlines.count()

    def all_downlines(self):
        """
        Returns all downline members under this reseller (including all nested levels).
        This recursively traverses the tree by following the sponsor relationship.
        """
        from django.db.models import Q
        
        # Get all reseller IDs in the downline tree
        downline_ids = set()
        to_process = [self.pk]
        
        while to_process:
            # Get direct downlines of current batch
            current_id = to_process.pop(0)
            direct_downlines = type(self).objects.filter(
                sponsor_id=current_id
            ).values_list('id', flat=True)
            
            for downline_id in direct_downlines:
                if downline_id not in downline_ids:
                    downline_ids.add(downline_id)
                    to_process.append(downline_id)
        
        # Return queryset of all downlines
        if downline_ids:
            return type(self).objects.filter(id__in=downline_ids)
        else:
            return type(self).objects.none()
    
    def get_total_commission_earned(self):
        """
        Calculate total commission earned from all confirmed bookings.
        Only counts commissions from bookings with CONFIRMED status.
        """
        from travel.models import ResellerCommission, BookingStatus
        
        return ResellerCommission.objects.filter(
            reseller=self,
            booking__status=BookingStatus.CONFIRMED
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
    
    def get_commission_breakdown(self):
        """
        Get commission breakdown by source:
        - from_booking: Commission from own bookings (level 0)
        - from_downline: Commission from downline bookings (level 1+)
        - pending_commission: Commission from bookings that are not yet confirmed
        """
        from travel.models import ResellerCommission, BookingStatus
        
        # Commission from own bookings (level 0) - confirmed
        from_booking = ResellerCommission.objects.filter(
            reseller=self,
            level=0,
            booking__status=BookingStatus.CONFIRMED
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Commission from downline bookings (level 1+) - confirmed
        from_downline = ResellerCommission.objects.filter(
            reseller=self,
            level__gte=1,
            booking__status=BookingStatus.CONFIRMED
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Pending commission (from bookings that are not yet confirmed)
        pending_commission = ResellerCommission.objects.filter(
            reseller=self,
            booking__status=BookingStatus.PENDING
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return {
            'from_booking': from_booking,
            'from_downline': from_downline,
            'pending_commission': pending_commission,
        }
    
    def get_total_withdrawn(self):
        """
        Calculate total amount already withdrawn (approved or completed withdrawals).
        """
        from travel.models import WithdrawalRequest, WithdrawalRequestStatus
        
        return WithdrawalRequest.objects.filter(
            reseller=self,
            status__in=[WithdrawalRequestStatus.APPROVED, WithdrawalRequestStatus.COMPLETED]
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
    
    def get_pending_withdrawal_amount(self):
        """
        Calculate total amount in pending withdrawal requests.
        """
        from travel.models import WithdrawalRequest, WithdrawalRequestStatus
        
        return WithdrawalRequest.objects.filter(
            reseller=self,
            status=WithdrawalRequestStatus.PENDING
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
    
    def get_available_commission_balance(self):
        """
        Calculate available commission balance that can be withdrawn.
        
        Formula:
        Available Balance = Total Earned - Total Withdrawn - Pending Withdrawals
        
        Only commissions from CONFIRMED bookings are considered.
        """
        total_earned = self.get_total_commission_earned()
        total_withdrawn = self.get_total_withdrawn()
        pending_withdrawals = self.get_pending_withdrawal_amount()
        
        available = total_earned - total_withdrawn - pending_withdrawals
        return max(0, available)  # Ensure non-negative


class StaffProfile(models.Model):
    """
    Profile for internal admin / operations staff accounts.
    """

    user = models.OneToOneField(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="staff_profile",
        limit_choices_to={"role": UserRole.STAFF},
    )
    full_name = models.CharField(
        max_length=255,
        help_text=_("Full name of the staff member."),
    )
    contact_phone = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Contact phone number."),
    )
    photo = models.ImageField(
        upload_to="profile_photos/staff/",
        blank=True,
        null=True,
        verbose_name="Profile Photo",
        help_text=_("Staff profile photo."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Staff Profile"
        verbose_name_plural = "Staff Profiles"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.user.email})"


class CustomerProfile(models.Model):
    """
    Profile for customer accounts.
    Customers are end-users who browse and book tours.
    They do not get commission or referrals - just pure booking.
    """

    user = models.OneToOneField(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="customer_profile",
        limit_choices_to={"role": UserRole.CUSTOMER},
    )
    full_name = models.CharField(
        max_length=255,
        help_text=_("Full name of the customer.")
    )
    contact_phone = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Contact phone number.")
    )
    address = models.TextField(
        blank=True,
        help_text=_("Customer address for billing/shipping purposes.")
    )
    photo = models.ImageField(
        upload_to="profile_photos/customers/",
        blank=True,
        null=True,
        verbose_name="Profile Photo",
        help_text=_("Customer profile photo.")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["full_name"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.user.email})"
