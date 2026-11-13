"""
Regression tests for feature-breaking bugs:

- flexible packages could only be booked once per date
- unpaid PENDING bookings held seats forever
- converting a customer to a reseller deleted their bookings
- "today" was the UTC date (payment uploads failed 00:00-07:00 WIB)
- emails greeted users as "None None"
- checklist items were saved as null
- sales reports multiplied revenue by the number of commission rows
"""
import shutil
import tempfile
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from io import BytesIO
from unittest import mock

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from account.models import (
    CustomerProfile,
    CustomUser,
    ResellerProfile,
    SupplierApprovalStatus,
    SupplierProfile,
    UserRole,
)
from itinerary.models import ItineraryBoard, ItineraryCard, ItineraryCardChecklist, ItineraryColumn
from travel.models import (
    Booking,
    BookingStatus,
    Payment,
    SeatSlot,
    SeatSlotStatus,
    TourDate,
    TourPackage,
)

MEDIA_ROOT = tempfile.mkdtemp(prefix="feature-bug-tests-media-")


def png_file(name="proof.png"):
    buf = BytesIO()
    Image.new("RGB", (4, 4), (10, 200, 10)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class FeatureBugTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def make_user(self, email, role, **extra):
        return CustomUser.objects.create_user(
            email=email, password="pass12345", role=role, is_active=True, **extra
        )

    def setUp(self):
        self.api = APIClient()
        self.staff = self.make_user("staff@example.com", UserRole.STAFF, is_staff=True)
        self.supplier = SupplierProfile.objects.create(
            user=self.make_user("supplier@example.com", UserRole.SUPPLIER),
            company_name="Nusantara Tours",
            contact_person="Ayu",
            contact_phone="0811",
            approval_status=SupplierApprovalStatus.APPROVED,
        )
        self.customer = CustomerProfile.objects.create(
            user=self.make_user("customer@example.com", UserRole.CUSTOMER),
            full_name="Budi Santoso",
            contact_phone="0812",
        )
        self.tour = TourPackage.objects.create(
            supplier=self.supplier,
            name="Seoul Spring",
            slug="seoul-spring",
            itinerary="<p>Day 1</p>",
            country="South Korea",
            days=5,
            nights=4,
            max_group_size=20,
            base_price=2_000_000,
            commission=200_000,
            is_active=True,
        )
        self.date = TourDate.objects.create(
            package=self.tour,
            departure_date=timezone.localdate() + timedelta(days=45),
            price=4_000_000,
            total_seats=10,
        )

    def post_booking(self, user, path, payload):
        self.api.force_authenticate(user)
        return self.api.post(path, payload, format="json")

    def customer_booking(self, passengers=2):
        response = self.post_booking(
            self.customer.user,
            "/api/v1/customers/me/bookings/",
            {
                "tour_date": self.date.id,
                "seat_slots": [{"passenger_name": f"P{i}"} for i in range(passengers)],
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        return Booking.objects.latest("id")

    # ---------------------------------------------------------- flexible

    def test_flexible_package_can_be_booked_repeatedly_on_same_date(self):
        TourPackage.objects.filter(pk=self.tour.pk).update(is_flexible=True)
        day = (timezone.localdate() + timedelta(days=30)).isoformat()

        for passengers in (2, 2, 3):
            response = self.post_booking(
                self.customer.user,
                "/api/v1/customers/me/bookings/",
                {
                    "package_id": self.tour.id,
                    "departure_date": day,
                    "seat_slots": [{"passenger_name": f"P{i}"} for i in range(passengers)],
                },
            )
            self.assertEqual(response.status_code, 201, response.data)

        tour_date = TourDate.objects.get(package=self.tour, departure_date=day)
        self.assertEqual(tour_date.seat_slots.filter(status=SeatSlotStatus.BOOKED).count(), 7)
        self.assertEqual(tour_date.total_seats, 7)
        self.assertEqual(Booking.objects.filter(tour_date=tour_date).count(), 3)
        # Server-side price for flexible packages is the package base price.
        self.assertEqual(Booking.objects.latest("id").total_amount, 3 * 2_000_000)

    def test_flexible_booking_with_two_date_rows_on_same_day_does_not_crash(self):
        TourPackage.objects.filter(pk=self.tour.pk).update(is_flexible=True)
        day = timezone.localdate() + timedelta(days=30)
        TourDate.objects.create(package=self.tour, departure_date=day, price=1, total_seats=1, airline="GA")
        TourDate.objects.create(package=self.tour, departure_date=day, price=1, total_seats=1, airline="SQ")
        response = self.post_booking(
            self.customer.user,
            "/api/v1/customers/me/bookings/",
            {
                "package_id": self.tour.id,
                "departure_date": day.isoformat(),
                "seat_slots": [{"passenger_name": "P0"}, {"passenger_name": "P1"}],
            },
        )
        self.assertEqual(response.status_code, 201, response.data)

    # ---------------------------------------------------------- expiry

    def test_unpaid_bookings_expire_and_release_seats(self):
        from travel.tasks import expire_unpaid_bookings

        old_unpaid = self.customer_booking()
        old_paid = self.customer_booking()
        fresh = self.customer_booking()
        Payment.objects.create(
            booking=old_paid, amount=1, transfer_date=timezone.localdate(), proof_image=png_file()
        )
        long_ago = timezone.now() - timedelta(hours=settings.BOOKING_PAYMENT_HOLD_HOURS + 1)
        Booking.objects.filter(pk__in=[old_unpaid.pk, old_paid.pk]).update(created_at=long_ago)
        seat_ids = list(old_unpaid.seat_slots.values_list("id", flat=True))

        expire_unpaid_bookings()

        old_unpaid.refresh_from_db()
        old_paid.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(old_unpaid.status, BookingStatus.CANCELLED)
        self.assertEqual(old_paid.status, BookingStatus.PENDING)
        self.assertEqual(fresh.status, BookingStatus.PENDING)
        for seat in SeatSlot.objects.filter(id__in=seat_ids):
            self.assertEqual(seat.status, SeatSlotStatus.AVAILABLE)
            self.assertEqual(seat.passenger_name, "")

    @override_settings(BOOKING_PAYMENT_HOLD_HOURS=0)
    def test_expiry_can_be_disabled(self):
        from travel.tasks import expire_unpaid_bookings

        booking = self.customer_booking()
        Booking.objects.filter(pk=booking.pk).update(created_at=timezone.now() - timedelta(days=30))
        expire_unpaid_bookings()
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.PENDING)

    # ---------------------------------------------------------- conversion

    def test_converting_customer_with_bookings_keeps_bookings(self):
        booking = self.customer_booking()
        self.api.force_authenticate(self.staff)
        response = self.api.post(
            f"/api/v1/admin/customers/{self.customer.id}/convert-to-reseller/", {}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Booking.objects.filter(pk=booking.pk).exists())
        self.assertEqual(booking.seat_slots.filter(status=SeatSlotStatus.BOOKED).count(), 2)
        user = CustomUser.objects.get(pk=self.customer.user.pk)
        self.assertEqual(user.role, UserRole.RESELLER)
        self.assertTrue(ResellerProfile.objects.filter(user=user).exists())

    def test_converting_customer_without_bookings_removes_customer_profile(self):
        self.api.force_authenticate(self.staff)
        response = self.api.post(
            f"/api/v1/admin/customers/{self.customer.id}/convert-to-reseller/", {}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(CustomerProfile.objects.filter(pk=self.customer.pk).exists())

    # ---------------------------------------------------------- timezone

    def test_payment_dated_local_today_is_accepted_after_local_midnight(self):
        booking = self.customer_booking()
        # 18:30 UTC on 14 Nov is 01:30 WIB on 15 Nov.
        fake_now = datetime(2026, 11, 14, 18, 30, tzinfo=dt_timezone.utc)
        self.api.force_authenticate(self.customer.user)
        with mock.patch("django.utils.timezone.now", return_value=fake_now):
            self.assertEqual(timezone.localdate().isoformat(), "2026-11-15")
            response = self.api.patch(
                f"/api/v1/customers/me/bookings/{booking.id}/payment/",
                {"amount": 1_000_000, "transfer_date": "2026-11-15", "proof_image": png_file()},
                format="multipart",
            )
        self.assertIn(response.status_code, (200, 201), response.data)
        self.assertEqual(booking.payments.count(), 1)

    # ---------------------------------------------------------- names

    def test_get_full_name_uses_profile_name_or_empty(self):
        self.assertEqual(self.customer.user.get_full_name(), "Budi Santoso")
        self.assertEqual(self.supplier.user.get_full_name(), "Nusantara Tours")
        self.assertEqual(self.staff.get_full_name(), "")
        self.assertEqual(self.staff.get_full_name() or self.staff.email, "staff@example.com")

    # ---------------------------------------------------------- checklist

    def test_checklist_items_are_saved(self):
        board = ItineraryBoard.objects.create(supplier=self.supplier, title="Seoul", price=1)
        column = ItineraryColumn.objects.create(board=board, title="Day 1")
        card = ItineraryCard.objects.create(column=column, title="Myeongdong")
        self.api.force_authenticate(self.supplier.user)
        items = [{"id": "a", "text": "Buy T-money"}, {"id": "b", "text": "Exchange cash", "completed": True}]
        response = self.api.post(
            "/api/v1/itinerary/suppliers/me/checklists/",
            {"card": card.id, "title": "Prep", "items": items},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        saved = ItineraryCardChecklist.objects.get().items
        self.assertEqual(saved[0], {"id": "a", "text": "Buy T-money", "completed": False})
        self.assertEqual(saved[1]["completed"], True)

    # ---------------------------------------------------------- reports

    def test_sales_report_counts_each_booking_once(self):
        top = ResellerProfile.objects.create(
            user=self.make_user("top@example.com", UserRole.RESELLER), full_name="Top", referral_code="TOP00001"
        )
        mid = ResellerProfile.objects.create(
            user=self.make_user("mid@example.com", UserRole.RESELLER),
            full_name="Mid",
            referral_code="MID00001",
            sponsor=top,
        )
        seller = ResellerProfile.objects.create(
            user=self.make_user("seller@example.com", UserRole.RESELLER),
            full_name="Seller",
            referral_code="SEL00001",
            sponsor=mid,
        )
        response = self.post_booking(
            seller.user,
            "/api/v1/resellers/me/bookings/",
            {"tour_date": self.date.id, "seat_slots": [{"passenger_name": "A"}, {"passenger_name": "B"}]},
        )
        self.assertEqual(response.status_code, 201, response.data)
        booking = Booking.objects.get()
        self.assertGreater(booking.commissions.count(), 1)

        today = timezone.localdate().isoformat()
        self.api.force_authenticate(self.staff)
        response = self.api.get(f"/api/v1/admin/reports/sales/?start_date={today}&end_date={today}")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["sales"], booking.total_amount)
        self.assertEqual(
            response.data[0]["commission"], sum(c.amount for c in booking.commissions.all())
        )

        self.api.force_authenticate(self.supplier.user)
        response = self.api.get(f"/api/v1/suppliers/me/reports/sales/?start_date={today}&end_date={today}")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[0]["sales"], booking.total_amount)
