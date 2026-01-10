from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta


class TourType(models.TextChoices):
    """Tour type options for Indonesian citizens."""
    CONVENTIONAL = "CONVENTIONAL", _("Conventional Tour")
    MUSLIM = "MUSLIM", _("Muslim Tour")


class SeatSlotStatus(models.TextChoices):
    """Status of individual seat slots."""
    AVAILABLE = "AVAILABLE", _("Available")
    RESERVED = "RESERVED", _("Reserved")
    BOOKED = "BOOKED", _("Booked")
    CANCELLED = "CANCELLED", _("Cancelled")


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    CONFIRMED = "CONFIRMED", _("Confirmed")
    CANCELLED = "CANCELLED", _("Cancelled")


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending review")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")

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
    itinerary = models.TextField(
        help_text=_("Day-by-day itinerary of the tour package."),
    )

    # Location information
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

    # Tour type (for Indonesian citizens)
    tour_type = models.CharField(
        max_length=20,
        choices=TourType.choices,
        default=TourType.CONVENTIONAL,
        help_text=_("Tour type: Conventional Tour or Muslim Tour (for Indonesian citizens)."),
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
    cancellation_policy = models.TextField(
        blank=True,
        help_text=_("Cancellation and refund policy details."),
    )
    important_notes = models.TextField(
        blank=True,
        help_text=_("Important information participants should know."),
    )

    # Pricing
    base_price = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text=_("Reference price in IDR (Indonesian Rupiah). Actual price can vary per date."),
        default=0,
    )
    visa_price = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text=_("Visa price in IDR (Indonesian Rupiah). Actual price can vary per date."),
        default=0,
    )
    tipping_price = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text=_("Tipping price in IDR (Indonesian Rupiah). Actual price can vary per date."),
        default=0,
    )

    # Itinerary PDF
    itinerary_pdf = models.FileField(
        upload_to="tours/itineraries/",
        blank=True,
        null=True,
        help_text=_("PDF file containing the detailed itinerary for the tour package."),
    )

    # Commission settings (Admin-only editable)
    commission = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text=_("Commission amount per seat (per passenger) in IDR for the tour package."),
        default=0,
    )

    # Status
    is_active = models.BooleanField(default=True)
    
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
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tour_type", "is_active"]),
            models.Index(fields=["supplier", "is_active"]),
            models.Index(fields=["slug"]),  # For slug-based lookups
            models.Index(fields=["country"]),  # For country filtering
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(nights__lte=models.F('days')),
                name='nights_not_greater_than_days'
            ),
            models.CheckConstraint(
                check=models.Q(commission__gte=0),
                name='commission_valid'
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name}, {self.country}"
    
    @property
    def duration_display(self):
        """Return formatted duration string (e.g., '5 Hari / 4 Malam')."""
        return f"{self.days} Hari / {self.nights} Malam"

    
    def get_reseller_commission(self, reseller):
        """
        Get the fixed commission amount per seat (per passenger) for a specific reseller for this tour package.
        Returns:
        - ResellerTourCommission.commission_amount if exists (reseller-specific override)
        - TourPackage.commission if ResellerTourCommission doesn't exist (general tour commission)
        - None if both are 0 or not set
        
        Note: This returns commission PER SEAT. The actual commission for a booking will be
        multiplied by the number of seats in the booking.
        """
        try:
            commission = ResellerTourCommission.objects.get(
                reseller=reseller,
                tour_package=self,
                is_active=True
            )
            return commission.commission_amount
        except ResellerTourCommission.DoesNotExist:
            # Fall back to tour package's general commission
            return self.commission if self.commission and self.commission > 0 else None
    
    @classmethod
    def get_active_tours(cls):
        """Get all active tour packages."""
        return cls.objects.filter(is_active=True)


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
    price = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text=_("Price per person in IDR (Indonesian Rupiah) for this tour date."),
        default=0,
    )
    total_seats = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Total number of seats available. Must be at least 1.")
    )
    airline = models.CharField(
        max_length=255,
        help_text=_("Airline for this tour date."),
        null=True,
        blank=True,
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
            models.Index(fields=["departure_date"]),  # For filtering by date range
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0),
                name='tour_date_price_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(total_seats__gte=1),
                name='tour_date_seats_positive'
            ),
        ]
    
    def clean(self):
        """Validate departure date and price."""
        super().clean()
        
        if self.departure_date:
            today = timezone.now().date()
            
            # Ensure departure date is in the future
            if self.departure_date < today:
                raise ValidationError({
                    'departure_date': 'Tanggal keberangkatan harus di masa depan.'
                })
            
            # Optional: Limit advance bookings (e.g., 2 years)
            max_future_date = today + timedelta(days=730)
            if self.departure_date > max_future_date:
                raise ValidationError({
                    'departure_date': 'Tanggal keberangkatan tidak boleh lebih dari 2 tahun ke depan.'
                })
        
        if self.price is not None and self.price < 0:
            raise ValidationError({
                'price': 'Harga tidak boleh negatif.'
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
        Optimized to use bulk_create for better performance.
        """
        existing_slots = set(
            self.seat_slots.values_list('seat_number', flat=True)
        )
        existing_count = len(existing_slots)
        
        if existing_count >= self.total_seats:
            return
        
        slots_to_create = []
        slots_needed = self.total_seats - existing_count
        
        # Convert existing slots to integers for comparison (handle both int and string formats)
        existing_nums = set()
        for slot in existing_slots:
            try:
                existing_nums.add(int(slot))
            except (ValueError, TypeError):
                # If seat_number is not numeric, skip numeric generation
                pass
        
        # Generate numeric seat numbers if all existing slots are numeric
        if existing_nums or not existing_slots:
            slot_num = 1
            while len(slots_to_create) < slots_needed:
                # Find next available seat number
                while slot_num in existing_nums:
                    slot_num += 1
                
                slots_to_create.append(
                    SeatSlot(
                        tour_date=self,
                        seat_number=str(slot_num),
                        status=SeatSlotStatus.AVAILABLE,
                    )
                )
                existing_nums.add(slot_num)
                slot_num += 1
        else:
            # If non-numeric seat numbers exist, use a different strategy
            # Generate slots with a prefix to avoid conflicts
            slot_num = existing_count + 1
            while len(slots_to_create) < slots_needed:
                seat_number = f"SEAT-{slot_num}"
                if seat_number not in existing_slots:
                    slots_to_create.append(
                        SeatSlot(
                            tour_date=self,
                            seat_number=seat_number,
                            status=SeatSlotStatus.AVAILABLE,
                        )
                    )
                slot_num += 1
        
        if slots_to_create:
            SeatSlot.objects.bulk_create(slots_to_create, batch_size=100)
    
    @property
    def remaining_seats(self):
        """Calculate remaining seats dynamically from seat slots.
        
        Excludes seats that are:
        - Status is CANCELLED, OR
        - Status is BOOKED (regardless of booking status - PENDING or CONFIRMED bookings make seats unavailable)
        
        This ensures that once a seat is booked (even with PENDING booking), it's no longer available
        for other resellers to book.
        
        Note: Uses a fresh query (not prefetched cache) to ensure accuracy after bookings are created.
        """
        from django.db.models import Q
        
        # Use a fresh query instead of prefetched cache to ensure we get the latest seat status
        # This is important because seat slots can be updated after the prefetch
        # Use the model from the related manager to avoid circular import
        SeatSlotModel = self.seat_slots.model
        return SeatSlotModel.objects.filter(
            tour_date=self
        ).exclude(
            Q(status=SeatSlotStatus.BOOKED)
        ).count()
    
    @property
    def available_seats_count(self):
        """Return count of available seat slots."""
        return self.remaining_seats
    
    @property
    def booked_seats_count(self):
        """Return count of booked seat slots.
        
        Note: Uses a fresh query (not prefetched cache) to ensure accuracy after bookings are created.
        """
        # Use a fresh query instead of prefetched cache to ensure we get the latest seat status
        # Use the model from the related manager to avoid circular import
        SeatSlotModel = self.seat_slots.model
        return SeatSlotModel.objects.filter(
            tour_date=self,
            status=SeatSlotStatus.BOOKED
        ).count()

    @property
    def duration_display(self):
        """Return formatted duration string (e.g., '24 Januari 2026 - 29 Januari 2026')."""
        end_date = self.departure_date + timedelta(days=self.package.days - 1)
        return f"{self.departure_date.strftime('%d %B %Y')} - {end_date.strftime('%d %B %Y')}"
    
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
                    'is_primary': 'Hanya satu gambar utama yang diperbolehkan per paket tur.'
                })
    
    def save(self, *args, **kwargs):
        """Validate before saving, with better error handling."""
        try:
            self.full_clean()
        except ValidationError as e:
            # Provide better error messages
            if 'image' in e.message_dict:
                raise ValidationError({
                    'image': ['Gambar wajib diisi. Silakan pilih file gambar untuk diunggah.']
                })
            raise
        super().save(*args, **kwargs)
    
    def __str__(self) -> str:
        return f"{self.package.name} - Image {self.order}"


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
        db_index=True,  # Index for faster lookups by seat number
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
    
    # Passport information
    passport = models.ImageField(
        upload_to="passports/",
        blank=True,
        null=True,
        help_text=_("Passport image."),
    )
    
    # Visa information
    visa_required = models.BooleanField(
        default=False,
        help_text=_("Whether visa is required for this passenger."),
    )
    
    # Additional information
    special_requests = models.TextField(
        blank=True,
        help_text=_("Special requests or dietary restrictions."),
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
            models.Index(fields=["tour_date", "booking"]),  # For booking-related queries
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(seat_number=''),
                name='seat_number_not_empty'
            ),
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
                            'status': f'Transisi status tidak valid dari {old_status} ke {new_status}.'
                        })
            except SeatSlot.DoesNotExist:
                pass  # New instance, no validation needed
        
        # If status is BOOKED, require passenger information and booking
        if self.status == SeatSlotStatus.BOOKED:
            if not self.booking:
                raise ValidationError({
                    'booking': 'Booking wajib diisi ketika status kursi adalah BOOKED.'
                })
            if not self.passenger_name:
                raise ValidationError({
                    'passenger_name': 'Nama penumpang wajib diisi ketika kursi dipesan.'
                })
        
        # Validate booking tour_date matches seat tour_date
        if self.booking and self.booking.tour_date != self.tour_date:
            raise ValidationError({
                'booking': 'Tanggal tur booking harus sesuai dengan tanggal tur kursi.'
            })
    
    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self) -> str:
        return f"{self.tour_date} - Seat {self.seat_number} ({self.status})"



class Booking(models.Model):
    """
    A reseller booking a specific tour date on behalf of their customer.
    
    IMPORTANT: Understanding passengers:
    - seat_slots: Multiple SeatSlot objects, each representing ONE PASSENGER
      Each SeatSlot has its own passenger details (name, passport image, visa requirement, etc.)
      One booking can have multiple seat slots (multiple passengers).
    
    Example:
    - Reseller "ABC Travel" creates a booking
    - seat_slots: 5 seats
      - Seat 1: passenger_name "John Smith"
      - Seat 2: passenger_name "Jane Smith"
      - Seat 3: passenger_name "Bob Johnson"
      - Seat 4: passenger_name "Alice Johnson"
      - Seat 5: passenger_name "Charlie Brown"
    
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

    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
    )

    # Platform fee (fixed at Rp. 50,000) for supplier
    platform_fee = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=50000,
        help_text=_("Platform fee in IDR (default: Rp. 50,000)."),
    )
    total_amount = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text=_("Total booking amount in IDR (Indonesian Rupiah)."),
        default=0,
    )


    notes = models.TextField(blank=True)
    
    booking_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_("Unique professional booking reference number (e.g., BK-2024-000123)."),
    )

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
        return f"Booking {self.booking_number} - {self.tour_date} ({self.seats_booked} seats)"
    
    def generate_booking_number(self):
        """
        Generate a professional booking number in format: BK-YYYY-NNNNNN
        where YYYY is the year and NNNNNN is a 6-digit sequential number.
        """
        from django.utils import timezone
        from django.db.models import Max
        
        current_year = timezone.now().year
        
        # Get the maximum booking number for this year
        max_booking = Booking.objects.filter(
            booking_number__startswith=f'BK-{current_year}-'
        ).aggregate(Max('booking_number'))
        
        max_number = max_booking['booking_number__max']
        
        if max_number:
            # Extract the number part and increment
            try:
                last_number = int(max_number.split('-')[-1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            # First booking of the year
            next_number = 1
        
        # Format as 6-digit number with leading zeros
        return f'BK-{current_year}-{next_number:06d}'
    
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
    
    def get_passenger_by_seat(self, seat_number):
        """Get passenger details for a specific seat."""
        return self.seat_slots.filter(seat_number=seat_number).first()
    
    def can_be_cancelled(self):
        """Check if booking can be cancelled."""
        return self.status == BookingStatus.PENDING
    
    def can_be_confirmed(self):
        """Check if booking can be confirmed (has at least one approved payment)."""
        if self.status != BookingStatus.PENDING:
            return False
        # Check if any payment exists and is approved
        return Payment.objects.filter(booking=self, status=PaymentStatus.APPROVED).exists()
    
    def clean(self):
        """Validate booking has at least one seat slot."""
        super().clean()
        if self.pk and self.seat_slots.count() == 0:
            raise ValidationError({
                'tour_date': 'Booking harus memiliki minimal satu kursi.'
            })
    
    def save(self, *args, **kwargs):
        """Validate before saving and generate booking number if new."""
        # Generate booking number only for new bookings
        if not self.booking_number:
            self.booking_number = self.generate_booking_number()
        
        self.full_clean()
        super().save(*args, **kwargs)



class Payment(models.Model):
    """
    Manual payment record where reseller uploads transfer proof and details.
    A booking can have multiple payment records (payment history).
    """

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text=_("Payment amount in IDR (Indonesian Rupiah)."),
        default=0,
    )
    transfer_date = models.DateField(
        help_text=_("Date when the transfer was made. Cannot be in the future.")
    )

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
            models.Index(fields=["booking"]),  # For reverse lookups
            models.Index(fields=["reviewed_by"]),  # For admin queries
            models.Index(fields=["transfer_date"]),  # For date range queries
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gte=0),
                name='payment_amount_non_negative'
            ),
        ]
    
    def clean(self):
        """Validate payment details."""
        super().clean()
        
        # Validate transfer date is not in the future
        if self.transfer_date:
            today = timezone.now().date()
            if self.transfer_date > today:
                raise ValidationError({
                    'transfer_date': 'Tanggal transfer tidak boleh di masa depan.'
                })
        
        # Note: With multiple payments, we don't validate against total_amount here
        # The total of all approved payments should match booking total, but individual
        # payments can be partial. This validation is removed to allow partial payments.
    
    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        booking_number = self.booking.booking_number if self.booking else f"#{self.booking_id}"
        return f"Payment for booking {booking_number} - Rp. {self.amount:,}"


