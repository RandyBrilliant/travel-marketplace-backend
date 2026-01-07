from rest_framework import serializers
from django.utils.text import slugify
from django.conf import settings
import os
import json
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
    SeatSlot,
    SeatSlotStatus,
)
from account.models import ResellerProfile, SupplierProfile


def build_absolute_image_url(relative_url, request=None):
    """
    Build absolute HTTPS URL for images.
    Uses request if available, otherwise falls back to production domain.
    """
    if not relative_url:
        return None
    
    # If already absolute, return as-is
    if relative_url.startswith('http'):
        return relative_url
    
    # Use request if available (most reliable, respects X-Forwarded-Proto)
    if request:
        return request.build_absolute_uri(relative_url)
    
    # Fallback for production (when no request available, e.g., in tokens)
    if settings.DEBUG:
        return f"http://localhost:8000{relative_url}"
    
    # Production: always use HTTPS
    default_domain = getattr(settings, 'API_DOMAIN', None) or os.environ.get('API_DOMAIN', 'api.goholiday.id')
    return f"https://{default_domain}{relative_url}"


class ItineraryItemSerializer(serializers.ModelSerializer):
    """Serializer for itinerary items (day-by-day itinerary)."""
    
    class Meta:
        model = ItineraryItem
        fields = ["id", "day_number", "title", "description"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        """
        Ensure day_number is unique per package for this itinerary.
        We keep one itinerary row per day; multiple activities should be in description.
        """
        # Package is provided via serializer.save(package=...) in the view
        package = getattr(self.instance, "package", None)
        if not package and "package" in attrs:
            package = attrs["package"]

        day_number = attrs.get("day_number", getattr(self.instance, "day_number", None))

        if package and day_number is not None:
            qs = ItineraryItem.objects.filter(package=package, day_number=day_number)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "day_number": [
                            "Itinerary untuk hari ini sudah ada. Tambahkan aktivitas tambahan di deskripsi hari tersebut."
                        ]
                    }
                )

        return attrs


class TourImageSerializer(serializers.ModelSerializer):
    """Serializer for tour gallery images (read-only for list/detail)."""
    
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = TourImage
        fields = ["id", "image", "caption", "order", "is_primary", "created_at", "package"]
        read_only_fields = ["id", "created_at"]
    
    def get_image(self, obj):
        """Return absolute URL for image."""
        if obj.image:
            request = self.context.get("request")
            return build_absolute_image_url(obj.image.url, request)
        return None


class TourImageCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating tour images (accepts image file)."""
    
    image_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = TourImage
        fields = ["id", "package", "image", "caption", "order", "is_primary", "created_at", "image_url"]
        read_only_fields = ["id", "created_at", "image_url"]
    
    def get_image_url(self, obj):
        """Return absolute URL for image."""
        if obj.image:
            request = self.context.get("request")
            return build_absolute_image_url(obj.image.url, request)
        return None
    
    def validate_image(self, value):
        """Validate that image is provided."""
        if not value:
            raise serializers.ValidationError("Image file is required.")
        return value
    
    def create(self, validated_data):
        """Create tour image and optimize it to WebP format."""
        from .utils import optimize_image_to_webp
        
        instance = super().create(validated_data)
        
        # Optimize image immediately after creation
        if instance.image:
            try:
                optimize_image_to_webp(instance.image, max_width=1920, max_height=1920, quality=85)
                # Save the optimized image
                instance.save(update_fields=['image'])
            except Exception as e:
                # Log error but don't fail the creation
                import sys
                print(f"Warning: Failed to optimize image: {str(e)}", file=sys.stderr)
        
        return instance
    
    def update(self, instance, validated_data):
        """Update tour image and optimize it to WebP format if image changed."""
        from .utils import optimize_image_to_webp
        
        image_changed = 'image' in validated_data and validated_data['image'] != instance.image
        
        instance = super().update(instance, validated_data)
        
        # Optimize image if it was updated
        if image_changed and instance.image:
            try:
                optimize_image_to_webp(instance.image, max_width=1920, max_height=1920, quality=85)
                # Save the optimized image
                instance.save(update_fields=['image'])
            except Exception as e:
                # Log error but don't fail the update
                import sys
                print(f"Warning: Failed to optimize image: {str(e)}", file=sys.stderr)
        
        return instance


class SeatSlotSerializer(serializers.ModelSerializer):
    """Serializer for seat slots within a tour date."""
    
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    booking_id = serializers.IntegerField(source="booking.id", read_only=True, allow_null=True)
    booking_number = serializers.CharField(source="booking.booking_number", read_only=True, allow_null=True)
    
    class Meta:
        model = SeatSlot
        fields = [
            "id",
            "seat_number",
            "status",
            "status_display",
            "booking_id",
            "booking_number",
            "passenger_name",
            "passenger_email",
            "passenger_phone",
            "passenger_date_of_birth",
            "passenger_gender",
            "passenger_nationality",
            "passport_number",
            "passport_issue_date",
            "passport_expiry_date",
            "passport_issue_country",
        ]
        read_only_fields = [
            "id",
            "status_display",
            "booking_id",
            "booking_number",
            "passenger_name",
            "passenger_email",
            "passenger_phone",
            "passenger_date_of_birth",
            "passenger_gender",
            "passenger_nationality",
            "passport_number",
            "passport_issue_date",
            "passport_expiry_date",
            "passport_issue_country",
        ]


class TourDateSerializer(serializers.ModelSerializer):
    """Serializer for tour dates."""
    
    available_seats_count = serializers.IntegerField(read_only=True)
    booked_seats_count = serializers.IntegerField(read_only=True)
    seat_slots = serializers.SerializerMethodField()
    
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
            "seat_slots",
        ]
        read_only_fields = ["id", "remaining_seats", "available_seats_count", "booked_seats_count", "seat_slots"]
    
    def get_seat_slots(self, obj):
        """Return seat slots ordered by seat number."""
        # Get seat slots, ordered by seat number (natural sort)
        slots = obj.seat_slots.all().order_by('seat_number')
        return SeatSlotSerializer(slots, many=True, context=self.context).data


class TourPackageSerializer(serializers.ModelSerializer):
    """Serializer for tour packages (supplier view)."""
    
    supplier = serializers.PrimaryKeyRelatedField(read_only=True)
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
    itinerary_items = ItineraryItemSerializer(many=True, read_only=True)
    images = TourImageSerializer(many=True, read_only=True)
    dates = TourDateSerializer(many=True, read_only=True)
    duration_display = serializers.CharField(read_only=True)
    group_size_display = serializers.CharField(read_only=True)
    main_image_url = serializers.SerializerMethodField()
    itinerary_pdf_url = serializers.SerializerMethodField()
    
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
            "country",
            "days",
            "nights",
            "duration_display",
            "max_group_size",
            "group_type",
            "group_size_display",
            "tour_type",
            "category",
            "highlights",
            "inclusions",
            "exclusions",
            "meeting_point",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "badge",
            "main_image",
            "main_image_url",
            "itinerary_pdf",
            "itinerary_pdf_url",
            "is_active",
            "is_featured",
            "itinerary_items",
            "images",
            "dates",
            "reseller_groups",
            "commission",
            "commission_notes",
            "created_at",
            "updated_at",
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
            "main_image_url",
            "itinerary_pdf_url",
            # Commission fields are admin-only
            "commission",
            "commission_notes",
        ]
    
    def get_main_image_url(self, obj):
        """Return absolute URL for main image if exists."""
        if obj.main_image:
            request = self.context.get("request")
            return build_absolute_image_url(obj.main_image.url, request)
        return None
    
    def get_itinerary_pdf_url(self, obj):
        """Return absolute URL for itinerary PDF if exists."""
        if obj.itinerary_pdf:
            request = self.context.get("request")
            return build_absolute_image_url(obj.itinerary_pdf.url, request)
        return None
    
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
            "country",
            "days",
            "nights",
            "duration_display",
            "tour_type",
            "category",
            "base_price",
            "badge",
            "main_image_url",
            "is_active",
            "is_featured",
            "supplier_name",
            "created_at",
        ]
    
    def get_main_image_url(self, obj):
        """
        Return absolute URL for main image if exists.
        Fallback to primary gallery image (or first gallery image) when main_image is not set.
        """
        request = self.context.get("request")
        
        # Prefer explicit main_image
        if obj.main_image:
            return build_absolute_image_url(obj.main_image.url, request)
        
        # Fallback to primary gallery image, then first gallery image
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image and primary_image.image:
            return build_absolute_image_url(primary_image.image.url, request)
        
        first_image = obj.images.first()
        if first_image and first_image.image:
            return build_absolute_image_url(first_image.image.url, request)
        
        return None


class PublicTourPackageDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for public tour package detail view."""
    
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
    duration_display = serializers.CharField(read_only=True)
    group_size_display = serializers.CharField(read_only=True)
    main_image_url = serializers.SerializerMethodField()
    itinerary_pdf_url = serializers.SerializerMethodField()
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
            "country",
            "days",
            "nights",
            "duration_display",
            "max_group_size",
            "group_type",
            "group_size_display",
            "tour_type",
            "category",
            "highlights",
            "inclusions",
            "exclusions",
            "meeting_point",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "badge",
            "main_image_url",
            "itinerary_pdf_url",
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
            "itinerary_pdf_url",
            "created_at",
        ]
    
    def get_main_image_url(self, obj):
        """Return absolute URL for main image if exists."""
        if obj.main_image:
            request = self.context.get("request")
            return build_absolute_image_url(obj.main_image.url, request)
        return None
    
    def get_itinerary_pdf_url(self, obj):
        """Return absolute URL for itinerary PDF if exists."""
        if obj.itinerary_pdf:
            request = self.context.get("request")
            return build_absolute_image_url(obj.itinerary_pdf.url, request)
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
            "country",
            "days",
            "nights",
            "max_group_size",
            "group_type",
            "tour_type",
            "category",
            "highlights",
            "inclusions",
            "exclusions",
            "meeting_point",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "badge",
            "main_image",
            "itinerary_pdf",
            "is_active",
            "is_featured",
            "reseller_groups",
            # Commission fields (now editable by suppliers as well)
            "commission",
            "commission_notes",
        ]
        read_only_fields = ["id", "supplier", "slug"]
    
    def validate_highlights(self, value):
        """Convert list to JSON if needed."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format")
        return value
    
    def validate_inclusions(self, value):
        """Convert list to JSON if needed."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format")
        return value
    
    def validate_exclusions(self, value):
        """Convert list to JSON if needed."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format")
        return value
    
    def validate(self, attrs):
        """Validate that nights is not greater than days."""
        days = attrs.get('days')
        nights = attrs.get('nights')
        
        # If updating, get existing values if not provided
        if self.instance:
            days = days if days is not None else self.instance.days
            nights = nights if nights is not None else self.instance.nights
        
        if days is not None and nights is not None:
            if nights > days:
                raise serializers.ValidationError({
                    'nights': f'Number of nights ({nights}) cannot be greater than number of days ({days}).'
                })
        
        return attrs
    
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
    
    def create(self, validated_data):
        """Create tour package and auto-generate slug if needed."""
        # Ensure slug is generated from name if not provided or empty
        name = validated_data.get("name")
        if not name:
            raise serializers.ValidationError({"name": "Name is required to create a tour package."})
        
        # Remove slug from validated_data if it's empty or not provided
        slug = validated_data.pop("slug", None)
        if not slug or slug == "":
            slug = slugify(name)
        
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while TourPackage.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        validated_data["slug"] = slug
        return super().create(validated_data)


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
            "country",
            "days",
            "nights",
            "max_group_size",
            "group_type",
            "tour_type",
            "category",
            "highlights",
            "inclusions",
            "exclusions",
            "meeting_point",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "badge",
            "main_image",
            "itinerary_pdf",
            "is_active",
            "is_featured",
            "reseller_groups",
            # Commission fields (editable for admin)
            "commission",
            "commission_notes",
        ]
        read_only_fields = ["id", "slug"]
    
    def validate(self, attrs):
        """Validate that nights is not greater than days."""
        days = attrs.get('days')
        nights = attrs.get('nights')
        
        # If updating, get existing values if not provided
        if self.instance:
            days = days if days is not None else self.instance.days
            nights = nights if nights is not None else self.instance.nights
        
        if days is not None and nights is not None:
            if nights > days:
                raise serializers.ValidationError({
                    'nights': f'Number of nights ({nights}) cannot be greater than number of days ({days}).'
                })
        
        return attrs
    
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


class SeatSlotSerializer(serializers.ModelSerializer):
    """Serializer for seat slot details."""
    
    class Meta:
        model = SeatSlot
        fields = [
            "id",
            "seat_number",
            "status",
            "passenger_name",
            "passenger_email",
            "passenger_phone",
            "passenger_date_of_birth",
            "passenger_gender",
            "passenger_nationality",
            "passport_number",
            "passport_issue_date",
            "passport_expiry_date",
            "passport_issue_country",
            "visa_required",
            "visa_number",
            "visa_issue_date",
            "visa_expiry_date",
            "visa_type",
            "special_requests",
            "emergency_contact_name",
            "emergency_contact_phone",
        ]
        read_only_fields = [
            "id",
        ]


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
    seat_slots = SeatSlotSerializer(many=True, read_only=True)
    
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
            "seat_slots",
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

