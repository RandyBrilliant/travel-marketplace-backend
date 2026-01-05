from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils import timezone
from django.conf import settings
from account.tasks import send_email_verification, send_password_reset_email

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
    ChangePasswordSerializer,
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
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get the first (and should be only) profile for the user
        profile = queryset.first()
        
        if profile is None:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Handle GET (list)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_me(self, request, *args, **kwargs):
        """
        Update the current user's profile.
        Supports both PUT (full update) and PATCH (partial update).
        This custom action allows PUT/PATCH on the list endpoint.
        """
        queryset = self.filter_queryset(self.get_queryset())
        profile = queryset.first()
        
        if profile is None:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        partial = request.method == 'PATCH'
        serializer = self.get_serializer(profile, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    


class SupplierProfileViewSet(BaseOwnProfileViewSet):
    """
    CRUD for the authenticated supplier's own profile.
    """

    serializer_class = SupplierProfileSerializer

    def get_profile_queryset_for_user(self, user):
        if not user.is_authenticated or user.role != UserRole.SUPPLIER:
            return SupplierProfile.objects.none()
        return SupplierProfile.objects.select_related('user').filter(user=user)


class ResellerProfileViewSet(BaseOwnProfileViewSet):
    """
    CRUD for the authenticated reseller's own profile.
    """

    serializer_class = ResellerProfileSerializer

    def get_profile_queryset_for_user(self, user):
        if not user.is_authenticated or user.role != UserRole.RESELLER:
            return ResellerProfile.objects.none()
        return ResellerProfile.objects.select_related('user', 'sponsor', 'group_root').filter(user=user)


class StaffProfileViewSet(BaseOwnProfileViewSet):
    """
    CRUD for the authenticated staff/admin user's own profile.
    """

    serializer_class = StaffProfileSerializer

    def get_profile_queryset_for_user(self, user):
        if not user.is_authenticated or user.role != UserRole.STAFF:
            return StaffProfile.objects.none()
        return StaffProfile.objects.select_related('user').filter(user=user)


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
        user = validated_data.get("user")
        
        if not user and email and password:
            with transaction.atomic():
                user_role = self.get_user_role()
                # Staff users need is_staff=True to access admin endpoints
                is_staff = user_role == UserRole.STAFF
                user = CustomUser.objects.create_user(
                    email=email,
                    password=password,
                    role=user_role,
                    is_active=True,
                    is_staff=is_staff,
                )
                validated_data["user"] = user
        elif user:
            # Validate that existing user has the correct role
            expected_role = self.get_user_role()
            if user.role != expected_role:
                raise serializers.ValidationError(
                    {"user": f"User must have role '{expected_role}', but has '{user.role}'."}
                )
        
        return validated_data

    def _update_user_data(self, instance, data):
        """Update user email if provided."""
        email = data.pop("email", None)
        # Note: is_active is handled by a separate activate/deactivate endpoint
        
        if instance.user and email is not None:
            if email != instance.user.email:
                if CustomUser.objects.filter(email=email).exclude(pk=instance.user.pk).exists():
                    raise serializers.ValidationError(
                        {"email": ["A user with this email already exists."]}
                    )
                instance.user.email = email
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
        
        # Update serializer's validated_data with the user (if created)
        if "user" in validated_data:
            serializer.validated_data["user"] = validated_data["user"]
        
        profile = serializer.save()
        
        response_serializer = self.get_serializer(profile)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Update profile. Also allows updating user email."""
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
    filterset_fields = ["user__is_active"]
    search_fields = ["company_name", "contact_person", "user__email"]

    def get_user_role(self):
        return UserRole.SUPPLIER


class AdminResellerProfileViewSet(BaseAdminProfileViewSet):
    """Admin-only CRUD (except delete) for managing all reseller profiles."""

    queryset = ResellerProfile.objects.select_related("user", "sponsor", "group_root").order_by("-created_at")
    serializer_class = AdminResellerProfileSerializer
    filterset_fields = ["user__is_active"]
    search_fields = [
        "full_name",
        "user__email",
        "referral_code",
        "bank_account_name",
        "bank_account_number",
    ]

    def get_user_role(self):
        return UserRole.RESELLER

    @action(detail=True, methods=["get"], url_path="downlines")
    def downlines(self, request, pk=None):
        """
        Get all downlines (direct and indirect) for a reseller.
        Returns paginated list of reseller profiles in the downline tree.
        """
        try:
            reseller = self.get_object()
            
            # Get all downlines using the model method
            downlines_queryset = reseller.all_downlines().select_related("user", "sponsor").order_by("-created_at")
            
            # Apply pagination
            page = self.paginate_queryset(downlines_queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            # If no pagination, return all
            serializer = self.get_serializer(downlines_queryset, many=True)
            return Response(serializer.data)
        except ResellerProfile.DoesNotExist:
            return Response(
                {"detail": "Reseller profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminStaffProfileViewSet(BaseAdminProfileViewSet):
    """Admin-only CRUD (except delete) for managing all staff profiles."""

    queryset = StaffProfile.objects.select_related("user").order_by("-created_at")
    serializer_class = AdminStaffProfileSerializer
    filterset_fields = ["user__is_active"]
    search_fields = ["full_name", "user__email"]

    def get_user_role(self):
        return UserRole.STAFF


# ==================== USER INFO ENDPOINT ====================

class CurrentUserView(APIView):
    """
    API endpoint to get current authenticated user information.
    Used by frontend to get user info since tokens are in httpOnly cookies.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Return current user information."""
        user = request.user
        from account.models import UserRole
        
        # Get profile info based on role
        full_name = user.email
        photo_url = None
        
        try:
            if user.role == UserRole.SUPPLIER and hasattr(user, "supplier_profile"):
                profile = user.supplier_profile
                full_name = profile.company_name
                if profile.photo:
                    photo_url = request.build_absolute_uri(profile.photo.url) if request else profile.photo.url
            elif user.role == UserRole.RESELLER and hasattr(user, "reseller_profile"):
                profile = user.reseller_profile
                full_name = profile.full_name
                if profile.photo:
                    photo_url = request.build_absolute_uri(profile.photo.url) if request else profile.photo.url
            elif user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
                profile = user.staff_profile
                full_name = profile.full_name
                if profile.photo:
                    photo_url = request.build_absolute_uri(profile.photo.url) if request else profile.photo.url
        except Exception:
            pass
        
        return Response({
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'full_name': full_name,
            'profile_picture_url': photo_url,
            'email_verified': user.email_verified,
        })


# ==================== LOGOUT ENDPOINT ====================

class LogoutView(APIView):
    """
    API endpoint to logout user by clearing httpOnly cookies.
    Also blacklists the refresh token if provided.
    """
    permission_classes = [permissions.AllowAny]  # Allow unauthenticated access
    authentication_classes = []  # No authentication required for logout

    def post(self, request):
        """Logout user by clearing authentication cookies."""
        from rest_framework_simplejwt.tokens import RefreshToken
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Try to blacklist the refresh token if available
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info("Refresh token blacklisted successfully")
            except Exception as e:
                # If blacklisting fails, continue with logout anyway
                logger.warning(f"Failed to blacklist token: {e}")
        
        # Create response
        response = Response(
            {'detail': 'Successfully logged out.'},
            status=status.HTTP_200_OK
        )
        
        # Cookie settings - must match EXACTLY how they were set during login
        is_secure = not settings.DEBUG
        
        # For cookie deletion to work, we need to try multiple approaches
        # because browsers can be finicky about cookie deletion
        
        # Method 1: Delete with no domain (works for localhost)
        response.delete_cookie('access_token', path='/', samesite='Lax')
        response.delete_cookie('refresh_token', path='/', samesite='Lax')
        
        # Method 2: Also set to empty with max_age=0 (belt and suspenders)
        response.set_cookie(
            'access_token',
            value='',
            max_age=0,
            path='/',
            httponly=True,
            secure=is_secure,
            samesite='Lax',
        )
        
        response.set_cookie(
            'refresh_token',
            value='',
            max_age=0,
            path='/',
            httponly=True,
            secure=is_secure,
            samesite='Lax',
        )
        
        logger.info(f"Logout cookies cleared (DEBUG={settings.DEBUG}, secure={is_secure})")
        
        return response


# ==================== PASSWORD CHANGE ENDPOINT ====================
# Universal endpoint for all user types to change their password

class ChangePasswordView(APIView):
    """
    API endpoint for authenticated users to change their password.
    Works for all user types (STAFF, SUPPLIER, RESELLER).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Change the authenticated user's password."""
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        # Verify old password
        if not user.check_password(old_password):
            return Response(
                {'old_password': ['Current password is incorrect.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        try:
            user.set_password(new_password)
            user.save()
            return Response(
                {'detail': 'Password has been successfully changed.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'detail': f'An error occurred while changing password: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==================== EMAIL VERIFICATION ENDPOINTS ====================

class SendEmailVerificationView(APIView):
    """
    API endpoint for admin to send email verification to a user.
    Also allows users to send verification to themselves.
    Works for all user types (STAFF, SUPPLIER, RESELLER).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        """Send email verification email to the specified user."""
        try:
            user = CustomUser.objects.get(pk=user_id)
            
            # Allow users to send verification to themselves, or require admin for others
            if not request.user.is_staff and request.user.id != user_id:
                return Response(
                    {'detail': 'You do not have permission to send verification email to this user.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Send verification email asynchronously
            send_email_verification.delay(user.id)
            
            return Response(
                {'detail': f'Verification email has been sent to {user.email}.'},
                status=status.HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'An error occurred while sending verification email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RequestPasswordResetView(APIView):
    """
    Public API endpoint for users to request password reset by email.
    Works for all user types (STAFF, SUPPLIER, RESELLER).
    No authentication required.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Send password reset email to the user with the provided email."""
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'email': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(email=email.lower().strip())
            
            # Generate password reset token
            from django.utils.encoding import force_bytes
            from django.utils.http import urlsafe_base64_encode
            
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_token = f"{uid}/{token}"
            
            # Send password reset email asynchronously
            send_password_reset_email.delay(user.id, reset_token)
            
            # Always return success message (security: don't reveal if email exists)
            return Response(
                {'detail': 'If an account with that email exists, a password reset email has been sent.'},
                status=status.HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            # Don't reveal if email exists or not (security best practice)
            return Response(
                {'detail': 'If an account with that email exists, a password reset email has been sent.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'detail': f'An error occurred while sending password reset email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResetPasswordView(APIView):
    """
    API endpoint for admin to send password reset email to a user.
    Works for all user types (STAFF, SUPPLIER, RESELLER).
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, user_id):
        """Send password reset email to the specified user."""
        try:
            user = CustomUser.objects.get(pk=user_id)
            
            # Generate password reset token
            from django.utils.encoding import force_bytes
            from django.utils.http import urlsafe_base64_encode
            
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_token = f"{uid}/{token}"
            
            # Send password reset email asynchronously
            send_password_reset_email.delay(user.id, reset_token)
            
            return Response(
                {'detail': f'Password reset email has been sent to {user.email}.'},
                status=status.HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'An error occurred while sending password reset email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResetPasswordConfirmView(APIView):
    """
    API endpoint to reset user password using uid and token from email link.
    No authentication required - uses token-based verification.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        """Reset user password using uid and token."""
        try:
            # Decode user ID from base64
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response(
                {'detail': 'Invalid password reset link.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if token is valid
        if not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'Invalid or expired password reset token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate new password
        new_password = request.data.get('new_password')
        if not new_password:
            return Response(
                {'new_password': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate password using Django's password validators
        try:
            from django.contrib.auth.password_validation import validate_password
            validate_password(new_password, user)
        except Exception as e:
            return Response(
                {'new_password': list(e.messages) if hasattr(e, 'messages') else [str(e)]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset the password
        try:
            user.set_password(new_password)
            user.save()
            
            return Response(
                {
                    'detail': 'Password has been successfully reset. You can now login with your new password.',
                    'email': user.email,
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'detail': f'An error occurred while resetting password: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyEmailView(APIView):
    """
    API endpoint to verify user email using uid and token from email link.
    No authentication required - uses token-based verification.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        """Verify user email using uid and token."""
        try:
            # Decode user ID from base64
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response(
                {'detail': 'Invalid verification link.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if token is valid
        if not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'Invalid or expired verification token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if email is already verified
        if user.email_verified:
            return Response(
                {'detail': 'Email has already been verified.'},
                status=status.HTTP_200_OK
            )

        # Verify the email
        try:
            user.email_verified = True
            user.email_verified_at = timezone.now()
            user.save()
            
            return Response(
                {
                    'detail': 'Email has been successfully verified.',
                    'email': user.email,
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'detail': f'An error occurred while verifying email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==================== ACTIVATE/DEACTIVATE ACCOUNT ENDPOINT ====================

class ActivateDeactivateAccountView(APIView):
    """
    API endpoint for admin to activate or deactivate a user account.
    Works for all user types (STAFF, SUPPLIER, RESELLER).
    Accepts profile_type and profile_id to identify which profile to update.
    """
    from account.authentication import CookieJWTAuthentication
    
    # Only use JWT auth (cookie-based), skip SessionAuth to avoid CSRF requirement
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, profile_type, profile_id):
        """
        Activate or deactivate a user account.
        
        Request body:
        {
            "is_active": true/false
        }
        """
        is_active = request.data.get('is_active')
        
        if is_active is None:
            return Response(
                {'is_active': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(is_active, bool):
            return Response(
                {'is_active': ['This field must be a boolean.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get the profile based on type
            if profile_type == 'staff':
                try:
                    profile = StaffProfile.objects.select_related('user').get(pk=profile_id)
                except StaffProfile.DoesNotExist:
                    return Response(
                        {'detail': 'Staff profile not found.'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            elif profile_type == 'supplier':
                try:
                    profile = SupplierProfile.objects.select_related('user').get(pk=profile_id)
                except SupplierProfile.DoesNotExist:
                    return Response(
                        {'detail': 'Supplier profile not found.'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            elif profile_type == 'reseller':
                try:
                    profile = ResellerProfile.objects.select_related('user').get(pk=profile_id)
                except ResellerProfile.DoesNotExist:
                    return Response(
                        {'detail': 'Reseller profile not found.'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                return Response(
                    {'detail': f'Invalid profile type: {profile_type}. Must be one of: staff, supplier, reseller.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update user's is_active status
            if profile.user:
                profile.user.is_active = is_active
                profile.user.save()
                
                return Response(
                    {
                        'detail': f'Account has been {"activated" if is_active else "deactivated"} successfully.',
                        'is_active': is_active,
                        'user_id': profile.user.id,
                        'profile_id': profile.id,
                        'profile_type': profile_type
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'detail': 'Profile does not have an associated user.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {'detail': f'An error occurred while updating account status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==================== PUBLIC REGISTRATION ENDPOINT ====================

class RegisterResellerView(APIView):
    """
    Public API endpoint for reseller registration.
    Creates a new user with RESELLER role and associated ResellerProfile.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Register a new reseller account.
        
        Request body:
        {
            "email": "user@example.com",
            "password": "securepassword123",
            "full_name": "John Doe",
            "contact_phone": "+6281234567890" (optional),
            "address": "Address" (optional),
            "sponsor_referral_code": "ABC123" (optional)
        }
        """
        from account.serializers import ResellerProfileSerializer
        
        email = request.data.get('email')
        password = request.data.get('password')
        full_name = request.data.get('full_name')
        contact_phone = request.data.get('contact_phone', '')
        address = request.data.get('address', '')
        sponsor_referral_code = request.data.get('sponsor_referral_code', '')

        # Validate required fields
        if not email:
            return Response(
                {'email': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not password:
            return Response(
                {'password': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not full_name:
            return Response(
                {'full_name': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user with this email already exists
        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {'email': ['A user with this email already exists.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate password
        try:
            from django.contrib.auth.password_validation import validate_password
            validate_password(password)
        except Exception as e:
            return Response(
                {'password': list(e.messages) if hasattr(e, 'messages') else [str(e)]},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Create user
                user = CustomUser.objects.create_user(
                    email=email,
                    password=password,
                    role=UserRole.RESELLER,
                    is_active=True,  # Resellers are active by default
                )

                # Handle sponsor referral code if provided
                sponsor = None
                if sponsor_referral_code:
                    try:
                        sponsor = ResellerProfile.objects.get(referral_code=sponsor_referral_code)
                    except ResellerProfile.DoesNotExist:
                        user.delete()  # Clean up user if sponsor code is invalid
                        return Response(
                            {'sponsor_referral_code': [f"Sponsor with referral code '{sponsor_referral_code}' does not exist."]},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # Create reseller profile directly (bypass serializer since user is read-only)
                from account.models import ResellerProfile
                profile = ResellerProfile.objects.create(
                    user=user,
                    full_name=full_name,
                    contact_phone=contact_phone,
                    address=address,
                    sponsor=sponsor,
                )
                
                # Send email verification
                try:
                    send_email_verification.delay(user.id)
                except Exception as e:
                    # Log error but don't fail registration
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send verification email: {str(e)}")

                return Response(
                    {
                        'detail': 'Reseller account created successfully. Please check your email to verify your account.',
                        'user_id': user.id,
                        'email': user.email,
                    },
                    status=status.HTTP_201_CREATED
                )

        except Exception as e:
            return Response(
                {'detail': f'An error occurred during registration: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )