"""
Standardized API response utilities.
"""
from rest_framework.response import Response
from rest_framework import status
from typing import Any, Dict, Optional


class StandardResponse(Response):
    """
    Standardized API response format for consistent API responses.
    
    Usage:
        return StandardResponse(
            data={'tours': [...]},
            message='Tours retrieved successfully',
            meta={'total': 100, 'page': 1}
        )
    """
    
    def __init__(
        self,
        data: Any = None,
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
        meta: Optional[Dict] = None,
        **kwargs
    ):
        """
        Create a standardized API response.
        
        Args:
            data: The response data
            message: Optional success message
            status_code: HTTP status code
            meta: Optional metadata (pagination, timestamps, etc.)
            **kwargs: Additional arguments passed to Response
        """
        response_data = {
            'success': True,
            'data': data,
        }
        
        if message:
            response_data['message'] = message
        
        if meta:
            response_data['meta'] = meta
        
        super().__init__(response_data, status=status_code, **kwargs)


class ErrorResponse(Response):
    """
    Standardized error response format.
    
    Usage:
        return ErrorResponse(
            message='Validation failed',
            errors={'email': ['This field is required']},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    """
    
    def __init__(
        self,
        message: str,
        errors: Optional[Dict] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: Optional[str] = None,
        **kwargs
    ):
        """
        Create a standardized error response.
        
        Args:
            message: Error message
            errors: Optional field-specific errors
            status_code: HTTP status code
            error_code: Optional error code for programmatic handling
            **kwargs: Additional arguments passed to Response
        """
        response_data = {
            'success': False,
            'error': {
                'message': message,
            }
        }
        
        if error_code:
            response_data['error']['code'] = error_code
        
        if errors:
            response_data['error']['errors'] = errors
        
        super().__init__(response_data, status=status_code, **kwargs)

