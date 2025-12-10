from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from account.token_views import CustomTokenObtainPairView
from account.views import (
    SupplierProfileViewSet,
    ResellerProfileViewSet,
    StaffProfileViewSet,
    AdminSupplierProfileViewSet,
    AdminResellerProfileViewSet,
    AdminStaffProfileViewSet,
)

router = DefaultRouter()
router.register(r"suppliers/me/profile", SupplierProfileViewSet, basename="supplier-profile")
router.register(r"resellers/me/profile", ResellerProfileViewSet, basename="reseller-profile")
router.register(r"admin/staff/me/profile", StaffProfileViewSet, basename="staff-profile")

# Admin-only endpoints for managing all profiles
router.register(
    r"admin/suppliers", AdminSupplierProfileViewSet, basename="admin-supplier-profile"
)
router.register(
    r"admin/resellers", AdminResellerProfileViewSet, basename="admin-reseller-profile"
)
router.register(
    r"admin/staff", AdminStaffProfileViewSet, basename="admin-staff-profile"
)

urlpatterns = [
    path("", include(router.urls)),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
