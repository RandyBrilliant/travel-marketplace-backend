from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from django.db import transaction

from account.models import (
    CustomUser,
    SupplierProfile,
    ResellerProfile,
    StaffProfile,
    UserRole,
)
from account.serializers import (
    SupplierProfileSerializer,
    ResellerProfileSerializer,
    StaffProfileSerializer,
    AdminSupplierProfileSerializer,
    AdminResellerProfileSerializer,
    AdminStaffProfileSerializer,
)


class BaseOwnProfileViewSet(viewsets.ModelViewSet):
    """
    Base class for 'my profile' behavior:
    - Only authenticated users
    - List returns the current user's profile as a single object (not array)
    - Retrieve/update/destroy limited to current user's profile
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Child classes must implement `get_profile_queryset_for_user`.
        base_qs = self.get_profile_queryset_for_user(self.request.user)
        return base_qs

    def get_profile_queryset_for_user(self, user):
        raise NotImplementedError

    def perform_create(self, serializer):
        # Child classes should pass in the correct `user` instance.
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """
        Override list to return a single object instead of an array.
        Returns the current user's profile or 404 if not found.
        Also handles PUT/PATCH requests on the list endpoint.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get the first (and should be only) profile for the user
        profile = queryset.first()
        
        if profile is None:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Handle PUT/PATCH on list endpoint
        if request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = self.get_serializer(profile, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        
        # Handle GET (list)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    


class SupplierProfileViewSet(BaseOwnProfileViewSet):
    """
    CRUD for the authenticated supplier's own profile.
    """

    serializer_class = SupplierProfileSerializer

    def get_profile_queryset_for_user(self, user):
        if not user.is_authenticated or user.role != UserRole.SUPPLIER:
            return SupplierProfile.objects.none()
        return SupplierProfile.objects.filter(user=user)


class ResellerProfileViewSet(BaseOwnProfileViewSet):
    """
    CRUD for the authenticated reseller's own profile.
    """

    serializer_class = ResellerProfileSerializer

    def get_profile_queryset_for_user(self, user):
        if not user.is_authenticated or user.role != UserRole.RESELLER:
            return ResellerProfile.objects.none()
        return ResellerProfile.objects.filter(user=user)


class StaffProfileViewSet(BaseOwnProfileViewSet):
    """
    CRUD for the authenticated staff/admin user's own profile.
    """

    serializer_class = StaffProfileSerializer

    def get_profile_queryset_for_user(self, user):
        if not user.is_authenticated or user.role != UserRole.STAFF:
            return StaffProfile.objects.none()
        return StaffProfile.objects.filter(user=user)


# ==================== ADMIN VIEWSETS ====================
# Admin-only viewsets for managing all profiles (CRUD except delete)


class BaseAdminProfileViewSet(viewsets.ModelViewSet):
    """
    Base class for admin profile management:
    - Admin-only access (is_staff required)
    - Full CRUD except delete (destroy disabled)
    - Lists all profiles, not just current user's
    - Supports auto-creating user when creating profile
    """

    permission_classes = [permissions.IsAdminUser]

    def get_user_role(self):
        """Override in subclasses to return the appropriate UserRole."""
        raise NotImplementedError("Subclasses must implement get_user_role()")

    def _create_user_if_needed(self, validated_data):
        """Create user if email and password provided and user not set."""
        email = validated_data.pop("email", None)
        password = validated_data.pop("password", None)
        phone_number = validated_data.pop("phone_number", None)
        user = validated_data.get("user")
        
        if not user and email and password:
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    email=email,
                    password=password,
                    role=self.get_user_role(),
                    phone_number=phone_number or "",
                    is_active=True,
                )
                validated_data["user"] = user
        
        return validated_data

    def _update_user_data(self, instance, data):
        """Update user email and phone_number if provided."""
        email = data.pop("email", None)
        phone_number = data.pop("phone_number", None)
        
        if instance.user and (email is not None or phone_number is not None):
            if email is not None and email != instance.user.email:
                if CustomUser.objects.filter(email=email).exclude(pk=instance.user.pk).exists():
                    raise serializers.ValidationError(
                        {"email": ["A user with this email already exists."]}
                    )
                instance.user.email = email
            if phone_number is not None:
                instance.user.phone_number = phone_number
            instance.user.save()

    def create(self, request, *args, **kwargs):
        """Create profile. If user doesn't exist and email/password provided, auto-create user."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data.copy()
        validated_data = self._create_user_if_needed(validated_data)
        
        # Remove user creation fields from serializer's validated_data before saving
        serializer.validated_data.pop("email", None)
        serializer.validated_data.pop("password", None)
        serializer.validated_data.pop("phone_number", None)
        
        # Update serializer's validated_data with the user (if created)
        if "user" in validated_data:
            serializer.validated_data["user"] = validated_data["user"]
        
        profile = serializer.save()
        
        response_serializer = self.get_serializer(profile)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Update profile. Also allows updating user email and phone_number."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data.copy()
        
        self._update_user_data(instance, data)
        
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Disable delete action for profiles.
        Deactivate the associated user instead.
        """
        return Response(
            {
                "error": "Delete is not allowed. Deactivate the associated user account instead."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class AdminSupplierProfileViewSet(BaseAdminProfileViewSet):
    """Admin-only CRUD (except delete) for managing all supplier profiles."""

    queryset = SupplierProfile.objects.select_related("user").order_by("-created_at")
    serializer_class = AdminSupplierProfileSerializer
    filterset_fields = ["status", "user__is_active"]
    search_fields = ["company_name", "contact_person", "user__email", "tax_id"]

    def get_user_role(self):
        return UserRole.SUPPLIER


class AdminResellerProfileViewSet(BaseAdminProfileViewSet):
    """Admin-only CRUD (except delete) for managing all reseller profiles."""

    queryset = ResellerProfile.objects.select_related("user").order_by("-created_at")
    serializer_class = AdminResellerProfileSerializer
    filterset_fields = ["status", "user__is_active"]
    search_fields = [
        "display_name",
        "user__email",
        "referral_code",
        "bank_account_name",
        "bank_account_number",
    ]

    def get_user_role(self):
        return UserRole.RESELLER


class AdminStaffProfileViewSet(BaseAdminProfileViewSet):
    """Admin-only CRUD (except delete) for managing all staff profiles."""

    queryset = StaffProfile.objects.select_related("user").order_by("-created_at")
    serializer_class = AdminStaffProfileSerializer
    filterset_fields = ["department", "user__is_active"]
    search_fields = ["name", "job_title", "department", "user__email"]

    def get_user_role(self):
        return UserRole.STAFF

