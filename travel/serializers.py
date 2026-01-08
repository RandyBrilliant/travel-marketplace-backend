from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.utils.text import slugify
from django.conf import settings
import os
import json
import logging
from .models import (
    TourPackage,
    TourDate,
    TourImage,
    ResellerTourCommission,
    ResellerGroup,
    Booking,
    SeatSlot,
    SeatSlotStatus,
    Payment,
    ResellerCommission,
)
from .utils import optimize_image_to_webp
from account.models import ResellerProfile, SupplierProfile

logger = logging.getLogger('travel')


def build_absolute_image_url(relative_url, request=None):
    """
    Build absolute URL from relative path for embedding in JWT token.
    
    Note: This method is called without request context in get_token().
    For production, ensure API_DOMAIN is set in environment variables.
    """
    if not relative_url or relative_url.startswith('http'):
        return relative_url
    
    # Ensure it starts with /
    if not relative_url.startswith('/'):
        relative_url = '/' + relative_url
    
    # Use API domain from settings or environment
    if settings.DEBUG:
        base_url = 'http://localhost:8000'
    else:
        api_domain = getattr(settings, 'API_DOMAIN', None) or os.environ.get('API_DOMAIN', 'data.goholiday.id')
        base_url = f'https://{api_domain}'
    
    return f'{base_url}{relative_url}'


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
            raise serializers.ValidationError("File gambar wajib diisi.")
        return value
    
    def create(self, validated_data):
        """Create tour image and optimize it to WebP format."""
        instance = super().create(validated_data)
        
        # Optimize image immediately after creation
        if instance.image:
            try:
                optimize_image_to_webp(instance.image, max_width=1920, max_height=1920, quality=85)
                # Save the optimized image
                instance.save(update_fields=['image'])
            except Exception as e:
                # Log error but don't fail the creation
                logger.warning(f"Failed to optimize image {instance.image.name}: {str(e)}", exc_info=True)
        
        return instance
    
    def update(self, instance, validated_data):
        """Update tour image and optimize it to WebP format if image changed."""
        
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
    """Serializer for seat slots within a tour date with comprehensive passenger details."""
    
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    booking_id = serializers.IntegerField(source="booking.id", read_only=True, allow_null=True)
    
    class Meta:
        model = SeatSlot
        fields = [
            "id",
            "seat_number",
            "status",
            "status_display",
            "booking_id",
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status_display", "booking_id", "created_at", "updated_at"]


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
            "airline",
            "price",
            "total_seats",
            "remaining_seats",
            "is_high_season",
            "available_seats_count",
            "booked_seats_count",
            "seat_slots",
        ]
        read_only_fields = ["id", "remaining_seats", "available_seats_count", "booked_seats_count", "seat_slots"]
    
    def validate_departure_date(self, value):
        """Validate departure date is in the future and not too far ahead."""
        from django.utils import timezone
        from datetime import timedelta
        
        if value:
            today = timezone.now().date()
            
            if value < today:
                raise serializers.ValidationError("Tanggal keberangkatan harus di masa depan.")
            
            # Limit advance bookings to 2 years
            max_future_date = today + timedelta(days=730)
            if value > max_future_date:
                raise serializers.ValidationError("Tanggal keberangkatan tidak boleh lebih dari 2 tahun ke depan.")
        
        return value
    
    def validate_price(self, value):
        """Validate price is not negative."""
        if value is not None and value < 0:
            raise serializers.ValidationError("Harga tidak boleh negatif.")
        return value
    
    def validate_total_seats(self, value):
        """Validate total seats is at least 1."""
        if value is not None and value < 1:
            raise serializers.ValidationError("Total kursi harus minimal 1.")
        return value
    
    def get_seat_slots(self, obj):
        """Return seat slots ordered by seat number."""
        # Get seat slots, ordered by seat number (natural sort)
        # Use prefetch_related if available to avoid N+1 queries
        if hasattr(obj, '_prefetched_objects_cache') and 'seat_slots' in obj._prefetched_objects_cache:
            slots = obj._prefetched_objects_cache['seat_slots']
        else:
            slots = obj.seat_slots.all()
        slots = sorted(slots, key=lambda x: (len(x.seat_number), x.seat_number))
        return SeatSlotSerializer(slots, many=True, context=self.context).data


