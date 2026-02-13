from django.contrib import admin
from .models import (
    TourPackage,
    TourDate,
    TourImage,
    SeatSlot,
    Booking,
    Payment,
    ResellerCommission,
    ResellerTourCommission,
    ResellerGroup,
    WithdrawalRequest,
    PromoCode,
)

# Register your models here.

@admin.register(TourPackage)
class TourPackageAdmin(admin.ModelAdmin):
    list_display = ["name", "supplier", "country", "tour_type", "base_price", "is_active", "reseller_groups_count"]
    list_display_links = ["name"]
    list_filter = ["tour_type", "is_active", "created_at"]
    search_fields = ["name", "country", "supplier__company_name", "slug"]
    filter_horizontal = ["reseller_groups"]
    readonly_fields = ["slug", "duration_display", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("supplier", "name", "slug", "itinerary")
        }),
        ("Location", {
            "fields": ("country",)
        }),
        ("Duration & Group", {
            "fields": ("days", "nights", "duration_display", "max_group_size")
        }),
        ("Tour Details", {
            "fields": ("tour_type", "highlights", "inclusions", "exclusions")
        }),
        ("Pricing", {
            "fields": ("base_price", "visa_price", "tipping_price")
        }),
        ("Additional Information", {
            "fields": ("cancellation_policy", "important_notes", "itinerary_pdf")
        }),
        ("Settings", {
            "fields": ("is_active", "reseller_groups")
        }),
        ("Commission Settings", {
            "fields": ("commission",),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("supplier", "supplier__user").prefetch_related("reseller_groups")
    
    def reseller_groups_count(self, obj):
        """Display count of reseller groups assigned to this tour."""
        count = obj.reseller_groups.count()
        if count == 0:
            return "All Resellers"
        return f"{count} Group(s)"
    reseller_groups_count.short_description = "Access Groups"


@admin.register(TourDate)
class TourDateAdmin(admin.ModelAdmin):
    """
    Admin interface for TourDate.
    
    Note: remaining_seats is now a computed property (not a database field).
    It calculates available seats dynamically from seat_slots.
    """
    list_display = ["package", "departure_date", "departure_city", "price", "total_seats", "airline", "remaining_seats", "is_high_season", "has_shopping_stop"]
    list_display_links = ["package", "departure_date"]
    list_filter = ["departure_date", "is_high_season", "has_shopping_stop", "departure_city", "package__supplier"]
    search_fields = ["package__name", "package__country", "departure_city", "airline"]
    readonly_fields = ["remaining_seats", "available_seats_count", "booked_seats_count"]
    date_hierarchy = "departure_date"
    
    fieldsets = (
        ("Tour Information", {
            "fields": ("package", "departure_date", "departure_city", "airline", "is_high_season", "has_shopping_stop")
        }),
        ("Pricing & Capacity", {
            "fields": ("price", "total_seats", "remaining_seats", "available_seats_count", "booked_seats_count")
        }),
        ("Additional Information", {
            "fields": ("notes",),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("package", "package__supplier")


@admin.register(ResellerGroup)
class ResellerGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "is_active", "reseller_count", "tour_count", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    filter_horizontal = ["resellers"]
    raw_id_fields = ["created_by"]
    
    def reseller_count(self, obj):
        """Display count of resellers in this group."""
        return obj.resellers.count()
    reseller_count.short_description = "Resellers"
    
    def tour_count(self, obj):
        """Display count of tour packages assigned to this group."""
        return obj.tour_packages.count()
    tour_count.short_description = "Tour Packages"


@admin.register(ResellerTourCommission)
class ResellerTourCommissionAdmin(admin.ModelAdmin):
    list_display = ["reseller", "tour_package", "commission_amount", "is_active"]
    list_filter = ["is_active", "tour_package__tour_type"]
    search_fields = ["reseller__full_name", "tour_package__name"]
    raw_id_fields = ["reseller", "tour_package"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    Admin interface for Booking.
    
    Note: seats_booked is now a computed property (not a database field).
    It calculates the count of seat_slots dynamically.
    """
    list_display = ["id", "reseller", "tour_date", "seats_booked", "status", "total_amount", "platform_fee", "created_at"]
    list_display_links = ["id", "reseller", "tour_date"]
    list_filter = ["status", "created_at", "tour_date__package"]
    search_fields = ["reseller__full_name", "tour_date__package__name"]
    readonly_fields = ["seats_booked", "passenger_count", "total_amount"]
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Booking Information", {
            "fields": ("reseller", "tour_date", "status")
        }),
        ("Booking Details", {
            "fields": ("seats_booked", "passenger_count", "platform_fee", "total_amount")
        }),
        ("Additional Information", {
            "fields": ("notes",)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related."""
        qs = super().get_queryset(request)
        return qs.select_related("reseller", "reseller__user", "tour_date", "tour_date__package").prefetch_related("seat_slots")
    
    def total_amount(self, obj):
        """Display total booking amount."""
        return f"Rp {obj.total_amount:,}"
    total_amount.short_description = "Total Amount"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["booking", "amount_display", "status", "transfer_date", "reviewed_by", "reviewed_at", "created_at"]
    list_display_links = ["booking"]
    list_filter = ["status", "created_at", "reviewed_at"]
    search_fields = ["booking__reseller", "booking__reseller__user__email"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Booking Information", {
            "fields": ("booking",)
        }),
        ("Payment Details", {
            "fields": ("amount", "transfer_date")
        }),
        ("Transfer Information", {
            "fields": ("proof_image",)
        }),
        ("Review", {
            "fields": ("status", "reviewed_by", "reviewed_at")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("booking", "booking__reseller", "booking__tour_date", "reviewed_by")
    
    def amount_display(self, obj):
        """Display amount with currency formatting."""
        return f"Rp. {obj.amount:,}"
    amount_display.short_description = "Amount"


@admin.register(TourImage)
class TourImageAdmin(admin.ModelAdmin):
    """Admin interface for TourImage."""
    list_display = ["package", "image", "order", "is_primary", "created_at"]
    list_display_links = ["package"]
    list_filter = ["is_primary", "package__supplier", "created_at"]
    search_fields = ["package__name", "package__country"]
    readonly_fields = ["image_preview", "created_at"]
    ordering = ["package", "order"]
    
    fieldsets = (
        ("Tour Information", {
            "fields": ("package", "order", "is_primary")
        }),
        ("Image", {
            "fields": ("image", "caption", "image_preview")
        }),
        ("Timestamps", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("package", "package__supplier")
    
    def image_preview(self, obj):
        """Display image preview in admin."""
        if obj.image:
            from django.utils.html import format_html
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 200px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = "Image Preview"


@admin.register(SeatSlot)
class SeatSlotAdmin(admin.ModelAdmin):
    """Admin interface for SeatSlot."""
    list_display = ["booking", "tour_date", "passenger_name", "seat_number", "status", "created_at"]
    list_display_links = ["booking", "passenger_name"]
    list_filter = ["status", "tour_date__package", "created_at"]
    search_fields = ["booking__reseller", "passenger_name", "booking__reseller__user__email"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Booking Information", {
            "fields": ("booking", "tour_date")
        }),
        ("Passenger Details", {
            "fields": ("passenger_name", "seat_number", "status")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("booking", "booking__reseller", "tour_date", "tour_date__package")


@admin.register(ResellerCommission)
class ResellerCommissionAdmin(admin.ModelAdmin):
    list_display = ["reseller", "booking", "level", "amount_display", "created_at"]
    list_display_links = ["reseller", "booking"]
    list_filter = ["level", "created_at"]
    search_fields = ["reseller__full_name", "reseller__user__email"]
    readonly_fields = ["amount_display", "created_at", "updated_at"]
    raw_id_fields = ["reseller", "booking"]
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Commission Information", {
            "fields": ("reseller", "booking", "level")
        }),
        ("Amount", {
            "fields": ("amount", "amount_display")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def amount_display(self, obj):
        """Display amount with currency formatting."""
        return f"Rp. {obj.amount:,}"
    amount_display.short_description = "Amount"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("reseller", "reseller__user", "booking", "booking__tour_date")


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ["reseller", "amount_display", "status", "created_at", "approved_by", "approved_at"]
    list_display_links = ["reseller"]
    list_filter = ["status", "created_at", "approved_at"]
    search_fields = ["reseller__full_name", "reseller__user__email"]
    readonly_fields = ["amount_display", "created_at", "updated_at"]
    raw_id_fields = ["reseller", "approved_by"]
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Withdrawal Information", {
            "fields": ("reseller", "amount", "amount_display", "status")
        }),
        ("Notes", {
            "fields": ("notes", "admin_notes")
        }),
        ("Approval Information", {
            "fields": ("approved_by", "approved_at", "completed_at")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def amount_display(self, obj):
        """Display amount with currency formatting."""
        return f"Rp. {obj.amount:,}"
    amount_display.short_description = "Amount"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related("reseller", "reseller__user", "approved_by")


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_type", "discount_value", "min_purchase_amount", "times_used", "max_uses", "is_active", "applicable_to", "valid_from", "valid_until"]
    list_filter = ["is_active", "discount_type", "applicable_to"]
    search_fields = ["code", "description"]
    readonly_fields = ["times_used", "created_at", "updated_at"]
    date_hierarchy = "valid_from"
