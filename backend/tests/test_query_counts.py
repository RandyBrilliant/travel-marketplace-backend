"""
Query-count guards for the busiest public endpoints. Counts must not grow with
the number of departures, seats or tours.
"""
import os
from datetime import timedelta

from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from account.models import (
    CustomerProfile,
    CustomUser,
    ResellerProfile,
    SupplierApprovalStatus,
    SupplierProfile,
    UserRole,
)
from travel.models import Currency, TourDate, TourPackage

REPORT = os.environ.get("QUERY_COUNT_REPORT")


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class QueryCountTests(TestCase):
    def make_user(self, email, role, **extra):
        return CustomUser.objects.create_user(email=email, password="pass12345", role=role, is_active=True, **extra)

    def setUp(self):
        self.api = APIClient()
        self.supplier = SupplierProfile.objects.create(
            user=self.make_user("supplier@example.com", UserRole.SUPPLIER),
            company_name="Nusantara",
            contact_person="Ayu",
            contact_phone="0811",
            approval_status=SupplierApprovalStatus.APPROVED,
        )
        self.staff = self.make_user("staff@example.com", UserRole.STAFF, is_staff=True)
        self.reseller = ResellerProfile.objects.create(
            user=self.make_user("reseller@example.com", UserRole.RESELLER), full_name="R", referral_code="RESELL01"
        )
        self.customer = CustomerProfile.objects.create(
            user=self.make_user("customer@example.com", UserRole.CUSTOMER), full_name="C", contact_phone="0812"
        )
        self.idr = Currency.objects.create(code="IDR", name="Rupiah", symbol="Rp")

    def make_tour(self, slug, dates=0, seats=20):
        tour = TourPackage.objects.create(
            supplier=self.supplier, name=slug, slug=slug, itinerary="<p>x</p>", country="Japan",
            days=5, nights=4, max_group_size=20, base_price=1_000_000, commission=100_000,
            currency=self.idr, is_active=True,
        )
        for i in range(dates):
            TourDate.objects.create(
                package=tour,
                departure_date=timezone.localdate() + timedelta(days=30 + i),
                price=2_000_000,
                total_seats=seats,
            )
        return tour

    def book_each_date(self, tour, passengers=5):
        self.api.force_authenticate(self.customer.user)
        for date in tour.dates.all():
            response = self.api.post(
                "/api/v1/customers/me/bookings/",
                {"tour_date": date.id, "seat_slots": [{"passenger_name": f"P{i}"} for i in range(passengers)]},
                format="json",
            )
            self.assertEqual(response.status_code, 201, response.data)
        self.api.force_authenticate(None)

    def count(self, user, url):
        # Fresh user object each time, as in a real request (no cached profiles).
        if user is not None:
            user = CustomUser.objects.get(pk=user.pk)
        self.api.force_authenticate(user)
        cache.clear()  # measure the uncached path (the list endpoint caches responses)
        with CaptureQueriesContext(connection) as ctx:
            response = self.api.get(url)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        if REPORT:
            print(f"\n{len(ctx.captured_queries):4d} queries  {url}  as {getattr(user, 'email', 'anonymous')}")
            if REPORT == "sql":
                for q in ctx.captured_queries:
                    print("     ", q["sql"][:150])
        return len(ctx.captured_queries)

    def test_tour_detail_query_count_is_flat(self):
        tour = self.make_tour("japan", dates=10)
        self.book_each_date(tour)
        small = self.make_tour("korea", dates=1)
        self.book_each_date(small)

        for user in (None, self.reseller.user, self.staff):
            big = self.count(user, f"/api/v1/tours/{tour.slug}/")
            one = self.count(user, f"/api/v1/tours/{small.slug}/")
            self.assertLessEqual(big, one + 2, f"detail queries grow with departures ({one} -> {big})")
            self.assertLessEqual(big, 20)

    def test_tour_list_query_count_is_flat(self):
        for i in range(3):
            self.make_tour(f"few-{i}")
        few = {u: self.count(u, "/api/v1/tours/") for u in (None, self.reseller.user)}
        for i in range(20):
            self.make_tour(f"many-{i}")
        for user in (None, self.reseller.user):
            many = self.count(user, "/api/v1/tours/")
            self.assertLessEqual(many, few[user] + 2, f"list queries grow with tours ({few[user]} -> {many})")

    def test_booking_lists_query_count_is_flat(self):
        tour = self.make_tour("bookings-tour", dates=12, seats=10)
        from travel.models import Booking, Payment
        self.book_each_date(tour, passengers=2)  # 12 customer bookings
        # One reseller booking too, so reseller lists have rows.
        self.api.force_authenticate(self.reseller.user)
        first_date = tour.dates.first()
        self.api.post(
            "/api/v1/resellers/me/bookings/",
            {"tour_date": first_date.id, "seat_slots": [{"passenger_name": "R1"}]},
            format="json",
        )
        self.api.force_authenticate(None)
        for booking in Booking.objects.all()[:6]:
            Payment.objects.create(booking=booking, amount=1, transfer_date=timezone.localdate())

        cases = [
            (self.customer.user, "/api/v1/customers/me/bookings/"),
            (self.supplier.user, "/api/v1/suppliers/me/bookings/"),
            (self.staff, "/api/v1/admin/bookings/"),
        ]
        for user, url in cases:
            many = self.count(user, url)
            # Keep only one customer booking and measure again.
            self.assertLessEqual(many, 12, f"{url}: {many} queries for ~13 bookings")

    def test_cache_headers_are_public_only_for_anonymous_tour_list(self):
        tour = self.make_tour("headers", dates=1)
        response = self.api.get("/api/v1/tours/")
        self.assertEqual(response["Cache-Control"], "public, max-age=60")
        self.assertIn("Cookie", response["Vary"])

        self.api.cookies["access_token"] = "anything"
        response = self.api.get("/api/v1/tours/")
        self.assertEqual(response["Cache-Control"], "private, no-cache")
        del self.api.cookies["access_token"]

        response = self.api.get(f"/api/v1/tours/{tour.slug}/")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("public", response["Cache-Control"])


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class TourListFilterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()
        supplier = SupplierProfile.objects.create(
            user=CustomUser.objects.create_user(email="s@example.com", password="pass12345", role=UserRole.SUPPLIER, is_active=True),
            company_name="S", contact_person="S", contact_phone="0", approval_status=SupplierApprovalStatus.APPROVED,
        )
        idr = Currency.objects.create(code="IDR", name="Rupiah", symbol="Rp")
        today = timezone.localdate()
        self.month = (today.replace(day=1) + timedelta(days=62)).strftime("%Y-%m")
        in_month = today.replace(day=1) + timedelta(days=62)
        def tour(slug, price, flexible=False, departure=None, country="Japan"):
            t = TourPackage.objects.create(
                supplier=supplier, name=slug, slug=slug, itinerary="x", country=country, days=5, nights=4,
                max_group_size=10, base_price=price, currency=idr, is_active=True, is_flexible=flexible,
            )
            if departure:
                TourDate.objects.create(package=t, departure_date=departure, price=price, total_seats=5)
            return t
        tour("cheap-in-month", 5_000_000, departure=in_month)
        tour("pricey-in-month", 40_000_000, departure=in_month)
        tour("other-month", 10_000_000, departure=in_month + timedelta(days=40))
        tour("flexible", 8_000_000, flexible=True)
        tour("korea", 9_000_000, departure=in_month, country="South Korea")

    def slugs(self, query):
        response = self.api.get(f"/api/v1/tours/?{query}")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        rows = data["results"] if isinstance(data, dict) else data
        return {r["slug"] for r in rows}, data

    def test_filters(self):
        self.assertEqual(self.slugs(f"month={self.month}")[0], {"cheap-in-month", "pricey-in-month", "korea"})
        self.assertEqual(
            self.slugs(f"month={self.month}&include_flexible=true")[0],
            {"cheap-in-month", "pricey-in-month", "korea", "flexible"},
        )
        self.assertEqual(self.slugs("is_flexible=true")[0], {"flexible"})
        self.assertEqual(self.slugs("min_price=6000000&max_price=10000000")[0], {"other-month", "flexible", "korea"})
        self.assertEqual(self.slugs("country=Japan&max_price=9000000")[0], {"cheap-in-month", "flexible"})

    def test_paging_and_ordering(self):
        slugs, data = self.slugs("page=1&page_size=2&ordering=base_price")
        self.assertEqual(data["count"], 5)
        self.assertEqual([r["slug"] for r in data["results"]], ["cheap-in-month", "flexible"])
        _, data = self.slugs("page=3&page_size=2&ordering=base_price")
        self.assertEqual([r["slug"] for r in data["results"]], ["pricey-in-month"])
        _, data = self.slugs("page=1&page_size=500")
        self.assertEqual(data["page_size"], 50)
        # Without page: the plain array, as before.
        _, data = self.slugs("")
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)

    def test_unknown_ordering_and_category_do_not_error(self):
        for query in ("ordering=supplier__bank_account_number", "ordering=-is_featured,-created_at", "category=x"):
            response = self.api.get(f"/api/v1/tours/?{query}")
            self.assertEqual(response.status_code, 200, query)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class DashboardCacheTests(TestCase):
    def test_dashboard_and_reports_are_cached_per_user(self):
        cache.clear()
        api = APIClient()
        staff = CustomUser.objects.create_user(email="st@example.com", password="pass12345", role=UserRole.STAFF, is_staff=True, is_active=True)
        other = CustomUser.objects.create_user(email="st2@example.com", password="pass12345", role=UserRole.STAFF, is_staff=True, is_active=True)
        for url in ("/api/v1/admin/bookings/dashboard-stats/", "/api/v1/admin/reports/sales/"):
            api.force_authenticate(staff)
            with CaptureQueriesContext(connection) as first:
                self.assertEqual(api.get(url).status_code, 200)
            with CaptureQueriesContext(connection) as second:
                self.assertEqual(api.get(url).status_code, 200)
            self.assertLess(len(second.captured_queries), len(first.captured_queries), url)
            # A different user does not get the first user's cached response.
            api.force_authenticate(other)
            with CaptureQueriesContext(connection) as third:
                self.assertEqual(api.get(url).status_code, 200)
            self.assertEqual(len(third.captured_queries), len(first.captured_queries), url)
