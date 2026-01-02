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
    list_display = ["name", "supplier", "city", "country", "tour_type", "is_active", "is_featured", "reseller_groups_count"]
    list_filter = ["tour_type", "category", "is_active", "is_featured", "reseller_groups"]
    search_fields = ["name", "city", "country", "supplier__company_name"]
    filter_horizontal = ["reseller_groups"]
    
    def reseller_groups_count(self, obj):
        """Display count of reseller groups assigned to this tour."""
        count = obj.reseller_groups.count()
        if count == 0:
            return "All Resellers"
        return f"{count} Group(s)"
    reseller_groups_count.short_description = "Access Groups"


@admin.register(TourDate)
class TourDateAdmin(admin.ModelAdmin):
    list_display = ["package", "departure_date", "price", "total_seats", "remaining_seats"]
    list_filter = ["departure_date", "is_high_season"]
    search_fields = ["package__name"]


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
    list_display = ["id", "reseller", "tour_date", "customer_name", "seats_booked", "status", "platform_fee"]
    list_filter = ["status", "created_at"]
    search_fields = ["customer_name", "customer_email", "reseller__full_name"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["booking", "amount", "currency", "status", "reviewed_by", "reviewed_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["booking__customer_name", "sender_account_name"]


@admin.register(ResellerCommission)
class ResellerCommissionAdmin(admin.ModelAdmin):
    list_display = ["reseller", "booking", "level", "amount"]
    list_filter = ["level", "created_at"]
    search_fields = ["reseller__full_name"]
