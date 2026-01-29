from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import models

from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny, AllowAny
from .models import (
    ItineraryBoard,
    ItineraryColumn,
    ItineraryCard,
    ItineraryCardAttachment,
    ItineraryCardChecklist,
    ItineraryTransaction,
    ItineraryTransactionStatus,
)
from .serializers import (
    ItineraryBoardListSerializer,
    ItineraryBoardDetailSerializer,
    ItineraryBoardCreateUpdateSerializer,
    ItineraryColumnSerializer,
    ItineraryColumnCreateUpdateSerializer,
    ItineraryCardSerializer,
    ItineraryCardCreateUpdateSerializer,
    ItineraryCardAttachmentSerializer,
    ItineraryCardAttachmentCreateUpdateSerializer,
    ItineraryCardChecklistSerializer,
    ItineraryCardChecklistCreateUpdateSerializer,
    ItineraryTransactionSerializer,
    ItineraryTransactionCreateSerializer,
    ItineraryTransactionListSerializer,
    ItineraryTransactionPaymentUpdateSerializer,
)
from account.models import ResellerProfile, CustomerProfile


class IsReseller(permissions.BasePermission):
    """
    Permission check for reseller role.
    Checks if user has reseller profile.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_reseller


class IsSupplier(permissions.BasePermission):
    """
    Permission check for supplier role.
    Checks if user has supplier profile.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_supplier


class SupplierItineraryBoardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage their itinerary boards.
    
    Suppliers can:
    - List their own itinerary boards
    - Create new itinerary boards
    - Retrieve, update, and delete their own itinerary boards
    """
    
    permission_classes = [IsSupplier]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_public", "is_active"]
    search_fields = ["title", "description", "slug"]
    ordering_fields = ["created_at", "updated_at", "title", "price"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """
        Return only itinerary boards belonging to the authenticated supplier.
        
        Optimized with select_related and prefetch_related to avoid N+1 queries.
        """
        if not self.request.user.is_authenticated:
            return ItineraryBoard.objects.none()
        
        try:
            from account.models import SupplierProfile
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return ItineraryBoard.objects.filter(
                supplier=supplier_profile
            ).select_related(
                "supplier", "supplier__user", "currency"
            ).prefetch_related(
                "columns", "columns__cards", "columns__cards__attachments"
            ).all()
        except Exception:
            return ItineraryBoard.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail."""
        if self.action == "list":
            return ItineraryBoardListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return ItineraryBoardCreateUpdateSerializer
        return ItineraryBoardDetailSerializer
    
    def perform_create(self, serializer):
        """Set the supplier when creating an itinerary board."""
        from account.models import SupplierProfile
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            serializer.save(supplier=supplier_profile)
        except SupplierProfile.DoesNotExist:
            raise ValidationError("User must have a supplier profile to create itinerary boards.")


class SupplierItineraryColumnViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage columns within their boards.
    Suppliers can only manage columns for their own boards.
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['board']
    ordering_fields = ['order', 'created_at']
    ordering = ['order', 'id']
    serializer_class = ItineraryColumnCreateUpdateSerializer
    
    def get_queryset(self):
        """Only return columns for boards belonging to the current supplier."""
        from account.models import SupplierProfile
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            queryset = ItineraryColumn.objects.filter(
                board__supplier=supplier_profile
            ).select_related('board').prefetch_related(
                'cards',
                'cards__attachments',
                'cards__checklists',
            )
            
            # Filter by board if provided
            board_id = self.request.query_params.get('board')
            if board_id:
                queryset = queryset.filter(board_id=board_id)
            
            return queryset
        except SupplierProfile.DoesNotExist:
            return ItineraryColumn.objects.none()
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryColumnCreateUpdateSerializer
        return ItineraryColumnSerializer


class SupplierItineraryCardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage cards within their boards.
    Suppliers can only manage cards for columns in their own boards.
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['column', 'date']
    search_fields = ['title', 'description', 'location_name']
    ordering_fields = ['order', 'date', 'start_time', 'created_at']
    ordering = ['order', 'id']
    
    def get_queryset(self):
        """Only return cards for boards belonging to the current supplier."""
        from account.models import SupplierProfile
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            queryset = ItineraryCard.objects.filter(
                column__board__supplier=supplier_profile
            ).select_related(
                'column',
                'column__board',
                'created_by'
            ).prefetch_related(
                'attachments',
                'checklists',
            )
            
            # Filter by column if provided
            column_id = self.request.query_params.get('column')
            if column_id:
                queryset = queryset.filter(column_id=column_id)
            
            return queryset
        except SupplierProfile.DoesNotExist:
            return ItineraryCard.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for list/detail vs create/update."""
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryCardCreateUpdateSerializer
        return ItineraryCardSerializer
    
    def perform_create(self, serializer):
        """Set created_by to current user if not provided."""
        if 'created_by' not in serializer.validated_data:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()


class SupplierItineraryCardAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage card attachments.
    Suppliers can only manage attachments for cards in their own boards.
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['card']
    ordering_fields = ['created_at']
    ordering = ['created_at']
    
    def get_queryset(self):
        """Only return attachments for cards in boards belonging to the current supplier."""
        from account.models import SupplierProfile
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return ItineraryCardAttachment.objects.filter(
                card__column__board__supplier=supplier_profile
            ).select_related('card')
        except SupplierProfile.DoesNotExist:
            return ItineraryCardAttachment.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for list/detail vs create/update."""
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryCardAttachmentCreateUpdateSerializer
        return ItineraryCardAttachmentSerializer


class SupplierItineraryCardChecklistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to manage card checklists.
    Suppliers can only manage checklists for cards in their own boards.
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['card']
    ordering_fields = ['order', 'created_at']
    ordering = ['order', 'id']
    
    def get_queryset(self):
        """Only return checklists for cards in boards belonging to the current supplier."""
        from account.models import SupplierProfile
        try:
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return ItineraryCardChecklist.objects.filter(
                card__column__board__supplier=supplier_profile
            ).select_related('card')
        except SupplierProfile.DoesNotExist:
            return ItineraryCardChecklist.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for list/detail vs create/update."""
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryCardChecklistCreateUpdateSerializer
        return ItineraryCardChecklistSerializer


class AdminItineraryBoardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to view and manage itinerary boards.
    Admin can view, edit all boards but cannot create/delete them.
    Suppliers create and manage their own boards.
    """
    
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_public", "is_active", "supplier"]
    search_fields = ["title", "description", "slug", "supplier__company_name"]
    ordering_fields = ["created_at", "updated_at", "title", "price"]
    ordering = ["-created_at"]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Return all boards with optimized queries."""
        queryset = ItineraryBoard.objects.select_related(
            'supplier', 'supplier__user', 'currency'
        ).prefetch_related(
            'columns',
            'columns__cards',
            'columns__cards__attachments',
            'columns__cards__checklists',
        ).all()
        
        # Filter by supplier
        supplier_id = self.request.query_params.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filter by is_active
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by is_public
        is_public = self.request.query_params.get('is_public')
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == 'true')
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail/update."""
        if self.action == 'list':
            return ItineraryBoardListSerializer
        elif self.action in ['update', 'partial_update']:
            return ItineraryBoardCreateUpdateSerializer
        return ItineraryBoardDetailSerializer
    
    def perform_update(self, serializer):
        """Admin can only update certain fields."""
        serializer.save()
    
    def get_permissions(self):
        """
        Override permissions:
        - Only admins can view/update (no create/delete)
        """
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdminUser]
            # But actually return 403 for create/destroy
            return [IsAdminUser()]
        return super().get_permissions()
    
    def create(self, request, *args, **kwargs):
        """Suppliers create boards, not admins."""
        return Response(
            {"detail": "Admins cannot create itinerary boards. Suppliers create their own boards."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    def destroy(self, request, *args, **kwargs):
        """Admins cannot delete boards."""
        return Response(
            {"detail": "Admins cannot delete itinerary boards. Contact suppliers for deletion."},
            status=status.HTTP_403_FORBIDDEN
        )


class AdminItineraryColumnViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage columns.
    Admin has full CRUD access.
    """
    
    permission_classes = [IsAdminUser]
    queryset = ItineraryColumn.objects.all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['board']
    ordering_fields = ['order', 'created_at']
    ordering = ['order', 'id']
    
    def get_queryset(self):
        """Return columns with optimized queries."""
        queryset = ItineraryColumn.objects.select_related(
            'board'
        ).prefetch_related(
            'cards',
            'cards__attachments',
            'cards__checklists',
        ).all()
        
        # Filter by board if provided
        board_id = self.request.query_params.get('board')
        if board_id:
            queryset = queryset.filter(board_id=board_id)
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for list/detail vs create/update."""
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryColumnCreateUpdateSerializer
        return ItineraryColumnSerializer


class AdminItineraryCardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage cards.
    Admin has full CRUD access.
    """
    
    permission_classes = [IsAdminUser]
    queryset = ItineraryCard.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['column', 'date']
    search_fields = ['title', 'description', 'location_name']
    ordering_fields = ['order', 'date', 'start_time', 'created_at']
    ordering = ['order', 'id']
    
    def get_queryset(self):
        """Return cards with optimized queries."""
        queryset = ItineraryCard.objects.select_related(
            'column',
            'column__board',
            'created_by'
        ).prefetch_related(
            'attachments',
            'checklists',
        ).all()
        
        # Filter by column if provided
        column_id = self.request.query_params.get('column')
        if column_id:
            queryset = queryset.filter(column_id=column_id)
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for list/detail vs create/update."""
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryCardCreateUpdateSerializer
        return ItineraryCardSerializer
    
    def perform_create(self, serializer):
        """Set created_by to current user if not provided."""
        if 'created_by' not in serializer.validated_data:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()


class AdminItineraryCardAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage card attachments.
    Admin has full CRUD access.
    """
    
    permission_classes = [IsAdminUser]
    queryset = ItineraryCardAttachment.objects.all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['card']
    ordering_fields = ['created_at']
    ordering = ['created_at']
    
    def get_serializer_class(self):
        """Use different serializers for list/detail vs create/update."""
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryCardAttachmentCreateUpdateSerializer
        return ItineraryCardAttachmentSerializer


class AdminItineraryCardChecklistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage card checklists.
    Admin has full CRUD access.
    """
    
    permission_classes = [IsAdminUser]
    queryset = ItineraryCardChecklist.objects.all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['card']
    ordering_fields = ['order', 'created_at']
    ordering = ['order', 'id']
    
    def get_serializer_class(self):
        """Use different serializers for list/detail vs create/update."""
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryCardChecklistCreateUpdateSerializer
        return ItineraryCardChecklistSerializer


class ResellerItineraryBoardListView(APIView):
    """
    Public view for listing itinerary boards.
    Anyone (including non-logged in users) can view public boards (read-only).
    Returns only public boards.
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get list of public itinerary boards."""
        # Only return public and active boards
        queryset = ItineraryBoard.objects.filter(
            is_public=True,
            is_active=True
        ).select_related(
            'supplier', 'currency'
        ).prefetch_related(
            'columns',
        ).order_by('-created_at')
        
        # Optional: Filter by search query
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search) |
                models.Q(description__icontains=search)
            )
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        boards = queryset[start:end]
        
        serializer = ItineraryBoardListSerializer(
            boards,
            many=True,
            context={'request': request}
        )
        
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
            'page': page,
            'page_size': page_size,
        })


