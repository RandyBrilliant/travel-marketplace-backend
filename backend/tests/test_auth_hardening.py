"""
Auth hardening:
- email-verification tokens are not password-reset tokens (and vice versa)
- verification links are single-use; tokens are redacted from request logs
- login / reset / contact endpoints are rate limited, per IP and per account,
  using the real client IP from X-Forwarded-For behind nginx
"""
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from account.models import CustomUser, UserRole
from account.utils import (
    generate_email_verification_token,
    generate_password_reset_token,
)
from backend.middleware import _redact_tokens

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


class TokenSeparationTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = CustomUser.objects.create_user(
            email="victim@example.com", password="Original-pass-123", role=UserRole.CUSTOMER, is_active=True
        )

    def test_verification_token_cannot_reset_password(self):
        uid, token = generate_email_verification_token(self.user)
        response = self.api.post(
            f"/api/v1/reset-password/{uid}/{token}/", {"new_password": "Hijacked-pass-456"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Original-pass-123"))

    def test_reset_token_cannot_verify_email(self):
        uid, token = generate_password_reset_token(self.user)
        response = self.api.post(f"/api/v1/verify-email/{uid}/{token}/")
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_each_token_works_for_its_own_flow_and_verification_is_single_use(self):
        uid, token = generate_email_verification_token(self.user)
        response = self.api.post(f"/api/v1/verify-email/{uid}/{token}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        # Once verified, the same link no longer validates.
        response = self.api.post(f"/api/v1/verify-email/{uid}/{token}/")
        self.assertEqual(response.status_code, 400)

        uid, token = generate_password_reset_token(self.user)
        response = self.api.post(
            f"/api/v1/reset-password/{uid}/{token}/", {"new_password": "Brand-new-pass-789"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brand-new-pass-789"))

    def test_tokens_are_redacted_from_logged_paths(self):
        self.assertEqual(
            _redact_tokens("/api/v1/verify-email/MTI/cx2k1-abcdef0123/"),
            "/api/v1/verify-email/MTI/[redacted]/",
        )
        self.assertEqual(
            _redact_tokens("/api/v1/reset-password/MTI/cx2k1-abcdef0123/"),
            "/api/v1/reset-password/MTI/[redacted]/",
        )
        self.assertEqual(_redact_tokens("/api/v1/tours/bali/"), "/api/v1/tours/bali/")


@override_settings(CACHES=LOCMEM_CACHE)
class ThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()
        CustomUser.objects.create_user(
            email="target@example.com", password="Right-pass-123", role=UserRole.CUSTOMER, is_active=True
        )

    def login(self, email="target@example.com", ip="203.0.113.10", **headers):
        return self.api.post(
            "/api/v1/token/",
            {"email": email, "password": "wrong"},
            format="json",
            REMOTE_ADDR=ip,
            **headers,
        )

    def test_login_is_limited_per_ip(self):
        statuses = [self.login(email=f"user{i}@example.com").status_code for i in range(11)]
        self.assertTrue(all(code == 401 for code in statuses[:10]), statuses)
        self.assertEqual(statuses[10], 429)
        # A different client IP is unaffected.
        self.assertEqual(self.login(email="other@example.com", ip="203.0.113.99").status_code, 401)

    def test_login_is_limited_per_account_across_ips(self):
        statuses = [self.login(ip=f"198.51.100.{i}").status_code for i in range(21)]
        self.assertTrue(all(code == 401 for code in statuses[:20]), statuses)
        self.assertEqual(statuses[20], 429)

    def test_client_ip_comes_from_nginx_forwarded_header(self):
        # Behind nginx every request has the same REMOTE_ADDR; the client IP is
        # the last X-Forwarded-For entry (the one nginx appended).
        for i in range(10):
            self.login(email=f"a{i}@example.com", ip="172.18.0.2", HTTP_X_FORWARDED_FOR="9.9.9.9, 1.1.1.1")
        self.assertEqual(
            self.login(email="a@example.com", ip="172.18.0.2", HTTP_X_FORWARDED_FOR="9.9.9.9, 1.1.1.1").status_code,
            429,
        )
        # Another client behind the same nginx is not throttled, and a spoofed
        # first X-Forwarded-For entry does not change the bucket.
        self.assertEqual(
            self.login(email="b@example.com", ip="172.18.0.2", HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2").status_code,
            401,
        )

    def test_password_reset_requests_are_limited(self):
        codes = [
            self.api.post(
                "/api/v1/request-password-reset/", {"email": "target@example.com"}, format="json", REMOTE_ADDR="203.0.113.5"
            ).status_code
            for _ in range(6)
        ]
        self.assertNotEqual(codes[4], 429, codes)
        self.assertEqual(codes[5], 429, codes)

    def test_contact_form_is_limited(self):
        payload = {"name": "A", "email": "a@example.com", "subject": "general", "message": "Hello there, question."}
        codes = [
            self.api.post("/api/v1/contact/", payload, format="json", REMOTE_ADDR="203.0.113.6").status_code
            for _ in range(11)
        ]
        self.assertNotIn(429, codes[:10], codes)
        self.assertEqual(codes[10], 429, codes)
