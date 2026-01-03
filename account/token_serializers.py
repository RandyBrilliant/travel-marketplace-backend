from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings

from account.models import UserRole


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extend the default SimpleJWT serializer to embed extra user info in the JWT token payload.
    
    Token payload includes: full_name, email, role, profile_picture_url
    Response body only includes: access, refresh tokens
    """

    @classmethod
    def _get_profile_info(cls, user):
        """
        Get profile information (full name and photo URL) based on user role.
        Returns tuple: (full_name, photo_url)
        """
        full_name = None
        photo_url = None
        
        try:
            if user.role == UserRole.SUPPLIER and hasattr(user, "supplier_profile"):
                profile = user.supplier_profile
                full_name = profile.company_name
                if profile.photo:
                    photo_url = profile.photo.url
            elif user.role == UserRole.RESELLER and hasattr(user, "reseller_profile"):
                profile = user.reseller_profile
                full_name = profile.full_name
                if profile.photo:
                    photo_url = profile.photo.url
            elif user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
                profile = user.staff_profile
                full_name = profile.full_name
                if profile.photo:
                    photo_url = profile.photo.url
        except Exception:
            # If anything goes wrong, just skip to avoid breaking auth
            pass
        
        return full_name or user.email, photo_url

    @classmethod
    def _build_absolute_url(cls, relative_url, request=None):
        """
        Build absolute URL from relative path.
        If request is provided, uses it. Otherwise tries Site framework or settings.
        """
        if not relative_url:
            return None
        
        if relative_url.startswith('http'):
            return relative_url
        
        # Ensure it starts with /
        if not relative_url.startswith('/'):
            relative_url = '/' + relative_url
        
        # Use request if available (most reliable)
        if request:
            return request.build_absolute_uri(relative_url)
        
        # Try to use Site framework if available
        try:
            # Check if sites app is installed before importing
            if 'django.contrib.sites' in settings.INSTALLED_APPS:
                from django.contrib.sites.models import Site
                current_site = Site.objects.get_current()
                protocol = 'https' if not settings.DEBUG else 'http'
                return f"{protocol}://{current_site.domain}{relative_url}"
            else:
                raise ImportError("django.contrib.sites not in INSTALLED_APPS")
        except (ImportError, RuntimeError, Exception):
            # Fallback if sites framework not installed or other error
            if settings.DEBUG:
                return f"http://localhost:8000{relative_url}"
            # Production fallback - return relative URL or use a default domain
            # You can set a default domain in settings if needed
            default_domain = getattr(settings, 'DEFAULT_DOMAIN', 'localhost:8000')
            protocol = 'https' if not settings.DEBUG else 'http'
            return f"{protocol}://{default_domain}{relative_url}"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Always include email and role in token payload
        token["email"] = user.email
        token["role"] = user.role
        token["email_verified"] = user.email_verified

        # Get full name and profile picture URL
        full_name, photo_url = cls._get_profile_info(user)
        
        token["full_name"] = full_name
        
        if photo_url:
            # Build absolute URL (no request available in get_token, so use fallback)
            absolute_url = cls._build_absolute_url(photo_url)
            if absolute_url:
                token["profile_picture_url"] = absolute_url

        return token

    def validate(self, attrs):
        """
        Return only access and refresh tokens.
        All user info (email, role, full_name, profile_picture_url) is in the token payload.
        """
        data = super().validate(attrs)
        # Return only tokens - user info is in the JWT payload itself
        return data


