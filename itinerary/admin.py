from django.contrib import admin
from .models import (
    ItineraryBoard,
    ItineraryColumn,
    ItineraryCard,
    ItineraryCardAttachment,
    ItineraryCardChecklist,
    ItineraryTransaction,
)


@admin.register(ItineraryBoard)
class ItineraryBoardAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'is_public', 'supplier', 'price', 'is_active', 'created_at']
    list_filter = ['is_public', 'is_active', 'supplier', 'created_at']
    search_fields = ['title', 'slug', 'share_token', 'supplier__company_name']
    readonly_fields = ['share_token', 'created_at', 'updated_at']
    fieldsets = (
        ('Supplier & Board Information', {
            'fields': ('supplier', 'title', 'description', 'slug')
        }),
        ('Media', {
            'fields': ('package_image', 'video_link')
        }),
        ('Pricing', {
            'fields': ('price', 'currency')
        }),
        ('Visibility & Access', {
            'fields': ('is_public', 'share_token')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ItineraryColumn)
class ItineraryColumnAdmin(admin.ModelAdmin):
    list_display = ['title', 'board', 'order', 'created_at']
    list_filter = ['board', 'created_at']
    search_fields = ['title', 'board__title']
    ordering = ['board', 'order']


@admin.register(ItineraryCard)
class ItineraryCardAdmin(admin.ModelAdmin):
    list_display = ['title', 'column', 'order', 'date', 'start_time', 'location_name', 'created_at']
    list_filter = ['column__board', 'date', 'created_at']
    search_fields = ['title', 'description', 'location_name']
    ordering = ['column', 'order']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ItineraryCardAttachment)
class ItineraryCardAttachmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'card', 'file_type', 'file_size', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['name', 'card__title']


@admin.register(ItineraryCardChecklist)
class ItineraryCardChecklistAdmin(admin.ModelAdmin):
    list_display = ['title', 'card', 'order', 'items_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'card__title']
    
    def items_count(self, obj):
        return len(obj.items)
    items_count.short_description = 'Items'


@admin.register(ItineraryTransaction)
class ItineraryTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_number', 'board', 'customer', 'amount', 'status', 'departure_date', 'arrival_date', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at', 'activated_at']
    search_fields = ['transaction_number', 'board__title', 'customer__email', 'customer__full_name']
    readonly_fields = ['transaction_number', 'created_at', 'updated_at', 'activated_at', 'payment_reviewed_at', 'payment_reviewed_by']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('transaction_number', 'board', 'customer', 'status')
        }),
        ('Travel Dates', {
            'fields': ('departure_date', 'arrival_date', 'expires_at')
        }),
        ('Pricing', {
            'fields': ('amount', 'currency')
        }),
        ('Payment Information', {
            'fields': ('payment_amount', 'payment_transfer_date', 'payment_proof_image', 'payment_status', 'payment_reviewed_at', 'payment_reviewed_by')
        }),
        ('Activation', {
            'fields': ('activated_at',)
        }),
        ('Additional Info', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('board', 'customer', 'payment_reviewed_by')


