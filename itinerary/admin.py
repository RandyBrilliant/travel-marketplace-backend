from django.contrib import admin
from .models import (
    ItineraryBoard,
    ItineraryColumn,
    ItineraryCard,
    ItineraryCardAttachment,
    ItineraryCardChecklist,
    ItineraryCardComment,
)


@admin.register(ItineraryBoard)
class ItineraryBoardAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'is_public', 'created_by', 'created_at']
    list_filter = ['is_public', 'allow_editing', 'created_at']
    search_fields = ['title', 'slug', 'share_token']
    readonly_fields = ['share_token', 'created_at', 'updated_at']
    fieldsets = (
        ('Board Information', {
            'fields': ('title', 'description', 'slug')
        }),
        ('Visibility & Access', {
            'fields': ('is_public', 'allow_editing', 'share_token')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(ItineraryColumn)
class ItineraryColumnAdmin(admin.ModelAdmin):
    list_display = ['title', 'board', 'order', 'color', 'created_at']
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


@admin.register(ItineraryCardComment)
class ItineraryCardCommentAdmin(admin.ModelAdmin):
    list_display = ['card', 'user', 'text_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['text', 'card__title', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Text'

