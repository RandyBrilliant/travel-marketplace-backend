from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from django.db import transaction, models
from django.utils.text import slugify
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly
from account.models import UserRole, SupplierProfile, ResellerProfile
from .models import TourPackage, TourDate, TourImage, ItineraryItem, ResellerTourCommission, ResellerGroup
from .serializers import (
    TourPackageSerializer,
    TourPackageListSerializer,
    TourPackageCreateUpdateSerializer,
    TourDateSerializer,
    TourImageSerializer,
    ItineraryItemSerializer,
    ResellerTourCommissionSerializer,
    ResellerGroupSerializer,
)


class IsSupplier(permissions.BasePermission):
    """Permission check for supplier role."""
    
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.SUPPLIER
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
    
    def get_queryset(self):
        """Return only tour packages belonging to the authenticated supplier."""
        if not self.request.user.is_authenticated:
            return TourPackage.objects.none()
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return TourPackage.objects.filter(supplier=supplier_profile)
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
            serializer.save(supplier=supplier_profile)
        except SupplierProfile.DoesNotExist:
            raise ValidationError(
                {"detail": "Supplier profile not found. Please complete your profile setup."}
            )
    
    @action(detail=True, methods=["get", "post"], url_path="dates")
    def manage_dates(self, request, pk=None):
        """Manage tour dates for a package."""
        tour_package = self.get_object()
        
        if request.method == "GET":
            dates = tour_package.dates.all()
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
    
    def get_queryset(self):
        """Return only tour dates for packages belonging to the authenticated supplier."""
        if not self.request.user.is_authenticated:
            return TourDate.objects.none()
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return TourDate.objects.filter(package__supplier=supplier_profile)
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
    serializer_class = TourImageSerializer
    
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
            serializer.save(package=package)
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
        
        queryset = TourPackage.objects.filter(is_active=True).select_related("supplier").prefetch_related("reseller_groups")
        
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
                models.Q(city__icontains=search) |
                models.Q(country__icontains=search) |
                models.Q(summary__icontains=search)
            )
        
        # Ordering
        ordering = request.query_params.get("ordering", "-is_featured,-created_at")
        if ordering:
            queryset = queryset.order_by(*ordering.split(","))
        
        serializer = TourPackageListSerializer(queryset, many=True, context={"request": request})
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
