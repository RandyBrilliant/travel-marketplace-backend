from django.db import models
from django.contrib.auth.models import AbstractUser
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