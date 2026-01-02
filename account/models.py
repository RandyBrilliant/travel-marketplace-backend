from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class UserRole(models.TextChoices):
    """
    High-level roles for the marketplace.

    - SUPPLIER: Provides travel products.
    - RESELLER: Sells/markets products, get commission from sales.
    - STAFF: Internal operations/admin staff, non-superuser by default.
    """

    SUPPLIER = "SUPPLIER", _("Supplier")
    RESELLER = "RESELLER", _("Reseller")
    STAFF = "STAFF", _("Admin staff")


class CustomUser(AbstractUser):
    email = models.EmailField(verbose_name="Email Address", unique=True)
    role = models.CharField(
        max_length=20,
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
        return f"{self.email} | ({self.role})"

    @property
    def is_supplier(self) -> bool:
        return self.role == UserRole.SUPPLIER

    @property
    def is_reseller(self) -> bool:
        return self.role == UserRole.RESELLER

    @property
    def is_admin_staff(self) -> bool:
        """
        Convenience flag for your code to distinguish marketplace staff.
        Note: Django's `is_staff` is still used for admin-site access.
        """
        return self.role == UserRole.STAFF
    

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
        limit_choices_to={"role": UserRole.SUPPLIER},
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
        ]

    def __str__(self) -> str:
        return f"{self.company_name} ({self.user.email})"


class ResellerProfile(models.Model):
    """
    Reseller-specific data, including simple multi-level marketing (MLM)
    relationships and referral / verification code.
    """

    user = models.OneToOneField(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="reseller_profile",
        limit_choices_to={"role": UserRole.RESELLER},
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

    # Commission settings for this reseller (their own sales and downline override).
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(100.00)],
        help_text=_(
            "Default percentage this reseller earns from the commissionable "
            "amount of their own bookings (0-100)."
        ),
    )
    upline_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(100.00)],
        help_text=_(
            "Suggested percentage for direct upline override commissions, "
            "if your business logic uses it (0-100)."
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
        Returns all downline members in the same group tree (including deep levels).
        This uses group_root as a simple way to query all members under the same tree.
        """
        return type(self).objects.filter(group_root=self).exclude(pk=self.pk)


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


