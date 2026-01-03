"""
Custom exception handler for consistent error responses and logging.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, AuthenticationFailed, PermissionDenied, NotFound
import logging

logger = logging.getLogger(__name__)


def get_user_friendly_message(exc, status_code, wait_seconds=None):
    """
    Get user-friendly error message based on exception type and status code.
    
    Args:
        exc: The exception that was raised
        status_code: HTTP status code
        wait_seconds: Optional wait time in seconds (for rate limiting)
    """
    # Map common exceptions to user-friendly messages (Indonesian)
    if isinstance(exc, ValidationError):
        return 'Validasi gagal. Silakan periksa masukan Anda.'
    elif isinstance(exc, AuthenticationFailed):
        return 'Autentikasi gagal. Silakan periksa kredensial Anda.'
    elif isinstance(exc, PermissionDenied):
        return 'Anda tidak memiliki izin untuk melakukan tindakan ini.'
    elif isinstance(exc, NotFound):
        return 'The requested resource was not found.'
    elif status_code == 400:
        return 'Permintaan tidak valid. Silakan periksa masukan Anda.'
    elif status_code == 401:
        return 'Autentikasi diperlukan. Silakan login.'
    elif status_code == 403:
        return 'Anda tidak memiliki izin untuk mengakses sumber daya ini.'
    elif status_code == 404:
        return 'Sumber daya yang diminta tidak ditemukan.'
    elif status_code == 405:
        return 'Metode ini tidak diizinkan untuk endpoint ini.'
    elif status_code == 429:
        # Use provided wait_seconds or try to get from exception
        if wait_seconds is None and hasattr(exc, 'wait') and exc.wait:
            wait_seconds = int(exc.wait)
        
        if wait_seconds is not None:
            if wait_seconds < 60:
                return f'Terlalu banyak percobaan login. Silakan coba lagi dalam {wait_seconds} detik.'
            else:
                wait_minutes = wait_seconds // 60
                return f'Terlalu banyak percobaan login. Silakan coba lagi dalam {wait_minutes} menit.'
        return 'Terlalu banyak percobaan login. Akun Anda telah dikunci sementara. Silakan coba lagi dalam beberapa menit.'
    elif status_code >= 500:
        return 'Terjadi kesalahan pada server. Silakan coba lagi nanti.'
    else:
        return 'Terjadi kesalahan saat memproses permintaan Anda.'


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses
    and logs errors appropriately.
    
    Args:
        exc: The exception that was raised
        context: Dictionary containing request, view, and args
        
    Returns:
        Response: Formatted error response
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        status_code = response.status_code
        
        # Extract wait time from throttle exception if available (before generating message)
        wait_seconds = None
        if status_code == 429:
            # DRF throttle exceptions have a 'wait' attribute
            if hasattr(exc, 'wait') and exc.wait:
                wait_seconds = int(exc.wait)
            # Also check response.data (DRF sometimes includes it there)
            elif isinstance(response.data, dict):
                if 'wait' in response.data:
                    wait_seconds = int(response.data['wait'])
        
        user_message = get_user_friendly_message(exc, status_code, wait_seconds)
        
        # Extract field-specific errors if available
        errors = None
        if isinstance(response.data, dict):
            # Handle DRF validation errors
            if 'non_field_errors' in response.data:
                errors = {'general': response.data['non_field_errors']}
            else:
                # Extract field errors
                field_errors = {}
                for key, value in response.data.items():
                    if isinstance(value, list):
                        field_errors[key] = value
                    elif isinstance(value, dict):
                        field_errors[key] = value
                if field_errors:
                    errors = field_errors
        
        # Customize error response format
        custom_response_data = {
            'success': False,
            'error': {
                'status_code': status_code,
                'message': user_message,
                'details': response.data if response.data else None
            }
        }
        
        # Add throttle wait time for rate limiting errors
        if status_code == 429 and wait_seconds is not None:
            custom_response_data['error']['wait_seconds'] = wait_seconds
        
        # Add field-specific errors if available
        if errors:
            custom_response_data['error']['errors'] = errors
        
        response.data = custom_response_data
        
        # Log errors based on severity
        request = context.get('request')
        request_path = request.path if request else None
        request_method = request.method if request else None
        
        if status_code >= 500:
            logger.error(
                f"Server error: {exc}",
                exc_info=True,
                extra={
                    'context': context,
                    'request_path': request_path,
                    'request_method': request_method,
                    'status_code': status_code,
                }
            )
        elif status_code >= 400:
            logger.warning(
                f"Client error: {exc}",
                extra={
                    'context': context,
                    'status_code': status_code,
                    'request_path': request_path,
                    'request_method': request_method,
                    'error_details': str(response.data),
                }
            )
    
    return response

