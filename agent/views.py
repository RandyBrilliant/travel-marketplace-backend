import logging

from django.conf import settings
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from account.models import SupplierApprovalStatus, SupplierProfile
from itinerary.models import ItineraryBoard, ItineraryCard, ItineraryColumn
from itinerary.serializers import (
    ItineraryBoardDetailSerializer,
    ItineraryCardSerializer,
    ItineraryColumnSerializer,
)
from travel.models import Currency, TourDate, TourImage, TourPackage
from travel.serializers import CurrencySerializer, TourDateSerializer, TourImageSerializer

from .permissions import IsStaffAgent
from .serializers import (
    AgentBoardCreateSerializer,
    AgentBoardListSerializer,
    AgentCardCreateSerializer,
    AgentColumnCreateSerializer,
    AgentPublishSerializer,
    AgentSupplierSerializer,
    AgentTourCreateSerializer,
    AgentTourImageSerializer,
    AgentTourSerializer,
)

logger = logging.getLogger(__name__)


def _log_agent(request, action, **extra):
    logger.info(
        "agent_action user=%s action=%s extra=%s",
        getattr(request.user, "id", None),
        action,
        extra,
    )


def _admin_board_url(board):
    base = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    return f"{base}/admin/itinerary-boards/{board.slug}" if base else ""


class AgentSupplierLookupView(generics.ListAPIView):
    permission_classes = [IsStaffAgent]
    serializer_class = AgentSupplierSerializer

    def get_queryset(self):
        queryset = SupplierProfile.objects.filter(
            approval_status=SupplierApprovalStatus.APPROVED,
            user__is_active=True,
        ).select_related("user")
        query = (self.request.query_params.get("search") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(company_name__icontains=query)
                | Q(contact_person__icontains=query)
                | Q(user__email__icontains=query)
            )
        return queryset.order_by("company_name")


class AgentCurrencyListView(generics.ListAPIView):
    permission_classes = [IsStaffAgent]
    serializer_class = CurrencySerializer
    queryset = Currency.objects.all().order_by("code")


class AgentCountryListView(APIView):
    permission_classes = [IsStaffAgent]

    def get(self, request):
        from travel.countries import CANONICAL_COUNTRIES

        return Response({"results": [{"name": name} for name in CANONICAL_COUNTRIES]})


