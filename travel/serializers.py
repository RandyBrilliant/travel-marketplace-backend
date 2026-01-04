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
    ResellerTourCommission,
    ResellerGroup,
    Booking,
    BookingStatus,
    SeatSlotStatus,
)
from account.models import ResellerProfile, SupplierProfile


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
            "reseller_groups",
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


class PublicTourPackageDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for public tour package detail view."""
    
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
    duration_display = serializers.CharField(read_only=True)
    group_size_display = serializers.CharField(read_only=True)
    main_image_url = serializers.SerializerMethodField()
    images = TourImageSerializer(many=True, read_only=True)
    itinerary_items = ItineraryItemSerializer(many=True, read_only=True)
    dates = serializers.SerializerMethodField()
    
    class Meta:
        model = TourPackage
        fields = [
            "id",
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
            "main_image_url",
            "images",
            "itinerary_items",
            "dates",
            "supplier_name",
            "is_active",
            "is_featured",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "duration_display",
            "group_size_display",
            "main_image_url",
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
    
    def get_dates(self, obj):
        """Return available tour dates (only future dates with available seats)."""
        from django.utils import timezone
        
        # Get future dates with available seats
        # Note: remaining_seats is a property, not a database field
        # We need to filter by seat_slots__status instead
        future_dates = obj.dates.filter(
            departure_date__gte=timezone.now().date(),
            seat_slots__status=SeatSlotStatus.AVAILABLE
        ).distinct().order_by("departure_date")[:10]  # Limit to 10 upcoming dates
        
        return TourDateSerializer(future_dates, many=True, context=self.context).data


class TourPackageCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating tour packages (excludes nested relations)."""
    
    supplier = serializers.PrimaryKeyRelatedField(read_only=True)
    reseller_groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ResellerGroup.objects.filter(is_active=True),
        required=False,
    )
    
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
            "reseller_groups",
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


class AdminTourPackageSerializer(serializers.ModelSerializer):
    """Serializer for admin to create/update tour packages with commission fields."""
    
    supplier = serializers.PrimaryKeyRelatedField(
        queryset=SupplierProfile.objects.all(),
        required=True
    )
    reseller_groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ResellerGroup.objects.filter(is_active=True),
        required=False,
    )
    
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
            "reseller_groups",
            # Commission fields (editable for admin)
            "commission_rate",
            "commission_type",
            "fixed_commission_amount",
            "commission_notes",
        ]
        read_only_fields = ["id", "slug"]
    
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


class ResellerTourCommissionSerializer(serializers.ModelSerializer):
    """Serializer for reseller tour commission settings."""
    
    reseller_name = serializers.CharField(source="reseller.full_name", read_only=True)
    reseller_email = serializers.EmailField(source="reseller.user.email", read_only=True)
    tour_package_name = serializers.CharField(source="tour_package.name", read_only=True)
    tour_package_slug = serializers.SlugField(source="tour_package.slug", read_only=True)
    
    class Meta:
        model = ResellerTourCommission
        fields = [
            "id",
            "reseller",
            "reseller_name",
            "reseller_email",
            "tour_package",
            "tour_package_name",
            "tour_package_slug",
            "commission_amount",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ResellerGroupSerializer(serializers.ModelSerializer):
    """Serializer for reseller groups."""
    
    created_by_name = serializers.CharField(source="created_by.email", read_only=True)
    reseller_count = serializers.IntegerField(source="resellers.count", read_only=True)
    tour_count = serializers.IntegerField(source="tour_packages.count", read_only=True)
    reseller_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ResellerProfile.objects.all(),
        source="resellers",
        write_only=True,
        required=False,
    )
    
    class Meta:
        model = ResellerGroup
        fields = [
            "id",
            "name",
            "description",
            "created_by",
            "created_by_name",
            "is_active",
            "reseller_count",
            "tour_count",
            "reseller_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_by_name", "created_at", "updated_at"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def to_representation(self, instance):
        """Include reseller details in read operations."""
        representation = super().to_representation(instance)
        # Include reseller details if needed
        if self.context.get("request") and hasattr(instance, "resellers"):
            representation["resellers"] = [
                {
                    "id": r.id,
                    "full_name": r.full_name,
                    "email": r.user.email,
                }
                for r in instance.resellers.all()
            ]
        return representation
    
    def create(self, validated_data):
        """Create group and assign resellers."""
        resellers = validated_data.pop("resellers", [])
        group = ResellerGroup.objects.create(**validated_data)
        if resellers:
            group.resellers.set(resellers)
        return group
    
    def update(self, instance, validated_data):
        """Update group and resellers."""
        resellers = validated_data.pop("resellers", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if resellers is not None:
            instance.resellers.set(resellers)
        return instance


class BookingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for booking list view."""
    
    reseller_name = serializers.CharField(source="reseller.full_name", read_only=True)
    tour_package_name = serializers.CharField(source="tour_date.package.name", read_only=True)
    departure_date = serializers.DateField(source="tour_date.departure_date", read_only=True)
    seats_booked = serializers.IntegerField(read_only=True)
    total_amount = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            "id",
            "reseller",
            "reseller_name",
            "tour_date",
            "tour_package_name",
            "departure_date",
            "customer_name",
            "customer_email",
            "customer_phone",
            "status",
            "seats_booked",
            "platform_fee",
            "total_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "seats_booked", "total_amount"]


class BookingSerializer(serializers.ModelSerializer):
    """Detailed serializer for booking detail view."""
    
    reseller_name = serializers.CharField(source="reseller.full_name", read_only=True)
    reseller_email = serializers.EmailField(source="reseller.user.email", read_only=True)
    tour_package_name = serializers.CharField(source="tour_date.package.name", read_only=True)
    tour_package_slug = serializers.SlugField(source="tour_date.package.slug", read_only=True)
    departure_date = serializers.DateField(source="tour_date.departure_date", read_only=True)
    tour_price = serializers.IntegerField(source="tour_date.price", read_only=True)
    seats_booked = serializers.IntegerField(read_only=True)
    total_amount = serializers.IntegerField(read_only=True)
    subtotal = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            "id",
            "reseller",
            "reseller_name",
            "reseller_email",
            "tour_date",
            "tour_package_name",
            "tour_package_slug",
            "departure_date",
            "tour_price",
            "customer_name",
            "customer_email",
            "customer_phone",
            "status",
            "seats_booked",
            "platform_fee",
            "subtotal",
            "total_amount",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "seats_booked",
            "total_amount",
            "subtotal",
        ]

