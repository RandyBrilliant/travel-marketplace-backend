"""
Health check endpoint for monitoring and load balancers.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Health check endpoint for monitoring and load balancers.
    Returns 200 if healthy, 503 if unhealthy.
    
    Checks:
    - Database connection
    - Cache/Redis connection
    """
    checks = {
        'status': 'healthy',
        'database': 'ok',
        'cache': 'ok',
    }
    status_code = 200
    
    # Check database connection
    try:
        connection.ensure_connection()
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        checks['database'] = 'error'
        checks['status'] = 'unhealthy'
        status_code = 503
    
    # Check cache/Redis connection
    try:
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        if result != 'ok':
            raise Exception("Cache health check failed - value mismatch")
    except Exception as e:
        logger.error(f"Cache health check failed: {e}", exc_info=True)
        checks['cache'] = 'error'
        checks['status'] = 'unhealthy'
        status_code = 503
    
    return JsonResponse(checks, status=status_code)

