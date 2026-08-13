import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


class IsStaffAgent(BasePermission):
    """Staff JWT, plus X-Agent-Key when HERMES_AGENT_API_KEY is configured."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_staff):
            return False

        expected = getattr(settings, "HERMES_AGENT_API_KEY", "") or ""
        if not expected:
            return True

        provided = request.headers.get("X-Agent-Key") or ""
        if not provided:
            return False
        return hmac.compare_digest(provided, expected)
