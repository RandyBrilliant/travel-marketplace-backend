from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from django.db import transaction, models
from django.db.utils import IntegrityError
from django.utils.text import slugify
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from account.models import UserRole, SupplierProfile, ResellerProfile
from .models import TourPackage, TourDate, TourImage, ItineraryItem, ResellerTourCommission, ResellerGroup, Booking, BookingStatus, SeatSlotStatus, PaymentStatus
from .serializers import (
    TourPackageSerializer,
    TourPackageListSerializer,
    TourPackageCreateUpdateSerializer,
    AdminTourPackageSerializer,
    TourDateSerializer,
    TourImageSerializer,
    TourImageCreateUpdateSerializer,
    ItineraryItemSerializer,
    ResellerTourCommissionSerializer,
    ResellerGroupSerializer,
    BookingSerializer,
    BookingListSerializer,
    PublicTourPackageDetailSerializer,
)


class IsSupplier(permissions.BasePermission):
    """Permission check for supplier role."""
    
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.SUPPLIER
        )


class IsReseller(permissions.BasePermission):
    """Permission check for reseller role."""
    
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.RESELLER
        )


class SupplierTourPackageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage their tour packages.
    
    Suppliers can:
    - List their own tour packages
    - Create new tour packages
    - Retrieve, update, and delete their own tour packages
    """
    
    permission_classes = [IsSupplier]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "tour_type", "is_active", "is_featured"]
    search_fields = ["name", "country", "summary"]
    ordering_fields = ["created_at", "updated_at", "name", "base_price"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """
        Return only tour packages belonging to the authenticated supplier.
        
        Optimized with select_related and prefetch_related to avoid N+1 queries.
        """
        if not self.request.user.is_authenticated:
            return TourPackage.objects.none()
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return TourPackage.objects.filter(
                supplier=supplier_profile
            ).select_related(
                "supplier", "supplier__user"
            ).prefetch_related(
                "reseller_groups", "images", "itinerary_items", "dates"
            )
        except SupplierProfile.DoesNotExist:
            return TourPackage.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail."""
        if self.action == "list":
            return TourPackageListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return TourPackageCreateUpdateSerializer
        return TourPackageSerializer
    
    def perform_create(self, serializer):
        """Set the supplier when creating a tour package."""
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            try:
                serializer.save(supplier=supplier_profile)
            except IntegrityError as e:
                # Provide user-friendly error messages for integrity errors
                error_msg = str(e)
                if "slug" in error_msg.lower():
                    raise ValidationError(
                        {
                            "slug": "A tour package with this name already exists. Please choose a different name.",
                            "detail": "Unable to create tour package. Please ensure the tour name is unique."
                        }
                    )
                elif "nights_not_greater_than_days" in error_msg.lower():
                    raise ValidationError(
                        {
                            "nights": "Number of nights cannot be greater than number of days.",
                            "detail": "Please ensure the number of nights is less than or equal to the number of days."
                        }
                    )
                else:
                    raise ValidationError(
                        {"detail": "Unable to create tour package. Please check your input and try again."}
                    )
        except SupplierProfile.DoesNotExist:
            raise ValidationError(
                {"detail": "Supplier profile not found. Please complete your profile setup."}
            )
    
    @action(detail=True, methods=["get", "post"], url_path="dates")
    def manage_dates(self, request, pk=None):
        """
        Manage tour dates for a package.
        
        Optimized query to prefetch seat_slots for remaining_seats calculation.
        """
        tour_package = self.get_object()
        
        if request.method == "GET":
            # Prefetch seat_slots to optimize remaining_seats property calculation
            dates = tour_package.dates.prefetch_related("seat_slots").all()
            serializer = TourDateSerializer(dates, many=True, context={"request": request})
            return Response(serializer.data)
        
        elif request.method == "POST":
            serializer = TourDateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save(package=tour_package)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["get", "post"], url_path="images")
    def manage_images(self, request, pk=None):
        """Manage tour images for a package."""
        tour_package = self.get_object()
        
        if request.method == "GET":
            images = tour_package.images.all()
            serializer = TourImageSerializer(images, many=True, context={"request": request})
            return Response(serializer.data)
        
        elif request.method == "POST":
            serializer = TourImageSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save(package=tour_package)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["get", "post"], url_path="itinerary")
    def manage_itinerary(self, request, pk=None):
        """Manage itinerary items for a package."""
        tour_package = self.get_object()
        
        if request.method == "GET":
            items = tour_package.itinerary_items.all()
            serializer = ItineraryItemSerializer(items, many=True)
            return Response(serializer.data)
        
        elif request.method == "POST":
            serializer = ItineraryItemSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(package=tour_package)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class SupplierTourDateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage tour dates.
    Suppliers can only manage dates for their own tour packages.
    """
    
    permission_classes = [IsSupplier]
    serializer_class = TourDateSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["package", "is_high_season"]
    ordering_fields = ["departure_date", "price"]
    ordering = ["departure_date"]
    
    def get_queryset(self):
        """
        Return only tour dates for packages belonging to the authenticated supplier.
        
        Optimized with select_related and prefetch_related to avoid N+1 queries.
        Prefetching seat_slots optimizes remaining_seats property calculation.
        """
        if not self.request.user.is_authenticated:
            return TourDate.objects.none()
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return TourDate.objects.filter(
                package__supplier=supplier_profile
            ).select_related(
                "package", "package__supplier"
            ).prefetch_related(
                "seat_slots"
            )
        except SupplierProfile.DoesNotExist:
            return TourDate.objects.none()
    
    def perform_create(self, serializer):
        """Verify the package belongs to the supplier before creating."""
        package_id = self.request.data.get("package")
        if not package_id:
            raise ValidationError({"package": ["This field is required."]})
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            package = TourPackage.objects.get(pk=package_id, supplier=supplier_profile)
            serializer.save(package=package)
        except TourPackage.DoesNotExist:
            raise ValidationError(
                {"package": ["Tour package not found or you don't have permission to access it."]}
            )


class SupplierTourImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage tour images.
    Suppliers can only manage images for their own tour packages.
    """
    
    permission_classes = [IsSupplier]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["package", "is_primary"]
    ordering_fields = ["order", "created_at"]
    ordering = ["order", "id"]
    
    def get_serializer_class(self):
        """Use different serializers for create/update vs list/detail."""
        if self.action in ["create", "update", "partial_update"]:
            return TourImageCreateUpdateSerializer
        return TourImageSerializer
    
    def get_queryset(self):
        """Return only images for packages belonging to the authenticated supplier."""
        if not self.request.user.is_authenticated:
            return TourImage.objects.none()
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return TourImage.objects.filter(package__supplier=supplier_profile)
        except SupplierProfile.DoesNotExist:
            return TourImage.objects.none()
    
    def perform_create(self, serializer):
        """Verify the package belongs to the supplier before creating."""
        package_id = self.request.data.get("package")
        if not package_id:
            raise ValidationError({"package": ["This field is required."]})
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            package = TourPackage.objects.get(pk=package_id, supplier=supplier_profile)
            serializer.save(package=package)
        except TourPackage.DoesNotExist:
            raise ValidationError(
                {"package": ["Tour package not found or you don't have permission to access it."]}
            )


class SupplierItineraryItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage itinerary items.
    Suppliers can only manage itinerary items for their own tour packages.
    """
    
    permission_classes = [IsSupplier]
    serializer_class = ItineraryItemSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["package"]
    ordering_fields = ["day_number", "id"]
    ordering = ["day_number", "id"]
    
    def get_queryset(self):
        """Return only itinerary items for packages belonging to the authenticated supplier."""
        if not self.request.user.is_authenticated:
            return ItineraryItem.objects.none()
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return ItineraryItem.objects.filter(package__supplier=supplier_profile)
        except SupplierProfile.DoesNotExist:
            return ItineraryItem.objects.none()
    
    def perform_create(self, serializer):
        """Verify the package belongs to the supplier before creating."""
        package_id = self.request.data.get("package")
        if not package_id:
            raise ValidationError({"package": ["This field is required."]})
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            package = TourPackage.objects.get(pk=package_id, supplier=supplier_profile)
            try:
                serializer.save(package=package)
            except IntegrityError as e:
                error_msg = str(e)
                # Handle unique (package, day_number) constraint with a friendly message
                if "itineraryitem_package_id_day_number" in error_msg or "day_number" in error_msg:
                    raise ValidationError(
                        {
                            "day_number": [
                                "Itinerary untuk hari ini sudah ada. Tambahkan aktivitas tambahan di deskripsi hari tersebut."
                            ]
                        }
                    )
                # Fallback generic validation error
                raise ValidationError(
                    {"detail": "Unable to create itinerary item. Please check your input and try again."}
                )
        except TourPackage.DoesNotExist:
            raise ValidationError(
                {"package": ["Tour package not found or you don't have permission to access it."]}
            )


class PublicTourPackageListView(APIView):
    """
    Public endpoint for listing tour packages.
    Can be filtered by supplier and tour_type.
    Accessible to authenticated users (resellers) and public.
    For resellers, only shows tours they have access to based on reseller groups.
    """
    
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request):
        """List tour packages with optional filtering."""
        from .serializers import TourPackageListSerializer
        from django.core.cache import cache
        from hashlib import md5
        
        # Create cache key from query parameters
        cache_key = f'tours_list_{md5(request.GET.urlencode().encode()).hexdigest()}'
        
        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        
        # Optimize queryset with select_related and prefetch_related
        # This prevents N+1 queries when accessing related objects
        queryset = TourPackage.objects.filter(
            is_active=True
        ).select_related(
            "supplier", "supplier__user"
        ).prefetch_related(
            "reseller_groups",
            "reseller_groups__resellers",
            "images",  # used by TourPackageListSerializer.get_main_image_url
        )
        
        # Filter by supplier if provided
        supplier_id = request.query_params.get("supplier")
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filter by tour_type if provided (CONVENTIONAL or MUSLIM)
        tour_type = request.query_params.get("tour_type")
        if tour_type:
            queryset = queryset.filter(tour_type=tour_type)
        
        # Filter by category if provided
        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by reseller groups - only show tours visible to the authenticated reseller
        if request.user.is_authenticated and request.user.role == UserRole.RESELLER:
            try:
                reseller_profile = ResellerProfile.objects.get(user=request.user)
                # Filter tours that are either:
                # 1. Not assigned to any group (visible to all), OR
                # 2. Assigned to a group that includes this reseller
                queryset = queryset.filter(
                    models.Q(reseller_groups__isnull=True) |  # No groups = visible to all
                    models.Q(reseller_groups__resellers=reseller_profile)  # Reseller in group
                ).distinct()
            except ResellerProfile.DoesNotExist:
                # If reseller profile doesn't exist, return empty queryset
                queryset = TourPackage.objects.none()
        
        # Search
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(country__icontains=search) |
                models.Q(summary__icontains=search)
            )
        
        # Filter by month/year (format: YYYY-MM)
        month = request.query_params.get("month")
        if month:
            try:
                from datetime import datetime
                # Parse YYYY-MM format
                year, month_num = map(int, month.split("-"))
                # Get the first and last day of the month
                first_day = datetime(year, month_num, 1).date()
                # Get last day of month
                if month_num == 12:
                    last_day = datetime(year + 1, 1, 1).date()
                else:
                    last_day = datetime(year, month_num + 1, 1).date()
                
                # Filter tours that have dates in this month with available seats
                queryset = queryset.filter(
                    dates__departure_date__gte=first_day,
                    dates__departure_date__lt=last_day,
                    dates__seat_slots__status=SeatSlotStatus.AVAILABLE
                ).distinct()
            except (ValueError, TypeError):
                # Invalid month format, ignore filter
                pass
        
        # Ordering
        ordering = request.query_params.get("ordering", "-is_featured,-created_at")
        if ordering:
            queryset = queryset.order_by(*ordering.split(","))
        
        serializer = TourPackageListSerializer(queryset, many=True, context={"request": request})
        response_data = serializer.data
        
        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, response_data, 300)
        
        return Response(response_data)


class PublicTourPackageDetailView(APIView):
    """
    Public endpoint for retrieving a single tour package detail.
    Accessible to authenticated users (resellers) and public.
    For resellers, checks if they have access based on reseller groups.
    """
    
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request, pk):
        """Get tour package detail by ID."""
        from django.http import Http404
        
        try:
            tour = TourPackage.objects.filter(
                is_active=True
            ).select_related(
                "supplier", "supplier__user"
            ).prefetch_related(
                "reseller_groups", "reseller_groups__resellers",
                "images", "itinerary_items", "dates"
            ).get(pk=pk)
        except TourPackage.DoesNotExist:
            raise Http404("Tour package not found")
        
        # Check if reseller has access to this tour
        if request.user.is_authenticated and request.user.role == UserRole.RESELLER:
            try:
                reseller_profile = ResellerProfile.objects.get(user=request.user)
                # Check if tour is accessible to this reseller
                # Tour is accessible if:
                # 1. Not assigned to any group (visible to all), OR
                # 2. Assigned to a group that includes this reseller
                if tour.reseller_groups.exists():
                    if not tour.reseller_groups.filter(resellers=reseller_profile).exists():
                        raise Http404("Tour package not found")
            except ResellerProfile.DoesNotExist:
                raise Http404("Tour package not found")
        
        serializer = PublicTourPackageDetailSerializer(tour, context={"request": request})
        return Response(serializer.data)


class AdminResellerGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage reseller groups.
    Admin can create groups and assign resellers to them.
    """
    
    permission_classes = [IsAdminUser]
    serializer_class = ResellerGroupSerializer
    queryset = ResellerGroup.objects.all()
    
    def get_queryset(self):
        """Allow filtering by is_active."""
        queryset = ResellerGroup.objects.prefetch_related("resellers", "tour_packages").all()
        
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)


class AdminTourPackageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to view and manage all tour packages.
    Admin can view, edit, and manage commission settings for all tours.
    """
    
    permission_classes = [IsAdminUser]
    queryset = TourPackage.objects.all()
    
    def get_queryset(self):
        """
        Return all tour packages with optimized queries.
        Allow filtering by supplier, category, tour_type, is_active, and search.
        """
        queryset = TourPackage.objects.select_related(
            "supplier",
            "supplier__user",
        ).prefetch_related(
            "reseller_groups",
            "images",
            "itinerary_items",
            "dates",
        ).all()
        
        # Filter by supplier
        supplier_id = self.request.query_params.get("supplier")
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filter by category
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by tour_type
        tour_type = self.request.query_params.get("tour_type")
        if tour_type:
            queryset = queryset.filter(tour_type=tour_type)
        
        # Filter by is_active
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        
        # Filter by is_featured
        is_featured = self.request.query_params.get("is_featured")
        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured.lower() == "true")
        
        # Search by name, city, country, or summary
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(city__icontains=search) |
                models.Q(country__icontains=search) |
                models.Q(summary__icontains=search)
            )
        
        # Ordering
        ordering = self.request.query_params.get("ordering", "-is_featured,-created_at")
        if ordering:
            queryset = queryset.order_by(*ordering.split(","))
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail."""
        if self.action == "list":
            return TourPackageListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            # For admin, use AdminTourPackageSerializer to allow editing commission fields
            return AdminTourPackageSerializer
        return AdminTourPackageSerializer
    
    def perform_create(self, serializer):
        """Admin can create tours and assign to any supplier."""
        # Supplier must be provided in the request data
        supplier_id = self.request.data.get("supplier")
        if not supplier_id:
            raise ValidationError({"supplier": ["This field is required."]})
        
        try:
            supplier = SupplierProfile.objects.get(pk=supplier_id)
            serializer.save(supplier=supplier)
        except SupplierProfile.DoesNotExist:
            raise ValidationError({"supplier": ["Supplier profile not found."]})


class AdminResellerTourCommissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage reseller tour commission settings.
    Admin can set different fixed commission amounts for each reseller per tour package.
    """
    
    permission_classes = [IsAdminUser]
    serializer_class = ResellerTourCommissionSerializer
    queryset = ResellerTourCommission.objects.all()
    
    def get_queryset(self):
        """Allow filtering by reseller and tour_package."""
        queryset = ResellerTourCommission.objects.select_related(
            "reseller", "reseller__user", "tour_package"
        ).all()
        
        reseller_id = self.request.query_params.get("reseller")
        if reseller_id:
            queryset = queryset.filter(reseller_id=reseller_id)
        
        tour_package_id = self.request.query_params.get("tour_package")
        if tour_package_id:
            queryset = queryset.filter(tour_package_id=tour_package_id)
        
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        
        return queryset


class SupplierBookingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for suppliers to view bookings for their own tours.
    Suppliers can only view bookings, not confirm or cancel them.
    """
    
    permission_classes = [IsSupplier]
    queryset = Booking.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "tour_date", "tour_date__package"]
    search_fields = [
        "customer_name", "customer_email", "reseller__full_name",
        "reseller__user__email", "tour_date__package__name",
    ]
    ordering_fields = [
        "created_at", "status", "total_amount", "departure_date",
        "reseller__full_name", "tour_date__package__name",
    ]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """
        Return only bookings for tours owned by the authenticated supplier.
        Allow filtering by status, tour_date, and search.
        """
        if not self.request.user.is_authenticated:
            return Booking.objects.none()
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            # Get bookings for tours owned by this supplier
            queryset = Booking.objects.filter(
                tour_date__package__supplier=supplier_profile
            ).select_related(
                "reseller", "reseller__user", "tour_date", "tour_date__package", "payment"
            ).prefetch_related(
                "seat_slots", "seat_slots__tour_date"
            ).all()
            
            # Apply additional filters
            status = self.request.query_params.get("status")
            if status:
                queryset = queryset.filter(status=status)
            
            tour_date_id = self.request.query_params.get("tour_date")
            if tour_date_id:
                queryset = queryset.filter(tour_date_id=tour_date_id)
            
            tour_package_id = self.request.query_params.get("tour_date__package")
            if tour_package_id:
                queryset = queryset.filter(tour_date__package_id=tour_package_id)
            
            # Search
            search = self.request.query_params.get("search")
            if search:
                queryset = queryset.filter(
                    models.Q(customer_name__icontains=search) |
                    models.Q(customer_email__icontains=search) |
                    models.Q(reseller__full_name__icontains=search) |
                    models.Q(reseller__user__email__icontains=search) |
                    models.Q(tour_date__package__name__icontains=search)
                )
            
            # Ordering
            ordering = self.request.query_params.get("ordering", "-created_at")
            if ordering:
                queryset = queryset.order_by(*ordering.split(","))
            
            return queryset
        except SupplierProfile.DoesNotExist:
            return Booking.objects.none()
    
    def get_serializer_class(self):
        if self.action == "list":
            return BookingListSerializer
        return BookingSerializer
    
    @action(detail=False, methods=["get"], url_path="dashboard-stats")
    def dashboard_stats(self, request):
        """
        Get dashboard statistics for supplier.
        Returns aggregated statistics for the supplier's bookings.
        """
        from django.db.models import Count, Q
        from .models import PaymentStatus
        from django.utils import timezone
        from datetime import timedelta
        
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=request.user)
        except SupplierProfile.DoesNotExist:
            return Response(
                {"detail": "Supplier profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get bookings for tours owned by this supplier
        bookings_queryset = Booking.objects.filter(
            tour_date__package__supplier=supplier_profile
        ).select_related("tour_date", "tour_date__package", "payment").prefetch_related("seat_slots")
        
        # Total Bookings
        total_bookings = bookings_queryset.count()
        
        # Bookings by Status
        pending_bookings = bookings_queryset.filter(status=BookingStatus.PENDING).count()
        confirmed_bookings = bookings_queryset.filter(status=BookingStatus.CONFIRMED).count()
        cancelled_bookings = bookings_queryset.filter(status=BookingStatus.CANCELLED).count()
        
        # Total Revenue (sum of total_amount from confirmed bookings with approved payments)
        # Optimized: Calculate in database using annotations instead of Python loops
        from django.db.models import Sum, F, Count
        
        confirmed_with_approved_payment = bookings_queryset.filter(
            status=BookingStatus.CONFIRMED,
            payment__status=PaymentStatus.APPROVED
        ).annotate(
            seat_count=Count('seat_slots')
        ).annotate(
            booking_total=F('tour_date__price') * F('seat_count') + F('platform_fee')
        )
        
        # Aggregate in database instead of Python
        revenue_result = confirmed_with_approved_payment.aggregate(
            total=Sum('booking_total')
        )
        total_revenue = revenue_result['total'] or 0
        
        # Recent bookings count (last 30 days) for trend calculation
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_bookings = bookings_queryset.filter(created_at__gte=thirty_days_ago).count()
        
        return Response({
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "confirmed_bookings": confirmed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "total_revenue": total_revenue,
            "recent_bookings": recent_bookings,
        })
    
    @action(detail=False, methods=["get"], url_path="revenue-chart")
    def revenue_chart(self, request):
        """
        Get revenue chart data grouped by date for supplier's bookings.
        Returns daily revenue for the specified period.
        """
        from django.db.models.functions import TruncDate
        from django.db.models import Q
        from .models import PaymentStatus
        from django.utils import timezone
        from datetime import timedelta
        from collections import defaultdict
        
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=request.user)
        except SupplierProfile.DoesNotExist:
            return Response(
                {"detail": "Supplier profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get time range parameter (default 90 days)
        time_range = request.query_params.get("range", "90d")
        days = 90
        if time_range == "30d":
            days = 30
        elif time_range == "7d":
            days = 7
        
        # Calculate date range
        end_datetime = timezone.now()
        start_datetime = end_datetime - timedelta(days=days)
        start_date = start_datetime.date()
        end_date = end_datetime.date()
        
        # Create datetime boundaries for filtering (start of start_date, end of end_date)
        from datetime import datetime as dt
        start_bound = timezone.make_aware(dt.combine(start_date, dt.min.time()))
        end_bound = timezone.make_aware(dt.combine(end_date, dt.max.time()))
        
        # Get confirmed bookings with approved payments in the date range for this supplier
        # Optimized: Calculate booking_total in database
        from django.db.models import Sum, F, Count
        
        bookings = Booking.objects.filter(
            tour_date__package__supplier=supplier_profile,
            created_at__gte=start_bound,
            created_at__lte=end_bound,
            status="CONFIRMED",
            payment__status=PaymentStatus.APPROVED
        ).select_related("tour_date", "tour_date__package").annotate(
            seat_count=Count('seat_slots')
        ).annotate(
            booking_total=F('tour_date__price') * F('seat_count') + F('platform_fee')
        )
        
        # Group revenue by date
        revenue_by_date = defaultdict(int)
        for booking in bookings:
            date_str = booking.created_at.date().isoformat()
            revenue_by_date[date_str] += booking.booking_total
        
        # Create list of all dates in range and fill with revenue data
        chart_data = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            chart_data.append({
                "date": date_str,
                "revenue": revenue_by_date.get(date_str, 0),
            })
            current_date += timedelta(days=1)
        
        return Response(chart_data)


class ResellerBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for resellers to view and create their own bookings.
    Resellers can create bookings and view their own bookings.
    """
    
    permission_classes = [IsReseller]
    queryset = Booking.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "tour_date", "tour_date__package"]
    search_fields = [
        "customer_name", "customer_email", "tour_date__package__name",
    ]
    ordering_fields = [
        "created_at", "status", "total_amount", "departure_date",
        "tour_date__package__name",
    ]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """
        Return only bookings belonging to the authenticated reseller.
        Allow filtering by status, tour_date, and search.
        """
        if not self.request.user.is_authenticated:
            return Booking.objects.none()
        
        try:
            reseller_profile = ResellerProfile.objects.get(user=self.request.user)
            # Get bookings created by this reseller
            queryset = Booking.objects.filter(
                reseller=reseller_profile
            ).select_related(
                "reseller", "reseller__user", "tour_date", "tour_date__package", "payment"
            ).prefetch_related(
                "seat_slots", "seat_slots__tour_date"
            ).all()
            
            # Apply additional filters
            status = self.request.query_params.get("status")
            if status:
                queryset = queryset.filter(status=status)
            
            tour_date_id = self.request.query_params.get("tour_date")
            if tour_date_id:
                queryset = queryset.filter(tour_date_id=tour_date_id)
            
            tour_package_id = self.request.query_params.get("tour_date__package")
            if tour_package_id:
                queryset = queryset.filter(tour_date__package_id=tour_package_id)
            
            # Search
            search = self.request.query_params.get("search")
            if search:
                queryset = queryset.filter(
                    models.Q(customer_name__icontains=search) |
                    models.Q(customer_email__icontains=search) |
                    models.Q(tour_date__package__name__icontains=search)
                )
            
            # Ordering
            ordering = self.request.query_params.get("ordering", "-created_at")
            if ordering:
                queryset = queryset.order_by(*ordering.split(","))
            
            return queryset
        except ResellerProfile.DoesNotExist:
            return Booking.objects.none()
    
    def get_serializer_class(self):
        if self.action == "list":
            return BookingListSerializer
        return BookingSerializer
    
    def perform_create(self, serializer):
        """Set the reseller when creating a booking."""
        try:
            reseller_profile = ResellerProfile.objects.get(user=self.request.user)
            serializer.save(reseller=reseller_profile)
        except ResellerProfile.DoesNotExist:
            raise ValidationError(
                {"detail": "Reseller profile not found. Please complete your profile setup."}
            )


class AdminBookingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for admin to view and manage bookings.
    Admin can view all bookings, filter by status, reseller, tour date, etc.
    """
    
    permission_classes = [IsAdminUser]
    queryset = Booking.objects.all()
    
    def get_queryset(self):
        """Optimize queryset by prefetching related objects."""
        return Booking.objects.select_related(
            "reseller", "reseller__user", "tour_date", "tour_date__package", "payment"
        ).prefetch_related("seat_slots")
    
    @action(detail=False, methods=["get"], url_path="dashboard-stats")
    def dashboard_stats(self, request):
        """
        Get dashboard statistics.
        Returns aggregated statistics for the admin dashboard.
        """
        from django.db.models import Count, Q
        from account.models import SupplierProfile, ResellerProfile
        from .models import TourPackage, PaymentStatus
        from django.utils import timezone
        from datetime import timedelta
        
        # Total Revenue (sum of total_amount from confirmed bookings with approved payments)
        # Optimized: Calculate in database using annotations instead of Python loops
        from django.db.models import Sum, F, Count
        
        confirmed_bookings = Booking.objects.filter(
            status="CONFIRMED",
            payment__status=PaymentStatus.APPROVED
        ).select_related("tour_date", "tour_date__package").annotate(
            seat_count=Count('seat_slots')
        ).annotate(
            booking_total=F('tour_date__price') * F('seat_count') + F('platform_fee')
        )
        
        # Aggregate in database instead of Python
        revenue_result = confirmed_bookings.aggregate(
            total=Sum('booking_total')
        )
        total_revenue = revenue_result['total'] or 0
        
        # Total Bookings (all bookings)
        total_bookings = Booking.objects.count()
        
        # Total Suppliers (active suppliers)
        total_suppliers = SupplierProfile.objects.filter(user__is_active=True).count()
        
        # Total Tours (active tours)
        total_tours = TourPackage.objects.filter(is_active=True).count()
        
        # Recent bookings count (last 30 days) for trend calculation
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_bookings = Booking.objects.filter(created_at__gte=thirty_days_ago).count()
        
        # Previous period bookings for comparison
        sixty_days_ago = timezone.now() - timedelta(days=60)
        previous_bookings = Booking.objects.filter(
            created_at__gte=sixty_days_ago,
            created_at__lt=thirty_days_ago
        ).count()
        
        # Calculate booking growth percentage
        booking_growth = 0
        if previous_bookings > 0:
            booking_growth = ((recent_bookings - previous_bookings) / previous_bookings) * 100
        elif recent_bookings > 0:
            booking_growth = 100  # 100% growth if no previous bookings
        
        # Revenue from last 30 days
        # Optimized: Calculate in database using annotations instead of Python loops
        from django.db.models import Sum, F, Count
        
        recent_confirmed_bookings = Booking.objects.filter(
            created_at__gte=thirty_days_ago,
            status="CONFIRMED",
            payment__status=PaymentStatus.APPROVED
        ).select_related("tour_date", "tour_date__package").annotate(
            seat_count=Count('seat_slots')
        ).annotate(
            booking_total=F('tour_date__price') * F('seat_count') + F('platform_fee')
        )
        
        recent_revenue_result = recent_confirmed_bookings.aggregate(
            total=Sum('booking_total')
        )
        recent_revenue = recent_revenue_result['total'] or 0
        
        # Previous period revenue
        previous_confirmed_bookings = Booking.objects.filter(
            created_at__gte=sixty_days_ago,
            created_at__lt=thirty_days_ago,
            status="CONFIRMED",
            payment__status=PaymentStatus.APPROVED
        ).select_related("tour_date", "tour_date__package").annotate(
            seat_count=Count('seat_slots')
        ).annotate(
            booking_total=F('tour_date__price') * F('seat_count') + F('platform_fee')
        )
        
        previous_revenue_result = previous_confirmed_bookings.aggregate(
            total=Sum('booking_total')
        )
        previous_revenue = previous_revenue_result['total'] or 0
        
        # Calculate revenue growth percentage
        revenue_growth = 0
        if previous_revenue > 0:
            revenue_growth = ((recent_revenue - previous_revenue) / previous_revenue) * 100
        elif recent_revenue > 0:
            revenue_growth = 100  # 100% growth if no previous revenue
        
        return Response({
            "total_revenue": total_revenue,
            "revenue_growth": round(revenue_growth, 1),
            "total_bookings": total_bookings,
            "booking_growth": round(booking_growth, 1),
            "total_suppliers": total_suppliers,
            "total_tours": total_tours,
        })
    
    @action(detail=False, methods=["get"], url_path="revenue-chart")
    def revenue_chart(self, request):
        """
        Get revenue chart data grouped by date.
        Returns daily revenue for the specified period.
        """
        from django.db.models.functions import TruncDate
        from django.db.models import Q
        from .models import PaymentStatus
        from django.utils import timezone
        from datetime import timedelta
        from collections import defaultdict
        
        # Get time range parameter (default 90 days)
        time_range = request.query_params.get("range", "90d")
        days = 90
        if time_range == "30d":
            days = 30
        elif time_range == "7d":
            days = 7
        
        # Calculate date range
        end_datetime = timezone.now()
        start_datetime = end_datetime - timedelta(days=days)
        start_date = start_datetime.date()
        end_date = end_datetime.date()
        
        # Create datetime boundaries for filtering (start of start_date, end of end_date)
        from datetime import datetime as dt
        start_bound = timezone.make_aware(dt.combine(start_date, dt.min.time()))
        end_bound = timezone.make_aware(dt.combine(end_date, dt.max.time()))
        
        # Get confirmed bookings with approved payments in the date range
        # Optimized: Calculate booking_total in database
        from django.db.models import Sum, F, Count
        
        bookings = Booking.objects.filter(
            created_at__gte=start_bound,
            created_at__lte=end_bound,
            status="CONFIRMED",
            payment__status=PaymentStatus.APPROVED
        ).select_related("tour_date", "tour_date__package").annotate(
            seat_count=Count('seat_slots')
        ).annotate(
            booking_total=F('tour_date__price') * F('seat_count') + F('platform_fee')
        )
        
        # Group revenue by date
        revenue_by_date = defaultdict(int)
        for booking in bookings:
            date_str = booking.created_at.date().isoformat()
            revenue_by_date[date_str] += booking.booking_total
        
        # Create list of all dates in range and fill with revenue data
        chart_data = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            chart_data.append({
                "date": date_str,
                "revenue": revenue_by_date.get(date_str, 0),
            })
            current_date += timedelta(days=1)
        
        return Response(chart_data)
    
    def get_queryset(self):
        """
        Return all bookings with optimized queries.
        Allow filtering by status, reseller, tour_date, and search.
        """
        queryset = Booking.objects.select_related(
            "reseller",
            "reseller__user",
            "tour_date",
            "tour_date__package",
            "tour_date__package__supplier",
        ).prefetch_related(
            "seat_slots",
            "payment",
        ).all()
        
        # Filter by status
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by reseller
        reseller_id = self.request.query_params.get("reseller")
        if reseller_id:
            queryset = queryset.filter(reseller_id=reseller_id)
        
        # Filter by tour_date
        tour_date_id = self.request.query_params.get("tour_date")
        if tour_date_id:
            queryset = queryset.filter(tour_date_id=tour_date_id)
        
        # Filter by tour_package
        tour_package_id = self.request.query_params.get("tour_package")
        if tour_package_id:
            queryset = queryset.filter(tour_date__package_id=tour_package_id)
        
        # Search by customer name, email, or booking ID
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(customer_name__icontains=search) |
                models.Q(customer_email__icontains=search) |
                models.Q(id__icontains=search)
            )
        
        # Ordering
        ordering = self.request.query_params.get("ordering", "-created_at")
        if ordering:
            queryset = queryset.order_by(*ordering.split(","))
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail."""
        if self.action == "list":
            return BookingListSerializer
        return BookingSerializer
    
    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm_booking(self, request, pk=None):
        """
        Confirm a booking (change status from PENDING to CONFIRMED).
        Requires that payment is approved.
        """
        booking = self.get_object()
        
        if booking.status != BookingStatus.PENDING:
            return Response(
                {"detail": f"Booking can only be confirmed when status is PENDING. Current status: {booking.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if payment exists and is approved
        if not hasattr(booking, 'payment') or not booking.payment:
            return Response(
                {"detail": "Booking cannot be confirmed without an approved payment."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if booking.payment.status != PaymentStatus.APPROVED:
            return Response(
                {"detail": f"Payment must be approved before confirming booking. Current payment status: {booking.payment.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = BookingStatus.CONFIRMED
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_booking(self, request, pk=None):
        """
        Cancel a booking (change status to CANCELLED).
        Only PENDING bookings can be cancelled.
        """
        booking = self.get_object()
        
        if booking.status != BookingStatus.PENDING:
            return Response(
                {"detail": f"Only PENDING bookings can be cancelled. Current status: {booking.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = BookingStatus.CANCELLED
        booking.save()
        
        # Release seat slots
        booking.seat_slots.update(status=SeatSlotStatus.AVAILABLE, booking=None)
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)