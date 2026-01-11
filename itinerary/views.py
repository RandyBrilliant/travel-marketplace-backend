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
)
from account.models import ResellerProfile


class IsReseller(permissions.BasePermission):
    """
    Permission check for reseller role.
    Checks if user has reseller profile.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_reseller


class AdminItineraryBoardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage itinerary boards.
    Admin has full CRUD access.
    """
    
    permission_classes = [IsAdminUser]
    queryset = ItineraryBoard.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_public', 'allow_editing']
    search_fields = ['title', 'description', 'slug']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return all boards with optimized queries."""
        queryset = ItineraryBoard.objects.select_related(
            'created_by'
        ).prefetch_related(
            'columns',
            'columns__cards',
            'columns__cards__attachments',
            'columns__cards__checklists',
        ).all()
        
        # Filter by is_public
        is_public = self.request.query_params.get('is_public')
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == 'true')
        
        # Filter by allow_editing
        allow_editing = self.request.query_params.get('allow_editing')
        if allow_editing is not None:
            queryset = queryset.filter(allow_editing=allow_editing.lower() == 'true')
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail/create/update."""
        if self.action == 'list':
            return ItineraryBoardListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ItineraryBoardCreateUpdateSerializer
        return ItineraryBoardDetailSerializer
    
    def perform_create(self, serializer):
        """Set created_by to current user if not provided."""
        if 'created_by' not in serializer.validated_data:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()


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
        # Only return public boards
        queryset = ItineraryBoard.objects.filter(
            is_public=True
        ).select_related(
            'created_by'
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
                    is_public=True
                ).select_related(
                    'created_by'
                ).prefetch_related(
                    'columns',
                    'columns__cards',
                    'columns__cards__attachments',
                    'columns__cards__checklists',
                ).get()
            elif slug:
                board = ItineraryBoard.objects.filter(
                    slug=slug,
                    is_public=True
                ).select_related(
                    'created_by'
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
