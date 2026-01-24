import secrets
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta


class ItineraryBoard(models.Model):
    # Supplier who created and owns this itinerary board
    supplier = models.ForeignKey(
        "account.SupplierProfile",
        on_delete=models.CASCADE,
        related_name="itinerary_boards",
        help_text=_("Supplier who created and owns this itinerary board."),
    )
    
    # Board metadata
    title = models.CharField(
        max_length=255,
        help_text=_("Board title (e.g., '5D4N China Tour - Jan 2024')")
    )
    description = models.TextField(blank=True)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("URL-friendly identifier")
    )
    
    # Visibility & Access
    is_public = models.BooleanField(
        default=True,
        help_text=_("If True, board is publicly accessible via shareable link")
    )
    share_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Unique token for sharing (auto-generated)")
    )
    
    # Pricing
    price = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text=_("Price for accessing this itinerary board in IDR (Indonesian Rupiah)."),
        default=0,
    )
    
    # Currency support
    currency = models.ForeignKey(
        "travel.Currency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="itinerary_boards",
        help_text=_("Currency used for pricing. If null, IDR is assumed."),
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this itinerary board is active and available for purchase."),
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Itinerary Board"
        verbose_name_plural = "Itinerary Boards"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['supplier', 'is_public']),
            models.Index(fields=['supplier', 'is_active']),
            models.Index(fields=['is_active', 'is_public']),
            models.Index(fields=['share_token']),
            models.Index(fields=['slug']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.title} ({'Public' if self.is_public else 'Private'})"
    
    def save(self, *args, **kwargs):
        """Generate share_token and slug if not set, and validate before saving."""
        if not self.share_token:
            # Generate a secure random token
            self.share_token = secrets.token_urlsafe(32)
        
        if not self.slug:
            # Generate slug from title if not provided
            base_slug = slugify(self.title)
            self.slug = self._generate_unique_slug(base_slug)
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def _generate_unique_slug(self, base_slug):
        """Generate a unique slug by appending a number if needed."""
        slug = base_slug
        counter = 1
        # Exclude current instance if updating
        queryset = ItineraryBoard.objects.filter(slug=slug)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.exists():
            slug = f"{base_slug}-{counter}"
            queryset = ItineraryBoard.objects.filter(slug=slug)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            counter += 1
        return slug
    
    def generate_new_share_token(self):
        """Generate a new share token (useful for security rotation)."""
        self.share_token = secrets.token_urlsafe(32)
        self.save(update_fields=['share_token'])


class ItineraryColumn(models.Model):
    """
    Columns represent groupings of cards (e.g., "Day 1", "Day 2", "Activities", "Important Info").
    Similar to Trello lists.
    """
    
    board = models.ForeignKey(
        ItineraryBoard,
        on_delete=models.CASCADE,
        related_name='columns'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order (lower = first)")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Itinerary Column"
        verbose_name_plural = "Itinerary Columns"
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['board', 'order']),
        ]
    
    def __str__(self) -> str:
        return f"{self.board.title} - {self.title}"


class ItineraryCard(models.Model):
    """
    Cards represent individual items/activities in the itinerary.
    Can contain rich content: text, images, attachments, checklists, locations, times.
    """
    
    column = models.ForeignKey(
        ItineraryColumn,
        on_delete=models.CASCADE,
        related_name='cards'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Time/Date information
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_("Activity start time")
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_("Activity end time")
    )
    date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Specific date (if different from column context)")
    )
    
    # Location
    location_name = models.CharField(max_length=255, blank=True)
    location_address = models.TextField(blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_("Latitude coordinate")
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_("Longitude coordinate")
    )
    
    # Visual
    cover_image = models.ImageField(
        upload_to='itinerary/card_covers/',
        null=True,
        blank=True
    )
    
    # Ordering
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Position within column")
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Itinerary Card"
        verbose_name_plural = "Itinerary Cards"
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['column', 'order']),
            models.Index(fields=['date', 'start_time']),
        ]
    
    def __str__(self) -> str:
        return f"{self.column.title} - {self.title}"
    
    def clean(self):
        """Validate time range if both start_time and end_time are set."""
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({
                'end_time': 'End time must be after start time.'
            })


