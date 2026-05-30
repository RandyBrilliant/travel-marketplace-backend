"""
Email configuration (Resend).

Requires RESEND_API_KEY in production. When DEBUG=1 and no API key, uses the
console backend so emails print to stdout (local testing).
"""
from __future__ import annotations

import os
from typing import Any

from django.core.exceptions import ImproperlyConfigured

RESEND_PROVIDER = "resend"
CONSOLE_PROVIDER = "console"
AUTO_PROVIDER = "auto"
VALID_EMAIL_PROVIDERS = frozenset({AUTO_PROVIDER, RESEND_PROVIDER, CONSOLE_PROVIDER})

DEFAULT_RESEND_SENDING_DOMAIN = "notifications.goholiday.id"


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _is_debug() -> bool:
    return _env("DEBUG", "0").lower() in ("1", "true", "yes", "on")


def get_resend_sending_domain() -> str:
    return _env("RESEND_SENDING_DOMAIN", DEFAULT_RESEND_SENDING_DOMAIN)


def default_from_email_for_provider(provider: str) -> str:
    if provider == RESEND_PROVIDER:
        return f"noreply@{get_resend_sending_domain()}"
    return "noreply@localhost"


def validate_resend_from_email(from_email: str, sending_domain: str | None = None) -> None:
    """Ensure DEFAULT_FROM_EMAIL uses the verified Resend sending domain."""
    domain = (sending_domain or get_resend_sending_domain()).lower()
    if "@" not in from_email:
        raise ImproperlyConfigured(
            f"DEFAULT_FROM_EMAIL must be a full address on '{domain}' "
            f"(e.g. noreply@{domain})."
        )
    from_domain = from_email.rsplit("@", 1)[-1].strip().lower()
    if from_domain != domain:
        raise ImproperlyConfigured(
            f"DEFAULT_FROM_EMAIL must use your verified Resend domain '{domain}' "
            f"(e.g. noreply@{domain}), got '{from_email}'."
        )


def resolve_email_provider() -> str:
    requested = _env("EMAIL_PROVIDER", AUTO_PROVIDER).lower()
    if requested not in VALID_EMAIL_PROVIDERS:
        raise ImproperlyConfigured(
            f"Invalid EMAIL_PROVIDER={requested!r}. "
            f"Use one of: {', '.join(sorted(VALID_EMAIL_PROVIDERS))}."
        )

    if requested == CONSOLE_PROVIDER:
        return CONSOLE_PROVIDER
    if requested == RESEND_PROVIDER:
        return RESEND_PROVIDER

    # auto
    if _env("RESEND_API_KEY"):
        return RESEND_PROVIDER
    if _is_debug():
        return CONSOLE_PROVIDER
    return RESEND_PROVIDER


def build_email_settings() -> dict[str, Any]:
    """Build Django email settings from environment variables."""
    provider = resolve_email_provider()
    resend_api_key = _env("RESEND_API_KEY")
    resend_sending_domain = get_resend_sending_domain()
    resend_signing_secret = _env("RESEND_SIGNING_SECRET")

    settings: dict[str, Any] = {
        "EMAIL_PROVIDER": provider,
        "RESEND_API_KEY": resend_api_key,
        "RESEND_SENDING_DOMAIN": resend_sending_domain,
        "EMAIL_TIMEOUT": int(_env("EMAIL_TIMEOUT", "30")),
    }

    if provider == CONSOLE_PROVIDER:
        settings["EMAIL_BACKEND"] = "django.core.mail.backends.console.EmailBackend"
        return settings

    if not resend_api_key:
        raise ImproperlyConfigured(
            "RESEND_API_KEY is required. Set it in .env or use EMAIL_PROVIDER=console "
            "with DEBUG=1 for local testing."
        )

    from_email = _env("DEFAULT_FROM_EMAIL") or default_from_email_for_provider(RESEND_PROVIDER)
    validate_resend_from_email(from_email, resend_sending_domain)
    settings["DEFAULT_FROM_EMAIL"] = from_email

    anymail: dict[str, str] = {"RESEND_API_KEY": resend_api_key}
    if resend_signing_secret:
        anymail["RESEND_SIGNING_SECRET"] = resend_signing_secret

    settings["EMAIL_BACKEND"] = "anymail.backends.resend.EmailBackend"
    settings["ANYMAIL"] = anymail
    return settings


def validate_email_configuration() -> str:
    """Validate email backend; returns a short label for logging."""
    from django.conf import settings

    if not settings.DEFAULT_FROM_EMAIL and settings.EMAIL_PROVIDER != CONSOLE_PROVIDER:
        raise ValueError("DEFAULT_FROM_EMAIL is not configured.")

    backend = settings.EMAIL_BACKEND.lower()
    anymail = getattr(settings, "ANYMAIL", {})

    if "resend" in backend:
        api_key = getattr(settings, "RESEND_API_KEY", "") or anymail.get("RESEND_API_KEY", "")
        if not api_key:
            raise ValueError("Resend API key not configured. Set RESEND_API_KEY in .env")
        sending_domain = getattr(settings, "RESEND_SENDING_DOMAIN", get_resend_sending_domain())
        validate_resend_from_email(settings.DEFAULT_FROM_EMAIL, sending_domain)
        return f"Resend HTTP API ({sending_domain})"

    if "console" in backend:
        return "console backend"

    return settings.EMAIL_BACKEND


def is_http_api_backend() -> bool:
    """True when using the Resend HTTP API via Anymail."""
    from django.conf import settings

    return "anymail" in settings.EMAIL_BACKEND.lower()
