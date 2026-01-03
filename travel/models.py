from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta


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
        unique=True,
        help_text=_("Name of the reseller group (must be unique)."),
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
    base_price = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Reference price in IDR (Indonesian Rupiah). Must be at least 1 IDR. Actual price can vary per date."),
    )
    currency = models.CharField(
        max_length=10,
        default="IDR",
        help_text=_("Currency code. Defaults to IDR (Indonesian Rupiah)."),
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
    fixed_commission_amount = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Fixed commission amount in IDR (if commission_type is FIXED). Admin-only field."),
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
            models.Index(fields=["supplier", "is_active"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(nights__lte=models.F('days')),
                name='nights_not_greater_than_days'
            ),
            models.CheckConstraint(
                check=models.Q(fixed_commission_amount__isnull=True) | 
                       (models.Q(commission_type='FIXED') & models.Q(fixed_commission_amount__gte=1)),
                name='fixed_commission_valid_when_fixed_type'
            ),
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
        Returns the commission amount in IDR as an integer.
        """
        if self.commission_type == "PERCENTAGE":
            # Calculate percentage and round to nearest integer (IDR doesn't have decimals)
            return int(round((booking_amount * self.commission_rate) / 100))
        elif self.commission_type == "FIXED" and self.fixed_commission_amount:
            return self.fixed_commission_amount
        return 0
    
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
    
    @classmethod
    def get_active_tours(cls):
        """Get all active tour packages."""
        return cls.objects.filter(is_active=True)
    
    @classmethod
    def get_featured_tours(cls):
        """Get featured and active tour packages."""
        return cls.objects.filter(is_active=True, is_featured=True)


class TourDate(models.Model):
    """
    A specific departure date for a package, with its own price & seat inventory.
    """

    package = models.ForeignKey(
        TourPackage,
        on_delete=models.CASCADE,
        related_name="dates",
    )
    departure_date = models.DateField(
        help_text=_("Departure date for this tour. Must be in the future.")
    )
    price = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Price per person in IDR (Indonesian Rupiah) for this tour date. Must be greater than zero.")
    )
    total_seats = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Total number of seats available. Must be at least 1.")
    )

    is_high_season = models.BooleanField(
        default=False,
        help_text=_("Mark if this date is considered high season."),
    )

    class Meta:
        unique_together = ("package", "departure_date")
        ordering = ["departure_date"]
        verbose_name = "Tour Date"
        verbose_name_plural = "Tour Dates"
        indexes = [
            models.Index(fields=["package", "departure_date"]),
            models.Index(fields=["departure_date", "is_high_season"]),
            models.Index(fields=["package", "is_high_season"]),
        ]
    
    def clean(self):
        """Validate departure date and price."""
        super().clean()
        
        if self.departure_date:
            today = timezone.now().date()
            
            # Ensure departure date is in the future
            if self.departure_date < today:
                raise ValidationError({
                    'departure_date': 'Departure date must be in the future.'
                })
            
            # Optional: Limit advance bookings (e.g., 2 years)
            max_future_date = today + timedelta(days=730)
            if self.departure_date > max_future_date:
                raise ValidationError({
                    'departure_date': 'Departure date cannot be more than 2 years in the future.'
                })
        
        if self.price is not None and self.price < 1:
            raise ValidationError({
                'price': 'Price must be at least 1 IDR.'
            })
    
    def save(self, *args, **kwargs):
        """Validate and auto-generate seat slots if this is a new TourDate."""
        self.full_clean()  # Enforce validation
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Auto-generate slots for new tour dates
        if is_new:
            self.generate_seat_slots()

    def __str__(self) -> str:
        return f"{self.package.name} - {self.departure_date}"
    
    def generate_seat_slots(self):
        """
        Generate seat slots for this tour date based on total_seats.
        Can be called after creating a TourDate to auto-create all slots.
        """
        existing_slots = set(self.seat_slots.values_list('seat_number', flat=True))
        existing_count = len(existing_slots)
        
        if existing_count >= self.total_seats:
            return
        
        slots_to_create = []
        slot_num = 1
        
        while len(slots_to_create) + existing_count < self.total_seats:
            # Find next available seat number
            while str(slot_num) in existing_slots:
                slot_num += 1
            
            slots_to_create.append(
                SeatSlot(
                    tour_date=self,
                    seat_number=str(slot_num),
                    status=SeatSlotStatus.AVAILABLE,
                )
            )
            existing_slots.add(str(slot_num))
            slot_num += 1
        
        if slots_to_create:
            SeatSlot.objects.bulk_create(slots_to_create)
    
    @property
    def remaining_seats(self):
        """Calculate remaining seats dynamically from seat slots."""
        return self.seat_slots.filter(status=SeatSlotStatus.AVAILABLE).count()
    
    @property
    def available_seats_count(self):
        """Return count of available seat slots."""
        return self.remaining_seats
    
    @property
    def booked_seats_count(self):
        """Return count of booked seat slots."""
        return self.seat_slots.filter(status=SeatSlotStatus.BOOKED).count()
    
    @classmethod
    def get_available_dates(cls, package=None):
        """
        Get tour dates with available seats.
        
        Args:
            package: Optional TourPackage to filter by
        
        Returns:
            QuerySet of TourDate objects with available seats
        """
        queryset = cls.objects.filter(
            seat_slots__status=SeatSlotStatus.AVAILABLE
        ).distinct()
        if package:
            queryset = queryset.filter(package=package)
        return queryset


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
        help_text=_("Whether this is a primary image (shown first). Only one primary image allowed per package."),
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Tour Image"
        verbose_name_plural = "Tour Images"
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["package", "is_primary"]),
        ]
    
    def clean(self):
        """Validate that only one primary image exists per package."""
        super().clean()
        if self.is_primary:
            existing_primary = TourImage.objects.filter(
                package=self.package,
                is_primary=True
            ).exclude(pk=self.pk if self.pk else None)
            if existing_primary.exists():
                raise ValidationError({
                    'is_primary': 'Only one primary image is allowed per tour package.'
                })
    
    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)
    
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
        verbose_name = "Itinerary Item"
        verbose_name_plural = "Itinerary Items"
        unique_together = ("package", "day_number")
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
    
    Each seat slot represents one passenger seat. When booked, it stores complete
    passenger information including passport, visa, and contact details.
    
    Important: Each seat = one passenger. One booking can have multiple seat slots
    (multiple passengers), but each seat slot has its own passenger details.
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
        verbose_name = "Seat Slot"
        verbose_name_plural = "Seat Slots"
        unique_together = ("tour_date", "seat_number")
        ordering = ["tour_date", "seat_number"]
        indexes = [
            models.Index(fields=["tour_date", "status"]),
            models.Index(fields=["booking"]),
            models.Index(fields=["booking", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["passenger_email"]),
            models.Index(fields=["passport_number"]),
        ]
    
    def clean(self):
        """Validate seat slot status transitions and passenger information."""
        super().clean()
        
        # Validate status transitions
        if self.pk:  # Only validate on updates
            try:
                old_instance = SeatSlot.objects.get(pk=self.pk)
                old_status = old_instance.status
                new_status = self.status
                
                # Define valid transitions
                valid_transitions = {
                    SeatSlotStatus.AVAILABLE: [SeatSlotStatus.RESERVED, SeatSlotStatus.BOOKED],
                    SeatSlotStatus.RESERVED: [SeatSlotStatus.BOOKED, SeatSlotStatus.AVAILABLE, SeatSlotStatus.CANCELLED],
                    SeatSlotStatus.BOOKED: [SeatSlotStatus.CANCELLED],
                    SeatSlotStatus.CANCELLED: []  # Terminal state
                }
                
                if old_status != new_status:
                    if new_status not in valid_transitions.get(old_status, []):
                        raise ValidationError({
                            'status': f'Invalid status transition from {old_status} to {new_status}.'
                        })
            except SeatSlot.DoesNotExist:
                pass  # New instance, no validation needed
        
        # If status is BOOKED, require passenger information and booking
        if self.status == SeatSlotStatus.BOOKED:
            if not self.booking:
                raise ValidationError({
                    'booking': 'Booking is required when seat status is BOOKED.'
                })
            if not self.passenger_name:
                raise ValidationError({
                    'passenger_name': 'Passenger name is required when seat is booked.'
                })
            if not self.passenger_email:
                raise ValidationError({
                    'passenger_email': 'Passenger email is required when seat is booked.'
                })
            if not self.passport_number:
                raise ValidationError({
                    'passport_number': 'Passport number is required for booked seats.'
                })
        
        # Validate booking tour_date matches seat tour_date
        if self.booking and self.booking.tour_date != self.tour_date:
            raise ValidationError({
                'booking': 'Booking tour date must match seat slot tour date.'
            })
        
        # Validate passport dates
        if self.passport_issue_date and self.passport_expiry_date:
            if self.passport_expiry_date <= self.passport_issue_date:
                raise ValidationError({
                    'passport_expiry_date': 'Passport expiry date must be after issue date.'
                })
            
            # Check if expired
            if self.passport_expiry_date < timezone.now().date():
                raise ValidationError({
                    'passport_expiry_date': 'Passport has already expired.'
                })
        
        # Validate visa dates
        if self.visa_required:
            if not self.visa_number:
                raise ValidationError({
                    'visa_number': 'Visa number is required when visa is required.'
                })
        
        if self.visa_issue_date and self.visa_expiry_date:
            if self.visa_expiry_date <= self.visa_issue_date:
                raise ValidationError({
                    'visa_expiry_date': 'Visa expiry date must be after issue date.'
                })
    
    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self) -> str:
        return f"{self.tour_date} - Seat {self.seat_number} ({self.status})"


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    CONFIRMED = "CONFIRMED", _("Confirmed")
    CANCELLED = "CANCELLED", _("Cancelled")


class Booking(models.Model):
    """
    A reseller booking a specific tour date on behalf of their customer.
    
    IMPORTANT: Understanding customer vs passengers:
    - customer_name/email/phone: The BOOKING CONTACT (person making the booking)
      This is typically the reseller's client, group organizer, or travel agent contact.
      This person may or may not be one of the actual passengers.
    
    - seat_slots: Multiple SeatSlot objects, each representing ONE PASSENGER
      Each SeatSlot has its own passenger details (name, passport, visa, etc.)
      One booking can have multiple seat slots (multiple passengers).
    
    Example:
    - Reseller "ABC Travel" creates a booking
    - customer_name: "John Smith" (the booking contact/organizer)
    - seat_slots: 5 seats
      - Seat 1: passenger_name "John Smith" (also a passenger)
      - Seat 2: passenger_name "Jane Smith" (John's wife)
      - Seat 3: passenger_name "Bob Johnson" (friend)
      - Seat 4: passenger_name "Alice Johnson" (Bob's wife)
      - Seat 5: passenger_name "Charlie Brown" (another friend)
    
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
        help_text=_(
            "Primary booking contact name (person making the booking). "
            "This may or may not be the same as the passengers. "
            "For group bookings, this is typically the group organizer or travel agent contact."
        ),
    )
    customer_email = models.EmailField(
        help_text=_("Email of the booking contact (for booking confirmations and communication).")
    )
    customer_phone = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Phone number of the booking contact.")
    )

    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
    )

    # Platform fee (fixed at Rp. 50,000)
    platform_fee = models.PositiveIntegerField(
        default=50000,
        help_text=_("Platform fee in IDR (default: Rp. 50,000)."),
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reseller", "status"]),
            models.Index(fields=["tour_date", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Booking #{self.pk} - {self.tour_date} ({self.seats_booked} seats)"
    
    @property
    def seats_booked(self):
        """Return the actual count of seat slots linked to this booking."""
        return self.seat_slots.count()
    
    @property
    def passengers(self):
        """Return all passengers (seat slots) for this booking."""
        return self.seat_slots.select_related('tour_date').all()
    
    @property
    def passenger_count(self):
        """Return number of passengers."""
        return self.seats_booked
    
    @property
    def booking_contact_is_passenger(self):
        """Check if booking contact is also a passenger."""
        return self.seat_slots.filter(
            passenger_email=self.customer_email
        ).exists()
    
    @property
    def total_amount(self):
        """Calculate total booking amount (tour price * seats + platform fee)."""
        return (
            self.tour_date.price * self.seats_booked +
            self.platform_fee
        )
    
    @property
    def subtotal(self):
        """Tour date price * number of seats (before platform fee)."""
        return self.tour_date.price * self.seats_booked
    
    def get_passenger_by_seat(self, seat_number):
        """Get passenger details for a specific seat."""
        return self.seat_slots.filter(seat_number=seat_number).first()
    
    def can_be_cancelled(self):
        """Check if booking can be cancelled."""
        return self.status == BookingStatus.PENDING
    
    def can_be_confirmed(self):
        """Check if booking can be confirmed (has approved payment)."""
        return (
            self.status == BookingStatus.PENDING and
            hasattr(self, 'payment') and
            self.payment and
            self.payment.status == PaymentStatus.APPROVED
        )
    
    def clean(self):
        """Validate booking has at least one seat slot."""
        super().clean()
        if self.pk and self.seat_slots.count() == 0:
            raise ValidationError({
                'tour_date': 'Booking must have at least one seat slot.'
            })
    
    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
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
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Payment amount in IDR (Indonesian Rupiah). Must be greater than zero.")
    )
    currency = models.CharField(max_length=10, default="IDR")

    transfer_date = models.DateField(
        help_text=_("Date when the transfer was made. Cannot be in the future.")
    )
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
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]
    
    def clean(self):
        """Validate payment details."""
        super().clean()
        
        # Validate transfer date is not in the future
        if self.transfer_date:
            today = timezone.now().date()
            if self.transfer_date > today:
                raise ValidationError({
                    'transfer_date': 'Transfer date cannot be in the future.'
                })
    
    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)

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
    commission_amount = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Fixed commission amount in IDR for this reseller for this tour package. Must be greater than zero."),
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
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Commission amount in IDR (Indonesian Rupiah). Must be at least 1 IDR.")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Reseller Commission"
        verbose_name_plural = "Reseller Commissions"
        indexes = [
            models.Index(fields=["reseller", "level"]),
            models.Index(fields=["booking", "reseller"]),
        ]

    def __str__(self) -> str:
        return f"Commission {self.amount} for {self.reseller} (booking #{self.booking_id}, level {self.level})"
