from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from django.db import models
from django.db.utils import IntegrityError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from account.models import UserRole, SupplierProfile, ResellerProfile, CustomerProfile
from .models import TourPackage, TourDate, TourImage, ResellerTourCommission, ResellerGroup, Booking, BookingStatus, SeatSlotStatus, PaymentStatus, SeatSlot, WithdrawalRequest, WithdrawalRequestStatus, ResellerCommission, Currency
from .serializers import (
    TourPackageSerializer,
    TourPackageListSerializer,
    TourPackageCreateUpdateSerializer,
    AdminTourPackageSerializer,
    TourDateSerializer,
    TourImageSerializer,
    TourImageCreateUpdateSerializer,
    ResellerTourCommissionSerializer,
    ResellerGroupSerializer,
    BookingSerializer,
    BookingListSerializer,
    PublicTourPackageDetailSerializer,
    ResellerCommissionSerializer,
    CurrencySerializer,
)


class IsSupplier(permissions.BasePermission):
    """
    Permission check for supplier role.
    Now supports dual roles - checks if user has supplier profile and is approved.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_supplier):
            return False
        
        # Check if supplier is approved
        try:
            supplier_profile = request.user.supplier_profile
            from account.models import SupplierApprovalStatus
            return supplier_profile.approval_status == SupplierApprovalStatus.APPROVED
        except AttributeError:
            return False


class IsReseller(permissions.BasePermission):
    """
    Permission check for reseller role.
    Now supports dual roles - checks if user has reseller profile.
    """
    
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_reseller
        )


class IsCustomer(permissions.BasePermission):
    """
    Permission check for customer role.
    Checks if user has customer profile.
    """
    
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_customer
        )


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing available currencies.
    Read-only access for all users (authenticated and non-authenticated).
    """
    
    permission_classes = [permissions.AllowAny]
    queryset = Currency.objects.filter(is_active=True).order_by("code")
    serializer_class = CurrencySerializer
    filterset_fields = ["code", "is_active"]
    search_fields = ["code", "name", "symbol"]
    ordering_fields = ["code", "name"]
    ordering = ["code"]


class AdminCurrencyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage currencies (Create, Read, Update).
    Admin-only access. Delete functionality is disabled.
    """
    
    permission_classes = [permissions.IsAdminUser]
    queryset = Currency.objects.all().order_by("code")
    serializer_class = CurrencySerializer
    filterset_fields = ["code", "is_active"]
    search_fields = ["code", "name", "symbol"]
    ordering_fields = ["code", "name", "is_active"]
    ordering = ["code"]
    
    def destroy(self, request, *args, **kwargs):
        """Disable delete functionality for currencies."""
        return Response(
            {"detail": "Deleting currencies is not allowed."},
            status=status.HTTP_403_FORBIDDEN
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
    filterset_fields = ["tour_type", "is_active"]
    search_fields = ["name", "country"]
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
                "reseller_groups", "images", "dates"
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
                            "slug": "Paket tur dengan nama ini sudah ada. Silakan pilih nama yang berbeda.",
                            "detail": "Tidak dapat membuat paket tur. Pastikan nama tur unik."
                        }
                    )
                elif "nights_not_greater_than_days" in error_msg.lower():
                    raise ValidationError(
                        {
                            "nights": "Jumlah malam tidak boleh lebih besar dari jumlah hari.",
                            "detail": "Pastikan jumlah malam kurang dari atau sama dengan jumlah hari."
                        }
                    )
                else:
                    raise ValidationError(
                        {"detail": "Tidak dapat membuat paket tur. Silakan periksa input Anda dan coba lagi."}
                    )
        except SupplierProfile.DoesNotExist:
            raise ValidationError(
                {"detail": "Profil supplier tidak ditemukan. Silakan lengkapi pengaturan profil Anda."}
            )
    
    @action(detail=False, methods=["get"], url_path="reseller-groups")
    def reseller_groups(self, request):
        """Get list of active reseller groups for suppliers to assign to tour packages."""
        from .serializers import ResellerGroupSerializer
        
        queryset = ResellerGroup.objects.filter(is_active=True).prefetch_related(
            models.Prefetch("resellers", queryset=ResellerProfile.objects.select_related("user"))
        ).order_by("name")
        
        serializer = ResellerGroupSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)
    
    @action(detail=True, methods=["get", "post"], url_path="dates")
    def manage_dates(self, request, pk=None):
        """
        Manage tour dates for a package.
        
        GET: List tour dates with pagination and filtering.
        - Supports date filtering via `from_date` and `to_date` query parameters (YYYY-MM-DD format)
        - Supports pagination via `page` and `page_size` query parameters
        - Supports ordering via `ordering` query parameter (default: departure_date)
        
        POST: Create a new tour date.
        
        Optimized query to prefetch seat_slots for remaining_seats calculation.
        """
        # Get tour package directly to avoid queryset ordering conflicts
        # The ordering parameter is for TourDate, not TourPackage
        if not request.user.is_authenticated:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Authentication required.")
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=request.user)
            tour_package = TourPackage.objects.select_related("supplier", "supplier__user").get(
                pk=pk, supplier=supplier_profile
            )
        except SupplierProfile.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Supplier profile not found.")
        except TourPackage.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Tour package not found.")
        
        if request.method == "GET":
            from django.utils.dateparse import parse_date
            from django.utils import timezone
            
            # Start with base queryset
            dates = tour_package.dates.prefetch_related("seat_slots").all()
            
            # Apply date filtering
            from_date = request.query_params.get("from_date")
            to_date = request.query_params.get("to_date")
            
            if from_date:
                try:
                    from_date_parsed = parse_date(from_date)
                    if from_date_parsed:
                        dates = dates.filter(departure_date__gte=from_date_parsed)
                except (ValueError, TypeError):
                    pass  # Invalid date format, ignore filter
            
            if to_date:
                try:
                    to_date_parsed = parse_date(to_date)
                    if to_date_parsed:
                        dates = dates.filter(departure_date__lte=to_date_parsed)
                except (ValueError, TypeError):
                    pass  # Invalid date format, ignore filter
            
            # Apply ordering (default to departure_date)
            ordering = request.query_params.get("ordering", "departure_date")
            if ordering:
                dates = dates.order_by(*ordering.split(","))
            
            # Apply pagination
            page = self.paginate_queryset(dates)
            if page is not None:
                serializer = TourDateSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(serializer.data)
            
            # If no pagination, return all
            serializer = TourDateSerializer(dates, many=True, context={"request": request})
            return Response(serializer.data)
        
        elif request.method == "POST":
            serializer = TourDateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            try:
                tour_date = serializer.save(package=tour_package)
                # Prefetch seat_slots for the response
                tour_date = TourDate.objects.prefetch_related("seat_slots").get(pk=tour_date.pk)
                response_serializer = TourDateSerializer(tour_date, context={"request": request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                raise ValidationError({"detail": str(e)})
    
    @action(detail=True, methods=["get", "post"], url_path="images")
    def manage_images(self, request, pk=None):
        """Manage tour images for a package."""
        tour_package = self.get_object()
        
        if request.method == "GET":
            images = tour_package.images.all()
            serializer = TourImageSerializer(images, many=True, context={"request": request})
            return Response(serializer.data)
        
        elif request.method == "POST":
            serializer = TourImageCreateUpdateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            try:
                tour_image = serializer.save(package=tour_package)
                # Use read serializer for response
                response_serializer = TourImageSerializer(tour_image, context={"request": request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                raise ValidationError({"detail": str(e)})


class SupplierResellerGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage reseller groups.
    Suppliers can create groups and assign resellers to them.
    Only shows groups created by the current supplier.
    """
    
    permission_classes = [IsSupplier]
    serializer_class = ResellerGroupSerializer
    
    def get_queryset(self):
        """Return only reseller groups created by the current supplier."""
        if not self.request.user.is_authenticated:
            return ResellerGroup.objects.none()
        
        queryset = ResellerGroup.objects.filter(
            created_by=self.request.user
        ).prefetch_related(
            models.Prefetch("resellers", queryset=ResellerProfile.objects.select_related("user")),
            "tour_packages"
        )
        
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        
        # Ordering
        ordering = self.request.query_params.get("ordering")
        if ordering:
            queryset = queryset.order_by(*ordering.split(","))
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=["get"], url_path="available-resellers")
    def available_resellers(self, request):
        """
        Get all active resellers that can be assigned to groups.
        Suppliers need this to see available resellers when creating/editing groups.
        """
        from account.serializers import ResellerProfileSerializer
        from account.models import ResellerProfile
        
        # Get all active reseller profiles
        queryset = ResellerProfile.objects.filter(
            user__is_active=True
        ).select_related("user").order_by("user__email")
        
        # Support pagination if requested
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ResellerProfileSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ResellerProfileSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


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
            raise ValidationError({"package": ["Field ini wajib diisi."]})
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            package = TourPackage.objects.get(pk=package_id, supplier=supplier_profile)
            serializer.save(package=package)
        except TourPackage.DoesNotExist:
            raise ValidationError(
                {"package": ["Paket tur tidak ditemukan atau Anda tidak memiliki izin untuk mengaksesnya."]}
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
            raise ValidationError({"package": ["Field ini wajib diisi."]})
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            package = TourPackage.objects.get(pk=package_id, supplier=supplier_profile)
            serializer.save(package=package)
        except TourPackage.DoesNotExist:
            raise ValidationError(
                {"package": ["Paket tur tidak ditemukan atau Anda tidak memiliki izin untuk mengaksesnya."]}
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
        
        # Get reseller profile early for both cache key and filtering (optimize to fetch once)
        # Check if user has reseller profile (supports dual roles)
        reseller_profile = None
        reseller_group_ids = []
        if request.user.is_authenticated and request.user.is_reseller:
            try:
                reseller_profile = ResellerProfile.objects.prefetch_related('reseller_groups').get(user=request.user)
                reseller_groups = reseller_profile.reseller_groups.filter(is_active=True)
                reseller_group_ids = sorted(list(reseller_groups.values_list('id', flat=True)))
            except ResellerProfile.DoesNotExist:
                pass
        
        # Create cache key from query parameters
        # Include user role and reseller groups in cache key to differentiate reseller vs public views
        # Different resellers see different tours based on their groups
        user_identifier = 'anonymous'
        if request.user.is_authenticated:
            if reseller_profile:
                user_identifier = f'reseller_{reseller_profile.id}_groups_{"_".join(map(str, reseller_group_ids))}'
            elif request.user.is_reseller:
                user_identifier = f'reseller_{request.user.id}_no_profile'
            else:
                user_identifier = request.user.role
        
        cache_params = request.GET.urlencode()
        cache_key = f'tours_list_{user_identifier}_{md5(cache_params.encode()).hexdigest()}'
        
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
        # For anonymous/public users or non-reseller users, exclude tours with reseller groups
        # Supports dual roles - users with reseller profile can see reseller tours
        if reseller_profile is not None:
            # Filter tours that are either:
            # 1. Not assigned to any group (visible to all), OR
            # 2. Assigned to a group that includes this reseller
            # Note: Tours without any reseller groups are visible to all resellers
            if reseller_group_ids:
                # Reseller belongs to some groups
                # Show tours with no groups OR tours with groups that include this reseller
                queryset = queryset.filter(
                    models.Q(reseller_groups__isnull=True) |  # Tours with no groups
                    models.Q(reseller_groups__id__in=reseller_group_ids)  # Tours in reseller's groups
                ).distinct()
            else:
                # Reseller doesn't belong to any groups
                # Only show tours with no group assignment (visible to all)
                queryset = queryset.filter(reseller_groups__isnull=True)
        elif request.user.is_authenticated and request.user.is_reseller:
            # User has reseller profile but it doesn't exist (shouldn't happen, but handle gracefully)
            # Only show tours with no group assignment
            # This prevents unauthorized access to group-restricted tours
            queryset = queryset.filter(reseller_groups__isnull=True)
        else:
            # For anonymous users or authenticated users without reseller profile,
            # exclude tours that have any reseller groups assigned
            # These tours should only be visible to users with reseller profiles and appropriate group access
            queryset = queryset.filter(reseller_groups__isnull=True)
        
        # Search
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(country__icontains=search)
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
        ordering = request.query_params.get("ordering", "-created_at")
        if ordering:
            # Filter out is_featured from ordering since field doesn't exist
            ordering_fields = [f for f in ordering.split(",") if "is_featured" not in f]
            if ordering_fields:
                queryset = queryset.order_by(*ordering_fields)
        
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
    
    def get(self, request, slug):
        """Get tour package detail by slug."""
        from django.http import Http404
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"[Tour Detail] Getting tour {slug} for user {request.user} (authenticated={request.user.is_authenticated})")
        
        try:
            tour = TourPackage.objects.filter(
                is_active=True
            ).select_related(
                "supplier", "supplier__user"
            ).prefetch_related(
                "reseller_groups", "reseller_groups__resellers",
                "images",
                models.Prefetch(
                    "dates",
                    queryset=TourDate.objects.prefetch_related(
                        models.Prefetch(
                            "seat_slots",
                            queryset=SeatSlot.objects.select_related("booking")
                        )
                    ).order_by("departure_date")
                )
            ).get(slug=slug)
        except TourPackage.DoesNotExist:
            raise Http404("Paket tur tidak ditemukan")
        
        # Get tour's reseller groups to check access
        tour_groups = tour.reseller_groups.filter(is_active=True)
        
        # Check if tour has reseller group restrictions
        if tour_groups.exists():
            # Tour has group restrictions - only users with reseller profile and appropriate group access can view
            # Supports dual roles - suppliers with reseller profiles can access reseller tours
            if request.user.is_authenticated and request.user.is_reseller:
                try:
                    # Prefetch reseller_profile for serializer to avoid N+1 query
                    reseller_profile = ResellerProfile.objects.prefetch_related('reseller_groups').select_related('user').get(user=request.user)
                    request.user.reseller_profile = reseller_profile  # Cache for serializer
                    
                    # Check access:
                    # Reseller must be in at least one of the tour's groups
                    reseller_groups = reseller_profile.reseller_groups.filter(is_active=True)
                    reseller_group_ids = set(reseller_groups.values_list('id', flat=True))
                    tour_group_ids = set(tour_groups.values_list('id', flat=True))
                    
                    # Check if reseller belongs to any of the tour's groups
                    if not (reseller_group_ids & tour_group_ids):
                        # Reseller doesn't belong to any of the tour's groups
                        raise Http404("Paket tur tidak ditemukan")
                    # Reseller is in a group, allow access
                except ResellerProfile.DoesNotExist:
                    # Reseller profile doesn't exist, deny access
                    raise Http404("Paket tur tidak ditemukan")
            else:
                # Anonymous user or user without reseller profile - deny access to group-restricted tours
                raise Http404("Paket tur tidak ditemukan")
        else:
            # Tour has no group restrictions - visible to everyone
            # Cache reseller_profile for serializer if user has reseller profile (supports dual roles)
            if request.user.is_authenticated and request.user.is_reseller:
                try:
                    reseller_profile = ResellerProfile.objects.prefetch_related('reseller_groups').select_related('user').get(user=request.user)
                    request.user.reseller_profile = reseller_profile  # Cache for serializer
                except ResellerProfile.DoesNotExist:
                    pass  # Allow access even without profile if tour has no groups
        
        serializer = PublicTourPackageDetailSerializer(tour, context={"request": request})
        response = Response(serializer.data)
        # Add cache-busting headers to ensure fresh seat availability data
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


class AdminResellerGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage reseller groups.
    Admin can create groups and assign resellers to them.
    """
    
    permission_classes = [IsAdminUser]
    serializer_class = ResellerGroupSerializer
    queryset = ResellerGroup.objects.all()
    
    def get_queryset(self):
        """Allow filtering by is_active and ordering."""
        queryset = ResellerGroup.objects.prefetch_related(
            models.Prefetch("resellers", queryset=ResellerProfile.objects.select_related("user")),
            "tour_packages"
        ).all()
        
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        
        # Ordering
        ordering = self.request.query_params.get("ordering")
        if ordering:
            queryset = queryset.order_by(*ordering.split(","))
        
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
            models.Prefetch(
                "reseller_groups",
                queryset=ResellerGroup.objects.filter(is_active=True).prefetch_related("resellers")
            ),
            "images",
            "dates__seat_slots",
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
        
        # Search by name, country, or itinerary
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(country__icontains=search) |
                models.Q(itinerary__icontains=search)
            )
        
        # Ordering
        ordering = self.request.query_params.get("ordering", "-created_at")
        if ordering:
            # Filter out is_featured from ordering since field doesn't exist
            ordering_fields = [f for f in ordering.split(",") if "is_featured" not in f]
            if ordering_fields:
                queryset = queryset.order_by(*ordering_fields)
        
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
            raise ValidationError({"supplier": ["Field ini wajib diisi."]})
        
        try:
            supplier = SupplierProfile.objects.get(pk=supplier_id)
            serializer.save(supplier=supplier)
        except SupplierProfile.DoesNotExist:
            raise ValidationError({"supplier": ["Profil supplier tidak ditemukan."]})
    
    @action(detail=True, methods=["get", "post"], url_path="dates")
    def manage_dates(self, request, pk=None):
        """
        Manage tour dates for a package (Admin view).
        
        GET: List tour dates with pagination and filtering.
        - Supports date filtering via `from_date` and `to_date` query parameters (YYYY-MM-DD format)
        - Supports pagination via `page` and `page_size` query parameters
        - Supports ordering via `ordering` query parameter (default: departure_date)
        
        POST: Create a new tour date.
        
        Optimized query to prefetch seat_slots for remaining_seats calculation.
        """
        # Get tour package directly to avoid queryset ordering conflicts
        # The ordering parameter is for TourDate, not TourPackage
        try:
            tour_package = TourPackage.objects.select_related("supplier", "supplier__user").get(pk=pk)
        except TourPackage.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Tour package not found.")
        
        if request.method == "GET":
            from django.utils.dateparse import parse_date
            from django.utils import timezone
            
            # Start with base queryset
            dates = tour_package.dates.prefetch_related("seat_slots").all()
            
            # Apply date filtering
            from_date = request.query_params.get("from_date")
            to_date = request.query_params.get("to_date")
            
            if from_date:
                try:
                    from_date_parsed = parse_date(from_date)
                    if from_date_parsed:
                        dates = dates.filter(departure_date__gte=from_date_parsed)
                except (ValueError, TypeError):
                    pass  # Invalid date format, ignore filter
            
            if to_date:
                try:
                    to_date_parsed = parse_date(to_date)
                    if to_date_parsed:
                        dates = dates.filter(departure_date__lte=to_date_parsed)
                except (ValueError, TypeError):
                    pass  # Invalid date format, ignore filter
            
            # Apply ordering (default to departure_date)
            ordering = request.query_params.get("ordering", "departure_date")
            if ordering:
                dates = dates.order_by(*ordering.split(","))
            
            # Apply pagination
            page = self.paginate_queryset(dates)
            if page is not None:
                serializer = TourDateSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(serializer.data)
            
            # If no pagination, return all
            serializer = TourDateSerializer(dates, many=True, context={"request": request})
            return Response(serializer.data)
        
        elif request.method == "POST":
            serializer = TourDateSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            try:
                tour_date = serializer.save(package=tour_package)
                # Prefetch seat_slots for the response
                tour_date = TourDate.objects.prefetch_related("seat_slots").get(pk=tour_date.pk)
                response_serializer = TourDateSerializer(tour_date, context={"request": request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                raise ValidationError({"detail": str(e)})


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


class SupplierBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to view and manage bookings for their own tours.
    Suppliers can update booking status and payment status.
    """
    
    permission_classes = [IsSupplier]
    queryset = Booking.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "tour_date", "tour_date__package"]
    search_fields = [
        "reseller__full_name",
        "reseller__user__email", "tour_date__package__name",
    ]
    ordering_fields = [
        "created_at", "status", "total_amount", "tour_date__departure_date",
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
                "reseller", "reseller__user", "tour_date", "tour_date__package"
            ).prefetch_related(
                "seat_slots", "seat_slots__tour_date", "payments"
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
        if self.action in ['update', 'partial_update']:
            from .serializers import BookingUpdateSerializer
            return BookingUpdateSerializer
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
                {"detail": "Autentikasi diperlukan."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=request.user)
        except SupplierProfile.DoesNotExist:
            return Response(
                {"detail": "Profil supplier tidak ditemukan."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get bookings for tours owned by this supplier
        bookings_queryset = Booking.objects.filter(
            tour_date__package__supplier=supplier_profile
        ).select_related("tour_date", "tour_date__package").prefetch_related("seat_slots", "payments")
        
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
            payments__status=PaymentStatus.APPROVED
        ).distinct().annotate(
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
                {"detail": "Autentikasi diperlukan."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=request.user)
        except SupplierProfile.DoesNotExist:
            return Response(
                {"detail": "Profil supplier tidak ditemukan."},
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
            status=BookingStatus.CONFIRMED,
            payments__status=PaymentStatus.APPROVED
        ).distinct().select_related("tour_date", "tour_date__package").annotate(
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
    
    @action(detail=True, methods=["patch"], url_path="payment/status")
    def update_payment_status(self, request, pk=None):
        """Update payment status for a booking."""
        booking = self.get_object()
        
        # Ensure supplier owns this booking's tour
        if booking.tour_date.package.supplier.user != request.user:
            return Response(
                {"detail": "Anda tidak memiliki izin untuk memperbarui booking ini."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        latest_payment = booking.payments.order_by('-created_at').first()
        if not latest_payment:
            return Response(
                {"detail": "Booking tidak memiliki pembayaran."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {"detail": "Status wajib diisi."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in [PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED]:
            return Response(
                {"detail": f"Status tidak valid. Harus salah satu dari: {', '.join([PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED])}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment = latest_payment
        payment.status = new_status
        payment.reviewed_by = request.user
        payment.reviewed_at = timezone.now()
        payment.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=["patch"], url_path="payment")
    def update_payment(self, request, pk=None):
        """Update or create payment details (amount, transfer_date, proof_image) for a booking."""
        from .serializers import PaymentUpdateSerializer
        from .models import Payment
        
        booking = self.get_object()
        
        # Ensure supplier owns this booking's tour
        if booking.tour_date.package.supplier.user != request.user:
            return Response(
                {"detail": "Anda tidak memiliki izin untuk memperbarui booking ini."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Suppliers can create new payments or update a specific payment or the latest payment
        # Get the latest payment if it exists
        latest_payment = booking.payments.order_by('-created_at').first()
        
        # Check if we're updating a specific payment by ID
        payment_id = request.data.get('payment_id')
        
        if payment_id:
            # Update specific payment by ID
            try:
                payment = booking.payments.get(id=payment_id)
            except Payment.DoesNotExist:
                return Response(
                    {"detail": "Pembayaran tidak ditemukan."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer_data = {}
            if 'amount' in request.data:
                serializer_data['amount'] = request.data['amount']
            if 'transfer_date' in request.data:
                serializer_data['transfer_date'] = request.data['transfer_date']
            if 'proof_image' in request.data and request.data['proof_image']:
                serializer_data['proof_image'] = request.data['proof_image']
            if 'status' in request.data and request.data['status']:
                status_value = request.data['status']
                if status_value in [PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED]:
                    serializer_data['status'] = status_value
            
            serializer = PaymentUpdateSerializer(payment, data=serializer_data, partial=True)
            
            if serializer.is_valid():
                old_status = payment.status
                serializer.save()
                
                if 'status' in serializer_data:
                    new_status = serializer_data['status']
                    if old_status != new_status:
                        if new_status != PaymentStatus.PENDING:
                            payment.reviewed_by = request.user
                            payment.reviewed_at = timezone.now()
                        else:
                            payment.reviewed_by = None
                            payment.reviewed_at = None
                        payment.save(update_fields=['reviewed_by', 'reviewed_at'])
                
                booking_serializer = self.get_serializer(booking)
                return Response(booking_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if we're updating existing payment or creating new one
        update_existing = request.data.get('update_existing', 'false').lower() == 'true' and latest_payment
        
        if update_existing and latest_payment:
            # Update existing payment
            payment = latest_payment
            serializer_data = {}
            if 'amount' in request.data:
                serializer_data['amount'] = request.data['amount']
            if 'transfer_date' in request.data:
                serializer_data['transfer_date'] = request.data['transfer_date']
            # Only include proof_image if it's in the request and not empty
            if 'proof_image' in request.data and request.data['proof_image']:
                serializer_data['proof_image'] = request.data['proof_image']
            # Include status if provided
            if 'status' in request.data and request.data['status']:
                status_value = request.data['status']
                if status_value in [PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED]:
                    serializer_data['status'] = status_value
            
            serializer = PaymentUpdateSerializer(payment, data=serializer_data, partial=True)
            
            if serializer.is_valid():
                # Track old status before saving
                old_status = payment.status
                serializer.save()
                
                # Update reviewed_by and reviewed_at if status is being changed
                if 'status' in serializer_data:
                    new_status = serializer_data['status']
                    if old_status != new_status:
                        if new_status != PaymentStatus.PENDING:
                            payment.reviewed_by = request.user
                            payment.reviewed_at = timezone.now()
                        else:
                            payment.reviewed_by = None
                            payment.reviewed_at = None
                        payment.save(update_fields=['reviewed_by', 'reviewed_at'])
                
                # Return updated booking
                booking_serializer = self.get_serializer(booking)
                return Response(booking_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Create new payment
            amount = request.data.get('amount')
            transfer_date = request.data.get('transfer_date')
            
            if not amount or not transfer_date:
                return Response(
                    {"detail": "Jumlah pembayaran dan tanggal transfer wajib diisi untuk membuat pembayaran baru."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Prepare data for serializer
            serializer_data = {
                'amount': amount,
                'transfer_date': transfer_date,
            }
            # Only include proof_image if it's in the request
            if 'proof_image' in request.data and request.data['proof_image']:
                serializer_data['proof_image'] = request.data['proof_image']
            # Include status if provided, otherwise default to PENDING
            if 'status' in request.data and request.data['status']:
                status_value = request.data['status']
                if status_value in [PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED]:
                    serializer_data['status'] = status_value
                else:
                    serializer_data['status'] = PaymentStatus.PENDING
            else:
                serializer_data['status'] = PaymentStatus.PENDING
            
            # Use serializer to create payment (handles file uploads properly)
            serializer = PaymentUpdateSerializer(data=serializer_data)
            
            if serializer.is_valid():
                payment = serializer.save(booking=booking)
                # Set reviewed_by and reviewed_at if status is not PENDING
                if serializer_data['status'] != PaymentStatus.PENDING:
                    payment.reviewed_by = request.user
                    payment.reviewed_at = timezone.now()
                    payment.save(update_fields=['reviewed_by', 'reviewed_at'])
                # Return updated booking
                booking_serializer = self.get_serializer(booking)
                return Response(booking_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        "tour_date__package__name",
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
                "reseller", "reseller__user", "tour_date", "tour_date__package"
            ).prefetch_related(
                "seat_slots", "seat_slots__tour_date", "payments"
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
        if self.action == "create":
            from .serializers import BookingCreateSerializer
            return BookingCreateSerializer
        return BookingSerializer
    
    def perform_create(self, serializer):
        """Set the reseller when creating a booking."""
        try:
            reseller_profile = ResellerProfile.objects.get(user=self.request.user)
            serializer.save(reseller=reseller_profile)
        except ResellerProfile.DoesNotExist:
            raise ValidationError(
                {"detail": "Profil reseller tidak ditemukan. Silakan lengkapi pengaturan profil Anda."}
            )
    
    @action(detail=True, methods=["patch"], url_path="payment")
    def update_payment(self, request, pk=None):
        """Upload or update payment details (amount, transfer_date, proof_image) for a booking.
        
        Resellers can upload payment proof and details, but cannot change payment status.
        Status must be set by suppliers or admins.
        """
        from .serializers import ResellerPaymentUpdateSerializer
        from .models import Payment, PaymentStatus
        from django.utils import timezone
        
        booking = self.get_object()
        
        # Ensure reseller owns this booking
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            reseller_profile = ResellerProfile.objects.get(user=request.user)
            if booking.reseller != reseller_profile:
                return Response(
                    {"detail": "Anda tidak memiliki izin untuk memperbarui booking ini."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except ResellerProfile.DoesNotExist:
            return Response(
                {"detail": "Profil reseller tidak ditemukan."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Always create a new payment record (payment history)
        # Validate required fields for creating a new payment
        amount = request.data.get('amount')
        transfer_date = request.data.get('transfer_date')
        
        if not amount or not transfer_date:
            return Response(
                {"detail": "Jumlah pembayaran dan tanggal transfer wajib diisi untuk membuat pembayaran baru."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepare data for serializer (only include proof_image if it exists)
        serializer_data = {
            'amount': amount,
            'transfer_date': transfer_date,
        }
        # Only include proof_image if it's in the request
        if 'proof_image' in request.data and request.data['proof_image']:
            serializer_data['proof_image'] = request.data['proof_image']
        # Status always defaults to PENDING for reseller uploads
        serializer_data['status'] = PaymentStatus.PENDING
        
        # Use serializer to create payment (handles file uploads properly)
        serializer = ResellerPaymentUpdateSerializer(data=serializer_data)
        
        if serializer.is_valid():
            payment = serializer.save(booking=booking, status=PaymentStatus.PENDING)
            # Return updated booking
            booking_serializer = self.get_serializer(booking)
            return Response(booking_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=["get"], url_path="commissions")
    def commissions(self, request):
        """Get commission history for the authenticated reseller."""
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            reseller_profile = ResellerProfile.objects.get(user=request.user)
        except ResellerProfile.DoesNotExist:
            return Response(
                {"detail": "Profil reseller tidak ditemukan."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all commissions for this reseller with proper joins for serialization
        queryset = ResellerCommission.objects.filter(
            reseller=reseller_profile
        ).select_related(
            "booking", 
            "booking__tour_date", 
            "booking__tour_date__package", 
            "booking__reseller"
        ).prefetch_related(
            "booking__seat_slots"
        ).order_by("-created_at")
        
        # Filter by booking status if provided
        booking_status = request.query_params.get("booking_status")
        if booking_status:
            queryset = queryset.filter(booking__status=booking_status)
        
        # Filter by level if provided
        level = request.query_params.get("level")
        if level is not None:
            try:
                level_int = int(level)
                queryset = queryset.filter(level=level_int)
            except ValueError:
                pass
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ResellerCommissionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ResellerCommissionSerializer(queryset, many=True)
        return Response(serializer.data)


class CustomerBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for customers to view and create their own bookings.
    Customers can create direct bookings without commission/referral logic.
    """
    
    permission_classes = [IsCustomer]
    queryset = Booking.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "tour_date", "tour_date__package"]
    search_fields = [
        "tour_date__package__name",
    ]
    ordering_fields = [
        "created_at", "status", "total_amount",
        "tour_date__package__name",
    ]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """
        Return only bookings belonging to the authenticated customer.
        Allow filtering by status, tour_date, and search.
        """
        if not self.request.user.is_authenticated:
            return Booking.objects.none()
        
        try:
            customer_profile = CustomerProfile.objects.get(user=self.request.user)
            # Get bookings created by this customer
            queryset = Booking.objects.filter(
                customer=customer_profile
            ).select_related(
                "customer", "customer__user", "tour_date", "tour_date__package"
            ).prefetch_related(
                "seat_slots", "seat_slots__tour_date", "payments"
            ).all()
            
            # Apply additional filters
            status_filter = self.request.query_params.get("status")
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
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
                    models.Q(tour_date__package__name__icontains=search)
                )
            
            # Ordering
            ordering = self.request.query_params.get("ordering", "-created_at")
            if ordering:
                queryset = queryset.order_by(*ordering.split(","))
            
            return queryset
        except CustomerProfile.DoesNotExist:
            return Booking.objects.none()
    
    def get_serializer_class(self):
        if self.action == "list":
            return BookingListSerializer
        if self.action == "create":
            from .serializers import BookingCreateSerializer
            return BookingCreateSerializer
        return BookingSerializer
    
    def perform_create(self, serializer):
        """Set the customer when creating a booking."""
        try:
            customer_profile = CustomerProfile.objects.get(user=self.request.user)
            serializer.save(customer=customer_profile)
        except CustomerProfile.DoesNotExist:
            raise ValidationError(
                {"detail": "Customer profile not found. Please complete your profile first."}
            )
    
    @action(detail=True, methods=["patch"], url_path="payment")
    def update_payment(self, request, pk=None):
        """Upload or update payment details (amount, transfer_date, proof_image) for a booking.
        
        Customers can upload payment proof and details, but cannot change payment status.
        Status must be set by suppliers or admins.
        """
        from .serializers import ResellerPaymentUpdateSerializer
        from .models import Payment, PaymentStatus
        from django.utils import timezone
        
        booking = self.get_object()
        
        # Ensure customer owns this booking
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            customer_profile = CustomerProfile.objects.get(user=request.user)
            if booking.customer != customer_profile:
                return Response(
                    {"detail": "You do not have permission to update this booking."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except CustomerProfile.DoesNotExist:
            return Response(
                {"detail": "Customer profile not found."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Always create a new payment record (payment history)
        # Validate required fields for creating a new payment
        amount = request.data.get('amount')
        transfer_date = request.data.get('transfer_date')
        
        if not amount or not transfer_date:
            return Response(
                {"detail": "Payment amount and transfer date are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepare data for serializer (only include proof_image if it exists)
        serializer_data = {
            'amount': amount,
            'transfer_date': transfer_date,
        }
        # Only include proof_image if it's in the request
        if 'proof_image' in request.data and request.data['proof_image']:
            serializer_data['proof_image'] = request.data['proof_image']
        # Status always defaults to PENDING for customer uploads
        serializer_data['status'] = PaymentStatus.PENDING
        
        # Use serializer to create payment (handles file uploads properly)
        serializer = ResellerPaymentUpdateSerializer(data=serializer_data)
        
        if serializer.is_valid():
            payment = serializer.save(booking=booking, status=PaymentStatus.PENDING)
            # Return updated booking
            booking_serializer = self.get_serializer(booking)
            return Response(booking_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to view and manage bookings.
    Admin can view all bookings, filter by status, reseller, tour date, etc.
    Admin can update booking status directly.
    """
    
    permission_classes = [IsAdminUser]
    queryset = Booking.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            from .serializers import BookingUpdateSerializer
            return BookingUpdateSerializer
        if self.action == "list":
            return BookingListSerializer
        return BookingSerializer
    
    def get_queryset(self):
        """Optimize queryset by prefetching related objects."""
        return Booking.objects.select_related(
            "reseller", "reseller__user", "tour_date", "tour_date__package"
        ).prefetch_related("seat_slots", "payments")
    
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
            status=BookingStatus.CONFIRMED,
            payments__status=PaymentStatus.APPROVED
        ).distinct().select_related("tour_date", "tour_date__package").annotate(
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
            status=BookingStatus.CONFIRMED,
            payments__status=PaymentStatus.APPROVED
        ).distinct().select_related("tour_date", "tour_date__package").annotate(
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
            status=BookingStatus.CONFIRMED,
            payments__status=PaymentStatus.APPROVED
        ).distinct().select_related("tour_date", "tour_date__package").annotate(
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
            status=BookingStatus.CONFIRMED,
            payments__status=PaymentStatus.APPROVED
        ).distinct().select_related("tour_date", "tour_date__package").annotate(
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
            "payments",
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
        
        # Search by booking ID or reseller name
        search = self.request.query_params.get("search")
        if search:
            # Try to parse as integer for ID search
            try:
                booking_id = int(search)
                queryset = queryset.filter(
                    models.Q(id=booking_id) |
                    models.Q(reseller__full_name__icontains=search) |
                    models.Q(reseller__user__email__icontains=search)
                )
            except ValueError:
                # Not a number, search by reseller name and email
                queryset = queryset.filter(
                    models.Q(reseller__full_name__icontains=search) |
                    models.Q(reseller__user__email__icontains=search)
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
                {"detail": f"Booking hanya dapat dikonfirmasi ketika status adalah PENDING. Status saat ini: {booking.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if any payment exists and is approved
        approved_payment = booking.payments.filter(status=PaymentStatus.APPROVED).first()
        if not approved_payment:
            latest_payment = booking.payments.order_by('-created_at').first()
            if not latest_payment:
                return Response(
                    {"detail": "Booking tidak dapat dikonfirmasi tanpa pembayaran yang disetujui."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"detail": f"Pembayaran harus disetujui sebelum mengonfirmasi booking. Status pembayaran saat ini: {latest_payment.status}"},
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
                {"detail": f"Hanya booking dengan status PENDING yang dapat dibatalkan. Status saat ini: {booking.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = BookingStatus.CANCELLED
        booking.save()
        
        # Delete commissions associated with this booking
        # Resellers should not receive commission for cancelled bookings
        booking.commissions.all().delete()
        
        # Release seat slots - make them available again
        # Only when booking is cancelled, seats become available again
        booking.seat_slots.update(status=SeatSlotStatus.AVAILABLE, booking=None)
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"], url_path="payment/approve")
    def approve_payment(self, request, pk=None):
        """Approve the latest payment for a booking."""
        booking = self.get_object()
        
        latest_payment = booking.payments.order_by('-created_at').first()
        if not latest_payment:
            return Response(
                {"detail": "Booking tidak memiliki pembayaran."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment = latest_payment
        payment.status = PaymentStatus.APPROVED
        payment.reviewed_by = request.user
        payment.reviewed_at = timezone.now()
        payment.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"], url_path="payment/reject")
    def reject_payment(self, request, pk=None):
        """Reject the latest payment for a booking."""
        booking = self.get_object()
        
        latest_payment = booking.payments.order_by('-created_at').first()
        if not latest_payment:
            return Response(
                {"detail": "Booking tidak memiliki pembayaran."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment = latest_payment
        payment.status = PaymentStatus.REJECTED
        payment.reviewed_by = request.user
        payment.reviewed_at = timezone.now()
        payment.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=["patch"], url_path="payment/status")
    def update_payment_status(self, request, pk=None):
        """Update status of the latest payment for a booking."""
        booking = self.get_object()
        
        latest_payment = booking.payments.order_by('-created_at').first()
        if not latest_payment:
            return Response(
                {"detail": "Booking tidak memiliki pembayaran."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {"detail": "Status wajib diisi."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in [PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED]:
            return Response(
                {"detail": f"Status tidak valid. Harus salah satu dari: {', '.join([PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED])}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment = latest_payment
        payment.status = new_status
        payment.reviewed_by = request.user
        payment.reviewed_at = timezone.now()
        payment.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=["patch"], url_path="payment")
    def update_payment(self, request, pk=None):
        """Update or create payment details (amount, transfer_date, proof_image) for a booking."""
        from .serializers import PaymentUpdateSerializer
        from .models import Payment
        
        booking = self.get_object()
        
        # Admin can create new payments or update the latest payment
        # Get the latest payment if it exists
        latest_payment = booking.payments.order_by('-created_at').first()
        
        # Check if we're updating existing payment or creating new one
        # If payment_id is provided, update that specific payment, otherwise update latest or create new
        payment_id = request.data.get('payment_id')
        
        if payment_id:
            # Update specific payment by ID
            try:
                payment = booking.payments.get(id=payment_id)
            except Payment.DoesNotExist:
                return Response(
                    {"detail": "Pembayaran tidak ditemukan."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer_data = {}
            if 'amount' in request.data:
                serializer_data['amount'] = request.data['amount']
            if 'transfer_date' in request.data:
                serializer_data['transfer_date'] = request.data['transfer_date']
            if 'proof_image' in request.data and request.data['proof_image']:
                serializer_data['proof_image'] = request.data['proof_image']
            if 'status' in request.data and request.data['status']:
                status_value = request.data['status']
                if status_value in [PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED]:
                    serializer_data['status'] = status_value
            
            serializer = PaymentUpdateSerializer(payment, data=serializer_data, partial=True)
            
            if serializer.is_valid():
                old_status = payment.status
                serializer.save()
                
                if 'status' in serializer_data:
                    new_status = serializer_data['status']
                    if old_status != new_status:
                        if new_status != PaymentStatus.PENDING:
                            payment.reviewed_by = request.user
                            payment.reviewed_at = timezone.now()
                        else:
                            payment.reviewed_by = None
                            payment.reviewed_at = None
                        payment.save(update_fields=['reviewed_by', 'reviewed_at'])
                
                booking_serializer = self.get_serializer(booking)
                return Response(booking_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update latest payment or create new one
        update_existing = request.data.get('update_existing', 'false').lower() == 'true' and latest_payment
        
        if update_existing and latest_payment:
            # Update existing payment
            payment = latest_payment
            serializer_data = {}
            if 'amount' in request.data:
                serializer_data['amount'] = request.data['amount']
            if 'transfer_date' in request.data:
                serializer_data['transfer_date'] = request.data['transfer_date']
            if 'proof_image' in request.data and request.data['proof_image']:
                serializer_data['proof_image'] = request.data['proof_image']
            if 'status' in request.data and request.data['status']:
                status_value = request.data['status']
                if status_value in [PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED]:
                    serializer_data['status'] = status_value
            
            serializer = PaymentUpdateSerializer(payment, data=serializer_data, partial=True)
            
            if serializer.is_valid():
                old_status = payment.status
                serializer.save()
                
                if 'status' in serializer_data:
                    new_status = serializer_data['status']
                    if old_status != new_status:
                        if new_status != PaymentStatus.PENDING:
                            payment.reviewed_by = request.user
                            payment.reviewed_at = timezone.now()
                        else:
                            payment.reviewed_by = None
                            payment.reviewed_at = None
                        payment.save(update_fields=['reviewed_by', 'reviewed_at'])
                
                booking_serializer = self.get_serializer(booking)
                return Response(booking_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Create new payment
            amount = request.data.get('amount')
            transfer_date = request.data.get('transfer_date')
            
            if not amount or not transfer_date:
                return Response(
                    {"detail": "Jumlah pembayaran dan tanggal transfer wajib diisi untuk membuat pembayaran baru."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer_data = {
                'amount': amount,
                'transfer_date': transfer_date,
            }
            if 'proof_image' in request.data and request.data['proof_image']:
                serializer_data['proof_image'] = request.data['proof_image']
            if 'status' in request.data and request.data['status']:
                status_value = request.data['status']
                if status_value in [PaymentStatus.PENDING, PaymentStatus.APPROVED, PaymentStatus.REJECTED]:
                    serializer_data['status'] = status_value
                else:
                    serializer_data['status'] = PaymentStatus.PENDING
            else:
                serializer_data['status'] = PaymentStatus.PENDING
            
            serializer = PaymentUpdateSerializer(data=serializer_data)
            
            if serializer.is_valid():
                payment = serializer.save(booking=booking)
                if serializer_data['status'] != PaymentStatus.PENDING:
                    payment.reviewed_by = request.user
                    payment.reviewed_at = timezone.now()
                    payment.save(update_fields=['reviewed_by', 'reviewed_at'])
                
                booking_serializer = self.get_serializer(booking)
                return Response(booking_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Import withdrawal views from separate file to keep views.py manageable
from .withdrawal_views import ResellerWithdrawalViewSet, AdminWithdrawalViewSet