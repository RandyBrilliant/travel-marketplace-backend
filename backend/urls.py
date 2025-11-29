from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from account.views import (
    UserViewSet,
    SupplierProfileViewSet,
    ResellerProfileViewSet,
    StaffProfileViewSet,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"suppliers/me/profile", SupplierProfileViewSet, basename="supplier-profile")
router.register(r"resellers/me/profile", ResellerProfileViewSet, basename="reseller-profile")
router.register(r"staff/me/profile", StaffProfileViewSet, basename="staff-profile")

urlpatterns = [
    path("", include(router.urls)),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