class TourPackageSerializer(serializers.ModelSerializer):
    """Serializer for tour packages (supplier view)."""
    
    supplier = serializers.PrimaryKeyRelatedField(read_only=True)
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
    images = TourImageSerializer(many=True, read_only=True)
    dates = TourDateSerializer(many=True, read_only=True)
    duration_display = serializers.CharField(read_only=True)
    group_size_display = serializers.CharField(read_only=True)
    itinerary_pdf_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TourPackage
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "name",
            "slug",
            "itinerary",
            "country",
            "days",
            "nights",
            "duration_display",
            "max_group_size",
            "group_size_display",
            "tour_type",
            "highlights",
            "inclusions",
            "exclusions",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "visa_price",
            "tipping_price",
            "itinerary_pdf",
            "itinerary_pdf_url",
            "is_active",
            "images",
            "dates",
            "reseller_groups",
            "commission",
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
            "itinerary_pdf_url",
            "commission",
        ]
    
    def get_itinerary_pdf_url(self, obj):
        """Return absolute URL for itinerary PDF if exists."""
        if obj.itinerary_pdf:
            request = self.context.get("request")
            return build_absolute_image_url(obj.itinerary_pdf.url, request)
        return None
    
    def validate_slug(self, value):
        """Auto-generate slug from name if not provided."""
        if not value and self.initial_data.get("name"):
            value = self._generate_unique_slug(self.initial_data["name"])
        return value
    
    def create(self, validated_data):
        """Create tour package and auto-generate slug if needed."""
        if "slug" not in validated_data or not validated_data["slug"]:
            validated_data["slug"] = self._generate_unique_slug(validated_data["name"])
        return super().create(validated_data)
    
    @staticmethod
    def _generate_unique_slug(name, instance=None):
        """Generate a unique slug from name."""
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        queryset = TourPackage.objects.filter(slug=slug)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        while queryset.exists():
            slug = f"{base_slug}-{counter}"
            queryset = TourPackage.objects.filter(slug=slug)
            if instance:
                queryset = queryset.exclude(pk=instance.pk)
            counter += 1
        return slug


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
            "country",
            "days",
            "nights",
            "duration_display",
            "tour_type",
            "base_price",
            "is_active",
            "supplier_name",
            "main_image_url",
            "created_at",
        ]
    
    def get_main_image_url(self, obj):
        """
        Return absolute URL for primary image from gallery images.
        Gets the image marked as primary (is_primary=True), or None if no primary image exists.
        """
        # Get primary image from prefetched images if available
        if hasattr(obj, '_prefetched_objects_cache') and 'images' in obj._prefetched_objects_cache:
            images = obj._prefetched_objects_cache['images']
            primary_image = next((img for img in images if img.is_primary), None)
        else:
            # Fallback to query if not prefetched
            primary_image = obj.images.filter(is_primary=True).first()
        
        if primary_image and primary_image.image:
            request = self.context.get("request")
            return build_absolute_image_url(primary_image.image.url, request)
        
        return None

class PublicTourPackageDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for public tour package detail view."""
    
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
    duration_display = serializers.CharField(read_only=True)
    group_size_display = serializers.CharField(read_only=True)
    itinerary_pdf_url = serializers.SerializerMethodField()
    images = TourImageSerializer(many=True, read_only=True)
    dates = serializers.SerializerMethodField()
    reseller_commission = serializers.SerializerMethodField()
    
    class Meta:
        model = TourPackage
        fields = [
            "id",
            "name",
            "slug",
            "itinerary",
            "country",
            "days",
            "nights",
            "duration_display",
            "max_group_size",
            "group_size_display",
            "tour_type",
            "highlights",
            "inclusions",
            "exclusions",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "visa_price",
            "tipping_price",
            "itinerary_pdf_url",
            "images",
            "dates",
            "supplier_name",
            "reseller_commission",
            "is_active",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "duration_display",
            "group_size_display",
            "itinerary_pdf_url",
            "created_at",
        ]
    
    def get_itinerary_pdf_url(self, obj):
        """Return absolute URL for itinerary PDF if exists."""
        if obj.itinerary_pdf:
            request = self.context.get("request")
            return build_absolute_image_url(obj.itinerary_pdf.url, request)
        return None
    
    def get_dates(self, obj):
        """Return available tour dates (only future dates with available seats)."""
        from django.utils import timezone
        from django.db.models import Count, Q
        
        # Always query database for accurate filtering and counting
        # Prefetching is handled in the view
        today = timezone.now().date()
        future_dates = obj.dates.filter(
            departure_date__gte=today
        ).annotate(
            available_count=Count('seat_slots', filter=Q(seat_slots__status=SeatSlotStatus.AVAILABLE))
        ).filter(
            available_count__gt=0
        ).prefetch_related("seat_slots").order_by("departure_date")[:10]
        
        return TourDateSerializer(future_dates, many=True, context=self.context).data
    
    def get_reseller_commission(self, obj):
        """Return reseller commission amount if user is authenticated reseller."""
        from account.models import UserRole
        
        request = self.context.get("request")
        if request and request.user.is_authenticated and request.user.role == UserRole.RESELLER:
            # Use prefetched reseller_profile if available to avoid N+1 query
            if hasattr(request.user, 'reseller_profile'):
                reseller_profile = request.user.reseller_profile
            else:
                try:
                    reseller_profile = ResellerProfile.objects.select_related('user').get(user=request.user)
                except ResellerProfile.DoesNotExist:
                    return None
            commission = obj.get_reseller_commission(reseller_profile)
            return commission
        return None


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
            "itinerary",
            "country",
            "days",
            "nights",
            "max_group_size",
            "tour_type",
            "highlights",
            "inclusions",
            "exclusions",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "visa_price",
            "tipping_price",
            "itinerary_pdf",
            "is_active",
            "reseller_groups",
            "commission",
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
                raise serializers.ValidationError("Format JSON tidak valid")
        return value
    
    def validate_inclusions(self, value):
        """Convert list to JSON if needed."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Format JSON tidak valid")
        return value
    
    def validate_exclusions(self, value):
        """Convert list to JSON if needed."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Format JSON tidak valid")
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
                    'nights': f'Jumlah malam ({nights}) tidak boleh lebih besar dari jumlah hari ({days}).'
                })
        
        return attrs
    
    def validate_slug(self, value):
        """Auto-generate slug from name if not provided."""
        if not value and self.initial_data.get("name"):
            value = TourPackageSerializer._generate_unique_slug(self.initial_data["name"], self.instance)
        return value
    
    def create(self, validated_data):
        """Create tour package and auto-generate slug if needed."""
        # Ensure slug is generated from name if not provided or empty
        name = validated_data.get("name")
        if not name:
            raise serializers.ValidationError({"name": "Nama wajib diisi untuk membuat paket tur."})
        
        # Remove slug from validated_data if it's empty or not provided
        slug = validated_data.pop("slug", None)
        if not slug or slug == "":
            slug = TourPackageSerializer._generate_unique_slug(name)
        
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
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
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
            "itinerary",
            "country",
            "days",
            "nights",
            "duration_display",
            "max_group_size",
            "group_size_display",
            "tour_type",
            "highlights",
            "inclusions",
            "exclusions",
            "cancellation_policy",
            "important_notes",
            "base_price",
            "visa_price",
            "tipping_price",
            "itinerary_pdf",
            "is_active",
            "reseller_groups",
            "images",
            "dates",
            # Commission fields (editable for admin)
            "commission",
            # Timestamps
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "supplier_name",
            "duration_display",
            "group_size_display",
            "images",
            "dates",
            "created_at",
            "updated_at",
        ]
    
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
                    'nights': f'Jumlah malam ({nights}) tidak boleh lebih besar dari jumlah hari ({days}).'
                })
        
        return attrs
    
    def validate_slug(self, value):
        """Auto-generate slug from name if not provided."""
        if not value and self.initial_data.get("name"):
            value = TourPackageSerializer._generate_unique_slug(self.initial_data["name"], self.instance)
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
    
    def to_representation(self, instance):
        """Include reseller details in read operations."""
        representation = super().to_representation(instance)
        # Include reseller details if needed
        # Use prefetched resellers to avoid N+1 queries
        if self.context.get("request") and hasattr(instance, "resellers"):
            if hasattr(instance, '_prefetched_objects_cache') and 'resellers' in instance._prefetched_objects_cache:
                resellers = instance._prefetched_objects_cache['resellers']
            else:
                resellers = instance.resellers.select_related('user').all()
            
            representation["resellers"] = [
                {
                    "id": r.id,
                    "full_name": r.full_name,
                    "email": r.user.email,
                }
                for r in resellers
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
    payment_status = serializers.CharField(source="payment.status", read_only=True, allow_null=True)
    
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
            "payment_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "seats_booked", "total_amount", "payment_status"]


class BookingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating booking status (admin only)."""
    
    class Meta:
        model = Booking
        fields = ["status", "notes"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SeatSlotCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating seat slots with passenger details during booking."""
    
    class Meta:
        model = SeatSlot
        fields = [
            "seat_number",
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
        ]


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bookings with seat slots and passenger details."""
    
    seat_slots = SeatSlotCreateSerializer(many=True, required=True)
    
    class Meta:
        model = Booking
        fields = [
            "tour_date",
            "customer_name",
            "customer_email",
            "customer_phone",
            "platform_fee",
            "total_amount",
            "notes",
            "seat_slots",
        ]
    
    def validate_seat_slots(self, value):
        """Validate that at least one seat slot is provided."""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Minimal satu kursi harus dipilih.")
        return value
    
    def validate(self, attrs):
        """Validate seat slots belong to the tour date."""
        tour_date = attrs.get('tour_date')
        seat_slots = attrs.get('seat_slots', [])
        
        if tour_date and seat_slots:
            # Get available seat numbers for this tour date
            available_seats = set(
                tour_date.seat_slots.filter(status=SeatSlotStatus.AVAILABLE)
                .values_list('seat_number', flat=True)
            )
            
            # Check all requested seats are available
            requested_seats = {slot['seat_number'] for slot in seat_slots}
            unavailable_seats = requested_seats - available_seats
            
            if unavailable_seats:
                raise serializers.ValidationError({
                    'seat_slots': f'Kursi {", ".join(unavailable_seats)} tidak tersedia.'
                })
            
            # Check for duplicate seat numbers
            if len(requested_seats) != len(seat_slots):
                raise serializers.ValidationError({
                    'seat_slots': 'Nomor kursi duplikat tidak diperbolehkan.'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create booking and assign seat slots with passenger details."""
        from django.db import transaction
        from django.db.models import F
        
        seat_slots_data = validated_data.pop('seat_slots')
        tour_date = validated_data['tour_date']
        
        with transaction.atomic():
            # Use select_for_update to prevent race conditions
            seat_numbers = [slot['seat_number'] for slot in seat_slots_data]
            seat_slots = list(
                tour_date.seat_slots.select_for_update().filter(
                    seat_number__in=seat_numbers,
                    status=SeatSlotStatus.AVAILABLE
                )
            )
            
            # Check if all requested seats are available
            available_seat_numbers = {slot.seat_number for slot in seat_slots}
            requested_seat_numbers = set(seat_numbers)
            unavailable_seats = requested_seat_numbers - available_seat_numbers
            
            if unavailable_seats:
                raise ValidationError({
                    'seat_slots': f'Kursi {", ".join(unavailable_seats)} tidak tersedia.'
                })
            
            # Check for duplicates in request
            if len(seat_numbers) != len(requested_seat_numbers):
                raise ValidationError({
                    'seat_slots': 'Nomor kursi duplikat tidak diperbolehkan.'
                })
            
            # Create booking
            booking = Booking.objects.create(**validated_data)
            
            # Create a mapping for quick lookup
            seat_slot_map = {slot.seat_number: slot for slot in seat_slots}
            
            # Assign seat slots and update passenger details
            for slot_data in seat_slots_data:
                seat_number = slot_data.pop('seat_number')
                seat_slot = seat_slot_map[seat_number]
                
                # Update seat slot with passenger details and assign to booking
                # Convert empty strings to None for optional fields
                for key, value in slot_data.items():
                    if value == "":
                        value = None
                    setattr(seat_slot, key, value)
                seat_slot.booking = booking
                seat_slot.status = SeatSlotStatus.BOOKED
                seat_slot.save()
            
            return booking


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
    payment_status = serializers.CharField(source="payment.status", read_only=True, allow_null=True)
    payment_amount = serializers.IntegerField(source="payment.amount", read_only=True, allow_null=True)
    payment_proof_image = serializers.ImageField(source="payment.proof_image", read_only=True, allow_null=True)
    payment_id = serializers.IntegerField(source="payment.id", read_only=True, allow_null=True)
    
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
            "payment_status",
            "payment_amount",
            "payment_proof_image",
            "payment_id",
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
            "payment_status",
            "payment_amount",
        ]


# ==================== PAYMENT SERIALIZERS ====================

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment records with validation."""
    
    booking_id = serializers.IntegerField(source="booking.id", read_only=True)
    booking_customer_name = serializers.CharField(source="booking.customer_name", read_only=True)
    booking_total_amount = serializers.IntegerField(source="booking.total_amount", read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            "id",
            "booking",
            "booking_id",
            "booking_customer_name",
            "booking_total_amount",
            "amount",
            "transfer_date",
            "sender_account_name",
            "sender_bank_name",
            "sender_account_number",
            "proof_image",
            "status",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "booking_id",
            "booking_customer_name",
            "booking_total_amount",
            "status",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]


class PaymentApprovalSerializer(serializers.ModelSerializer):
    """Serializer for approving/rejecting payments (admin use)."""
    
    class Meta:
        model = Payment
        fields = [
            "id",
            "status",
            "reviewed_at",
        ]
        read_only_fields = [
            "id",
            "reviewed_at",
        ]


# ==================== COMMISSION SERIALIZERS ====================

class ResellerCommissionSerializer(serializers.ModelSerializer):
    """Serializer for reseller commissions per booking."""
    
    reseller_name = serializers.CharField(source="reseller.full_name", read_only=True)
    reseller_email = serializers.EmailField(source="reseller.user.email", read_only=True)
    booking_id = serializers.IntegerField(source="booking.id", read_only=True)
    
    class Meta:
        model = ResellerCommission
        fields = [
            "id",
            "booking",
            "booking_id",
            "reseller",
            "reseller_name",
            "reseller_email",
            "level",
            "amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "booking_id",
            "reseller_name",
            "reseller_email",
            "created_at",
            "updated_at",
        ]
