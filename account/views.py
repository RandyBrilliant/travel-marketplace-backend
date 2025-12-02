from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action

from account.models import (
    CustomUser,
    SupplierProfile,
    ResellerProfile,
    StaffProfile,
    CustomerProfile,
    UserRole,
)
from account.serializers import (
    UserSerializer,
    SupplierProfileSerializer,
    ResellerProfileSerializer,
    StaffProfileSerializer,
    CustomerProfileSerializer,
    UserRegistrationSerializer,
    AdminSupplierProfileSerializer,
    AdminResellerProfileSerializer,
    AdminStaffProfileSerializer,
    AdminCustomerProfileSerializer,
)


class IsAdminUserOrReadOnly(permissions.BasePermission):
    """
    Allow full access to admin users; read-only for others.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class UserViewSet(viewsets.ModelViewSet):
    """
    User management viewset:
    - POST (create/register): Public - anyone can register
    - GET, PUT, PATCH, DELETE: Admin-only - only staff can manage users
    """

    queryset = CustomUser.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer

    def get_serializer_class(self):
        """
        Use UserRegistrationSerializer for registration (POST),
        UserSerializer for all other operations.
        """
        if self.action == "create":
            return UserRegistrationSerializer
        return UserSerializer

    def get_permissions(self):
        """
        Allow public registration (POST), but require admin for other operations.
        """
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def create(self, request, *args, **kwargs):
        """
        Override create to handle registration with profile creation.
        Returns a cleaner response with user data (excluding password).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Return user data without password fields
        user_serializer = UserSerializer(user)
        return Response(
            {
                "message": "User registered successfully.",
                "user": user_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Disable delete action - use deactivate instead.
        """
        return Response(
            {"error": "Delete is not allowed. Use the deactivate endpoint instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def deactivate(self, request, pk=None):
        """
        Deactivate a user account instead of deleting it.
        Admin-only endpoint.
        """
        user = self.get_object()
        user.is_active = False
        user.save()

        serializer = self.get_serializer(user)
        return Response(
            {
                "message": f"User {user.email} has been deactivated successfully.",
                "user": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def activate(self, request, pk=None):
        """
        Activate a previously deactivated user account.
        Admin-only endpoint.
        """
        user = self.get_object()
        user.is_active = True
        user.save()

        serializer = self.get_serializer(user)
        return Response(
            {
                "message": f"User {user.email} has been activated successfully.",
                "user": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class BaseOwnProfileViewSet(viewsets.ModelViewSet):
    """
    Base class for 'my profile' behavior:
    - Only authenticated users
    - List returns only the current user's profile (or empty)
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
    """

    permission_classes = [permissions.IsAdminUser]

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
    """
    Admin-only CRUD (except delete) for managing all supplier profiles.
    """

    queryset = SupplierProfile.objects.select_related("user").order_by("-created_at")
    serializer_class = AdminSupplierProfileSerializer
    filterset_fields = ["status", "user__is_active"]
    search_fields = ["company_name", "contact_person", "user__email", "tax_id"]


class AdminResellerProfileViewSet(BaseAdminProfileViewSet):
    """
    Admin-only CRUD (except delete) for managing all reseller profiles.
    """

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


class AdminStaffProfileViewSet(BaseAdminProfileViewSet):
    """
    Admin-only CRUD (except delete) for managing all staff profiles.
    """

    queryset = StaffProfile.objects.select_related("user").order_by("-created_at")
    serializer_class = AdminStaffProfileSerializer
    filterset_fields = ["department", "user__is_active"]
    search_fields = ["name", "job_title", "department", "user__email"]


class AdminCustomerProfileViewSet(BaseAdminProfileViewSet):
    """
    Admin-only CRUD (except delete) for managing all customer profiles.
    """

    queryset = CustomerProfile.objects.select_related("user").order_by("-created_at")
    serializer_class = AdminCustomerProfileSerializer
    filterset_fields = ["country", "gender", "user__is_active"]
    search_fields = [
        "first_name",
        "last_name",
        "user__email",
        "phone_number",
        "city",
        "country",
    ]

