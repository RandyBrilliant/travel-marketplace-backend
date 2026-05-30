"""Tests for email provider configuration."""
import os
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from backend.email import (
    DEFAULT_RESEND_SENDING_DOMAIN,
    MAILGUN_PROVIDER,
    RESEND_PROVIDER,
    SMTP_PROVIDER,
    build_email_settings,
    default_from_email_for_provider,
    is_http_api_backend,
    resolve_email_provider,
    validate_email_configuration,
    validate_resend_from_email,
)


class ResolveEmailProviderTests(SimpleTestCase):
    def test_auto_prefers_resend_when_key_set(self):
        env = {
            "EMAIL_PROVIDER": "auto",
            "RESEND_API_KEY": "re_test",
            "MAILGUN_API_KEY": "mg_test",
            "MAILGUN_DOMAIN": "example.com",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(resolve_email_provider(), RESEND_PROVIDER)

    def test_auto_uses_mailgun_when_only_mailgun_configured(self):
        env = {
            "EMAIL_PROVIDER": "auto",
            "RESEND_API_KEY": "",
            "MAILGUN_API_KEY": "mg_test",
            "MAILGUN_DOMAIN": "example.com",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(resolve_email_provider(), MAILGUN_PROVIDER)

    def test_auto_falls_back_to_smtp_without_api_keys(self):
        with patch.dict(os.environ, {"EMAIL_PROVIDER": "auto"}, clear=True):
            self.assertEqual(resolve_email_provider(), SMTP_PROVIDER)


class BuildEmailSettingsTests(SimpleTestCase):
    def test_resend_backend_when_forced(self):
        env = {
            "EMAIL_PROVIDER": "resend",
            "RESEND_API_KEY": "re_test_key",
            "DEFAULT_FROM_EMAIL": f"noreply@{DEFAULT_RESEND_SENDING_DOMAIN}",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = build_email_settings()
        self.assertEqual(cfg["EMAIL_PROVIDER"], RESEND_PROVIDER)
        self.assertEqual(cfg["EMAIL_BACKEND"], "anymail.backends.resend.EmailBackend")
        self.assertEqual(cfg["ANYMAIL"]["RESEND_API_KEY"], "re_test_key")
        self.assertEqual(cfg["DEFAULT_FROM_EMAIL"], f"noreply@{DEFAULT_RESEND_SENDING_DOMAIN}")

    def test_resend_rejects_wrong_from_domain(self):
        env = {
            "EMAIL_PROVIDER": "resend",
            "RESEND_API_KEY": "re_test_key",
            "DEFAULT_FROM_EMAIL": "noreply@goholiday.id",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                build_email_settings()

    def test_default_from_for_resend_provider(self):
        self.assertEqual(
            default_from_email_for_provider(RESEND_PROVIDER),
            f"noreply@{DEFAULT_RESEND_SENDING_DOMAIN}",
        )

    def test_mailgun_backend_when_forced(self):
        env = {
            "EMAIL_PROVIDER": "mailgun",
            "MAILGUN_API_KEY": "key",
            "MAILGUN_DOMAIN": "goholiday.id",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = build_email_settings()
        self.assertEqual(cfg["EMAIL_BACKEND"], "anymail.backends.mailgun.EmailBackend")
        self.assertEqual(cfg["ANYMAIL"]["MAILGUN_SENDER_DOMAIN"], "goholiday.id")

    def test_resend_requires_api_key_when_forced(self):
        with patch.dict(os.environ, {"EMAIL_PROVIDER": "resend"}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                build_email_settings()


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

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    def test_smtp_is_not_http_api(self):
        self.assertFalse(is_http_api_backend())
