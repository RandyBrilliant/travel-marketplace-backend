from rest_framework import serializers
from django.conf import settings
from .models import (
    ItineraryBoard,
    ItineraryColumn,
    ItineraryCard,
    ItineraryCardAttachment,
    ItineraryCardChecklist,
    ItineraryTransaction,
    ItineraryTransactionStatus,
)


class ItineraryCardChecklistSerializer(serializers.ModelSerializer):
    """Serializer for card checklists."""
    
    items_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    
    def get_items_count(self, obj):
        return len(obj.items) if obj.items else 0
    
    def get_completed_count(self, obj):
        if not obj.items:
            return 0
        return sum(1 for item in obj.items if item.get('completed', False))
    
    class Meta:
        model = ItineraryCardChecklist
        fields = [
            'id',
            'card',
            'title',
            'items',
            'items_count',
            'completed_count',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItineraryCardAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for card attachments."""
    
    file_url = serializers.SerializerMethodField()
    
    def get_file_url(self, obj):
        """Get full URL for the attachment file."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    class Meta:
        model = ItineraryCardAttachment
        fields = [
            'id',
            'card',
            'file',
            'file_url',
            'name',
            'file_type',
            'file_size',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ItineraryCardSerializer(serializers.ModelSerializer):
    """Serializer for itinerary cards."""
    
    cover_image_url = serializers.SerializerMethodField()
    attachments = ItineraryCardAttachmentSerializer(many=True, read_only=True)
    checklists = ItineraryCardChecklistSerializer(many=True, read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)
    
    def get_cover_image_url(self, obj):
        """Get full URL for the cover image."""
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None
    
    class Meta:
        model = ItineraryCard
        fields = [
            'id',
            'column',
            'title',
            'description',
            'start_time',
            'end_time',
            'date',
            'location_name',
            'location_address',
            'latitude',
            'longitude',
            'cover_image',
            'cover_image_url',
            'order',
            'created_by',
            'created_by_email',
            'created_at',
            'updated_at',
            'attachments',
            'checklists',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItineraryColumnSerializer(serializers.ModelSerializer):
    """Serializer for itinerary columns."""
    
    cards = ItineraryCardSerializer(many=True, read_only=True)
    cards_count = serializers.IntegerField(source='cards.count', read_only=True)
    
    class Meta:
        model = ItineraryColumn
        fields = [
            'id',
            'board',
            'title',
            'description',
            'order',
            'created_at',
            'updated_at',
            'cards',
            'cards_count',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItineraryBoardListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for board list views."""
    
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    columns_count = serializers.IntegerField(source='columns.count', read_only=True)
    
    class Meta:
        model = ItineraryBoard
        fields = [
            'id',
            'title',
            'slug',
            'description',
            'is_public',
            'share_token',
            'supplier',
            'supplier_name',
            'price',
            'currency',
            'is_active',
            'created_at',
            'updated_at',
            'columns_count',
        ]
        read_only_fields = ['id', 'slug', 'share_token', 'created_at', 'updated_at']


class ItineraryBoardDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for board detail views."""
    
    columns = ItineraryColumnSerializer(many=True, read_only=True)
    columns_count = serializers.IntegerField(source='columns.count', read_only=True)
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    
    class Meta:
        model = ItineraryBoard
        fields = [
            'id',
            'title',
            'slug',
            'description',
            'is_public',
            'share_token',
            'supplier',
            'supplier_name',
            'price',
            'currency',
            'is_active',
            'created_at',
            'updated_at',
            'columns',
            'columns_count',
        ]
        read_only_fields = ['id', 'slug', 'share_token', 'created_at', 'updated_at']


class ItineraryBoardCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating boards."""
    
    class Meta:
        model = ItineraryBoard
        fields = [
            'id',
            'title',
            'description',
            'is_public',
            'price',
            'currency',
            'is_active',
            'slug',
            'share_token',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'share_token', 'created_at', 'updated_at']
    
    def validate_title(self, value):
        """Validate title is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Judul wajib diisi.")
        return value.strip()


class ItineraryColumnCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating columns."""
    
    class Meta:
        model = ItineraryColumn
        fields = [
            'id',
            'board',
            'title',
            'description',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItineraryCardCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating cards."""
    
    class Meta:
        model = ItineraryCard
        fields = [
            'id',
            'column',
            'title',
            'description',
            'start_time',
            'end_time',
            'date',
            'location_name',
            'location_address',
            'latitude',
            'longitude',
            'cover_image',
            'order',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItineraryCardAttachmentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating attachments."""
    
    class Meta:
        model = ItineraryCardAttachment
        fields = [
            'id',
            'card',
            'file',
            'name',
            'file_type',
            'file_size',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_file(self, value):
        """Validate file is provided."""
        if not value:
            raise serializers.ValidationError("File wajib diisi.")
        return value
    
    def validate(self, attrs):
        """Auto-populate file_type and file_size if file is provided."""
        if 'file' in attrs and attrs['file']:
            file = attrs['file']
            # Auto-detect file type
            if 'file_type' not in attrs or not attrs['file_type']:
                import mimetypes
                file_type, _ = mimetypes.guess_type(file.name)
                attrs['file_type'] = file_type or file.name.split('.')[-1] if '.' in file.name else 'unknown'
            
            # Auto-calculate file size
            if 'file_size' not in attrs or not attrs['file_size']:
                attrs['file_size'] = file.size
            
            # Auto-set name if not provided
            if 'name' not in attrs or not attrs['name']:
                attrs['name'] = file.name
        
        return attrs


class ItineraryCardChecklistCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating checklists."""
    
    class Meta:
        model = ItineraryCardChecklist
        fields = [
            'id',
            'card',
            'title',
            'items',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_items(self, value):
        """Validate items structure."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Items harus berupa array.")
        
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Setiap item harus berupa objek.")
            if 'text' not in item:
                raise serializers.ValidationError("Setiap item harus memiliki field 'text'.")
            if 'id' not in item:
                raise serializers.ValidationError("Setiap item harus memiliki field 'id'.")
            if 'completed' not in item:
                item['completed'] = False
        

class ItineraryTransactionSerializer(serializers.ModelSerializer):
    """Serializer for itinerary transactions."""
    
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    board_title = serializers.CharField(source='board.title', read_only=True)
    supplier_name = serializers.CharField(source='board.supplier.company_name', read_only=True, allow_null=True)
    is_access_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = ItineraryTransaction
        fields = [
            'id',
            'board',
            'board_title',
            'customer',
            'customer_email',
            'supplier_name',
            'status',
            'amount',
            'access_duration_days',
            'created_at',
            'activated_at',
            'expires_at',
            'completed_at',
            'transaction_number',
            'external_reference',
            'notes',
            'is_access_valid',
        ]
        read_only_fields = [
            'id',
            'board_title',
            'customer_email',
            'supplier_name',
            'amount',
            'created_at',
            'activated_at',
            'expires_at',
            'completed_at',
            'transaction_number',
            'is_access_valid',
        ]
    
    def get_is_access_valid(self, obj):
        """Check if customer currently has valid access."""
        return obj.is_access_valid()


class ItineraryTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating itinerary transactions."""
    
    class Meta:
        model = ItineraryTransaction
        fields = [
            'id',
            'board',
            'access_duration_days',
            'notes',
        ]
        read_only_fields = ['id']
    
    def validate_board(self, value):
        """Validate that the board exists and is active."""
        if not value.is_active:
            raise serializers.ValidationError("Itinerary board tidak aktif.")
        if not value.is_public:
            raise serializers.ValidationError("Itinerary board tidak tersedia untuk publik.")
        return value


class ItineraryTransactionListSerializer(serializers.ModelSerializer):
    """Serializer for listing itinerary transactions."""
    
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    board_title = serializers.CharField(source='board.title', read_only=True)
    supplier_name = serializers.CharField(source='board.supplier.company_name', read_only=True, allow_null=True)
    is_access_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = ItineraryTransaction
        fields = [
            'id',
            'board',
            'board_title',
            'customer_email',
            'supplier_name',
            'status',
            'access_duration_days',
            'activated_at',
            'expires_at',
            'transaction_number',
            'is_access_valid',
            'created_at',
            'amount',
        ]
        read_only_fields = [
            'id',
            'board',
            'board_title',
            'customer_email',
            'supplier_name',
            'transaction_number',
            'is_access_valid',
            'created_at',
            'activated_at',
            'expires_at',
            'amount',
        ]
    
    def get_is_access_valid(self, obj):
        """Check if customer currently has valid access."""
        return obj.is_access_valid()
