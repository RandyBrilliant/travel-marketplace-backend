"""Tests for email provider configuration."""
import os
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from backend.email import (
    CONSOLE_PROVIDER,
    DEFAULT_RESEND_SENDING_DOMAIN,
    RESEND_PROVIDER,
    build_email_settings,
    default_from_email_for_provider,
    is_http_api_backend,
    resolve_email_provider,
    validate_email_configuration,
    validate_resend_from_email,
)


class ResolveEmailProviderTests(SimpleTestCase):
    def test_auto_uses_resend_when_key_set(self):
        env = {"EMAIL_PROVIDER": "auto", "RESEND_API_KEY": "re_test", "DEBUG": "0"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(resolve_email_provider(), RESEND_PROVIDER)

    def test_auto_uses_console_in_debug_without_key(self):
        with patch.dict(os.environ, {"EMAIL_PROVIDER": "auto", "DEBUG": "1"}, clear=True):
            self.assertEqual(resolve_email_provider(), CONSOLE_PROVIDER)

    def test_auto_requires_resend_in_production_without_key(self):
        with patch.dict(os.environ, {"EMAIL_PROVIDER": "auto", "DEBUG": "0"}, clear=True):
            self.assertEqual(resolve_email_provider(), RESEND_PROVIDER)


class BuildEmailSettingsTests(SimpleTestCase):
    def test_resend_backend(self):
        env = {
            "EMAIL_PROVIDER": "resend",
            "RESEND_API_KEY": "re_test_key",
            "DEFAULT_FROM_EMAIL": f"noreply@{DEFAULT_RESEND_SENDING_DOMAIN}",
            "DEBUG": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = build_email_settings()
        self.assertEqual(cfg["EMAIL_PROVIDER"], RESEND_PROVIDER)
        self.assertEqual(cfg["EMAIL_BACKEND"], "anymail.backends.resend.EmailBackend")
        self.assertEqual(cfg["ANYMAIL"]["RESEND_API_KEY"], "re_test_key")

    def test_resend_rejects_wrong_from_domain(self):
        env = {
            "EMAIL_PROVIDER": "resend",
            "RESEND_API_KEY": "re_test_key",
            "DEFAULT_FROM_EMAIL": "noreply@goholiday.id",
            "DEBUG": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                build_email_settings()

    def test_console_backend_in_debug(self):
        with patch.dict(
            os.environ,
            {"EMAIL_PROVIDER": "console", "DEBUG": "1"},
            clear=True,
        ):
            cfg = build_email_settings()
        self.assertEqual(cfg["EMAIL_BACKEND"], "django.core.mail.backends.console.EmailBackend")

    def test_resend_requires_api_key_in_production(self):
        with patch.dict(
            os.environ,
            {"EMAIL_PROVIDER": "resend", "DEBUG": "0"},
            clear=True,
        ):
            with self.assertRaises(ImproperlyConfigured):
                build_email_settings()

    def test_default_from_for_resend_provider(self):
        self.assertEqual(
            default_from_email_for_provider(RESEND_PROVIDER),
            f"noreply@{DEFAULT_RESEND_SENDING_DOMAIN}",
        )


class ValidateResendFromEmailTests(SimpleTestCase):
    def test_accepts_notifications_domain(self):
        validate_resend_from_email(
            f"noreply@{DEFAULT_RESEND_SENDING_DOMAIN}",
            DEFAULT_RESEND_SENDING_DOMAIN,
        )

    def test_rejects_root_domain(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_resend_from_email("noreply@goholiday.id", DEFAULT_RESEND_SENDING_DOMAIN)


class ValidateEmailConfigurationTests(SimpleTestCase):
    @override_settings(
        DEFAULT_FROM_EMAIL=f"noreply@{DEFAULT_RESEND_SENDING_DOMAIN}",
        EMAIL_BACKEND="anymail.backends.resend.EmailBackend",
        EMAIL_PROVIDER=RESEND_PROVIDER,
        RESEND_API_KEY="re_test",
        RESEND_SENDING_DOMAIN=DEFAULT_RESEND_SENDING_DOMAIN,
        ANYMAIL={"RESEND_API_KEY": "re_test"},
    )
    def test_validate_resend_ok(self):
        self.assertEqual(
            validate_email_configuration(),
            f"Resend HTTP API ({DEFAULT_RESEND_SENDING_DOMAIN})",
        )

    @override_settings(
        DEFAULT_FROM_EMAIL="noreply@goholiday.id",
        EMAIL_BACKEND="anymail.backends.resend.EmailBackend",
        RESEND_API_KEY="re_test",
        RESEND_SENDING_DOMAIN=DEFAULT_RESEND_SENDING_DOMAIN,
        ANYMAIL={"RESEND_API_KEY": "re_test"},
    )
    def test_validate_resend_wrong_from_domain(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_email_configuration()

    @override_settings(
        DEFAULT_FROM_EMAIL=f"noreply@{DEFAULT_RESEND_SENDING_DOMAIN}",
        EMAIL_BACKEND="anymail.backends.resend.EmailBackend",
        RESEND_API_KEY="",
        ANYMAIL={},
    )
    def test_validate_resend_missing_key(self):
        with self.assertRaises(ValueError):
            validate_email_configuration()


class IsHttpApiBackendTests(SimpleTestCase):
    @override_settings(EMAIL_BACKEND="anymail.backends.resend.EmailBackend")
    def test_resend_is_http_api(self):
        self.assertTrue(is_http_api_backend())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_console_is_not_http_api(self):
        self.assertFalse(is_http_api_backend())
