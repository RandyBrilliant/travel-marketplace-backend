from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from account.models import (
    CustomUser,
    SupplierProfile,
    ResellerProfile,
    StaffProfile,
    UserRole,
)
from account.serializers import (
    UserSerializer,
    SupplierProfileSerializer,
    ResellerProfileSerializer,
    StaffProfileSerializer,
    UserRegistrationSerializer,
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