class ResellerItineraryBoardDetailView(APIView):
    """
    Public view for retrieving a single itinerary board.
    Anyone (including non-logged in users) can view public board details (read-only).
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, pk=None, slug=None):
        """Get board detail by ID or slug."""
        try:
            if pk:
                board = ItineraryBoard.objects.filter(
                    pk=pk,
                    is_public=True,
                    is_active=True
                ).select_related(
                    'supplier', 'currency'
                ).prefetch_related(
                    'columns',
                    'columns__cards',
                    'columns__cards__attachments',
                    'columns__cards__checklists',
                ).get()
            elif slug:
                board = ItineraryBoard.objects.filter(
                    slug=slug,
                    is_public=True,
                    is_active=True
                ).select_related(
                    'supplier', 'currency'
                ).prefetch_related(
                    'columns',
                    'columns__cards',
                    'columns__cards__attachments',
                    'columns__cards__checklists',
                ).get()
            else:
                raise Http404("ID board atau slug wajib diisi.")
        except ItineraryBoard.DoesNotExist:
            raise Http404("Board tidak ditemukan atau tidak bersifat publik.")
        
        serializer = ItineraryBoardDetailSerializer(
            board,
            context={'request': request}
        )
        
        return Response(serializer.data)


class IsCustomer(permissions.BasePermission):
    """
    Permission check for customer role.
    Allows both CUSTOMER and RESELLER roles to purchase itinerary access.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Allow both customers and resellers to purchase itinerary access
        return request.user.is_customer or request.user.is_reseller


