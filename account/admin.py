from django.contrib import admin
from .models import CustomUser, SupplierProfile, ResellerProfile, StaffProfile

# Register your models here.

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'role', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'full_name')
    ordering = ('email',)

@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name')
    list_filter = ('user__role',)
    search_fields = ('user__email', 'company_name')


@admin.register(ResellerProfile)
class ResellerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'contact_phone', 'address')
    list_filter = ('user__role',)
    search_fields = ('user__email',)

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    list_filter = ('user__role',)
    search_fields = ('user__email', 'department')