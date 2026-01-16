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
    WithdrawalRequest,
    WithdrawalRequestStatus,
)
from .utils import optimize_image_to_webp
from account.models import ResellerProfile, SupplierProfile

logger = logging.getLogger('travel')


class ResellerGroupListField(serializers.PrimaryKeyRelatedField):
    """
    Custom field that handles reseller groups with support for:
    - JSON string arrays from FormData (e.g., "[]", "[1,2,3]")
    - Regular arrays
    - String-to-int conversion for individual IDs
    """
    
    def __init__(self, **kwargs):
        # Ensure queryset is set if not provided
        if 'queryset' not in kwargs:
            kwargs['queryset'] = ResellerGroup.objects.filter(is_active=True)
        super().__init__(**kwargs)
    
    def get_value(self, dictionary):
        """
        Override to handle JSON string arrays from FormData.
        This is called before to_internal_value.
        """
        # Get the raw value from the request data
        value = dictionary.get(self.field_name, serializers.empty)
        
        # If it's a string, try to parse as JSON (for FormData)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return serializers.empty
            try:
                parsed = json.loads(value)
                # If it's an array, return it
                if isinstance(parsed, list):
                    return parsed
                # If it's a single value, wrap in list
                return [parsed]
            except (json.JSONDecodeError, TypeError):
                # Not JSON, treat as a single value
                return [value]
        
        return value
    
    def to_internal_value(self, data):
        """Convert string IDs to integers before processing."""
        # Handle None or empty values
        if data is None:
            return None
        
        # If it's already a ResellerGroup instance, return it
        if isinstance(data, ResellerGroup):
            return data
        
        # If it's already an integer, pass it to parent
        if isinstance(data, int):
            return super().to_internal_value(data)
        
        # If it's a string, convert to int
        if isinstance(data, str):
            data = data.strip()
            if not data:  # Skip empty strings
                return None
            try:
                data = int(data)
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    f"ID grup reseller tidak valid: '{data}'. Harus berupa angka."
                )
            return super().to_internal_value(data)
        
        # For any other type, raise an error
        raise serializers.ValidationError(
            f"Format grup reseller tidak valid: {data}. Harus berupa ID (angka)."
        )


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
    """Serializer for seat slots within a tour date with passenger details."""
    
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    booking_id = serializers.IntegerField(source="booking.id", read_only=True, allow_null=True)
    passport_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SeatSlot
        fields = [
            "id",
            "seat_number",
            "status",
            "status_display",
            "booking_id",
            "passenger_name",
            "passport",
            "passport_url",
            "visa_required",
            "special_requests",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status_display", "booking_id", "passport_url", "created_at", "updated_at"]
    
    def get_passport_url(self, obj):
        """Return absolute URL for passport image if exists."""
        if obj.passport:
            request = self.context.get("request")
            return build_absolute_image_url(obj.passport.url, request)
        return None


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
            "has_shopping_stop",
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
        """Validate total seats is at least 1 and not less than booked seats."""
        if value is not None and value < 1:
            raise serializers.ValidationError("Total kursi harus minimal 1.")
        
        # If updating, check that new total_seats is not less than booked seats
        if self.instance and value is not None:
            booked_seats_count = self.instance.seat_slots.filter(status=SeatSlotStatus.BOOKED).count()
            if value < booked_seats_count:
                raise serializers.ValidationError(
                    f"Total kursi tidak boleh kurang dari jumlah kursi yang sudah dibooking. "
                    f"Saat ini ada {booked_seats_count} kursi yang sudah dibooking."
                )
        
        return value
    
    def validate(self, attrs):
        """Validate that the combination of package, departure_date, and has_shopping_stop is unique."""
        from travel.models import TourDate
        
        # Get package from instance if updating, or from attrs if creating
        package = attrs.get('package') or (self.instance.package if self.instance else None)
        departure_date = attrs.get('departure_date')
        has_shopping_stop = attrs.get('has_shopping_stop', False)
        
        if package and departure_date:
            # Check if a TourDate with this combination already exists
            queryset = TourDate.objects.filter(
                package=package,
                departure_date=departure_date,
                has_shopping_stop=has_shopping_stop
            )
            
            # Exclude current instance if updating
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                variant_text = "dengan shopping stop" if has_shopping_stop else "tanpa shopping stop"
                raise serializers.ValidationError(
                    f"Tanggal keberangkatan {variant_text} untuk paket ini sudah ada. "
                    f"Silakan gunakan tanggal yang berbeda atau ubah opsi shopping stop."
                )
        
        return attrs
    
    def update(self, instance, validated_data):
        """
        Update tour date and regenerate seats if total_seats changed.
        When total_seats is updated:
        - Delete all seats that don't have status BOOKED (preserve booked seats)
        - Regenerate seats based on new total_seats count
        """
        total_seats_changed = 'total_seats' in validated_data and validated_data['total_seats'] != instance.total_seats
        
        # Update the instance
        instance = super().update(instance, validated_data)
        
        # If total_seats changed, regenerate seats
        if total_seats_changed:
            # Delete all seats that are not booked (preserve booked seats)
            instance.seat_slots.exclude(status=SeatSlotStatus.BOOKED).delete()
            
            # Regenerate seats based on new total_seats
            # Count existing booked seats
            booked_seats_count = instance.seat_slots.filter(status=SeatSlotStatus.BOOKED).count()
            
            # Generate new seats to match total_seats
            seats_needed = instance.total_seats - booked_seats_count
            
            if seats_needed > 0:
                # Get existing seat numbers to avoid duplicates
                existing_slots = set(
                    instance.seat_slots.values_list('seat_number', flat=True)
                )
                
                # Convert existing slots to integers for comparison
                existing_nums = set()
                for slot in existing_slots:
                    try:
                        existing_nums.add(int(slot))
                    except (ValueError, TypeError):
                        pass
                
                # Generate numeric seat numbers
                slots_to_create = []
                slot_num = 1
                while len(slots_to_create) < seats_needed:
                    # Find next available seat number
                    while slot_num in existing_nums:
                        slot_num += 1
                    
                    slots_to_create.append(
                        SeatSlot(
                            tour_date=instance,
                            seat_number=str(slot_num),
                            status=SeatSlotStatus.AVAILABLE,
                        )
                    )
                    existing_nums.add(slot_num)
                    slot_num += 1
                
                if slots_to_create:
                    SeatSlot.objects.bulk_create(slots_to_create, batch_size=100)
        
        return instance
    
    def get_seat_slots(self, obj):
        """Return seat slots ordered by seat number."""
        # Get seat slots, ordered by seat number (natural sort)
        # Use prefetch_related if available to avoid N+1 queries
        if hasattr(obj, '_prefetched_objects_cache') and 'seat_slots' in obj._prefetched_objects_cache:
            slots = obj._prefetched_objects_cache['seat_slots']
        else:
            slots = obj.seat_slots.all()
        
        # Show all seats with their status for all authenticated users
        # This allows resellers to see which seats are available vs booked
        # Unauthenticated users only see available seats
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            # Unauthenticated users: only show available seats
            slots = [slot for slot in slots if slot.status == SeatSlotStatus.AVAILABLE]
        
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
    reseller_groups = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True
    )
    
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
            "is_flexible",
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
            "is_flexible",
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
        """Return available tour dates (only future dates with available seats or configured seats)."""
        from django.utils import timezone
        
        # Note: seat_slots are already prefetched in the view with booking relationship
        # Don't prefetch again here to avoid "lookup was already seen" error
        today = timezone.now().date()
        future_dates = obj.dates.filter(
            departure_date__gte=today
        ).order_by("departure_date")[:20]  # Fetch more to account for filtering
        
        # Show ALL dates (including fully booked) so the UI can display them with appropriate styling
        dates_to_show = []
        for date in future_dates:
            # Show all dates with total_seats > 0 (regardless of availability)
            if date.total_seats > 0:
                dates_to_show.append(date)
            if len(dates_to_show) >= 10:
                break
        
        return TourDateSerializer(dates_to_show, many=True, context=self.context).data
    
    def get_reseller_commission(self, obj):
        """
        Return reseller commission amount if user has reseller profile.
        Supports dual roles - suppliers with reseller profiles can see commission.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        request = self.context.get("request")
        if request:
            logger.debug(f"[Commission Debug] request.user={request.user}, is_authenticated={request.user.is_authenticated}, is_reseller={getattr(request.user, 'is_reseller', 'N/A')}")
            if hasattr(request.user, 'role'):
                logger.debug(f"[Commission Debug] user.role={request.user.role}")
        
        if request and request.user.is_authenticated and request.user.is_reseller:
            logger.debug(f"[Commission Debug] User is authenticated reseller, attempting to get commission")
            # Use prefetched reseller_profile if available to avoid N+1 query
            if hasattr(request.user, 'reseller_profile'):
                logger.debug(f"[Commission Debug] Using prefetched reseller_profile")
                reseller_profile = request.user.reseller_profile
            else:
                logger.debug(f"[Commission Debug] Fetching reseller_profile from DB")
                try:
                    reseller_profile = ResellerProfile.objects.select_related('user').get(user=request.user)
                except ResellerProfile.DoesNotExist:
                    logger.warning(f"[Commission Debug] ResellerProfile.DoesNotExist for user {request.user}")
                    return None
            commission = obj.get_reseller_commission(reseller_profile)
            logger.debug(f"[Commission Debug] commission={commission}")
            return commission
        logger.debug(f"[Commission Debug] User not authenticated reseller, returning None")
        return None


class TourPackageCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating tour packages (excludes nested relations).
    
    Suppliers can now modify reseller_groups to control which reseller groups can view and book their tours.
    If reseller_groups is empty, the tour is visible to all resellers.
    """
    
    supplier = serializers.PrimaryKeyRelatedField(read_only=True)
    reseller_groups = ResellerGroupListField(
        many=True,
        required=False,
        allow_empty=True,
        queryset=ResellerGroup.objects.filter(is_active=True),
        # Suppliers can now modify reseller groups
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
            "is_flexible",
            "reseller_groups",
            "commission",
        ]
        read_only_fields = ["id", "supplier", "slug"]
    
    def validate_reseller_groups(self, value):
        """Additional validation for reseller groups (conversion handled by ResellerGroupField)."""
        # The custom field handles string-to-int conversion, so by this point
        # value should be a list of ResellerGroup instances or integers
        
        # Filter out None values (from empty strings)
        if value is None:
            return []
        
        if isinstance(value, list):
            filtered = [item for item in value if item is not None]
            # If all items were filtered out, return empty list
            return filtered
        
        return value
    
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
        
        # Handle reseller_groups ManyToMany field
        reseller_groups = validated_data.pop("reseller_groups", None)
        
        # Create the instance first
        instance = super().create(validated_data)
        
        # Then set the reseller_groups if provided
        if reseller_groups is not None:
            instance.reseller_groups.set(reseller_groups)
        
        return instance
    
    def update(self, instance, validated_data):
        """Update tour package, including reseller_groups."""
        # Handle reseller_groups ManyToMany field separately
        reseller_groups = validated_data.pop("reseller_groups", None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update reseller_groups if provided (even if empty list to clear groups)
        if reseller_groups is not None:
            instance.reseller_groups.set(reseller_groups)
        
        return instance


class AdminTourPackageSerializer(serializers.ModelSerializer):
    """Serializer for admin to create/update tour packages with commission fields."""
    
    supplier = serializers.PrimaryKeyRelatedField(
        queryset=SupplierProfile.objects.all(),
        required=True
    )
    reseller_groups = ResellerGroupListField(
        many=True,
        queryset=ResellerGroup.objects.filter(is_active=True),
        required=False,
    )
    reseller_groups_detail = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True)
    images = TourImageSerializer(many=True, read_only=True)
    dates = TourDateSerializer(many=True, read_only=True)
    duration_display = serializers.CharField(read_only=True)
    group_size_display = serializers.CharField(read_only=True)
    
    def get_reseller_groups_detail(self, obj):
        """Return detailed information about reseller groups."""
        groups = obj.reseller_groups.filter(is_active=True)
        return [
            {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "reseller_count": group.resellers.count(),
            }
            for group in groups
        ]
    
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
            "is_flexible",
            "reseller_groups",
            "reseller_groups_detail",
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
            "reseller_groups_detail",
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
    
    def update(self, instance, validated_data):
        """Update tour package, handling reseller_groups for partial updates."""
        # For ManyToMany fields, only update if explicitly provided in the request
        reseller_groups = validated_data.pop("reseller_groups", None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Only update reseller_groups if it was provided in the request
        if reseller_groups is not None:
            instance.reseller_groups.set(reseller_groups)
        # If reseller_groups is not in validated_data, it means it wasn't in the request
        # so we leave it unchanged (don't call .set())
        
        return instance


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
    reseller_email = serializers.EmailField(source="reseller.user.email", read_only=True)
    reseller_phone = serializers.CharField(source="reseller.contact_phone", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_email = serializers.EmailField(source="customer.user.email", read_only=True)
    customer_phone = serializers.CharField(source="customer.contact_phone", read_only=True)
    booked_by_type = serializers.SerializerMethodField()
    booked_by_name = serializers.SerializerMethodField()
    booked_by_email = serializers.SerializerMethodField()
    booked_by_phone = serializers.SerializerMethodField()
    tour_package_name = serializers.CharField(source="tour_date.package.name", read_only=True)
    supplier_name = serializers.CharField(source="tour_date.package.supplier.company_name", read_only=True)
    departure_date = serializers.DateField(source="tour_date.departure_date", read_only=True)
    seats_booked = serializers.IntegerField(read_only=True)
    total_amount = serializers.IntegerField(read_only=True)
    payment_status = serializers.SerializerMethodField()
    
    def get_booked_by_type(self, obj):
        """Get the type of user who made the booking (RESELLER or CUSTOMER)."""
        if obj.reseller:
            return "RESELLER"
        elif obj.customer:
            return "CUSTOMER"
        return None
    
    def get_booked_by_name(self, obj):
        """Get name of user who made the booking."""
        if obj.reseller:
            return obj.reseller.full_name
        elif obj.customer:
            return obj.customer.full_name
        return None
    
    def get_booked_by_email(self, obj):
        """Get email of user who made the booking."""
        if obj.reseller:
            return obj.reseller.user.email
        elif obj.customer:
            return obj.customer.user.email
        return None
    
    def get_booked_by_phone(self, obj):
        """Get phone of user who made the booking."""
        if obj.reseller:
            return obj.reseller.contact_phone
        elif obj.customer:
            return obj.customer.contact_phone
        return None
    
    def get_payment_status(self, obj):
        """Get status of the latest payment (for backward compatibility)."""
        latest_payment = obj.payments.order_by('-created_at').first()
        return latest_payment.status if latest_payment else None
    
    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_number",
            "reseller",
            "reseller_name",
            "reseller_email",
            "reseller_phone",
            "customer",
            "customer_name",
            "customer_email",
            "customer_phone",
            "booked_by_type",
            "booked_by_name",
            "booked_by_email",
            "booked_by_phone",
            "tour_date",
            "tour_package_name",
            "supplier_name",
            "departure_date",
            "status",
            "seats_booked",
            "platform_fee",
            "total_amount",
            "payment_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "booking_number", "created_at", "updated_at", "seats_booked", "total_amount", "payment_status"]


class BookingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating booking status (admin only)."""
    
    class Meta:
        model = Booking
        fields = ["status", "notes"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SeatSlotCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating seat slots with passenger details during booking.
    
    Note: seat_number is optional. If not provided or if the requested seat is unavailable,
    the backend will auto-assign an available seat.
    """
    
    seat_number = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = SeatSlot
        fields = [
            "seat_number",
            "passenger_name",
            "passport",
            "visa_required",
            "special_requests",
        ]


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bookings with seat slots and passenger details.
    
    For flexible packages (is_flexible=True), accepts package_id and departure_date
    instead of tour_date, and automatically creates/get TourDate.
    """
    
    # Make tour_date optional since flexible packages don't provide it
    tour_date = serializers.PrimaryKeyRelatedField(
        queryset=TourDate.objects.all(),
        required=False,
        allow_null=True
    )
    seat_slots = SeatSlotCreateSerializer(many=True, required=True)
    # Optional fields for flexible packages
    package_id = serializers.IntegerField(required=False, write_only=True)
    departure_date = serializers.DateField(required=False, write_only=True)
    
    def validate_departure_date(self, value):
        """Validate departure date is in the future and not too far ahead (for flexible packages)."""
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
    
    class Meta:
        model = Booking
        fields = [
            "tour_date",
            "package_id",
            "departure_date",
            "platform_fee",
            "total_amount",
            "notes",
            "seat_slots",
        ]
    
    def to_internal_value(self, data):
        """
        Override to handle multipart/form-data with nested files.
        If seat_slots comes as JSON string (for FormData with files),
        parse it and attach passport files from separate fields.
        """
        import json
        from django.http import QueryDict
        
        # Check if seat_slots is a string (from FormData)
        seat_slots_data = data.get('seat_slots')
        if isinstance(seat_slots_data, str):
            try:
                # Parse JSON string
                parsed_slots = json.loads(seat_slots_data)
                
                # Attach passport files from separate form fields
                # Frontend sends: passport_0, passport_1, etc.
                for i, slot in enumerate(parsed_slots):
                    passport_key = f'passport_{i}'
                    if passport_key in data:
                        slot['passport'] = data[passport_key]
                
                # Create new dict with parsed seat_slots
                # Don't use data.copy() as it can't pickle file objects
                if isinstance(data, QueryDict):
                    # Convert QueryDict to regular dict, excluding passport_X fields
                    new_data = {}
                    for key in data.keys():
                        if not key.startswith('passport_'):
                            new_data[key] = data[key]
                    new_data['seat_slots'] = parsed_slots
                    data = new_data
                else:
                    # Regular dict
                    new_data = {k: v for k, v in data.items() if not k.startswith('passport_')}
                    new_data['seat_slots'] = parsed_slots
                    data = new_data
                    
            except (json.JSONDecodeError, TypeError) as e:
                raise serializers.ValidationError({
                    'seat_slots': f'Format seat_slots tidak valid: {str(e)}'
                })
        
        return super().to_internal_value(data)
    
    def validate_seat_slots(self, value):
        """Validate that at least one seat slot is provided."""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Minimal satu kursi harus dipilih.")
        
        # If seat_number is not provided or is empty, we'll auto-assign in create()
        # So we allow seat_number to be optional here
        for slot in value:
            if 'seat_number' not in slot or not slot.get('seat_number'):
                # Will auto-assign in create() method
                pass
        
        return value
    
    def validate(self, attrs):
        """Validate booking data and seat slots."""
        tour_date = attrs.get('tour_date')
        package_id = attrs.get('package_id')
        departure_date = attrs.get('departure_date')
        seat_slots = attrs.get('seat_slots', [])
        
        # Validate that either tour_date (regular) or package_id + departure_date (flexible) is provided
        if not tour_date and (not package_id or not departure_date):
            raise serializers.ValidationError({
                '__all__': 'Either tour_date (for regular packages) or package_id + departure_date (for flexible packages) must be provided.'
            })
        
        if tour_date and (package_id or departure_date):
            raise serializers.ValidationError({
                '__all__': 'Cannot specify both tour_date and package_id/departure_date. Use tour_date for regular packages, or package_id + departure_date for flexible packages.'
            })
        
        # For flexible packages: validate package exists and is flexible
        if package_id and departure_date:
            try:
                from .models import TourPackage
                tour_package = TourPackage.objects.get(pk=package_id, is_active=True)
                if not tour_package.is_flexible:
                    raise serializers.ValidationError({
                        'package_id': 'This package is not flexible. Please use tour_date instead.'
                    })
                # Store package object and departure_date for use in create()
                attrs['_tour_package'] = tour_package
                attrs['_departure_date'] = departure_date
            except TourPackage.DoesNotExist:
                raise serializers.ValidationError({
                    'package_id': 'Tour package not found or not active.'
                })
        
        # For regular packages, validate seat availability
        if tour_date and seat_slots:
            # Check if we have enough available seats
            available_count = tour_date.seat_slots.filter(status=SeatSlotStatus.AVAILABLE).count()
            if available_count < len(seat_slots):
                raise serializers.ValidationError({
                    'seat_slots': f'Hanya {available_count} kursi tersedia, tetapi {len(seat_slots)} kursi diminta.'
                })
            
            # If seat numbers are provided, validate they're available
            # If not provided, we'll auto-assign in create() method
            requested_seats = {slot.get('seat_number') for slot in seat_slots if slot.get('seat_number')}
            
            if requested_seats:
                # Get available seat numbers for this tour date
                available_seats = set(
                    tour_date.seat_slots.filter(status=SeatSlotStatus.AVAILABLE)
                    .values_list('seat_number', flat=True)
                )
                
                # Check all requested seats are available
                unavailable_seats = requested_seats - available_seats
                
                if unavailable_seats:
                    # Some seats unavailable, but we'll auto-assign in create() if needed
                    # Just log a warning, don't fail validation
                    pass
            
            # Check for duplicate seat numbers (only if seat numbers are provided)
            if requested_seats and len(requested_seats) != len([s for s in seat_slots if s.get('seat_number')]):
                raise serializers.ValidationError({
                    'seat_slots': 'Nomor kursi duplikat tidak diperbolehkan.'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create booking and assign seat slots with passenger details.
        
        For flexible packages, automatically creates/get TourDate if it doesn't exist.
        """
        from django.db import transaction
        from django.utils import timezone
        from .models import TourPackage, TourDate, SeatSlotStatus
        
        seat_slots_data = validated_data.pop('seat_slots')
        
        # Handle flexible packages: get or create TourDate
        tour_package = validated_data.pop('_tour_package', None)
        departure_date = validated_data.pop('_departure_date', None)
        
        # Remove fields that are not part of the Booking model
        validated_data.pop('package_id', None)
        validated_data.pop('departure_date', None)
        
        # Get number of passengers early (needed for flexible package seat creation)
        num_passengers = len(seat_slots_data)
        
        if tour_package and departure_date:
            # Flexible package: get or create TourDate
            # Use get_or_create with transaction to handle concurrent bookings
            with transaction.atomic():
                tour_date, created = TourDate.objects.get_or_create(
                    package=tour_package,
                    departure_date=departure_date,
                    has_shopping_stop=False,  # Default for flexible packages
                    defaults={
                        'price': tour_package.base_price,
                        'total_seats': num_passengers,  # Create only the number of seats needed for this booking
                        'is_high_season': False,
                    }
                )
                # If TourDate was just created, it will auto-generate seat slots via save() signal
                # If it already existed, check if we need to add more seats
                if not created:
                    # TourDate already exists - check if we have enough seats
                    existing_seats_count = tour_date.seat_slots.count()
                    if existing_seats_count < num_passengers:
                        # Need to add more seats to accommodate this booking
                        from .models import SeatSlot, SeatSlotStatus
                        seats_to_add = num_passengers - existing_seats_count
                        new_seat_slots = []
                        for i in range(seats_to_add):
                            new_seat_slots.append(
                                SeatSlot(
                                    tour_date=tour_date,
                                    seat_number=str(existing_seats_count + i + 1),
                                    status=SeatSlotStatus.AVAILABLE
                                )
                            )
                        SeatSlot.objects.bulk_create(new_seat_slots)
                        # Update total_seats to reflect the new count
                        tour_date.total_seats = tour_date.seat_slots.count()
                        tour_date.save(update_fields=['total_seats'])
                validated_data['tour_date'] = tour_date
        else:
            # Regular package: use provided tour_date
            tour_date = validated_data.get('tour_date')
            if not tour_date:
                raise ValidationError('tour_date is required for regular packages')
        
        tour_date = validated_data['tour_date']
        
        with transaction.atomic():
            # Use select_for_update to prevent race conditions
            # Get available seats for this tour date
            available_seat_slots = list(
                tour_date.seat_slots.select_for_update().filter(
                    status=SeatSlotStatus.AVAILABLE
                ).order_by('seat_number')[:num_passengers]
            )
            
            # Check if we have enough available seats
            if len(available_seat_slots) < num_passengers:
                raise ValidationError({
                    'seat_slots': f'Hanya {len(available_seat_slots)} kursi tersedia, tetapi {num_passengers} kursi diminta.'
                })
            
            # Extract seat numbers from request (if provided)
            requested_seat_numbers = [slot.get('seat_number') for slot in seat_slots_data if slot.get('seat_number')]
            
            # If specific seat numbers are provided, try to use them
            if requested_seat_numbers and len(requested_seat_numbers) == num_passengers:
                # Try to find seats with the requested numbers
                requested_seats = list(
                    tour_date.seat_slots.select_for_update().filter(
                        seat_number__in=requested_seat_numbers,
                        status=SeatSlotStatus.AVAILABLE
                    )
                )
                
                # Check if all requested seats are available
                available_requested_numbers = {slot.seat_number for slot in requested_seats}
                requested_set = set(requested_seat_numbers)
                unavailable_seats = requested_set - available_requested_numbers
                
                if unavailable_seats:
                    # Some requested seats are not available, auto-assign instead
                    seat_slots_to_use = available_seat_slots[:num_passengers]
                else:
                    # All requested seats are available, use them
                    seat_slots_to_use = requested_seats
            else:
                # No specific seat numbers provided or incomplete, auto-assign available seats
                seat_slots_to_use = available_seat_slots[:num_passengers]
            
            # Check for duplicates
            if len(seat_slots_to_use) != num_passengers:
                raise ValidationError({
                    'seat_slots': f'Tidak dapat menemukan {num_passengers} kursi yang tersedia.'
                })
            
            # Create booking
            booking = Booking.objects.create(**validated_data)
            
            # Assign seat slots and update passenger details
            # IMPORTANT: Set seat status to BOOKED immediately when booking is created
            # (even if booking status is PENDING). Seats will only be available again
            # when booking is cancelled.
            for i, slot_data in enumerate(seat_slots_data):
                seat_slot = seat_slots_to_use[i]
                
                # Update seat slot with passenger details and assign to booking
                # Convert empty strings to None for optional fields
                for key, value in slot_data.items():
                    if key == 'seat_number':
                        # Skip seat_number as we're using auto-assigned seats
                        continue
                    if value == "":
                        value = None
                    setattr(seat_slot, key, value)
                
                # Set seat slot to BOOKED and assign to booking
                # This makes the seat unavailable immediately, regardless of booking status
                seat_slot.booking = booking
                seat_slot.status = SeatSlotStatus.BOOKED
                seat_slot.save()
            
            # Create commissions for reseller and upline
            self._create_commissions(booking)
            
            return booking
    
    def _create_commissions(self, booking):
        """
        Create commission records for the booking reseller and their upline hierarchy.
        
        NOTE: Customer bookings do NOT generate commissions. Only reseller bookings earn commission.
        
        Commission calculation logic:
        1. Level 0 (Booking Reseller):
           - First check ResellerTourCommission for this reseller + tour package (reseller-specific override)
           - If not found, use TourPackage.commission (general tour commission)
           - Base commission amount = commission_per_seat * booking.seats_booked (per seat calculation)
           - From the base commission, 100,000 IDR is deducted and distributed to uplines
           - Reseller keeps: base_commission - 100,000 IDR
           - Only create if final commission amount > 0
        
        2. Upline Commission Structure (Deducted from reseller's commission):
           The 100,000 IDR deducted from the reseller is distributed as follows:
           - Level 1 (Direct Upline/Sponsor): 50,000 IDR (50% of 100k)
           - Level 2 (Sponsor's Sponsor): 25,000 IDR (25% of 100k)
           - Level 3 (Level 2's Sponsor): 25,000 IDR (25% of 100k)
           - Level 4 and above: No commission (0 IDR)
           
        Example:
        - A makes booking and earns 150,000 IDR base commission
        - 100,000 IDR is deducted from A's commission
        - A keeps: 150,000 - 100,000 = 50,000 IDR (Level 0)
        - B (recruited A) gets: 50,000 IDR (Level 1)
        - C (recruited B) gets: 25,000 IDR (Level 2)
        - D (recruited C) gets: 25,000 IDR (Level 3)
        - E (recruited D) gets: 0 IDR (Level 4+)
        Total: 50,000 + 50,000 + 25,000 + 25,000 = 150,000 IDR
        """
        from .models import ResellerCommission, ResellerTourCommission
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Skip commission creation for customer bookings
        if not booking.reseller:
            logger.info(
                f"Skipping commission creation for booking {booking.id}: "
                f"Customer booking (no reseller involved)."
            )
            return
        
        booking_reseller = booking.reseller
        tour_package = booking.tour_date.package
        seats_count = booking.seats_booked  # Number of passengers/seats in this booking
        
        # Fixed upline deduction and distribution percentages
        # If base commission is >= 100,000 IDR, use fixed amounts
        # If base commission is < 100,000 IDR, use percentage-based distribution
        UPLINE_TOTAL_DEDUCTION_MAX = 100000  # Maximum deduction from reseller's commission
        UPLINE_PERCENTAGE = 0.5  # 50% of base commission goes to uplines if commission < 100k
        UPLINE_DISTRIBUTION = {
            1: 0.50,  # Level 1: 50% of upline share
            2: 0.25,  # Level 2: 25% of upline share
            3: 0.25,  # Level 3: 25% of upline share
        }
        
        # Level 0: Commission for the reseller who made the booking
        # Commission comes from: ResellerTourCommission (if exists) OR TourPackage.commission (fallback)
        # This is calculated per seat, then upline deduction is subtracted (only if reseller has uplines)
        tour_commission_per_seat = tour_package.get_reseller_commission(booking_reseller)
        
        if tour_commission_per_seat is not None and tour_commission_per_seat > 0:
            # Calculate base commission (before deduction)
            base_commission = tour_commission_per_seat * seats_count
            
            # Check if reseller has any upline (sponsor)
            # If no upline, reseller gets full commission without deduction
            has_upline = booking_reseller.sponsor is not None
            
            if has_upline:
                # Calculate upline deduction:
                # - If base_commission >= 100k, deduct fixed 100k
                # - If base_commission < 100k, deduct 50% of base commission
                if base_commission >= UPLINE_TOTAL_DEDUCTION_MAX:
                    upline_deduction = UPLINE_TOTAL_DEDUCTION_MAX
                else:
                    upline_deduction = int(base_commission * UPLINE_PERCENTAGE)
            else:
                # No upline = no deduction, reseller gets full commission
                upline_deduction = 0
                logger.info(
                    f"Reseller {booking_reseller.id} has no upline (group root), no deduction applied"
                )
            
            # Calculate final commission for reseller
            reseller_final_commission = base_commission - upline_deduction
            
            # Only create commission if reseller gets something (commission must be positive)
            if reseller_final_commission > 0:
                commission = ResellerCommission.objects.create(
                    booking=booking,
                    reseller=booking_reseller,
                    level=0,
                    amount=reseller_final_commission
                )
                # Check if it came from ResellerTourCommission or TourPackage.commission
                has_specific = ResellerTourCommission.objects.filter(
                    reseller=booking_reseller,
                    tour_package=tour_package,
                    is_active=True
                ).exists()
                commission_source = "ResellerTourCommission" if has_specific else "TourPackage.commission"
                logger.info(
                    f"Created commission {commission.id} for reseller {booking_reseller.id} (Level 0): "
                    f"{reseller_final_commission} IDR (base: {base_commission} IDR - upline deduction: {upline_deduction} IDR) "
                    f"from {commission_source} (tour {tour_package.id}, booking {booking.id})"
                )
            else:
                logger.warning(
                    f"No commission created for reseller {booking_reseller.id} on booking {booking.id} "
                    f"because final commission after upline deduction would be {reseller_final_commission} IDR "
                    f"(base: {base_commission} IDR - deduction: {upline_deduction} IDR). "
                    f"Commission must be positive."
                )
                return  # No upline commissions if reseller gets nothing
        else:
            logger.warning(
                f"No commission created for reseller {booking_reseller.id} on booking {booking.id} "
                f"because tour package {tour_package.id} has no commission set "
                f"(neither ResellerTourCommission nor TourPackage.commission)."
            )
            # If reseller doesn't get commission, uplines shouldn't either
            return
        
        # Upline Commission Structure: Traverse up to 3 levels
        # Calculate individual upline amounts based on total deduction
        current_upline = booking_reseller.sponsor
        level = 1
        
        while current_upline and level <= 3:
            # Calculate commission amount for this level based on deduction
            distribution_percentage = UPLINE_DISTRIBUTION.get(level, 0)
            commission_amount = int(upline_deduction * distribution_percentage)
            
            if commission_amount > 0:
                upline_commission_obj = ResellerCommission.objects.create(
                    booking=booking,
                    reseller=current_upline,
                    level=level,
                    amount=commission_amount
                )
                logger.info(
                    f"Created upline commission {upline_commission_obj.id} for upline {current_upline.id} (Level {level}): "
                    f"{commission_amount} IDR ({distribution_percentage*100}% of {upline_deduction} IDR deduction) (booking {booking.id})"
                )
            else:
                logger.info(
                    f"Skipping commission for upline {current_upline.id} at level {level}: "
                    f"no commission for this level"
                )
            
            # Move to next upline level
            current_upline = current_upline.sponsor
            level += 1
        
        if level == 1:
            logger.info(f"No sponsor for reseller {booking_reseller.id}, skipping upline commission")



class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for individual payment records."""
    
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True, allow_null=True)
    
    class Meta:
        model = Payment
        fields = [
            "id",
            "amount",
            "transfer_date",
            "proof_image",
            "status",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]


class BookingSerializer(serializers.ModelSerializer):
    """Detailed serializer for booking detail view."""
    
    reseller_name = serializers.CharField(source="reseller.full_name", read_only=True)
    reseller_email = serializers.EmailField(source="reseller.user.email", read_only=True)
    tour_package_name = serializers.CharField(source="tour_date.package.name", read_only=True)
    tour_package_slug = serializers.SlugField(source="tour_date.package.slug", read_only=True)
    tour_package_id = serializers.IntegerField(source="tour_date.package.id", read_only=True)
    departure_date = serializers.DateField(source="tour_date.departure_date", read_only=True)
    tour_price = serializers.IntegerField(source="tour_date.price", read_only=True)
    visa_price = serializers.IntegerField(source="tour_date.package.visa_price", read_only=True)
    tipping_price = serializers.IntegerField(source="tour_date.package.tipping_price", read_only=True)
    seats_booked = serializers.IntegerField(read_only=True)
    total_amount = serializers.IntegerField(read_only=True)
    subtotal = serializers.IntegerField(read_only=True)
    seat_slots = SeatSlotSerializer(many=True, read_only=True)
    
    # Payment history (list of all payments)
    payments = PaymentSerializer(many=True, read_only=True)
    
    # Backward compatibility: latest payment info (for existing code)
    payment_status = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()
    payment_transfer_date = serializers.SerializerMethodField()
    payment_proof_image = serializers.SerializerMethodField()
    payment_id = serializers.SerializerMethodField()
    
    reseller_commission = serializers.SerializerMethodField()
    
    def get_payment_status(self, obj):
        """Get status of the latest payment (for backward compatibility)."""
        latest_payment = obj.payments.order_by('-created_at').first()
        return latest_payment.status if latest_payment else None
    
    def get_payment_amount(self, obj):
        """Get amount of the latest payment (for backward compatibility)."""
        latest_payment = obj.payments.order_by('-created_at').first()
        return latest_payment.amount if latest_payment else None
    
    def get_payment_transfer_date(self, obj):
        """Get transfer date of the latest payment (for backward compatibility)."""
        latest_payment = obj.payments.order_by('-created_at').first()
        return latest_payment.transfer_date if latest_payment else None
    
    def get_payment_proof_image(self, obj):
        """Get proof image of the latest payment (for backward compatibility)."""
        latest_payment = obj.payments.order_by('-created_at').first()
        return latest_payment.proof_image.url if latest_payment and latest_payment.proof_image else None
    
    def get_payment_id(self, obj):
        """Get ID of the latest payment (for backward compatibility)."""
        latest_payment = obj.payments.order_by('-created_at').first()
        return latest_payment.id if latest_payment else None
    
    def get_reseller_commission(self, obj):
        """Get commission amount for the reseller who made this booking."""
        # Get commission for level 0 (the reseller who made the booking)
        commission = ResellerCommission.objects.filter(
            booking=obj,
            reseller=obj.reseller,
            level=0
        ).first()
        
        if commission:
            return commission.amount
        return None
    
    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_number",
            "reseller",
            "reseller_name",
            "reseller_email",
            "tour_date",
            "tour_package_name",
            "tour_package_slug",
            "tour_package_id",
            "departure_date",
            "tour_price",
            "visa_price",
            "tipping_price",
            "status",
            "seats_booked",
            "platform_fee",
            "subtotal",
            "total_amount",
            "notes",
            "seat_slots",
            "payments",
            "payment_status",
            "payment_amount",
            "payment_transfer_date",
            "payment_proof_image",
            "payment_id",
            "reseller_commission",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "booking_number",
            "created_at",
            "updated_at",
            "seats_booked",
            "total_amount",
            "subtotal",
            "payment_status",
            "payment_amount",
        ]


# ==================== COMMISSION SERIALIZERS ====================

class ResellerCommissionSerializer(serializers.ModelSerializer):
    """Serializer for reseller commission history."""
    
    booking_id = serializers.IntegerField(source="booking.id", read_only=True)
    booking_number = serializers.CharField(source="booking.booking_number", read_only=True)
    booking_status = serializers.CharField(source="booking.status", read_only=True)
    tour_package_name = serializers.CharField(source="booking.tour_date.package.name", read_only=True)
    tour_package_slug = serializers.SlugField(source="booking.tour_date.package.slug", read_only=True)
    departure_date = serializers.DateField(source="booking.tour_date.departure_date", read_only=True)
    seats_booked = serializers.SerializerMethodField()
    booking_total_amount = serializers.IntegerField(source="booking.total_amount", read_only=True)
    level_display = serializers.SerializerMethodField()
    
    def get_seats_booked(self, obj):
        """Get seats booked count from prefetched seat_slots or by querying."""
        booking = obj.booking
        if hasattr(booking, '_prefetched_objects_cache') and 'seat_slots' in booking._prefetched_objects_cache:
            return len(booking._prefetched_objects_cache['seat_slots'])
        return booking.seat_slots.count()
    
    def get_level_display(self, obj):
        """Get human-readable level description."""
        if obj.level == 0:
            return "Booking Saya"
        elif obj.level == 1:
            return "Dari Downline Langsung"
        else:
            return f"Dari Downline (Level {obj.level})"
    
    class Meta:
        model = ResellerCommission
        fields = [
            "id",
            "booking_id",
            "booking_number",
            "booking_status",
            "tour_package_name",
            "tour_package_slug",
            "departure_date",
            "seats_booked",
            "booking_total_amount",
            "level",
            "level_display",
            "amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "booking_id",
            "booking_status",
            "tour_package_name",
            "tour_package_slug",
            "departure_date",
            "seats_booked",
            "booking_total_amount",
            "level",
            "level_display",
            "amount",
            "created_at",
            "updated_at",
        ]


# ==================== PAYMENT SERIALIZERS ====================

class PaymentDetailSerializer(serializers.ModelSerializer):
    """Serializer for payment records with booking details (used in admin views)."""
    
    booking_id = serializers.IntegerField(source="booking.id", read_only=True)
    booking_total_amount = serializers.IntegerField(source="booking.total_amount", read_only=True)
    reseller_name = serializers.CharField(source="booking.reseller.full_name", read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            "id",
            "booking",
            "booking_id",
            "reseller_name",
            "booking_total_amount",
            "amount",
            "transfer_date",
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
            "reseller_name",
            "booking_total_amount",
            "status",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]


class PaymentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for suppliers to update payment details (amount, transfer_date, proof_image, status)."""
    
    class Meta:
        model = Payment
        fields = [
            "amount",
            "transfer_date",
            "proof_image",
            "status",
        ]
        read_only_fields = [
            "id",
            "booking",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]


class ResellerPaymentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for resellers to upload/update payment details (amount, transfer_date, proof_image).
    
    Resellers can only upload payment information, but cannot change the payment status.
    Status must be set by suppliers or admins.
    """
    
    class Meta:
        model = Payment
        fields = [
            "amount",
            "transfer_date",
            "proof_image",
        ]
        read_only_fields = [
            "id",
            "booking",
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

class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal requests (reseller view)."""
    
    reseller_name = serializers.CharField(source="reseller.full_name", read_only=True)
    reseller_email = serializers.EmailField(source="reseller.user.email", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.email", read_only=True, allow_null=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    
    class Meta:
        model = WithdrawalRequest
        fields = [
            "id",
            "reseller",
            "reseller_name",
            "reseller_email",
            "amount",
            "status",
            "status_display",
            "notes",
            "admin_notes",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reseller",
            "status",
            "admin_notes",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
    
    def validate_amount(self, value):
        """Validate withdrawal amount."""
        if value < 1:
            raise serializers.ValidationError("Jumlah penarikan harus minimal 1 IDR.")
        return value


class WithdrawalRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating withdrawal requests."""
    
    class Meta:
        model = WithdrawalRequest
        fields = [
            "amount",
            "notes",
        ]
    
    def validate_amount(self, value):
        """Validate withdrawal amount doesn't exceed available balance."""
        if value < 1:
            raise serializers.ValidationError("Jumlah penarikan harus minimal 1 IDR.")
        
        # Get reseller from context (set in view)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                from account.models import ResellerProfile
                reseller_profile = ResellerProfile.objects.get(user=request.user)
                available_balance = reseller_profile.get_available_commission_balance()
                
                if value > available_balance:
                    raise serializers.ValidationError(
                        f"Jumlah penarikan ({value:,} IDR) melebihi saldo komisi yang tersedia ({available_balance:,} IDR)."
                    )
            except ResellerProfile.DoesNotExist:
                pass
        
        return value


class WithdrawalRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin to update withdrawal request status."""
    
    class Meta:
        model = WithdrawalRequest
        fields = [
            "status",
            "admin_notes",
        ]
    
    def validate_status(self, value):
        """Validate status transitions."""
        instance = self.instance
        if instance:
            # Can only approve/reject pending requests
            if instance.status != WithdrawalRequestStatus.PENDING:
                if value in [WithdrawalRequestStatus.APPROVED, WithdrawalRequestStatus.REJECTED]:
                    raise serializers.ValidationError(
                        f"Hanya permintaan dengan status PENDING yang dapat diubah. Status saat ini: {instance.status}."
                    )
            # Can only complete approved requests
            if value == WithdrawalRequestStatus.COMPLETED:
                if instance.status != WithdrawalRequestStatus.APPROVED:
                    raise serializers.ValidationError(
                        f"Hanya permintaan dengan status APPROVED yang dapat diselesaikan. Status saat ini: {instance.status}."
                    )
        return value


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