class CustomerItineraryBoardDetailView(APIView):
    """
    View for customers to access itinerary boards they have purchased.
    Requires an active transaction to view the board content.
    """
    
    permission_classes = [IsCustomer]
    
    def get(self, request, pk=None, slug=None):
        """Get board detail by ID or slug if customer has active access."""
        try:
            # Find the board
            if pk:
                board = ItineraryBoard.objects.filter(
                    pk=pk,
                    is_active=True
                ).select_related(
                    'supplier', 'currency'
                ).prefetch_related(
                    'columns',
                    'columns__cards',
                    'columns__cards__attachments',
                    'columns__cards__checklists',
                ).get()
            elif slug:
                board = ItineraryBoard.objects.filter(
                    slug=slug,
                    is_active=True
                ).select_related(
                    'supplier', 'currency'
                ).prefetch_related(
                    'columns',
                    'columns__cards',
                    'columns__cards__attachments',
                    'columns__cards__checklists',
                ).get()
            else:
                raise Http404("ID board atau slug wajib diisi.")
        except ItineraryBoard.DoesNotExist:
            raise Http404("Board tidak ditemukan.")
        
        # Check if customer has an active transaction for this board
        has_access = ItineraryTransaction.objects.filter(
            customer=request.user,
            board=board,
            status='ACTIVE'
        ).exists()
        
        if not has_access:
            return Response(
                {"detail": "Anda tidak memiliki akses ke itinerary ini. Silakan beli akses terlebih dahulu."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ItineraryBoardDetailSerializer(
            board,
            context={'request': request}
        )
        
        return Response(serializer.data)


class CustomerItineraryTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for customers to purchase and manage itinerary access.
    Only authenticated customers can create transactions.
    Customers can view their own transactions.
    """
    
    permission_classes = [IsCustomer]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "board"]
    search_fields = ["board__title"]
    ordering_fields = ["created_at", "expires_at"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """Return only transactions belonging to the authenticated user (customer or reseller)."""
        if not self.request.user.is_authenticated:
            return ItineraryTransaction.objects.none()
        
        # Return transactions for the current user (works for both customers and resellers)
        queryset = ItineraryTransaction.objects.filter(
            customer=self.request.user
        ).select_related(
            "board", "board__supplier", "board__supplier__user", "customer"
        ).order_by("-created_at")
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail/create."""
        if self.action == "list":
            return ItineraryTransactionListSerializer
        if self.action == "create":
            return ItineraryTransactionCreateSerializer
        return ItineraryTransactionSerializer
    
    def perform_create(self, serializer):
        """Create transaction for current customer or reseller."""
        # No need to check for customer profile
        # Both customers and resellers can purchase itinerary access
        serializer.save(customer=self.request.user)
    
    @action(detail=True, methods=["patch"], url_path="activate")
    def activate_transaction(self, request, pk=None):
        """
        Activate a pending itinerary transaction.
        This grants the customer access to the itinerary for the specified duration.
        """
        transaction = self.get_object()
        
        if transaction.status != ItineraryTransactionStatus.PENDING:
            return Response(
                {"detail": f"Transaction is already {transaction.status}. Cannot activate."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            transaction.activate()
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": f"Error activating transaction: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["post"], url_path="extend-access")
    def extend_access(self, request, pk=None):
        """
        Extend the access duration for an active itinerary transaction.
        
        Request body:
        {
            "additional_days": 7
        }
        """
        transaction = self.get_object()
        additional_days = request.data.get("additional_days")
        
        if not additional_days:
            return Response(
                {"detail": "additional_days is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            additional_days = int(additional_days)
            if additional_days <= 0:
                return Response(
                    {"detail": "additional_days must be positive."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            transaction.extend_access(additional_days)
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {"detail": "additional_days must be an integer."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Error extending access: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["patch"], url_path="payment")
    def update_payment(self, request, pk=None):
        """
        Upload/update payment proof for an itinerary transaction.
        
        Request body (multipart/form-data):
        {
            "payment_amount": 100000,
            "payment_transfer_date": "2026-01-24",
            "payment_proof_image": <file>
        }
        """
        transaction = self.get_object()
        serializer = ItineraryTransactionPaymentUpdateSerializer(
            transaction, data=request.data, partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            # Return the full transaction data
            full_serializer = ItineraryTransactionSerializer(transaction)
            return Response(full_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResellerItineraryTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for resellers to purchase and manage itinerary access.
    Resellers can create transactions on behalf of their customers.
    """
    
    permission_classes = [IsReseller]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "board"]
    search_fields = ["board__title", "transaction_number"]
    ordering_fields = ["created_at", "expires_at"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """Return only transactions created by the authenticated reseller."""
        if not self.request.user.is_authenticated:
            return ItineraryTransaction.objects.none()
        
        try:
            # Since resellers can create transactions, filter by customer being the reseller's user
            queryset = ItineraryTransaction.objects.filter(
                customer=self.request.user
            ).select_related(
                "board", "board__supplier", "board__supplier__user", "customer"
            ).order_by("-created_at")
            
            return queryset
        except Exception:
            return ItineraryTransaction.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail/create."""
        if self.action == "list":
            return ItineraryTransactionListSerializer
        if self.action == "create":
            return ItineraryTransactionCreateSerializer
        return ItineraryTransactionSerializer
    
    def perform_create(self, serializer):
        """Create transaction for reseller's customer."""
        serializer.save(customer=self.request.user)
    
    @action(detail=True, methods=["patch"], url_path="payment")
    def update_payment(self, request, pk=None):
        """
        Upload/update payment proof for an itinerary transaction.
        
        Request body (multipart/form-data):
        {
            "payment_amount": 100000,
            "payment_transfer_date": "2026-01-24",
            "payment_proof_image": <file>
        }
        """
        transaction = self.get_object()
        serializer = ItineraryTransactionPaymentUpdateSerializer(
            transaction, data=request.data, partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            # Return the full transaction data
            full_serializer = ItineraryTransactionSerializer(transaction)
            return Response(full_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SupplierItineraryTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for suppliers to view and manage transactions for their itinerary boards.
    Suppliers can view, update transaction status, and activate transactions.
    """
    
    permission_classes = [IsSupplier]
    queryset = ItineraryTransaction.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "board"]
    search_fields = ["customer__email", "customer__full_name", "board__title", "transaction_number"]
    ordering_fields = ["created_at", "expires_at", "activated_at"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """Return only transactions for boards owned by the authenticated supplier."""
        if not self.request.user.is_authenticated:
            return ItineraryTransaction.objects.none()
        
        try:
            from account.models import SupplierProfile
            supplier_profile = SupplierProfile.objects.get(user=self.request.user)
            return ItineraryTransaction.objects.filter(
                board__supplier=supplier_profile
            ).select_related(
                "board", "board__supplier", "board__supplier__user", "customer"
            ).order_by("-created_at")
        except Exception:
            return ItineraryTransaction.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail."""
        if self.action == "list":
            return ItineraryTransactionListSerializer
        return ItineraryTransactionSerializer
    
    @action(detail=True, methods=["patch"], url_path="activate")
    def activate_transaction(self, request, pk=None):
        """Activate a pending itinerary transaction."""
        transaction = self.get_object()
        
        if transaction.status != ItineraryTransactionStatus.PENDING:
            return Response(
                {"detail": f"Transaction is already {transaction.status}. Cannot activate."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            transaction.activate()
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": f"Error activating transaction: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["patch"], url_path="approve-payment")
    def approve_payment(self, request, pk=None):
        """
        Approve the payment for an itinerary transaction.
        Only suppliers can approve payments for their boards.
        """
        transaction = self.get_object()
        
        if not transaction.payment_status:
            return Response(
                {"detail": "Belum ada pembayaran yang diunggah untuk transaksi ini."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if transaction.payment_status == "APPROVED":
            return Response(
                {"detail": "Pembayaran sudah disetujui."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.utils import timezone
            transaction.payment_status = "APPROVED"
            transaction.payment_reviewed_by = request.user
            transaction.payment_reviewed_at = timezone.now()
            transaction.save()
            
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": f"Error approving payment: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["patch"], url_path="reject-payment")
    def reject_payment(self, request, pk=None):
        """
        Reject the payment for an itinerary transaction.
        Only suppliers can reject payments for their boards.
        """
        transaction = self.get_object()
        
        if not transaction.payment_status:
            return Response(
                {"detail": "Belum ada pembayaran yang diunggah untuk transaksi ini."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if transaction.payment_status == "REJECTED":
            return Response(
                {"detail": "Pembayaran sudah ditolak."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.utils import timezone
            transaction.payment_status = "REJECTED"
            transaction.payment_reviewed_by = request.user
            transaction.payment_reviewed_at = timezone.now()
            transaction.save()
            
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": f"Error rejecting payment: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["get"], url_path="dashboard-stats")
    def dashboard_stats(self, request):
        """
        Get dashboard statistics for supplier's itinerary transactions.
        Returns aggregated statistics for the supplier's itinerary transactions.
        """
        from django.db.models import Count, Q, Sum
        from django.utils import timezone
        from datetime import timedelta
        from account.models import SupplierProfile
        
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Autentikasi diperlukan."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            supplier_profile = SupplierProfile.objects.get(user=request.user)
        except SupplierProfile.DoesNotExist:
            return Response(
                {"detail": "Profil supplier tidak ditemukan."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get transactions for itinerary boards owned by this supplier
        transactions_queryset = ItineraryTransaction.objects.filter(
            board__supplier=supplier_profile
        ).select_related("board", "customer")
        
        # Total Transactions
        total_transactions = transactions_queryset.count()
        
        # Transactions by Status
        pending_transactions = transactions_queryset.filter(status=ItineraryTransactionStatus.PENDING).count()
        active_transactions = transactions_queryset.filter(status=ItineraryTransactionStatus.ACTIVE).count()
        expired_transactions = transactions_queryset.filter(status=ItineraryTransactionStatus.EXPIRED).count()
        
        # Total Revenue (sum of amounts from active transactions)
        # Include all active transactions since payment approval happens after activation
        revenue_result = transactions_queryset.filter(
            status=ItineraryTransactionStatus.ACTIVE
        ).aggregate(
            total=Sum('amount')
        )
        total_revenue = revenue_result['total'] or 0
        
        # Recent transactions count (last 30 days) for trend calculation
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_transactions = transactions_queryset.filter(created_at__gte=thirty_days_ago).count()
        
        return Response({
            "total_transactions": total_transactions,
            "pending_transactions": pending_transactions,
            "active_transactions": active_transactions,
            "expired_transactions": expired_transactions,
            "total_revenue": total_revenue,
            "recent_transactions": recent_transactions,
        })


class AdminItineraryTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to view and manage all itinerary transactions.
    Admin can view all transactions, filter by status, and manage transaction lifecycle.
    """
    
    permission_classes = [IsAdminUser]
    queryset = ItineraryTransaction.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "board", "board__supplier"]
    search_fields = ["customer__email", "customer__full_name", "board__title", "transaction_number"]
    ordering_fields = ["created_at", "expires_at", "activated_at", "amount"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """Return all transactions with optimized queries."""
        return ItineraryTransaction.objects.select_related(
            "board", "board__supplier", "board__supplier__user", "customer"
        ).order_by("-created_at")
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail."""
        if self.action == "list":
            return ItineraryTransactionListSerializer
        return ItineraryTransactionSerializer
    
    @action(detail=True, methods=["patch"], url_path="activate")
    def activate_transaction(self, request, pk=None):
        """Activate a pending itinerary transaction."""
        transaction = self.get_object()
        
        if transaction.status != ItineraryTransactionStatus.PENDING:
            return Response(
                {"detail": f"Transaction is already {transaction.status}. Cannot activate."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            transaction.activate()
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": f"Error activating transaction: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["patch"], url_path="approve-payment")
    def approve_payment(self, request, pk=None):
        """
        Approve the payment for an itinerary transaction.
        Admin can approve payments for any transaction.
        """
        transaction = self.get_object()
        
        if not transaction.payment_status:
            return Response(
                {"detail": "Belum ada pembayaran yang diunggah untuk transaksi ini."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if transaction.payment_status == "APPROVED":
            return Response(
                {"detail": "Pembayaran sudah disetujui."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.utils import timezone
            transaction.payment_status = "APPROVED"
            transaction.payment_reviewed_by = request.user
            transaction.payment_reviewed_at = timezone.now()
            transaction.save()
            
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": f"Error approving payment: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["patch"], url_path="reject-payment")
    def reject_payment(self, request, pk=None):
        """
        Reject the payment for an itinerary transaction.
        Admin can reject payments for any transaction.
        """
        transaction = self.get_object()
        
        if not transaction.payment_status:
            return Response(
                {"detail": "Belum ada pembayaran yang diunggah untuk transaksi ini."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if transaction.payment_status == "REJECTED":
            return Response(
                {"detail": "Pembayaran sudah ditolak."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.utils import timezone
            transaction.payment_status = "REJECTED"
            transaction.payment_reviewed_by = request.user
            transaction.payment_reviewed_at = timezone.now()
            transaction.save()
            
            serializer = self.get_serializer(transaction)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": f"Error rejecting payment: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["get"], url_path="dashboard-stats")
    def dashboard_stats(self, request):
        """
        Get dashboard statistics for all itinerary transactions (admin view).
        Returns aggregated statistics for all itinerary transactions in the system.
        """
        from django.db.models import Count, Q, Sum
        from django.utils import timezone
        from datetime import timedelta
        
        # Get all itinerary transactions
        transactions_queryset = ItineraryTransaction.objects.all().select_related(
            "board", "board__supplier", "customer"
        )
        
        # Total Transactions
        total_transactions = transactions_queryset.count()
        
        # Transactions by Status
        pending_transactions = transactions_queryset.filter(status=ItineraryTransactionStatus.PENDING).count()
        active_transactions = transactions_queryset.filter(status=ItineraryTransactionStatus.ACTIVE).count()
        expired_transactions = transactions_queryset.filter(status=ItineraryTransactionStatus.EXPIRED).count()
        
        # Total Revenue (sum of amounts from active transactions)
        # Include all active transactions since payment approval happens after activation
        revenue_result = transactions_queryset.filter(
            status=ItineraryTransactionStatus.ACTIVE
        ).aggregate(
            total=Sum('amount')
        )
        total_revenue = revenue_result['total'] or 0
        
        # Recent transactions count (last 30 days) for trend calculation
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_transactions = transactions_queryset.filter(created_at__gte=thirty_days_ago).count()
        
        # Additional admin-specific stats
        total_boards = transactions_queryset.values('board').distinct().count()
        total_suppliers = transactions_queryset.values('board__supplier').distinct().count()
        
        return Response({
            "total_transactions": total_transactions,
            "pending_transactions": pending_transactions,
            "active_transactions": active_transactions,
            "expired_transactions": expired_transactions,
            "total_revenue": total_revenue,
            "recent_transactions": recent_transactions,
            "total_boards": total_boards,
            "total_suppliers": total_suppliers,
        })
