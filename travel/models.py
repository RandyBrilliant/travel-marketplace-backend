from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class TourCategory(models.TextChoices):
    """Tour category/tag options."""
    ADVENTURE = "ADVENTURE", _("Adventure")
    CULTURAL = "CULTURAL", _("Cultural")
    BEACH = "BEACH", _("Beach")
    CITY_BREAK = "CITY_BREAK", _("City Break")
    NATURE = "NATURE", _("Nature")
    FAMILY = "FAMILY", _("Family")


class TourBadge(models.TextChoices):
    """Featured badge options for tours."""
    BEST_SELLER = "BEST_SELLER", _("Best Seller")
    POPULAR = "POPULAR", _("Popular")
    TOP_RATED = "TOP_RATED", _("Top Rated")
    NEW = "NEW", _("New")


class TourType(models.TextChoices):
    """Tour type options for Indonesian citizens."""
    CONVENTIONAL = "CONVENTIONAL", _("Conventional Tour")
    MUSLIM = "MUSLIM", _("Muslim Tour")


class ResellerGroup(models.Model):
    """
    Group of resellers that can be assigned to specific tour packages.
    Allows suppliers to control which resellers can see and book specific tours.
    """
    
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the reseller group."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the group and its purpose."),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_reseller_groups",
        help_text=_("User who created this group (supplier or admin)."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this group is active."),
    )
    
    # Resellers in this group
    resellers = models.ManyToManyField(
        "account.ResellerProfile",
        related_name="reseller_groups",
        blank=True,
        help_text=_("Resellers belonging to this group."),
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Reseller Group"
        verbose_name_plural = "Reseller Groups"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["name"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.resellers.count()} resellers)"


