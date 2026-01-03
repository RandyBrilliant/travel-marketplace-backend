from django.contrib import admin
from .models import (
    TourPackage,
    TourDate,
    TourImage,
    ItineraryItem,
    Booking,
    Payment,
    ResellerCommission,
    ResellerTourCommission,
    ResellerGroup,
)

# Register your models here.

@admin.register(TourPackage)
class TourPackageAdmin(admin.ModelAdmin):
    list_display = ["name", "supplier", "city", "country", "tour_type", "base_price", "currency", "is_active", "is_featured", "reseller_groups_count"]
    list_display_links = ["name"]
    list_filter = ["tour_type", "category", "is_active", "is_featured", "currency", "created_at"]
    search_fields = ["name", "city", "country", "supplier__company_name", "slug"]
    filter_horizontal = ["reseller_groups"]
    readonly_fields = ["slug", "duration_display", "group_size_display", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("supplier", "name", "slug", "summary", "description")
        }),
        ("Location", {
            "fields": ("city", "country")
        }),
        ("Duration & Group", {
            "fields": ("days", "nights", "duration_display", "max_group_size", "group_type", "group_size_display")
        }),
        ("Tour Details", {
            "fields": ("tour_type", "category", "tags", "highlights", "inclusions", "exclusions")
        }),
        ("Pricing", {
            "fields": ("base_price", "currency")
        }),
        ("Media", {
            "fields": ("main_image", "badge")
        }),
        ("Additional Information", {
            "fields": ("meeting_point", "cancellation_policy", "important_notes", "itinerary_pdf")
        }),
        ("Settings", {
            "fields": ("is_active", "is_featured", "reseller_groups")
        }),
        ("Commission Settings (Admin Only)", {
            "fields": ("commission_rate", "commission_type", "fixed_commission_amount", "commission_notes"),
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
    list_display = ["package", "departure_date", "price", "total_seats", "remaining_seats", "is_high_season"]
    list_display_links = ["package", "departure_date"]
    list_filter = ["departure_date", "is_high_season", "package__supplier"]
    search_fields = ["package__name", "package__city", "package__country"]
    readonly_fields = ["remaining_seats", "available_seats_count", "booked_seats_count"]
    date_hierarchy = "departure_date"
    
    fieldsets = (
        ("Tour Information", {
            "fields": ("package", "departure_date", "is_high_season")
        }),
        ("Pricing & Capacity", {
            "fields": ("price", "total_seats", "remaining_seats", "available_seats_count", "booked_seats_count")
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
    list_display = ["reseller", "tour_package", "commission_amount", "currency", "is_active"]
    list_filter = ["is_active", "currency", "tour_package__tour_type"]
    search_fields = ["reseller__full_name", "tour_package__name"]
    raw_id_fields = ["reseller", "tour_package"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    Admin interface for Booking.
    
    Note: seats_booked is now a computed property (not a database field).
    It calculates the count of seat_slots dynamically.
    """
    list_display = ["id", "reseller", "tour_date", "customer_name", "seats_booked", "status", "total_amount", "platform_fee", "created_at"]
    list_display_links = ["id", "customer_name"]
    list_filter = ["status", "created_at", "tour_date__package"]
    search_fields = ["customer_name", "customer_email", "reseller__full_name", "tour_date__package__name"]
    readonly_fields = ["seats_booked", "passenger_count", "total_amount", "subtotal", "booking_contact_is_passenger"]
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Booking Information", {
            "fields": ("reseller", "tour_date", "status")
        }),
        ("Customer Contact", {
            "fields": ("customer_name", "customer_email", "customer_phone")
        }),
        ("Booking Details", {
            "fields": ("seats_booked", "passenger_count", "booking_contact_is_passenger", "platform_fee", "subtotal", "total_amount")
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
    list_display = ["booking", "amount_display", "currency", "status", "transfer_date", "reviewed_by", "reviewed_at", "created_at"]
    list_display_links = ["booking"]
    list_filter = ["status", "currency", "created_at", "reviewed_at"]
    search_fields = ["booking__customer_name", "booking__customer_email", "sender_account_name", "sender_bank_name"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Booking Information", {
            "fields": ("booking",)
        }),
        ("Payment Details", {
            "fields": ("amount", "currency", "transfer_date")
        }),
        ("Transfer Information", {
            "fields": ("sender_account_name", "sender_bank_name", "sender_account_number", "proof_image")
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
        return f"{obj.currency} {obj.amount:,}"
    amount_display.short_description = "Amount"


@admin.register(ResellerCommission)
class ResellerCommissionAdmin(admin.ModelAdmin):
    list_display = ["reseller", "booking", "level", "amount"]
    list_filter = ["level", "created_at"]
    search_fields = ["reseller__full_name"]
