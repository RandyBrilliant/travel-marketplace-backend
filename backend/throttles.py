import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginEmailThrottle(SimpleRateThrottle):
    """
    Limits login attempts per target account (by submitted email), so password
    guessing spread across many IPs is still capped. Per-IP limits are applied
    separately with ScopedRateThrottle.
    """

    scope = "auth_login_email"

    def get_cache_key(self, request, view):
        try:
            email = (request.data.get("email") or "").strip().lower()
        except AttributeError:
            return None
        if not email:
            return None
        ident = hashlib.sha256(email.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}
