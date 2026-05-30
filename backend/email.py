"""
Email provider configuration (Resend, Mailgun, SMTP).

Provider selection via EMAIL_PROVIDER:
  - auto (default): Resend if RESEND_API_KEY is set, else Mailgun HTTP API if
    MAILGUN_API_KEY + MAILGUN_DOMAIN, else SMTP when credentials are present.
  - resend | mailgun | smtp: force a specific backend (fails at startup if misconfigured).

Production migration: deploy with only existing MAILGUN_* vars unchanged; add RESEND_API_KEY
when Resend DNS is ready to switch providers without a code deploy.
"""
from __future__ import annotations

import os
from typing import Any

from django.core.exceptions import ImproperlyConfigured

RESEND_PROVIDER = "resend"
MAILGUN_PROVIDER = "mailgun"
SMTP_PROVIDER = "smtp"
AUTO_PROVIDER = "auto"
VALID_EMAIL_PROVIDERS = frozenset(
    {AUTO_PROVIDER, RESEND_PROVIDER, MAILGUN_PROVIDER, SMTP_PROVIDER}
)

# Verified Resend sending domain (subdomain used for transactional mail)
DEFAULT_RESEND_SENDING_DOMAIN = "notifications.goholiday.id"


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def get_resend_sending_domain() -> str:
    return _env("RESEND_SENDING_DOMAIN", DEFAULT_RESEND_SENDING_DOMAIN)


def default_from_email_for_provider(provider: str) -> str:
    """Suggested DEFAULT_FROM_EMAIL when the env var is not set."""
    if provider == RESEND_PROVIDER:
        return f"noreply@{get_resend_sending_domain()}"
    return "noreply@yourdomain.com"


def validate_resend_from_email(from_email: str, sending_domain: str | None = None) -> None:
    """
    Ensure DEFAULT_FROM_EMAIL uses the verified Resend sending domain.

    Raises ImproperlyConfigured at startup when misconfigured.
    """
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
    """Resolve the active email provider from env (auto-detect or explicit)."""
    requested = _env("EMAIL_PROVIDER", AUTO_PROVIDER).lower()
    if requested not in VALID_EMAIL_PROVIDERS:
        raise ImproperlyConfigured(
            f"Invalid EMAIL_PROVIDER={requested!r}. "
            f"Use one of: {', '.join(sorted(VALID_EMAIL_PROVIDERS))}."
        )

    if requested != AUTO_PROVIDER:
        return requested

    if _env("RESEND_API_KEY"):
        return RESEND_PROVIDER
    if _env("MAILGUN_API_KEY") and _env("MAILGUN_DOMAIN"):
        return MAILGUN_PROVIDER
    return SMTP_PROVIDER


def build_email_settings() -> dict[str, Any]:
    """
    Build Django email settings from environment variables.

    Returns keys: EMAIL_BACKEND, EMAIL_PROVIDER, ANYMAIL (optional),
    RESEND_API_KEY, MAILGUN_API_KEY, MAILGUN_DOMAIN, and SMTP-related settings.
    """
    provider = resolve_email_provider()
    resend_api_key = _env("RESEND_API_KEY")
    mailgun_api_key = _env("MAILGUN_API_KEY")
    mailgun_domain = _env("MAILGUN_DOMAIN")
    resend_signing_secret = _env("RESEND_SIGNING_SECRET")

    resend_sending_domain = get_resend_sending_domain()

    settings: dict[str, Any] = {
        "EMAIL_PROVIDER": provider,
        "RESEND_API_KEY": resend_api_key,
        "RESEND_SENDING_DOMAIN": resend_sending_domain,
        "MAILGUN_API_KEY": mailgun_api_key,
        "MAILGUN_DOMAIN": mailgun_domain,
        "EMAIL_TIMEOUT": int(_env("EMAIL_TIMEOUT", "30")),
    }

    if provider == RESEND_PROVIDER:
        if not resend_api_key:
            raise ImproperlyConfigured(
                "EMAIL_PROVIDER=resend requires RESEND_API_KEY to be set."
            )
        from_email = _env("DEFAULT_FROM_EMAIL") or default_from_email_for_provider(
            RESEND_PROVIDER
        )
        validate_resend_from_email(from_email, resend_sending_domain)
        settings["DEFAULT_FROM_EMAIL"] = from_email
        anymail: dict[str, str] = {"RESEND_API_KEY": resend_api_key}
        if resend_signing_secret:
            anymail["RESEND_SIGNING_SECRET"] = resend_signing_secret
        settings["EMAIL_BACKEND"] = "anymail.backends.resend.EmailBackend"
        settings["ANYMAIL"] = anymail
        return settings

    if provider == MAILGUN_PROVIDER:
        if not mailgun_api_key or not mailgun_domain:
            raise ImproperlyConfigured(
                "EMAIL_PROVIDER=mailgun requires MAILGUN_API_KEY and MAILGUN_DOMAIN."
            )
        settings["EMAIL_BACKEND"] = "anymail.backends.mailgun.EmailBackend"
        settings["ANYMAIL"] = {
            "MAILGUN_API_KEY": mailgun_api_key,
            "MAILGUN_SENDER_DOMAIN": mailgun_domain,
            "MAILGUN_API_URL": _env("MAILGUN_API_URL", "https://api.mailgun.net/v3"),
        }
        return settings

    # SMTP (legacy Mailgun SMTP or generic SMTP)
    settings["EMAIL_BACKEND"] = "django.core.mail.backends.smtp.EmailBackend"
    settings["EMAIL_HOST"] = _env("EMAIL_HOST") or _env("MAILGUN_SMTP_SERVER", "smtp.mailgun.org")
    settings["EMAIL_PORT"] = int(_env("EMAIL_PORT") or _env("MAILGUN_SMTP_PORT", "587"))
    settings["EMAIL_USE_TLS"] = _env("EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes", "on")
    settings["EMAIL_HOST_USER"] = _env("EMAIL_HOST_USER") or _env("MAILGUN_SMTP_LOGIN")
    settings["EMAIL_HOST_PASSWORD"] = _env("EMAIL_HOST_PASSWORD") or _env("MAILGUN_SMTP_PASSWORD")
    return settings


def validate_email_configuration() -> str:
    """
    Validate that the configured email backend can send mail.

    Returns a short description for logging. Raises ValueError when misconfigured.
    """
    from django.conf import settings

    if not settings.DEFAULT_FROM_EMAIL:
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

    if "mailgun" in backend:
        api_key = getattr(settings, "MAILGUN_API_KEY", "") or anymail.get("MAILGUN_API_KEY", "")
        if not api_key:
            raise ValueError("Mailgun API key not configured. Set MAILGUN_API_KEY in .env")
        return "Mailgun HTTP API"

    if "smtp" in backend:
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise ValueError(
                "SMTP credentials not configured. Set MAILGUN_SMTP_LOGIN and "
                "MAILGUN_SMTP_PASSWORD (or EMAIL_HOST_USER / EMAIL_HOST_PASSWORD)."
            )
        return f"SMTP ({settings.EMAIL_HOST})"

    if "console" in backend:
        return "console backend"

    return settings.EMAIL_BACKEND


def is_http_api_backend() -> bool:
    """True when using an Anymail HTTP API backend (Resend or Mailgun)."""
    from django.conf import settings

    return "anymail" in settings.EMAIL_BACKEND.lower()