class ItineraryCardAttachment(models.Model):
    """Attachments for cards (PDFs, images, documents)"""
    
    card = models.ForeignKey(
        ItineraryCard,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='itinerary/attachments/')
    name = models.CharField(
        max_length=255,
        help_text=_("Display name for the attachment")
    )
    file_type = models.CharField(
        max_length=50,
        help_text=_("MIME type or file extension")
    )
    file_size = models.PositiveIntegerField(
        help_text=_("File size in bytes")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Card Attachment"
        verbose_name_plural = "Card Attachments"
        ordering = ['created_at']
    
    def __str__(self) -> str:
        return f"{self.card.title} - {self.name}"


class ItineraryCardChecklist(models.Model):
    """Checklist items for cards"""
    
    card = models.ForeignKey(
        ItineraryCard,
        on_delete=models.CASCADE,
        related_name='checklists'
    )
    title = models.CharField(
        max_length=255,
        default="Checklist"
    )
    items = models.JSONField(
        default=list,
        help_text=_("List of {text: str, completed: bool, id: str} objects")
    )
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Card Checklist"
        verbose_name_plural = "Card Checklists"
        ordering = ['order', 'id']
    
    def __str__(self) -> str:
        completed_count = sum(1 for item in self.items if item.get('completed', False))
        total_count = len(self.items)
        return f"{self.card.title} - {self.title} ({completed_count}/{total_count})"


class ItineraryTransactionStatus(models.TextChoices):
    """Status of an itinerary transaction/access."""
    PENDING = "PENDING", _("Pending")
    ACTIVE = "ACTIVE", _("Active - Customer can view")
    EXPIRED = "EXPIRED", _("Expired - No longer accessible")
    COMPLETED = "COMPLETED", _("Completed - Transaction finished")
    CANCELLED = "CANCELLED", _("Cancelled")


class ItineraryTransaction(models.Model):
    """
    Tracks customer access to itinerary boards with time-limited availability.
    
    When a customer purchases/books an itinerary package, a transaction is created
    that grants them access for a specified duration (e.g., 7 days, 30 days).
    """

    # Board and customer relationship
    board = models.ForeignKey(
        ItineraryBoard,
        on_delete=models.CASCADE,
        related_name="transactions",
        help_text=_("The itinerary board being accessed."),
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="itinerary_transactions",
        help_text=_("Customer who has access to the itinerary."),
    )
    
    # Link to tour booking (optional - if transaction is from a booking)
    booking = models.ForeignKey(
        "travel.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="itinerary_transactions",
        help_text=_("Related tour booking that triggered this itinerary access."),
    )

    # Transaction details
    status = models.CharField(
        max_length=20,
        choices=ItineraryTransactionStatus.choices,
        default=ItineraryTransactionStatus.PENDING,
        db_index=True,
        help_text=_("Current status of the transaction."),
    )
    
    # Pricing (snapshot at time of purchase)
    amount = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text=_("Amount paid for this transaction in IDR (snapshot from board price)."),
        default=0,
    )

    # Access duration
    access_duration_days = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text=_("Number of days the customer has access to the itinerary."),
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the transaction was activated (customer got access)."),
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the customer's access expires."),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the transaction was completed or cancelled."),
    )

    # Transaction reference (auto-generated like booking_number)
    transaction_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_("Unique transaction reference number (e.g., IT-2026-000001)."),
    )
    
    # Optional external reference
    external_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Optional external reference (e.g., payment gateway transaction ID)."),
    )

    # Additional notes
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes about this transaction."),
    )

    # Payment fields (similar to Booking Payment model)
    payment_amount = models.IntegerField(
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
        help_text=_("Payment amount uploaded by customer/reseller in IDR."),
    )
    payment_transfer_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date when the transfer was made. Cannot be in the future."),
    )
    payment_proof_image = models.ImageField(
        upload_to="itinerary_payments/proof/",
        blank=True,
        null=True,
        help_text=_("Upload of the bank transfer slip or screenshot."),
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
        ],
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Status of the payment (null if no payment uploaded yet)."),
    )
    payment_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="itinerary_payments_reviewed",
        help_text=_("Admin who reviewed the payment."),
    )
    payment_reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the payment was reviewed."),
    )

    class Meta:
        verbose_name = "Itinerary Transaction"
        verbose_name_plural = "Itinerary Transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["board", "customer"]),
            models.Index(fields=["board", "status"]),
            models.Index(fields=["booking"]),
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["payment_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_number} - {self.customer.email} ({self.status})"

    def generate_transaction_number(self):
        """
        Generate a professional transaction number in format: IT-YYYY-NNNNNN
        where YYYY is the year and NNNNNN is a 6-digit sequential number.
        """
        from django.utils import timezone
        from django.db.models import Max
        
        current_year = timezone.now().year
        
        # Get the maximum transaction number for this year
        max_transaction = ItineraryTransaction.objects.filter(
            transaction_number__startswith=f'IT-{current_year}-'
        ).aggregate(Max('transaction_number'))
        
        max_number = max_transaction['transaction_number__max']
        
        if max_number:
            # Extract the number part and increment
            try:
                last_number = int(max_number.split('-')[-1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            # First transaction of the year
            next_number = 1
        
        # Format as 6-digit number with leading zeros
        return f'IT-{current_year}-{next_number:06d}'
    
    def save(self, *args, **kwargs):
        """Generate transaction_number, set amount from board, validate payment date, and set expires_at when status changes to ACTIVE."""
        from django.utils import timezone
        
        # Validate payment transfer date is not in the future
        if self.payment_transfer_date:
            today = timezone.now().date()
            if self.payment_transfer_date > today:
                raise ValidationError({
                    'payment_transfer_date': 'Tanggal transfer tidak boleh di masa depan.'
                })
        
        # Generate transaction number if not set
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        
        # Auto-set amount from board price if not set
        if self.amount == 0 and self.board:
            self.amount = self.board.price
        
        if self.status == ItineraryTransactionStatus.ACTIVE and not self.activated_at:
            self.activated_at = timezone.now()
            self.expires_at = self.activated_at + timedelta(days=self.access_duration_days)
        
        if self.status in (ItineraryTransactionStatus.CANCELLED, ItineraryTransactionStatus.COMPLETED):
            if not self.completed_at:
                self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)

    def is_access_valid(self) -> bool:
        """Check if customer currently has valid access."""
        if self.status != ItineraryTransactionStatus.ACTIVE:
            return False
        
        if self.expires_at and self.expires_at < timezone.now():
            return False
        
        return True

    def activate(self):
        """Activate the transaction and set expiry date."""
        from django.utils import timezone
        
        if self.status == ItineraryTransactionStatus.PENDING:
            self.status = ItineraryTransactionStatus.ACTIVE
            self.activated_at = timezone.now()
            self.expires_at = self.activated_at + timedelta(days=self.access_duration_days)
            self.save()

    def extend_access(self, additional_days: int):
        """Extend the access period by additional days."""
        from django.utils import timezone
        
        if self.expires_at:
            self.expires_at += timedelta(days=additional_days)
            self.save()
