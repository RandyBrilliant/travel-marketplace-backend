from rest_framework import serializers
from django.utils.text import slugify
from .models import (
    TourPackage,
    TourDate,
    TourImage,
    ItineraryItem,
    TourCategory,
    TourType,
    TourBadge,
)


class ItineraryItemSerializer(serializers.ModelSerializer):
    """Serializer for itinerary items (day-by-day itinerary)."""
    
    class Meta:
        model = ItineraryItem
        fields = ["id", "day_number", "title", "description"]
        read_only_fields = ["id"]


class TourImageSerializer(serializers.ModelSerializer):
    """Serializer for tour gallery images."""
    
    class Meta:
        model = TourImage
        fields = ["id", "image", "caption", "order", "is_primary", "created_at"]
        read_only_fields = ["id", "created_at"]


class TourDateSerializer(serializers.ModelSerializer):
    """Serializer for tour dates."""
    
    available_seats_count = serializers.IntegerField(read_only=True)
    booked_seats_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = TourDate
        fields = [
            "id",
            "departure_date",
            "price",
            "total_seats",
            "remaining_seats",
            "is_high_season",
            "available_seats_count",
            "booked_seats_count",
        ]
        read_only_fields = ["id", "remaining_seats", "available_seats_count", "booked_seats_count"]


class TourPackageSerializer(serializers.ModelSerializer):
    """Serializer for tour packages (supplier view)."""
    
    supplier = serializers.PrimaryKeyRelatedField(read_only=True)
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
    itinerary_items = ItineraryItemSerializer(many=True, read_only=True)
    images = TourImageSerializer(many=True, read_only=True)
    dates = TourDateSerializer(many=True, read_only=True)
    duration_display = serializers.CharField(read_only=True)
    group_size_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = TourPackage
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "name",
            "slug",
            "summary",
            "description",
            "city",
            "country",
            "days",
            "nights",
            "duration_display",
            "max_group_size",
            "group_type",
            "group_size_display",
            "tour_type",
            "category",
            "tags",
            "highlights",
            "inclusions",
            "exclusions",
            "meeting_point",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "currency",
            "badge",
            "main_image",
            "itinerary_pdf",
            "is_active",
            "is_featured",
            "itinerary_items",
            "images",
            "dates",
            "created_at",
            "updated_at",
            # Commission fields (read-only for suppliers)
            "commission_rate",
            "commission_type",
            "fixed_commission_amount",
            "commission_notes",
        ]
        read_only_fields = [
            "id",
            "supplier",
            "supplier_name",
            "slug",
            "created_at",
            "updated_at",
            "duration_display",
            "group_size_display",
            # Commission fields are admin-only
            "commission_rate",
            "commission_type",
            "fixed_commission_amount",
            "commission_notes",
        ]
    
    def validate_slug(self, value):
        """Auto-generate slug from name if not provided."""
        if not value and self.initial_data.get("name"):
            value = slugify(self.initial_data["name"])
            # Ensure uniqueness
            base_slug = value
            counter = 1
            while TourPackage.objects.filter(slug=value).exists():
                value = f"{base_slug}-{counter}"
                counter += 1
        return value
    
    def create(self, validated_data):
        """Create tour package and auto-generate slug if needed."""
        if "slug" not in validated_data or not validated_data["slug"]:
            validated_data["slug"] = slugify(validated_data["name"])
            # Ensure uniqueness
            base_slug = validated_data["slug"]
            counter = 1
            while TourPackage.objects.filter(slug=validated_data["slug"]).exists():
                validated_data["slug"] = f"{base_slug}-{counter}"
                counter += 1
        return super().create(validated_data)


class TourPackageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for tour package list view."""
    
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
    duration_display = serializers.CharField(read_only=True)
    main_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TourPackage
        fields = [
            "id",
            "name",
            "slug",
            "summary",
            "city",
            "country",
            "days",
            "nights",
            "duration_display",
            "tour_type",
            "category",
            "base_price",
            "currency",
            "badge",
            "main_image_url",
            "is_active",
            "is_featured",
            "supplier_name",
            "created_at",
        ]
    
    def get_main_image_url(self, obj):
        """Return absolute URL for main image if exists."""
        if obj.main_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.main_image.url)
            return obj.main_image.url
        return None


class TourPackageCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating tour packages (excludes nested relations)."""
    
    supplier = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = TourPackage
        fields = [
            "id",
            "supplier",
            "name",
            "slug",
            "summary",
            "description",
            "city",
            "country",
            "days",
            "nights",
            "max_group_size",
            "group_type",
            "tour_type",
            "category",
            "tags",
            "highlights",
            "inclusions",
            "exclusions",
            "meeting_point",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "currency",
            "badge",
            "main_image",
            "itinerary_pdf",
            "is_active",
            "is_featured",
        ]
        read_only_fields = ["id", "supplier", "slug"]
    
    def validate_slug(self, value):
        """Auto-generate slug from name if not provided."""
        if not value and self.initial_data.get("name"):
            value = slugify(self.initial_data["name"])
            # Ensure uniqueness
            base_slug = value
            counter = 1
            queryset = TourPackage.objects.filter(slug=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            while queryset.exists():
                value = f"{base_slug}-{counter}"
                queryset = TourPackage.objects.filter(slug=value)
                if self.instance:
                    queryset = queryset.exclude(pk=self.instance.pk)
                counter += 1
        return value

