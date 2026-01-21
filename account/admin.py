from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CustomUser,
    SupplierProfile,
    ResellerProfile,
    StaffProfile,
    CustomerProfile,
    ContactMessage,
)

# Register your models here.

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'role',
        'email_verified',
        'is_active',
        'is_staff',
        'is_superuser',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'email_verified')
    search_fields = ('email',)
    ordering = ('email',)
    readonly_fields = ('email_verified_at', 'date_joined', 'last_login')
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password', 'role', 'is_active', 'is_staff', 'is_superuser')
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
    list_display = ('user', 'company_name', 'contact_person', 'contact_phone', 'bank_account_name')
    list_filter = ('user__role', 'user__is_active', 'created_at')
    search_fields = ('user__email', 'company_name', 'contact_person', 'bank_account_name')
    readonly_fields = ('photo_preview', 'created_at', 'updated_at')
    list_select_related = ('user',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related to avoid N+1 queries."""
        return super().get_queryset(request).select_related('user')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Company Information', {
            'fields': ('company_name', 'contact_person', 'contact_phone', 'address')
        }),
        ('Profile Photo', {
            'fields': ('photo', 'photo_preview')
        }),
        ('Banking Information', {
            'fields': ('bank_name', 'bank_account_name', 'bank_account_number'),
            'description': 'Bank account details for commission payouts.'
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
        'full_name',
        'contact_phone',
        'referral_code',
        'bank_account_name',
    )
    list_filter = ('user__role', 'user__is_active', 'created_at')
    search_fields = (
        'user__email',
        'full_name',
        'referral_code',
        'bank_account_name',
        'bank_account_number',
    )
    readonly_fields = ('photo_preview', 'group_root', 'direct_downline_count', 'created_at', 'updated_at')
    list_select_related = ('user', 'sponsor', 'group_root')
    
    def get_queryset(self, request):
        """Optimize queryset with select_related to avoid N+1 queries."""
        return super().get_queryset(request).select_related('user', 'sponsor', 'group_root')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Basic Information', {
            'fields': ('full_name', 'contact_phone', 'address')
        }),
        ('Profile Photo', {
            'fields': ('photo', 'photo_preview')
        }),
        ('MLM Structure', {
            'fields': ('referral_code', 'sponsor', 'group_root', 'direct_downline_count')
        }),
        ('Commission Settings', {
            'fields': ('base_commission',)
        }),
        ('Banking Information', {
            'fields': ('bank_name', 'bank_account_name', 'bank_account_number'),
            'description': 'Bank account details for commission payouts.'
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
    list_display = ('user', 'full_name', 'contact_phone')
    list_filter = ('user__role', 'user__is_active', 'created_at')
    search_fields = ('user__email', 'full_name')
    readonly_fields = ('photo_preview', 'created_at', 'updated_at')
    list_select_related = ('user',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related to avoid N+1 queries."""
        return super().get_queryset(request).select_related('user')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Staff Information', {
            'fields': ('full_name', 'contact_phone')
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


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Admin interface for customer profiles."""
    list_display = ('user', 'full_name', 'contact_phone', 'created_at')
    list_filter = ('user__is_active', 'created_at')
    search_fields = ('user__email', 'full_name', 'contact_phone')
    readonly_fields = ('photo_preview', 'created_at', 'updated_at')
    list_select_related = ('user',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related to avoid N+1 queries."""
        return super().get_queryset(request).select_related('user')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Customer Information', {
            'fields': ('full_name', 'contact_phone', 'address')
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


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'get_subject_display', 'created_at', 'has_phone')
    list_filter = ('subject', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('id', 'created_at', 'updated_at', 'message_display')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('id', 'name', 'email', 'phone')
        }),
        ('Message', {
            'fields': ('subject', 'message_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def has_phone(self, obj):
        """Display if contact has provided phone number."""
        return bool(obj.phone)
    has_phone.short_description = "Has Phone"
    has_phone.boolean = True
    
    def message_display(self, obj):
        """Display message in a more readable format."""
        return format_html(
            '<div style="white-space: pre-wrap; word-wrap: break-word; max-width: 500px;">{}</div>',
            obj.message
        )
    message_display.short_description = "Message"
    
    def has_add_permission(self, request):
        """Prevent adding contact messages through admin (they come from API)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing contact messages."""
        return False
