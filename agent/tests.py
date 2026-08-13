from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from account.models import (
    CustomUser,
    SupplierApprovalStatus,
    SupplierProfile,
    UserRole,
)
from itinerary.models import ItineraryBoard
from travel.models import TourPackage


def _png():
    return SimpleUploadedFile(
        "cover.png",
        (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01"
            b"\x00\x05\xfe\xd4\xef\x00\x00\x00\x00IEND\xaeB`\x82"
        ),
        content_type="image/png",
    )


class AgentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = CustomUser.objects.create_user(
            email="ops@example.com",
            password="pass12345",
            role=UserRole.STAFF,
            is_staff=True,
            is_active=True,
        )
        self.supplier_user = CustomUser.objects.create_user(
            email="bali@example.com",
            password="pass12345",
            role=UserRole.SUPPLIER,
            is_active=True,
        )
        self.supplier = SupplierProfile.objects.create(
            user=self.supplier_user,
            company_name="Bali Paradise",
            contact_person="Made",
            contact_phone="0811",
            approval_status=SupplierApprovalStatus.APPROVED,
        )
        self.house = SupplierProfile.objects.create(
            user=CustomUser.objects.create_user(
                email="house@example.com",
                password="pass12345",
                role=UserRole.SUPPLIER,
                is_active=True,
            ),
            company_name="GoHoliday Ops",
            contact_person="Ops",
            contact_phone="0812",
            approval_status=SupplierApprovalStatus.APPROVED,
        )

    def test_requires_staff(self):
        response = self.client.get("/api/v1/agent/suppliers/")
        self.assertEqual(response.status_code, 401)

    def test_lookup_suppliers(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/v1/agent/suppliers/?search=Bali")
        self.assertEqual(response.status_code, 200)
        names = [row["company_name"] for row in response.data["results"]]
        self.assertIn("Bali Paradise", names)

    def test_create_tour_is_draft_and_owned(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/agent/tours/",
            {
                "name": "China 5D4N",
                "country": "China",
                "days": 5,
                "nights": 4,
                "base_price": 15000000,
                "itinerary": "<p>Day 1 Beijing</p>",
                "supplier": self.supplier.id,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        tour = TourPackage.objects.get(pk=response.data["id"])
        self.assertFalse(tour.is_active)
        self.assertEqual(tour.supplier_id, self.supplier.id)

    def test_publish_requires_dates_unless_flexible(self):
        self.client.force_authenticate(self.staff)
        created = self.client.post(
            "/api/v1/agent/tours/",
            {
                "name": "No Dates",
                "country": "Japan",
                "days": 3,
                "nights": 2,
                "base_price": 1,
                "itinerary": "x",
                "supplier": self.supplier.id,
            },
            format="json",
        )
        tour_id = created.data["id"]
        denied = self.client.post(
            f"/api/v1/agent/tours/{tour_id}/publish/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)
        self.client.patch(
            f"/api/v1/agent/tours/{tour_id}/",
            {"is_flexible": True},
            format="json",
        )
        ok = self.client.post(
            f"/api/v1/agent/tours/{tour_id}/publish/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(ok.status_code, 200, ok.data)

    def test_create_board_with_display_name(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/agent/boards/",
            {
                "title": "Japan 7D",
                "supplier": self.house.id,
                "supplier_display_name": "Sakura Travel",
                "is_active": True,
                "is_public": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        board = ItineraryBoard.objects.get(pk=response.data["id"])
        self.assertFalse(board.is_active)
        self.assertFalse(board.is_public)
        self.assertEqual(board.effective_supplier_name, "Sakura Travel")

    def test_publish_requires_confirm(self):
        self.client.force_authenticate(self.staff)
        created = self.client.post(
            "/api/v1/agent/tours/",
            {
                "name": "Draft Tour",
                "country": "Japan",
                "days": 3,
                "nights": 2,
                "base_price": 1,
                "itinerary": "x",
                "supplier": self.supplier.id,
                "is_flexible": True,
            },
            format="json",
        )
        tour_id = created.data["id"]
        denied = self.client.post(
            f"/api/v1/agent/tours/{tour_id}/publish/",
            {"confirm": False},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)
        ok = self.client.post(
            f"/api/v1/agent/tours/{tour_id}/publish/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(TourPackage.objects.get(pk=tour_id).is_active)

    @override_settings(HERMES_AGENT_API_KEY="secret-agent")
    def test_agent_key_required_when_configured(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/v1/agent/suppliers/")
        self.assertEqual(response.status_code, 403)
        self.client.credentials(HTTP_X_AGENT_KEY="secret-agent")
        response = self.client.get("/api/v1/agent/suppliers/")
        self.assertEqual(response.status_code, 200)

    def test_nested_board_column_card(self):
        self.client.force_authenticate(self.staff)
        board = self.client.post(
            "/api/v1/agent/boards/",
            {"title": "Board", "supplier": self.supplier.id},
            format="json",
        ).data
        column = self.client.post(
            f"/api/v1/agent/boards/{board['id']}/columns/",
            {"title": "Day 1", "order": 0},
            format="json",
        )
        self.assertEqual(column.status_code, 201, column.data)
        card = self.client.post(
            f"/api/v1/agent/columns/{column.data['id']}/cards/",
            {
                "title": "Forbidden City",
                "location_name": "Forbidden City",
                "location_address": "https://www.google.com/maps/search/?api=1&query=Forbidden+City+Beijing",
            },
            format="json",
        )
        self.assertEqual(card.status_code, 201, card.data)
        cover = self.client.post(
            f"/api/v1/agent/cards/{card.data['id']}/cover/",
            {"cover_image": _png()},
            format="multipart",
        )
        self.assertEqual(cover.status_code, 200, cover.data)

    def test_upload_tour_itinerary_pdf(self):
        self.client.force_authenticate(self.staff)
        created = self.client.post(
            "/api/v1/agent/tours/",
            {
                "name": "PDF Tour",
                "country": "Korea",
                "days": 5,
                "nights": 4,
                "base_price": 1,
                "itinerary": "Day 1 Seoul",
                "supplier": self.supplier.id,
                "is_flexible": True,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        tour_id = created.data["id"]
        pdf = SimpleUploadedFile(
            "korea-itinerary.pdf",
            b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n",
            content_type="application/pdf",
        )
        uploaded = self.client.post(
            f"/api/v1/agent/tours/{tour_id}/itinerary-pdf/",
            {"itinerary_pdf": pdf},
            format="multipart",
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.data)
        tour = TourPackage.objects.get(pk=tour_id)
        self.assertTrue(tour.itinerary_pdf)
        self.assertTrue(tour.itinerary_pdf.name.endswith(".pdf"))
        rejected = self.client.post(
            f"/api/v1/agent/tours/{tour_id}/itinerary-pdf/",
            {"itinerary_pdf": _png()},
            format="multipart",
        )
        self.assertEqual(rejected.status_code, 400)
