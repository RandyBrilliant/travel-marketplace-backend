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
from travel.models import TourPackage
from travel.serializers import TourDateSerializer, TourImageSerializer

from .permissions import IsStaffAgent
from .serializers import (
    AgentBoardCreateSerializer,
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
    queryset = TourPackage.objects.select_related("supplier", "supplier__user").prefetch_related(
        "images", "dates"
    )
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return AgentTourCreateSerializer
        return AgentTourSerializer


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


class AgentTourDateCreateView(APIView):
    permission_classes = [IsStaffAgent]

    def post(self, request, pk):
        tour = generics.get_object_or_404(TourPackage, pk=pk)
        serializer = TourDateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        tour_date = serializer.save(package=tour)
        _log_agent(request, "add_tour_date", tour_id=tour.id, date_id=tour_date.id)
        return Response(
            TourDateSerializer(tour_date, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


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


class AgentBoardListCreateView(generics.CreateAPIView):
    permission_classes = [IsStaffAgent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = AgentBoardCreateSerializer

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
