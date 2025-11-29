from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class UserRole(models.TextChoices):
    """
    High-level roles for the marketplace.

    - SUPPLIER: Provides travel products (e.g., tours, stays, transport).
    - RESELLER: Sells/markets products, often under their own brand.
    - STAFF: Internal operations/admin staff, non-superuser by default.
    """

    SUPPLIER = "SUPPLIER", _("Supplier")
    RESELLER = "RESELLER", _("Reseller")
    STAFF = "STAFF", _("Admin staff")


class CustomUser(AbstractUser):
    email = models.EmailField(verbose_name="Email Address", unique=True)
    full_name = models.CharField(max_length=255, verbose_name="Full Name")

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.RESELLER,
        verbose_name="Role",
        help_text=_("High-level role used for permissions and routing."),
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
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} | {self.full_name} ({self.role})"

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
    company_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Supplier Profile"
        verbose_name_plural = "Supplier Profiles"
        indexes = [
            models.Index(fields=["company_name"]),
        ]

    def __str__(self) -> str:
        return f"{self.company_name} ({self.user.email})"

    def clean(self):
        # Ensure the linked user has the correct role.
        if self.user and self.user.role != UserRole.SUPPLIER:
            raise ValidationError(
                {"user": _("Linked user must have role SUPPLIER for SupplierProfile.")}
            )


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
    display_name = models.CharField(
        max_length=255,
        help_text=_("Public / brand name shown to customers."),
    )
    contact_phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

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
    own_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text=_(
            "Default percentage this reseller earns from the commissionable "
            "amount of their own bookings."
        ),
    )
    upline_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3.00,
        help_text=_(
            "Suggested percentage for direct upline override commissions, "
            "if your business logic uses it."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reseller Profile"
        verbose_name_plural = "Reseller Profiles"
        indexes = [
            models.Index(fields=["display_name"]),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.user.email})"

    def clean(self):
        if self.user and self.user.role != UserRole.RESELLER:
            raise ValidationError(
                {"user": _("Linked user must have role RESELLER for ResellerProfile.")}
            )

    def save(self, *args, **kwargs):
        """
        Automatically maintain group_root:
        - If there is no sponsor, this reseller is the root of their own group.
        - If there is a sponsor, inherit the sponsor's group_root (or sponsor themselves).
        """
        if self.sponsor:
            self.group_root = self.sponsor.group_root or self.sponsor
        else:
            self.group_root = self
        super().save(*args, **kwargs)

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
    job_title = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Staff Profile"
        verbose_name_plural = "Staff Profiles"

    def __str__(self) -> str:
        return f"{self.user.full_name} - {self.job_title or 'Staff'}"

    def clean(self):
        if self.user and self.user.role != UserRole.STAFF:
            raise ValidationError(
                {"user": _("Linked user must have role STAFF for StaffProfile.")}
            )
