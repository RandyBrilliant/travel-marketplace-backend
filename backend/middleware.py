"""
Custom middleware for API improvements.
"""
import re
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class ResponseTimeMiddleware(MiddlewareMixin):
    """
    Middleware to add response time header to all API responses.
    """
    
    def process_request(self, request):
        """Store request start time."""
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Add response time header."""
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            response['X-Response-Time'] = f'{duration:.3f}s'
        return response


# Email-verification and password-reset links carry a one-time token in the
# URL path; keep it out of the logs.
_TOKEN_PATH_RE = re.compile(r"(/(?:verify-email|reset-password)/[^/]+/)[^/]+")


def _redact_tokens(path):
    return _TOKEN_PATH_RE.sub(r"\1[redacted]", path)


class APILoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests and responses.
    Logs request method, path, status, response time, and user info.
    """
    
    def process_request(self, request):
        """Store request info for logging."""
        # Only log API requests
        if request.path.startswith('/api/') or request.path.startswith('/health'):
            request._api_log_start = time.time()
            request._api_log_path = _redact_tokens(request.path)
            request._api_log_method = request.method
        return None
    
    def process_response(self, request, response):
        """Log API request/response."""
        if hasattr(request, '_api_log_start'):
            duration = time.time() - request._api_log_start
            
            # Get user info
            user_info = 'anonymous'
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_info = f'{request.user.email} ({request.user.role})'
            
            # Log request
            logger.info(
                f"API Request: {request._api_log_method} {request._api_log_path} | "
                f"Status: {response.status_code} | "
                f"Time: {duration:.3f}s | "
                f"User: {user_info}",
                extra={
                    'method': request._api_log_method,
                    'path': request._api_log_path,
                    'status_code': response.status_code,
                    'response_time': duration,
                    'user': user_info,
                    'query_params': dict(request.GET),
                }
            )
        
        return response


class CacheControlMiddleware(MiddlewareMixin):
    """
    Middleware to add cache control headers to API responses.
    Adds appropriate cache headers based on request type.
    """
    
    # Public tour list (exact paths only; tour detail carries live seat data
    # and sets its own no-store header).
    CACHEABLE_PATHS = [
        '/api/v1/tours/',
        '/api/tours/',
    ]
    
    # Endpoints that should never be cached
    NO_CACHE_PATHS = [
        '/api/v1/token/',
        '/api/token/',
        '/api/v1/change-password/',
        '/api/change-password/',
    ]
    
    @staticmethod
    def _is_personalised(request):
        # JWT auth runs inside DRF views, so request.user is not reliable here;
        # an auth cookie or header means the response may be user-specific.
        return bool(
            request.COOKIES.get('access_token')
            or request.COOKIES.get('refresh_token')
            or request.headers.get('Authorization')
        )

    def process_response(self, request, response):
        """Add cache control headers."""
        path = request.path
        
        # Don't cache error responses
        if response.status_code >= 400:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        
        # Don't cache specific endpoints
        if any(path.startswith(no_cache) for no_cache in self.NO_CACHE_PATHS):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        
        if request.method == 'GET' and path in self.CACHEABLE_PATHS:
            if self._is_personalised(request):
                # Resellers get group-restricted tours and their own commission.
                response['Cache-Control'] = 'private, no-cache'
            else:
                response['Cache-Control'] = 'public, max-age=60'
            response['Vary'] = 'Accept, Accept-Encoding, Cookie, Authorization'
            return response

        # Respect a header the view already set (e.g. tour detail's no-store).
        if response.has_header('Cache-Control'):
            return response
        
        # Default: no cache for other endpoints
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, private'
        
        return response

