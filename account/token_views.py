from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging

from account.token_serializers import CustomTokenObtainPairSerializer

logger = logging.getLogger(__name__)


class LoginThrottle(AnonRateThrottle):
    """Custom throttle for login endpoint - higher rate in development."""
    def get_rate(self):
        # Disable throttling in DEBUG mode, use higher rate in production
        if settings.DEBUG:
            return None  # No throttling in development
        return '100/minute'  # Increased from 20/minute


class RefreshTokenThrottle(AnonRateThrottle):
    """
    Custom throttle for token refresh endpoint.
    Prevents abuse of refresh token endpoint by limiting requests per IP.
    More lenient than login throttle since refreshing is a normal operation.
    """
    def get_rate(self):
        # Disable throttling in DEBUG mode, use higher rate in production
        if settings.DEBUG:
            return None  # No throttling in development
        return '30/minute'  # 30 refreshes per minute per IP


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Token obtain view that sets tokens in httpOnly cookies instead of response body.
    Uses CustomTokenObtainPairSerializer to include role and name in the token payload.
    Includes rate limiting to prevent brute force attacks.
    """

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle] if not settings.DEBUG else []

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Log failed login attempt for security monitoring (mask email for privacy)
            from account.utils import mask_email
            email = request.data.get('email', 'unknown')
            logger.warning(
                f"Failed login attempt",
                extra={
                    'email_masked': mask_email(email),
                    'ip_address': self.get_client_ip(request),
                    'error': str(e),
                }
            )
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get tokens from serializer
        access_token = serializer.validated_data.get('access')
        refresh_token = serializer.validated_data.get('refresh')
        
        # Create response
        response = Response(
            {
                "detail": "Login successful.",
                "user": {
                    "email": serializer.user.email,
                    "role": serializer.user.role,
                }
            },
            status=status.HTTP_200_OK
        )
        
        # Set httpOnly cookies
        is_secure = not settings.DEBUG  # Use Secure flag in production
        max_age_access = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
        max_age_refresh = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
        
        # Don't set domain - let the browser determine it based on the request
        # This works for both localhost (dev) and production domains
        response.set_cookie(
            key='access_token',
            value=access_token,
            max_age=max_age_access,
            httponly=True,
            secure=is_secure,
            samesite='Lax',
            path='/',
        )
        
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            max_age=max_age_refresh,
            httponly=True,
            secure=is_secure,
            samesite='Lax',
            path='/',
        )
        
        # Log successful login
        logger.info(
            f"Successful login",
            extra={
                'email': serializer.user.email,
                'role': serializer.user.role,
                'ip_address': self.get_client_ip(request),
            }
        )
        
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP address from request, handling proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CustomTokenRefreshView(TokenRefreshView):
    """
    Token refresh view that reads refresh token from cookie and sets new tokens in cookies.
    Includes rate limiting to prevent brute force attacks on token refresh endpoint.
    """
    
    throttle_classes = [RefreshTokenThrottle] if not settings.DEBUG else []
    
    def post(self, request, *args, **kwargs):
        # Get refresh token from cookie or request body (for backward compatibility)
        refresh_token = request.COOKIES.get('refresh_token') or request.data.get('refresh')
        
        if not refresh_token:
            # Log missing refresh token
            logger.warning(
                f"Refresh token not provided",
                extra={
                    'ip_address': self.get_client_ip(request),
                }
            )
            return Response(
                {"detail": "Refresh token not provided."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Validate and refresh token
        serializer = self.get_serializer(data={'refresh': refresh_token})
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Log failed token refresh attempt
            logger.warning(
                f"Failed token refresh attempt",
                extra={
                    'ip_address': self.get_client_ip(request),
                    'error': str(e),
                }
            )
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get new tokens
        access_token = serializer.validated_data.get('access')
        new_refresh_token = serializer.validated_data.get('refresh', refresh_token)
        
        # Create response
        response = Response(
            {"detail": "Token refreshed successfully."},
            status=status.HTTP_200_OK
        )
        
        # Set new httpOnly cookies
        is_secure = not settings.DEBUG
        max_age_access = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
        max_age_refresh = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
        
        # Don't set domain - let the browser determine it based on the request
        response.set_cookie(
            key='access_token',
            value=access_token,
            max_age=max_age_access,
            httponly=True,
            secure=is_secure,
            samesite='Lax',
            path='/',
        )
        
        response.set_cookie(
            key='refresh_token',
            value=new_refresh_token,
            max_age=max_age_refresh,
            httponly=True,
            secure=is_secure,
            samesite='Lax',
            path='/',
        )
        
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP address from request, handling proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip



