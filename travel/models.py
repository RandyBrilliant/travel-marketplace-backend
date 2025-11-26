from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Supplier(models.Model):
    """
    Company or individual providing tour products.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="supplier_profile",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Reseller(models.Model):
    """
    Partner who sells/markets supplier products.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reseller_profile",
    )
    company_name = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.company_name or self.user.full_name


class TourPackage(models.Model):
    """
    A tour product listed by a supplier (e.g. '3D2N Bali Getaway').
    """

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="packages",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    summary = models.TextField()

    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Reference price; actual price can vary per date."),
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class TourDate(models.Model):
    """
    A specific departure date for a package, with its own price & seat inventory.
    """

    package = models.ForeignKey(
        TourPackage,
        on_delete=models.CASCADE,
        related_name="dates",
    )
    departure_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_seats = models.PositiveIntegerField()
    remaining_seats = models.PositiveIntegerField()

    is_high_season = models.BooleanField(
        default=False,
        help_text=_("Mark if this date is considered high season."),
    )

    class Meta:
        unique_together = ("package", "departure_date")
        ordering = ["departure_date"]

    def __str__(self) -> str:
        return f"{self.package.name} - {self.departure_date}"


class ItineraryItem(models.Model):
    """
    Daily/step itinerary attached to a package.
    """

    package = models.ForeignKey(
        TourPackage,
        on_delete=models.CASCADE,
        related_name="itinerary_items",
    )
    day_number = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["day_number", "id"]

    def __str__(self) -> str:
        return f"Day {self.day_number}: {self.title}"


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    CONFIRMED = "CONFIRMED", _("Confirmed")
    CANCELLED = "CANCELLED", _("Cancelled")


class Booking(models.Model):
    """
    A reseller booking a specific tour date on behalf of their customer.
    Admin staff will review & confirm after payment proof is uploaded.
    """

    reseller = models.ForeignKey(
        Reseller,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    tour_date = models.ForeignKey(
        TourDate,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=50, blank=True)

    seats_booked = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Booking #{self.pk} - {self.tour_date} ({self.seats_booked} seats)"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending review")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class Payment(models.Model):
    """
    Manual payment record where reseller uploads transfer proof and details.
    """

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="payment",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="IDR")

    transfer_date = models.DateField()
    sender_account_name = models.CharField(max_length=255)
    sender_bank_name = models.CharField(max_length=255)
    sender_account_number = models.CharField(max_length=64)

    proof_image = models.ImageField(
        upload_to="payments/proof/",
        blank=True,
        null=True,
        help_text=_("Upload of the bank transfer slip or screenshot."),
    )

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Payment for booking #{self.booking_id} - {self.amount} {self.currency}"
