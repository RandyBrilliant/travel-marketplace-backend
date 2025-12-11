from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from account.models import UserRole, SupplierProfile
from .models import TourPackage, TourDate, TourImage, ItineraryItem
from .serializers import (
    TourPackageSerializer,
    TourPackageListSerializer,
    TourPackageCreateUpdateSerializer,
    TourDateSerializer,
    TourImageSerializer,
    ItineraryItemSerializer,
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