class ResellerTourCommission(models.Model):
    """
    Commission settings per reseller per tour package.
    Each reseller can have a different fixed commission amount per seat for each tour package.
    
    Note: commission_amount is PER SEAT (per passenger). The actual commission for a booking
    will be multiplied by the number of seats in the booking.
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
        help_text=_("Fixed commission amount per seat (per passenger) in IDR for this reseller for this tour package. Must be greater than zero."),
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
        return f"{self.reseller.full_name} - {self.tour_package.name}: {self.commission_amount} IDR"


class ResellerCommission(models.Model):
    """
    Commission entries per reseller per booking.

    IMPORTANT: Commission is calculated PER SEAT (per passenger), not per booking.
    The amount stored here is the total commission = commission_per_seat × number_of_seats_in_booking.

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
        help_text=_("Total commission amount in IDR (commission_per_seat × number_of_seats). Must be at least 1 IDR.")
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
        booking_number = self.booking.booking_number if self.booking else f"#{self.booking_id}"
        return f"Commission {self.amount} for {self.reseller} (booking {booking_number}, level {self.level})"


class WithdrawalRequestStatus(models.TextChoices):
    """Status choices for withdrawal requests."""
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")
    COMPLETED = "COMPLETED", _("Completed")


class WithdrawalRequest(models.Model):
    """
    Withdrawal request from reseller to withdraw their commission balance.
    
    Workflow:
    1. Reseller creates withdrawal request (PENDING)
    2. Admin reviews and approves/rejects (APPROVED/REJECTED)
    3. Admin marks as completed after payment is sent (COMPLETED)
    """
    
    reseller = models.ForeignKey(
        "account.ResellerProfile",
        on_delete=models.CASCADE,
        related_name="withdrawal_requests",
        help_text=_("Reseller requesting the withdrawal."),
    )
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Withdrawal amount in IDR (Indonesian Rupiah). Must be at least 1 IDR."),
    )
    status = models.CharField(
        max_length=20,
        choices=WithdrawalRequestStatus.choices,
        default=WithdrawalRequestStatus.PENDING,
        help_text=_("Current status of the withdrawal request."),
    )
    notes = models.TextField(
        blank=True,
        help_text=_("Optional notes from reseller or admin."),
    )
    admin_notes = models.TextField(
        blank=True,
        help_text=_("Admin notes (e.g., reason for rejection, payment confirmation)."),
    )
    approved_by = models.ForeignKey(
        "account.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_withdrawals",
        help_text=_("Admin user who approved/rejected this withdrawal."),
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the withdrawal was approved/rejected."),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the withdrawal payment was completed."),
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Withdrawal Request"
        verbose_name_plural = "Withdrawal Requests"
        indexes = [
            models.Index(fields=["reseller", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["created_at"]),
        ]
    
    def __str__(self) -> str:
        return f"Withdrawal {self.amount} IDR - {self.reseller} ({self.status})"
    
    def clean(self):
        """Validate withdrawal amount doesn't exceed available balance."""
        super().clean()
        if self.pk is None:  # Only validate on creation
            available_balance = self.reseller.get_available_commission_balance()
            if self.amount > available_balance:
                raise ValidationError({
                    'amount': f'Jumlah penarikan ({self.amount:,} IDR) melebihi saldo komisi yang tersedia ({available_balance:,} IDR).'
                })
    
    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)
