from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminItineraryBoardViewSet,
    AdminItineraryColumnViewSet,
    AdminItineraryCardViewSet,
    AdminItineraryCardAttachmentViewSet,
    AdminItineraryCardChecklistViewSet,
    AdminItineraryCardCommentViewSet,
    ResellerItineraryBoardListView,
    ResellerItineraryBoardDetailView,
)

router = DefaultRouter()
router.register(r'boards', AdminItineraryBoardViewSet, basename='admin-itinerary-board')
router.register(r'columns', AdminItineraryColumnViewSet, basename='admin-itinerary-column')
router.register(r'cards', AdminItineraryCardViewSet, basename='admin-itinerary-card')
router.register(r'attachments', AdminItineraryCardAttachmentViewSet, basename='admin-itinerary-attachment')
router.register(r'checklists', AdminItineraryCardChecklistViewSet, basename='admin-itinerary-checklist')
router.register(r'comments', AdminItineraryCardCommentViewSet, basename='admin-itinerary-comment')

urlpatterns = [
    # Admin endpoints (full CRUD)
    path('admin/itinerary/', include(router.urls)),
    
    # Reseller endpoints (read-only)
    path('resellers/me/itinerary-boards/', ResellerItineraryBoardListView.as_view(), name='reseller-itinerary-board-list'),
    path('resellers/me/itinerary-boards/<int:pk>/', ResellerItineraryBoardDetailView.as_view(), name='reseller-itinerary-board-detail'),
    path('resellers/me/itinerary-boards/slug/<str:slug>/', ResellerItineraryBoardDetailView.as_view(), name='reseller-itinerary-board-detail-slug'),
]
