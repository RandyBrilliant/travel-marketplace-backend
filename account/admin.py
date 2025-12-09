from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CustomUser,
    SupplierProfile,
    ResellerProfile,
    StaffProfile,
    ProfileStatus,
)

# Register your models here.

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'phone_number',
        'role',
        'email_verified',
        'is_active',
        'is_staff',
        'is_superuser',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'email_verified')
    search_fields = ('email', 'phone_number')
    ordering = ('email',)
    readonly_fields = ('email_verified_at', 'date_joined', 'last_login')
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password', 'role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Contact', {
            'fields': ('phone_number',)
        }),
        ('Email Verification', {
            'fields': ('email_verified', 'email_verified_at')
        }),
        ('Timestamps', {
            'fields': ('date_joined', 'last_login')
        }),
    )

@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'contact_person', 'contact_phone', 'status')
    list_filter = ('status', 'user__role')
    search_fields = ('user__email', 'company_name', 'contact_person', 'tax_id')
    readonly_fields = ('photo_preview', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Company Information', {
            'fields': ('company_name', 'contact_person', 'contact_phone', 'address', 'tax_id')
        }),
        ('Profile Photo', {
            'fields': ('photo', 'photo_preview')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def photo_preview(self, obj):
        """Display photo preview in admin."""
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 200px;" />',
                obj.photo.url
            )
        return "No photo"
    photo_preview.short_description = "Photo Preview"


@admin.register(ResellerProfile)
class ResellerProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'display_name',
        'contact_phone',
        'referral_code',
        'status',
        'bank_account_name',
    )
    list_filter = ('status', 'user__role')
    search_fields = (
        'user__email',
        'display_name',
        'referral_code',
        'bank_account_name',
        'bank_account_number',
    )
    readonly_fields = ('photo_preview', 'group_root', 'direct_downline_count', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Basic Information', {
            'fields': ('display_name', 'contact_phone', 'address')
        }),
        ('Profile Photo', {
            'fields': ('photo', 'photo_preview')
        }),
        ('MLM Structure', {
            'fields': ('referral_code', 'sponsor', 'group_root', 'direct_downline_count')
        }),
        ('Commission Settings', {
            'fields': ('own_commission_rate', 'upline_commission_rate')
        }),
        ('Banking Information', {
            'fields': ('bank_name', 'bank_account_name', 'bank_account_number'),
            'description': 'Bank account details for commission payouts.'
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def photo_preview(self, obj):
        """Display photo preview in admin."""
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 200px;" />',
                obj.photo.url
            )
        return "No photo"
    photo_preview.short_description = "Photo Preview"

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'job_title', 'department')
    list_filter = ('user__role', 'department')
    search_fields = ('user__email', 'name', 'department', 'job_title')
    readonly_fields = ('photo_preview', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Staff Information', {
            'fields': ('name', 'job_title', 'department', 'contact_phone')
        }),
        ('Profile Photo', {
            'fields': ('photo', 'photo_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def photo_preview(self, obj):
        """Display photo preview in admin."""
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 200px;" />',
                obj.photo.url
            )
        return "No photo"
    photo_preview.short_description = "Photo Preview"