class AgentTourListCreateView(generics.CreateAPIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = AgentTourCreateSerializer

    def perform_create(self, serializer):
        tour = serializer.save()
        _log_agent(
            self.request,
            "create_tour",
            tour_id=tour.id,
            supplier_id=tour.supplier_id,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        output = AgentTourSerializer(serializer.instance, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class AgentTourDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = TourPackage.objects.select_related(
        "supplier", "supplier__user", "currency"
    ).prefetch_related(
        "images", "dates"
    )
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return AgentTourCreateSerializer
        return AgentTourSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        tour = self.get_object()
        return Response(AgentTourSerializer(tour, context={"request": request}).data)


class AgentTourImageCreateView(APIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        tour = generics.get_object_or_404(TourPackage, pk=pk)
        payload = request.data.copy()
        payload["package"] = tour.id
        serializer = AgentTourImageSerializer(data=payload, context={"request": request})
        serializer.is_valid(raise_exception=True)
        image = serializer.save(package=tour)
        _log_agent(request, "upload_tour_image", tour_id=tour.id, image_id=image.id)
        return Response(
            TourImageSerializer(image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AgentTourImageDetailView(APIView):
    permission_classes = [IsStaffAgent]

    def delete(self, request, pk, image_id):
        tour = generics.get_object_or_404(TourPackage, pk=pk)
        image = generics.get_object_or_404(TourImage, pk=image_id, package=tour)
        confirm_primary = _truthy(
            request.query_params.get("confirm_primary")
            or (request.data.get("confirm_primary") if hasattr(request, "data") else False)
        )
        if image.is_primary and not confirm_primary:
            return Response(
                {
                    "detail": (
                        "This image is the tour cover (is_primary=true). "
                        "Upload/set another cover first, or pass confirm_primary=true."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        was_primary = image.is_primary
        image_pk = image.id
        image.delete()
        if was_primary:
            next_image = tour.images.order_by("order", "id").first()
            if next_image and not next_image.is_primary:
                TourImage.objects.filter(pk=next_image.pk).update(is_primary=True)
        _log_agent(request, "delete_tour_image", tour_id=tour.id, image_id=image_pk)
        remaining = TourImageSerializer(
            tour.images.all(), many=True, context={"request": request}
        ).data
        return Response(
            {
                "deleted": True,
                "image_id": image_pk,
                "tour_id": tour.id,
                "images": remaining,
            }
        )


MAX_ITINERARY_PDF_BYTES = 20 * 1024 * 1024


class AgentTourItineraryPdfView(APIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        tour = generics.get_object_or_404(TourPackage, pk=pk)
        pdf = request.FILES.get("itinerary_pdf") or request.FILES.get("file")
        if not pdf:
            return Response(
                {"itinerary_pdf": ["File PDF itinerary wajib diisi."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (getattr(pdf, "name", "") or "").lower()
        content_type = (getattr(pdf, "content_type", "") or "").split(";")[0].strip().lower()
        header = pdf.read(5)
        pdf.seek(0)
        if not name.endswith(".pdf") or header != b"%PDF-" or (
            content_type and content_type not in {"application/pdf", "application/octet-stream"}
        ):
            return Response(
                {"itinerary_pdf": ["Hanya file PDF yang diterima."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if pdf.size and pdf.size > MAX_ITINERARY_PDF_BYTES:
            return Response(
                {"itinerary_pdf": ["PDF melebihi batas 20MB."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tour.itinerary_pdf = pdf
        tour.save(update_fields=["itinerary_pdf"])
        _log_agent(request, "upload_tour_itinerary_pdf", tour_id=tour.id)
        return Response(AgentTourSerializer(tour, context={"request": request}).data)


def _truthy(value):
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return False


class AgentTourDateCreateView(APIView):
    permission_classes = [IsStaffAgent]

    def post(self, request, pk):
        tour = generics.get_object_or_404(TourPackage, pk=pk)
        serializer = TourDateSerializer(
            data=request.data,
            context={"request": request, "package": tour},
        )
        serializer.is_valid(raise_exception=True)
        tour_date = serializer.save(package=tour)
        _log_agent(request, "add_tour_date", tour_id=tour.id, date_id=tour_date.id)
        return Response(
            TourDateSerializer(tour_date, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AgentTourDateDetailView(APIView):
    permission_classes = [IsStaffAgent]

    def _get_date(self, pk, date_id):
        return generics.get_object_or_404(
            TourDate.objects.select_related("package").prefetch_related("seat_slots"),
            pk=date_id,
            package_id=pk,
        )

    def get(self, request, pk, date_id):
        tour_date = self._get_date(pk, date_id)
        return Response(TourDateSerializer(tour_date, context={"request": request}).data)

    def patch(self, request, pk, date_id):
        tour = generics.get_object_or_404(TourPackage, pk=pk)
        tour_date = self._get_date(pk, date_id)
        payload = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        if _truthy(payload.pop("sold_out", False)):
            payload["total_seats"] = 0
        if not payload:
            return Response(
                {"detail": "Provide at least one field to update (e.g. total_seats or sold_out)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TourDateSerializer(
            tour_date,
            data=payload,
            partial=True,
            context={"request": request, "package": tour},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _log_agent(
            request,
            "update_tour_date",
            tour_id=tour.id,
            date_id=tour_date.id,
            fields=sorted(str(key) for key in payload.keys()),
        )
        updated = TourDate.objects.prefetch_related("seat_slots").get(pk=tour_date.pk)
        return Response(TourDateSerializer(updated, context={"request": request}).data)


class AgentTourPublishView(APIView):
    permission_classes = [IsStaffAgent]

    def post(self, request, pk):
        serializer = AgentPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tour = generics.get_object_or_404(
            TourPackage.objects.prefetch_related("dates"),
            pk=pk,
        )
        if not tour.is_flexible and not tour.dates.exists():
            return Response(
                {
                    "detail": (
                        "Add at least one departure date before publishing, "
                        "or set is_flexible=true for open dates."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        tour.is_active = True
        tour.save(update_fields=["is_active"])
        _log_agent(request, "publish_tour", tour_id=tour.id)
        return Response(AgentTourSerializer(tour, context={"request": request}).data)


class AgentTourUnpublishView(APIView):
    permission_classes = [IsStaffAgent]

    def post(self, request, pk):
        serializer = AgentPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tour = generics.get_object_or_404(TourPackage, pk=pk)
        tour.is_active = False
        tour.save(update_fields=["is_active"])
        _log_agent(request, "unpublish_tour", tour_id=tour.id)
        return Response(AgentTourSerializer(tour, context={"request": request}).data)


class AgentBoardListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AgentBoardCreateSerializer
        return AgentBoardListSerializer

    def get_queryset(self):
        queryset = ItineraryBoard.objects.select_related(
            "supplier", "supplier__user", "currency"
        )
        query = (self.request.query_params.get("search") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(slug__icontains=query)
                | Q(supplier_display_name__icontains=query)
                | Q(supplier__company_name__icontains=query)
            )
        board_status = (self.request.query_params.get("status") or "").strip().lower()
        if board_status == "published":
            queryset = queryset.filter(is_active=True, is_public=True)
        elif board_status == "draft":
            queryset = queryset.filter(Q(is_active=False) | Q(is_public=False))
        is_active = self.request.query_params.get("is_active")
        if is_active is not None and str(is_active).strip() != "":
            queryset = queryset.filter(
                is_active=str(is_active).strip().lower() in {"1", "true", "yes"}
            )
        return queryset.order_by("-updated_at", "-id")

    def perform_create(self, serializer):
        board = serializer.save()
        _log_agent(
            self.request,
            "create_board",
            board_id=board.id,
            supplier_id=board.supplier_id,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        board = serializer.instance
        data = ItineraryBoardDetailSerializer(board, context={"request": request}).data
        data["admin_url"] = _admin_board_url(board)
        return Response(data, status=status.HTTP_201_CREATED)


class AgentBoardDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = ItineraryBoard.objects.select_related("supplier", "supplier__user").prefetch_related(
        "columns__cards"
    )
    serializer_class = ItineraryBoardDetailSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return AgentBoardCreateSerializer
        return ItineraryBoardDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        board = self.get_object()
        data = self.get_serializer(board).data
        data["admin_url"] = _admin_board_url(board)
        return Response(data)


class AgentBoardPackageImageView(APIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        board = generics.get_object_or_404(ItineraryBoard, pk=pk)
        image = request.FILES.get("package_image") or request.FILES.get("image")
        if not image:
            return Response(
                {"package_image": ["File gambar wajib diisi."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        board.package_image = image
        board.save(update_fields=["package_image"])
        _log_agent(request, "upload_board_image", board_id=board.id)
        data = ItineraryBoardDetailSerializer(board, context={"request": request}).data
        data["admin_url"] = _admin_board_url(board)
        return Response(data)


class AgentBoardColumnCreateView(APIView):
    permission_classes = [IsStaffAgent]

    def post(self, request, pk):
        board = generics.get_object_or_404(ItineraryBoard, pk=pk)
        payload = request.data.copy()
        payload["board"] = board.id
        serializer = AgentColumnCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        column = serializer.save(board=board)
        _log_agent(request, "add_board_column", board_id=board.id, column_id=column.id)
        return Response(
            ItineraryColumnSerializer(column, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AgentBoardPublishView(APIView):
    permission_classes = [IsStaffAgent]

    def post(self, request, pk):
        serializer = AgentPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = generics.get_object_or_404(ItineraryBoard, pk=pk)
        board.is_active = True
        board.is_public = True
        board.save(update_fields=["is_active", "is_public"])
        _log_agent(request, "publish_board", board_id=board.id)
        data = ItineraryBoardDetailSerializer(board, context={"request": request}).data
        data["admin_url"] = _admin_board_url(board)
        return Response(data)


class AgentCardCreateView(APIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        column = generics.get_object_or_404(ItineraryColumn, pk=pk)
        payload = request.data.copy()
        payload["column"] = column.id
        serializer = AgentCardCreateSerializer(data=payload, context={"request": request})
        serializer.is_valid(raise_exception=True)
        card = serializer.save(column=column, created_by=request.user)
        _log_agent(request, "add_board_card", column_id=column.id, card_id=card.id)
        return Response(
            ItineraryCardSerializer(card, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AgentCardDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = ItineraryCard.objects.select_related("column__board")
    serializer_class = ItineraryCardSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return AgentCardCreateSerializer
        return ItineraryCardSerializer


class AgentCardCoverView(APIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        card = generics.get_object_or_404(ItineraryCard, pk=pk)
        image = request.FILES.get("cover_image") or request.FILES.get("image")
        if not image:
            return Response(
                {"cover_image": ["File gambar wajib diisi."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        card.cover_image = image
        card.save(update_fields=["cover_image"])
        _log_agent(request, "upload_card_cover", card_id=card.id)
        return Response(ItineraryCardSerializer(card, context={"request": request}).data)
