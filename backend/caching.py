import functools
import hashlib

from django.core.cache import cache
from rest_framework.response import Response


def cache_per_user(seconds=60):
    """
    Cache a successful (200) GET response for `seconds`, per user and per full
    query string. For dashboard/report endpoints that run many aggregate
    queries; their numbers may lag by up to `seconds`.

    Works on @api_view functions (apply it directly above `def`, below the
    DRF decorators) and on ViewSet methods / @action handlers.
    """

    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            request = args[0] if hasattr(args[0], "user") else args[1]
            if request.method != "GET" or not request.user.is_authenticated:
                return view(*args, **kwargs)

            path_hash = hashlib.md5(request.get_full_path().encode()).hexdigest()
            key = f"view-cache:{view.__module__}.{view.__qualname__}:{request.user.pk}:{path_hash}"
            cached = cache.get(key)
            if cached is not None:
                return Response(cached)

            response = view(*args, **kwargs)
            if getattr(response, "status_code", None) == 200 and hasattr(response, "data"):
                cache.set(key, response.data, seconds)
            return response

        return wrapped

    return decorator