class TourPackage(models.Model):
    """
    A tour product listed by a supplier (e.g. '3D2N Bali Getaway').
    
    Only suppliers can create tours. Commission settings are admin-only editable.
    """

    supplier = models.ForeignKey(
        "account.SupplierProfile",
        on_delete=models.CASCADE,
        related_name="packages",
        help_text=_("Supplier who created and owns this tour package."),
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    summary = models.TextField()
    description = models.TextField(
        blank=True,
        help_text=_("Detailed description of the tour package."),
    )

    # Location information
    city = models.CharField(
        max_length=255,
        help_text=_("City where the tour takes place (e.g., 'Beijing', 'Tokyo')."),
    )
    country = models.CharField(
        max_length=255,
        help_text=_("Country where the tour takes place (e.g., 'China', 'Japan')."),
    )

    # Duration
    days = models.PositiveIntegerField(
        help_text=_("Number of days for the tour."),
    )
    nights = models.PositiveIntegerField(
        help_text=_("Number of nights for the tour."),
    )

    # Group information
    max_group_size = models.PositiveIntegerField(
        default=12,
        help_text=_("Maximum number of participants in a group."),
    )
    group_type = models.CharField(
        max_length=50,
        default="Small Group",
        help_text=_("Type of group (e.g., 'Small Group', 'Private', 'Large Group')."),
    )

    # Tour type (for Indonesian citizens)
    tour_type = models.CharField(
        max_length=20,
        choices=TourType.choices,
        default=TourType.CONVENTIONAL,
        help_text=_("Tour type: Conventional Tour or Muslim Tour (for Indonesian citizens)."),
    )

    # Categories/Tags
    category = models.CharField(
        max_length=50,
        choices=TourCategory.choices,
        help_text=_("Primary category for the tour."),
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Additional tags/categories as a list of strings."),
    )

    # Highlights/Features
    highlights = models.JSONField(
        default=list,
        help_text=_("List of key highlights/attractions (e.g., ['Forbidden City', 'Great Wall'])."),
    )

    # What's included/excluded
    inclusions = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of what's included (e.g., ['Hotel accommodation', 'Breakfast', 'Transportation'])."),
    )
    exclusions = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of what's not included (e.g., ['International flights', 'Travel insurance'])."),
    )

    # Additional information
    meeting_point = models.CharField(
        max_length=500,
        blank=True,
        help_text=_("Where participants should meet for the tour."),
    )
    cancellation_policy = models.TextField(
        blank=True,
        help_text=_("Cancellation and refund policy details."),
    )
    important_notes = models.TextField(
        blank=True,
        help_text=_("Important information participants should know."),
    )

    # Pricing
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Reference price; actual price can vary per date."),
    )
    currency = models.CharField(
        max_length=10,
        default="USD",
        help_text=_("Currency code (e.g., 'USD', 'IDR')."),
    )

    # Featured badge
    badge = models.CharField(
        max_length=20,
        choices=TourBadge.choices,
        blank=True,
        null=True,
        help_text=_("Featured badge (e.g., 'BEST_SELLER', 'POPULAR')."),
    )

    # Images
    main_image = models.ImageField(
        upload_to="tours/main/",
        blank=True,
        null=True,
        help_text=_("Main featured image for the tour."),
    )

    # Itinerary PDF
    itinerary_pdf = models.FileField(
        upload_to="tours/itineraries/",
        blank=True,
        null=True,
        help_text=_("PDF file containing the detailed itinerary for the tour package."),
    )

    # Commission settings (Admin-only editable)
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(100.00)],
        help_text=_("Default commission percentage for resellers (0-100). Admin-only field."),
    )
    commission_type = models.CharField(
        max_length=20,
        choices=[
            ("PERCENTAGE", _("Percentage")),
            ("FIXED", _("Fixed Amount")),
        ],
        default="PERCENTAGE",
        help_text=_("Type of commission calculation. Admin-only field."),
    )
    fixed_commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Fixed commission amount (if commission_type is FIXED). Admin-only field."),
    )
    commission_notes = models.TextField(
        blank=True,
        help_text=_("Admin notes about commission settings for this tour."),
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(
        default=False,
        help_text=_("Whether to feature this tour on the homepage."),
    )
    
    # Reseller groups that can access this tour package
    # If empty, tour is visible to all resellers
    # If not empty, only resellers in these groups can see this tour
    reseller_groups = models.ManyToManyField(
        ResellerGroup,
        related_name="tour_packages",
        blank=True,
        help_text=_(
            "Reseller groups that can access this tour package. "
            "If empty, tour is visible to all resellers. "
            "If not empty, only resellers in these groups can see this tour."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["city", "country"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["tour_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.city}, {self.country}"
    
    @property
    def duration_display(self):
        """Return formatted duration string (e.g., '5 Day / 4 Night')."""
        return f"{self.days} Day{'s' if self.days != 1 else ''} / {self.nights} Night{'s' if self.nights != 1 else ''}"
    
    @property
    def group_size_display(self):
        """Return formatted group size string (e.g., 'Small Group (Max 12)')."""
        return f"{self.group_type} (Max {self.max_group_size})"
    
    def calculate_commission(self, booking_amount):
        """
        Calculate commission amount based on commission settings.
        Returns the commission amount in the same currency as booking_amount.
        """
        if self.commission_type == "PERCENTAGE":
            return (booking_amount * self.commission_rate) / 100
        elif self.commission_type == "FIXED" and self.fixed_commission_amount:
            return self.fixed_commission_amount
        return 0.00
    
    def get_reseller_commission(self, reseller):
        """
        Get the fixed commission amount for a specific reseller for this tour package.
        Returns the commission amount from ResellerTourCommission if exists, otherwise None.
        """
        try:
            commission = ResellerTourCommission.objects.get(
                reseller=reseller,
                tour_package=self,
                is_active=True
            )
            return commission.commission_amount
        except ResellerTourCommission.DoesNotExist:
            return None


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
    
    def generate_seat_slots(self):
        """
        Generate seat slots for this tour date based on total_seats.
        Can be called after creating a TourDate to auto-create all slots.
        """
        existing_count = self.seat_slots.count()
        if existing_count >= self.total_seats:
            return
        
        slots_to_create = []
        for i in range(existing_count + 1, self.total_seats + 1):
            slots_to_create.append(
                SeatSlot(
                    tour_date=self,
                    seat_number=str(i),
                    status=SeatSlotStatus.AVAILABLE,
                )
            )
        
        SeatSlot.objects.bulk_create(slots_to_create)
        # Update remaining_seats
        self.remaining_seats = self.seat_slots.filter(
            status=SeatSlotStatus.AVAILABLE
        ).count()
        self.save(update_fields=['remaining_seats'])
    
    @property
    def available_seats_count(self):
        """Return count of available seat slots."""
        return self.seat_slots.filter(status=SeatSlotStatus.AVAILABLE).count()
    
    @property
    def booked_seats_count(self):
        """Return count of booked seat slots."""
        return self.seat_slots.filter(status=SeatSlotStatus.BOOKED).count()
    
    def save(self, *args, **kwargs):
        """Auto-generate seat slots if this is a new TourDate."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Auto-generate slots for new tour dates
        if is_new:
            self.generate_seat_slots()


class TourImage(models.Model):
    """
    Additional images for a tour package (gallery).
    """
    
    package = models.ForeignKey(
        TourPackage,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to="tours/gallery/",
        help_text=_("Tour gallery image."),
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Optional caption for the image."),
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order (lower numbers appear first)."),
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=_("Whether this is a primary image (shown first)."),
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["order", "id"]
    
    def __str__(self) -> str:
        return f"{self.package.name} - Image {self.order}"


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


class SeatSlotStatus(models.TextChoices):
    """Status of individual seat slots."""
    AVAILABLE = "AVAILABLE", _("Available")
    RESERVED = "RESERVED", _("Reserved")
    BOOKED = "BOOKED", _("Booked")
    CANCELLED = "CANCELLED", _("Cancelled")


class SeatSlot(models.Model):
    """
    Individual seat slot for a tour date.
    Each slot can store passenger information (passport, visa, etc.)
    and can be linked to a booking.
    """
    
    tour_date = models.ForeignKey(
        TourDate,
        on_delete=models.CASCADE,
        related_name="seat_slots",
    )
    seat_number = models.CharField(
        max_length=20,
        help_text=_("Seat identifier (e.g., 'A1', 'B12', or sequential number)."),
    )
    booking = models.ForeignKey(
        "Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seat_slots",
        help_text=_("Booking this seat belongs to (null if available)."),
    )
    status = models.CharField(
        max_length=20,
        choices=SeatSlotStatus.choices,
        default=SeatSlotStatus.AVAILABLE,
    )
    
    # Passenger information (filled when seat is booked)
    passenger_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Full name of the passenger."),
    )
    passenger_email = models.EmailField(blank=True)
    passenger_phone = models.CharField(max_length=50, blank=True)
    passenger_date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text=_("Passenger date of birth."),
    )
    passenger_gender = models.CharField(
        max_length=10,
        choices=[
            ("MALE", _("Male")),
            ("FEMALE", _("Female")),
            ("OTHER", _("Other")),
        ],
        blank=True,
    )
    passenger_nationality = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Passenger nationality (country code or name)."),
    )
    
    # Passport information
    passport_number = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Passport number."),
    )
    passport_issue_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Passport issue date."),
    )
    passport_expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Passport expiry date."),
    )
    passport_issue_country = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Country that issued the passport."),
    )
    
    # Visa information
    visa_required = models.BooleanField(
        default=False,
        help_text=_("Whether visa is required for this passenger."),
    )
    visa_number = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Visa number if applicable."),
    )
    visa_issue_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Visa issue date."),
    )
    visa_expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Visa expiry date."),
    )
    visa_type = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Type of visa (e.g., 'Tourist', 'Business', 'Transit')."),
    )
    
    # Additional information
    special_requests = models.TextField(
        blank=True,
        help_text=_("Special requests or dietary restrictions."),
    )
    emergency_contact_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Emergency contact name."),
    )
    emergency_contact_phone = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Emergency contact phone number."),
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("tour_date", "seat_number")
        ordering = ["tour_date", "seat_number"]
        indexes = [
            models.Index(fields=["tour_date", "status"]),
            models.Index(fields=["booking"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.tour_date} - Seat {self.seat_number} ({self.status})"


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
        "account.ResellerProfile",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    tour_date = models.ForeignKey(
        TourDate,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    customer_name = models.CharField(
        max_length=255,
        help_text=_("Primary customer/contact name for this booking."),
    )
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=50, blank=True)

    # Keep seats_booked for backward compatibility and quick reference
    # It should match the count of seat_slots linked to this booking
    seats_booked = models.PositiveIntegerField(
        help_text=_("Number of seats booked. Should match seat_slots count."),
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
    )

    # Platform fee (fixed at Rp. 50,000)
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50000.00,
        help_text=_("Platform fee in IDR (default: Rp. 50,000)."),
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Booking #{self.pk} - {self.tour_date} ({self.seats_booked} seats)"
    
    @property
    def actual_seats_count(self):
        """Return the actual count of seat slots linked to this booking."""
        return self.seat_slots.count()
    
    def save(self, *args, **kwargs):
        """Auto-update seats_booked to match actual seat slots count."""
        if self.pk:
            self.seats_booked = self.actual_seats_count
        super().save(*args, **kwargs)


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


class ResellerTourCommission(models.Model):
    """
    Commission settings per reseller per tour package.
    Each reseller can have a different fixed commission amount for each tour package.
    """

    reseller = models.ForeignKey(
        "account.ResellerProfile",
        on_delete=models.CASCADE,
        related_name="tour_commissions",
        help_text=_("Reseller who will receive this commission."),
    )
    tour_package = models.ForeignKey(
        TourPackage,
        on_delete=models.CASCADE,
        related_name="reseller_commissions",
        help_text=_("Tour package this commission applies to."),
    )
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Fixed commission amount for this reseller for this tour package."),
    )
    currency = models.CharField(
        max_length=10,
        default="IDR",
        help_text=_("Currency code (e.g., 'IDR', 'USD')."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this commission setting is active."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("reseller", "tour_package")
        ordering = ["-created_at"]
        verbose_name = "Reseller Tour Commission"
        verbose_name_plural = "Reseller Tour Commissions"
        indexes = [
            models.Index(fields=["reseller", "is_active"]),
            models.Index(fields=["tour_package", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.reseller.full_name} - {self.tour_package.name}: {self.commission_amount} {self.currency}"


class ResellerCommission(models.Model):
    """
    Commission entries per reseller per booking.

    This supports:
    - the reseller who made the booking (level 0), and
    - their uplines (level 1, 2, ...) for override commissions.
    """

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="commissions",
    )
    reseller = models.ForeignKey(
        "account.ResellerProfile",
        on_delete=models.CASCADE,
        related_name="commissions",
    )
    level = models.PositiveSmallIntegerField(
        default=0,
        help_text=_("0 = booking owner, 1 = direct upline, 2+ = higher levels."),
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Reseller Commission"
        verbose_name_plural = "Reseller Commissions"
        indexes = [
            models.Index(fields=["reseller", "level"]),
        ]

    def __str__(self) -> str:
        return f"Commission {self.amount} for {self.reseller} (booking #{self.booking_id}, level {self.level})"
