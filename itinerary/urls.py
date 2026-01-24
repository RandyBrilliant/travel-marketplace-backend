from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SupplierItineraryBoardViewSet,
    AdminItineraryBoardViewSet,
    AdminItineraryColumnViewSet,
    AdminItineraryCardViewSet,
    AdminItineraryCardAttachmentViewSet,
    AdminItineraryCardChecklistViewSet,
    SupplierItineraryColumnViewSet,
    SupplierItineraryCardViewSet,
    SupplierItineraryCardAttachmentViewSet,
    SupplierItineraryCardChecklistViewSet,
    ResellerItineraryBoardListView,
    ResellerItineraryBoardDetailView,
    CustomerItineraryTransactionViewSet,
    ResellerItineraryTransactionViewSet,
    SupplierItineraryTransactionViewSet,
    AdminItineraryTransactionViewSet,
)

router = DefaultRouter()
router.register(r'suppliers/me/boards', SupplierItineraryBoardViewSet, basename='supplier-itinerary-board')
router.register(r'suppliers/me/columns', SupplierItineraryColumnViewSet, basename='supplier-itinerary-column')
router.register(r'suppliers/me/cards', SupplierItineraryCardViewSet, basename='supplier-itinerary-card')
router.register(r'suppliers/me/attachments', SupplierItineraryCardAttachmentViewSet, basename='supplier-itinerary-attachment')
router.register(r'suppliers/me/checklists', SupplierItineraryCardChecklistViewSet, basename='supplier-itinerary-checklist')
router.register(r'suppliers/me/transactions', SupplierItineraryTransactionViewSet, basename='supplier-itinerary-transaction')
router.register(r'admin/boards', AdminItineraryBoardViewSet, basename='admin-itinerary-board')
router.register(r'admin/columns', AdminItineraryColumnViewSet, basename='admin-itinerary-column')
router.register(r'admin/cards', AdminItineraryCardViewSet, basename='admin-itinerary-card')
router.register(r'admin/attachments', AdminItineraryCardAttachmentViewSet, basename='admin-itinerary-attachment')
router.register(r'admin/checklists', AdminItineraryCardChecklistViewSet, basename='admin-itinerary-checklist')
router.register(r'admin/transactions', AdminItineraryTransactionViewSet, basename='admin-itinerary-transaction')
router.register(r'customers/me/transactions', CustomerItineraryTransactionViewSet, basename='customer-itinerary-transaction')
router.register(r'resellers/me/itinerary-transactions', ResellerItineraryTransactionViewSet, basename='reseller-itinerary-transaction')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Public endpoints (read-only, accessible to everyone)
    path('public/itinerary-boards/', ResellerItineraryBoardListView.as_view(), name='public-itinerary-board-list'),
    path('public/itinerary-boards/<int:pk>/', ResellerItineraryBoardDetailView.as_view(), name='public-itinerary-board-detail'),
    path('public/itinerary-boards/slug/<str:slug>/', ResellerItineraryBoardDetailView.as_view(), name='public-itinerary-board-detail-slug'),
    # Reseller endpoints (read-only, kept for backward compatibility)
    path('resellers/me/itinerary-boards/', ResellerItineraryBoardListView.as_view(), name='reseller-itinerary-board-list'),
    path('resellers/me/itinerary-boards/<int:pk>/', ResellerItineraryBoardDetailView.as_view(), name='reseller-itinerary-board-detail'),
    path('resellers/me/itinerary-boards/slug/<str:slug>/', ResellerItineraryBoardDetailView.as_view(), name='reseller-itinerary-board-detail-slug'),
]
