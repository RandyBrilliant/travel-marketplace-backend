"""
Regression tests for the critical security fixes:

1. Resellers/customers cannot edit or delete their own bookings.
2. Booking totals are computed server-side.
3. Resellers cannot edit or delete withdrawal requests; balance is enforced.
4. Itinerary buyers cannot activate or edit their own purchase.
5. The public board endpoint returns a teaser, not the paid content.
6. Passenger data is not exposed on the tour endpoint and is wiped on cancel.
7. Only the owning approved supplier can write into a board.
8/9. Rich text is sanitised; uploads are content-checked.
10. Resellers cannot change their own sponsor or base commission.
"""
import shutil
import tempfile
from datetime import timedelta
from io import BytesIO

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
from itinerary.models import (
    ItineraryBoard,
    ItineraryCard,
    ItineraryColumn,
    ItineraryTransaction,
)
from travel.models import (
    Booking,
    BookingStatus,
    PromoCode,
    PromoDiscountType,
    SeatSlot,
    SeatSlotStatus,
    TourDate,
    TourPackage,
    WithdrawalRequest,
)

MEDIA_ROOT = tempfile.mkdtemp(prefix="security-tests-media-")


def attachment(card_id, upload):
    return {"card": card_id, "file": upload, "name": upload.name, "file_type": "file", "file_size": upload.size}


