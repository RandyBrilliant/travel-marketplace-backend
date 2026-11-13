import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


class IsStaffAgent(BasePermission):
    """
    Staff JWT plus a matching X-Agent-Key header.

    Without HERMES_AGENT_API_KEY configured the agent API is closed, except in
    DEBUG (local development). A staff password alone is not enough to use it.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_staff):
            return False

        expected = getattr(settings, "HERMES_AGENT_API_KEY", "") or ""
        if not expected:
            return bool(settings.DEBUG)

        provided = request.headers.get("X-Agent-Key") or ""
        if not provided:
            return False
        return hmac.compare_digest(provided, expected)
