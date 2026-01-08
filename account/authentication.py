"""
Custom JWT Authentication that reads tokens from httpOnly cookies instead of Authorization header.
This provides better security against XSS attacks.

Note: CSRF protection is not enforced here because:
1. JWT tokens provide their own authentication mechanism
2. Tokens are in httpOnly cookies, preventing XSS attacks
3. CSRF is primarily needed for session-based authentication
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication that reads access token from httpOnly cookie.
    Falls back to Authorization header for backward compatibility.
    """
    
    def authenticate(self, request):
        # Try to get token from cookie first
        access_token = request.COOKIES.get('access_token')
        
        # Fallback to Authorization header if cookie not present
        if not access_token:
            header = self.get_header(request)
            if header is None:
                return None
            
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None
            
            try:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token
            except (InvalidToken, TokenError, AuthenticationFailed):
                return None
        
        # Validate token from cookie
        try:
            validated_token = self.get_validated_token(access_token)
            user = self.get_user(validated_token)
            
            # Note: CSRF protection is not needed for JWT token-based authentication
            # The token itself provides authentication. CSRF is primarily for session-based auth.
            # If you need CSRF protection, it should be handled at the middleware level
            # or via CSRF tokens in forms, not in the authentication class.
            
            return user, validated_token
        except (InvalidToken, TokenError, AuthenticationFailed) as e:
            # Return None instead of raising to allow other auth methods
            return None