def png_file(name="photo.png"):
    buf = BytesIO()
    Image.new("RGB", (4, 4), (200, 10, 10)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class SecurityLockdownTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    # ------------------------------------------------------------------ setup

    def make_user(self, email, role, **extra):
        return CustomUser.objects.create_user(
            email=email, password="pass12345", role=role, is_active=True, **extra
        )

    def make_supplier(self, email, approved=True):
        return SupplierProfile.objects.create(
            user=self.make_user(email, UserRole.SUPPLIER),
            company_name=email.split("@")[0],
            contact_person="Contact",
            contact_phone="0811",
            approval_status=(
                SupplierApprovalStatus.APPROVED if approved else SupplierApprovalStatus.PENDING
            ),
        )

    def make_reseller(self, email, code, sponsor=None):
        return ResellerProfile.objects.create(
            user=self.make_user(email, UserRole.RESELLER),
            full_name=email.split("@")[0],
            referral_code=code,
            sponsor=sponsor,
        )

    def setUp(self):
        self.api = APIClient()
        self.staff = self.make_user("staff@example.com", UserRole.STAFF, is_staff=True)
        self.supplier = self.make_supplier("supplier@example.com")
        self.other_supplier = self.make_supplier("other@example.com")
        self.sponsor = self.make_reseller("sponsor@example.com", "SPONSOR1")
        self.reseller = self.make_reseller("reseller@example.com", "RESELL01", sponsor=self.sponsor)
        self.customer = CustomerProfile.objects.create(
            user=self.make_user("customer@example.com", UserRole.CUSTOMER),
            full_name="Customer",
            contact_phone="0812",
        )

        self.tour = TourPackage.objects.create(
            supplier=self.supplier,
            name="Japan Winter",
            slug="japan-winter",
            itinerary="<p>Day 1</p>",
            country="Japan",
            days=5,
            nights=4,
            max_group_size=20,
            base_price=1_000_000,
            visa_price=500_000,
            tipping_price=200_000,
            commission=300_000,
            is_active=True,
        )
        self.date = TourDate.objects.create(
            package=self.tour,
            departure_date=timezone.now().date() + timedelta(days=60),
            price=3_000_000,
            total_seats=10,
        )

    def book(self, user, path, passengers=2, **extra):
        self.api.force_authenticate(user)
        payload = {
            "tour_date": self.date.id,
            "seat_slots": [
                {"passenger_name": f"Passenger {i}", "visa_required": i == 0}
                for i in range(passengers)
            ],
            **extra,
        }
        return self.api.post(path, payload, format="json")

    # ------------------------------------------------ 1 + 2. bookings

    def test_booking_total_is_computed_server_side(self):
        response = self.book(
            self.reseller.user,
            "/api/v1/resellers/me/bookings/",
            total_amount=1,
            platform_fee=0,
        )
        self.assertEqual(response.status_code, 201, response.data)
        booking = Booking.objects.get()
        # 2 x 3,000,000 + 1 visa x 500,000 + tipping 200,000 once.
        self.assertEqual(booking.total_amount, 6_700_000)
        self.assertEqual(booking.platform_fee, 50_000)

    def test_reseller_cannot_edit_or_delete_booking(self):
        self.assertEqual(self.book(self.reseller.user, "/api/v1/resellers/me/bookings/").status_code, 201)
        booking = Booking.objects.get()
        url = f"/api/v1/resellers/me/bookings/{booking.id}/"
        self.assertEqual(self.api.patch(url, {"status": "CONFIRMED"}, format="json").status_code, 405)
        self.assertEqual(self.api.put(url, {"status": "CONFIRMED"}, format="json").status_code, 405)
        self.assertEqual(self.api.delete(url).status_code, 405)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.PENDING)

    def test_customer_cannot_edit_or_delete_booking(self):
        self.assertEqual(self.book(self.customer.user, "/api/v1/customers/me/bookings/").status_code, 201)
        booking = Booking.objects.get()
        url = f"/api/v1/customers/me/bookings/{booking.id}/"
        self.assertEqual(self.api.patch(url, {"status": "CONFIRMED"}, format="json").status_code, 405)
        self.assertEqual(self.api.delete(url).status_code, 405)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.PENDING)

    def test_cannot_book_inactive_package_or_past_departure(self):
        TourPackage.objects.filter(pk=self.tour.pk).update(is_active=False)
        response = self.book(self.reseller.user, "/api/v1/resellers/me/bookings/")
        self.assertEqual(response.status_code, 400)

        TourPackage.objects.filter(pk=self.tour.pk).update(is_active=True)
        TourDate.objects.filter(pk=self.date.pk).update(
            departure_date=timezone.now().date() - timedelta(days=1)
        )
        response = self.book(self.reseller.user, "/api/v1/resellers/me/bookings/")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Booking.objects.exists())

    def test_booking_with_promo_code_succeeds_and_records_usage(self):
        promo = PromoCode.objects.create(
            code="HEMAT10",
            discount_type=PromoDiscountType.PERCENTAGE,
            discount_value=10,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30),
        )
        response = self.book(
            self.customer.user, "/api/v1/customers/me/bookings/", promo_code="hemat10"
        )
        self.assertEqual(response.status_code, 201, response.data)
        booking = Booking.objects.get()
        self.assertEqual(booking.promo_discount_amount, 670_000)
        self.assertEqual(booking.total_amount, 6_700_000 - 670_000)
        promo.refresh_from_db()
        self.assertEqual(promo.times_used, 1)
        self.assertTrue(promo.usage_records.filter(user=self.customer.user).exists())

    # ------------------------------------------------ 3. withdrawals

    def _give_reseller_confirmed_commission(self):
        self.assertEqual(self.book(self.reseller.user, "/api/v1/resellers/me/bookings/").status_code, 201)
        Booking.objects.update(status=BookingStatus.CONFIRMED)
        return self.reseller.get_available_commission_balance()

    def test_withdrawal_cannot_be_edited_or_deleted(self):
        balance = self._give_reseller_confirmed_commission()
        self.assertGreater(balance, 0)
        self.api.force_authenticate(self.reseller.user)
        response = self.api.post("/api/v1/resellers/me/withdrawals/", {"amount": 1}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        url = f"/api/v1/resellers/me/withdrawals/{WithdrawalRequest.objects.get().id}/"

        self.assertEqual(self.api.patch(url, {"amount": 500_000_000}, format="json").status_code, 405)
        self.assertEqual(self.api.delete(url).status_code, 405)
        self.assertEqual(WithdrawalRequest.objects.get().amount, 1)

    def test_withdrawal_over_balance_is_rejected(self):
        balance = self._give_reseller_confirmed_commission()
        self.api.force_authenticate(self.reseller.user)
        response = self.api.post(
            "/api/v1/resellers/me/withdrawals/", {"amount": balance + 1}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(WithdrawalRequest.objects.exists())

    # ------------------------------------------------ 4 + 5. itinerary boards

    def make_board(self, supplier=None, **extra):
        board = ItineraryBoard.objects.create(
            supplier=supplier or self.supplier,
            title="Tokyo 5D4N",
            price=250_000,
            is_public=True,
            is_active=True,
            **extra,
        )
        column = ItineraryColumn.objects.create(board=board, title="Day 1")
        ItineraryCard.objects.create(column=column, title="Shibuya", description="<p>Secret tips</p>")
        return board

    def test_buyer_cannot_activate_or_edit_itinerary_purchase(self):
        board = self.make_board()
        self.api.force_authenticate(self.customer.user)
        response = self.api.post(
            "/api/v1/customers/me/itinerary-transactions/", {"board": board.id}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        tx_url = f"/api/v1/customers/me/itinerary-transactions/{response.data['id']}/"

        self.assertEqual(self.api.patch(tx_url + "activate/").status_code, 404)
        self.assertEqual(
            self.api.post(tx_url + "extend-access/", {"additional_days": 3650}, format="json").status_code,
            404,
        )
        self.assertEqual(
            self.api.patch(tx_url, {"status": "ACTIVE", "payment_status": "APPROVED"}, format="json").status_code,
            405,
        )
        tx = ItineraryTransaction.objects.get()
        self.assertEqual(tx.status, "PENDING")
        self.assertNotEqual(tx.payment_status, "APPROVED")

        board_response = self.api.get(f"/api/v1/customers/me/itinerary-boards/{board.id}/")
        self.assertEqual(board_response.status_code, 403)

    def test_cannot_buy_private_board(self):
        board = self.make_board()
        ItineraryBoard.objects.filter(pk=board.pk).update(is_public=False)
        self.api.force_authenticate(self.customer.user)
        response = self.api.post(
            "/api/v1/customers/me/itinerary-transactions/", {"board": board.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_public_board_detail_is_a_teaser(self):
        board = self.make_board()
        for url in (
            f"/api/v1/itinerary/public/itinerary-boards/{board.id}/",
            f"/api/v1/itinerary/public/itinerary-boards/slug/{board.slug}/",
            f"/api/v1/itinerary/resellers/me/itinerary-boards/{board.id}/",
        ):
            response = self.api.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("columns", response.data)
            self.assertNotIn("share_token", response.data)
            self.assertEqual(response.data["columns_count"], 1)
            self.assertEqual(response.data["title"], board.title)

        listing = self.api.get("/api/v1/itinerary/public/itinerary-boards/")
        self.assertNotIn("share_token", listing.data["results"][0])

    # ------------------------------------------------ 6. passenger data

    def test_tour_endpoint_hides_passenger_details_from_other_users(self):
        self.assertEqual(self.book(self.reseller.user, "/api/v1/resellers/me/bookings/").status_code, 201)
        other = self.make_reseller("nosy@example.com", "NOSY0001")
        self.api.force_authenticate(other.user)
        response = self.api.get(f"/api/v1/tours/{self.tour.slug}/")
        self.assertEqual(response.status_code, 200)
        slots = [s for d in response.data["dates"] for s in d["seat_slots"]]
        self.assertTrue(any(s["status"] == SeatSlotStatus.BOOKED for s in slots))
        for slot in slots:
            for key in ("passenger_name", "passport", "passport_url", "special_requests", "booking_number"):
                self.assertNotIn(key, slot)

    def test_owner_supplier_and_staff_still_see_passengers(self):
        self.assertEqual(self.book(self.reseller.user, "/api/v1/resellers/me/bookings/").status_code, 201)
        self.api.force_authenticate(self.supplier.user)
        response = self.api.get(f"/api/v1/suppliers/me/tours/{self.tour.id}/")
        self.assertEqual(response.status_code, 200)
        names = {s.get("passenger_name") for d in response.data["dates"] for s in d["seat_slots"]}
        self.assertIn("Passenger 0", names)

        self.api.force_authenticate(self.staff)
        response = self.api.get(f"/api/v1/tours/{self.tour.slug}/")
        names = {s.get("passenger_name") for d in response.data["dates"] for s in d["seat_slots"]}
        self.assertIn("Passenger 0", names)

    def test_admin_cancel_wipes_passenger_details(self):
        self.assertEqual(self.book(self.reseller.user, "/api/v1/resellers/me/bookings/").status_code, 201)
        booking = Booking.objects.get()
        seat_ids = list(booking.seat_slots.values_list("id", flat=True))
        self.api.force_authenticate(self.staff)
        response = self.api.post(f"/api/v1/admin/bookings/{booking.id}/cancel/")
        self.assertEqual(response.status_code, 200, response.data)
        for seat in SeatSlot.objects.filter(id__in=seat_ids):
            self.assertEqual(seat.status, SeatSlotStatus.AVAILABLE)
            self.assertIsNone(seat.booking_id)
            self.assertEqual(seat.passenger_name, "")
            self.assertFalse(seat.passport)
            self.assertFalse(seat.visa_required)

    # ------------------------------------------------ 7. board write access

    def test_non_owner_cannot_write_into_board(self):
        board = self.make_board()
        column = board.columns.get()
        card = column.cards.get()

        # A customer (no supplier profile at all).
        self.api.force_authenticate(self.customer.user)
        self.assertEqual(
            self.api.post("/api/v1/itinerary/suppliers/me/columns/", {"board": board.id, "title": "x"}, format="json").status_code,
            403,
        )

        # Another approved supplier.
        self.api.force_authenticate(self.other_supplier.user)
        base = "/api/v1/itinerary/suppliers/me"
        self.assertEqual(
            self.api.post(f"{base}/columns/", {"board": board.id, "title": "x"}, format="json").status_code, 403
        )
        self.assertEqual(
            self.api.post(f"{base}/cards/", {"column": column.id, "title": "x"}, format="json").status_code, 403
        )
        self.assertEqual(
            self.api.post(f"{base}/checklists/", {"card": card.id, "title": "x", "items": []}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.api.post(f"{base}/attachments/", attachment(card.id, png_file()), format="multipart").status_code,
            403,
        )
        self.assertEqual(board.columns.count(), 1)
        self.assertEqual(column.cards.count(), 1)

        # The other supplier cannot move their own card into this board either.
        own_board = self.make_board(supplier=self.other_supplier)
        own_card = own_board.columns.get().cards.get()
        response = self.api.patch(f"{base}/cards/{own_card.id}/", {"column": column.id}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_owner_can_write_and_authorship_is_forced(self):
        board = self.make_board()
        column = board.columns.get()
        self.api.force_authenticate(self.supplier.user)
        response = self.api.post(
            "/api/v1/itinerary/suppliers/me/cards/",
            {"column": column.id, "title": "New", "created_by": self.staff.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ItineraryCard.objects.get(title="New").created_by, self.supplier.user)

    def test_pending_supplier_cannot_create_boards(self):
        pending = self.make_supplier("pending@example.com", approved=False)
        self.api.force_authenticate(pending.user)
        response = self.api.post(
            "/api/v1/itinerary/suppliers/me/boards/",
            {"title": "Spam", "price": 1, "is_public": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    # ------------------------------------------------ 8 + 9. content & uploads

    def test_rich_text_is_sanitised_on_write(self):
        self.api.force_authenticate(self.supplier.user)
        response = self.api.patch(
            f"/api/v1/suppliers/me/tours/{self.tour.id}/",
            {
                "itinerary": '<p>Day 1<img src="x" onerror="alert(1)"><script>alert(2)</script></p>',
                "important_notes": '<a href="javascript:alert(3)">click</a>',
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.tour.refresh_from_db()
        self.assertNotIn("onerror", self.tour.itinerary)
        self.assertNotIn("<script", self.tour.itinerary)
        self.assertIn("Day 1", self.tour.itinerary)
        self.assertNotIn("javascript:", self.tour.important_notes)

        board = self.make_board()
        card = board.columns.get().cards.get()
        response = self.api.patch(
            f"/api/v1/itinerary/suppliers/me/cards/{card.id}/",
            {"description": '<p onclick="steal()">Hi</p>'},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        card.refresh_from_db()
        self.assertNotIn("onclick", card.description)

    def test_media_upload_rejects_non_images_and_ignores_client_extension(self):
        self.api.force_authenticate(self.customer.user)
        html = SimpleUploadedFile("evil.html", b"<script>alert(1)</script>", content_type="image/png")
        response = self.api.post("/api/v1/media/upload/", {"file": html}, format="multipart")
        self.assertEqual(response.status_code, 400)

        svg = SimpleUploadedFile(
            "evil.svg", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>', content_type="image/svg+xml"
        )
        response = self.api.post("/api/v1/media/upload/", {"file": svg}, format="multipart")
        self.assertEqual(response.status_code, 400)

        response = self.api.post(
            "/api/v1/media/upload/", {"file": png_file("looks-like.html")}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["filename"].endswith(".png"))

    def test_itinerary_pdf_and_attachments_are_type_checked(self):
        self.api.force_authenticate(self.supplier.user)
        fake_pdf = SimpleUploadedFile("itinerary.pdf", b"<html>not a pdf</html>", content_type="application/pdf")
        response = self.api.patch(
            f"/api/v1/suppliers/me/tours/{self.tour.id}/", {"itinerary_pdf": fake_pdf}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)

        board = self.make_board()
        card = board.columns.get().cards.get()
        html = SimpleUploadedFile("notes.html", b"<script>alert(1)</script>", content_type="text/plain")
        response = self.api.post(
            "/api/v1/itinerary/suppliers/me/attachments/", attachment(card.id, html), format="multipart"
        )
        self.assertEqual(response.status_code, 400)

        response = self.api.post(
            "/api/v1/itinerary/suppliers/me/attachments/", attachment(card.id, png_file()), format="multipart"
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_passport_files_get_random_names(self):
        self.api.force_authenticate(self.customer.user)
        import json

        response = self.api.post(
            "/api/v1/customers/me/bookings/",
            {
                "tour_date": self.date.id,
                "seat_slots": json.dumps([{"passenger_name": "Budi"}]),
                "passport_0": png_file("budi-passport.png"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        seat = SeatSlot.objects.get(passenger_name="Budi")
        self.assertTrue(seat.passport.name.startswith("passports/"))
        self.assertNotIn("budi", seat.passport.name)

    # ------------------------------------------------ 10. sponsor

    def test_reseller_cannot_change_own_sponsor_or_base_commission(self):
        original_base = self.reseller.base_commission
        self.make_reseller("rival@example.com", "RIVAL001")
        self.api.force_authenticate(self.reseller.user)
        response = self.api.patch(
            "/api/v1/resellers/me/profile/update_me/",
            {"sponsor": None, "sponsor_referral_code": "RIVAL001", "base_commission": 999_999, "full_name": "New Name"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.reseller.refresh_from_db()
        self.assertEqual(self.reseller.sponsor_id, self.sponsor.id)
        self.assertEqual(self.reseller.base_commission, original_base)
        self.assertEqual(self.reseller.full_name, "New Name")

    def test_new_reseller_profile_still_joins_via_referral_code(self):
        user = self.make_user("joiner@example.com", UserRole.CUSTOMER)
        self.api.force_authenticate(user)
        response = self.api.post(
            "/api/v1/resellers/me/profile/",
            {"full_name": "Joiner", "sponsor_referral_code": "SPONSOR1", "sponsor": self.reseller.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ResellerProfile.objects.get(user=user).sponsor_id, self.sponsor.id)
