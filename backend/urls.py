from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from account.token_views import CustomTokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Import admin configuration to customize admin site
import backend.admin_config  # noqa

from backend.health import health_check
from account.token_views import CustomTokenObtainPairView
from account.views import (
    SupplierProfileViewSet,
    ResellerProfileViewSet,
    StaffProfileViewSet,
    CustomerProfileViewSet,
    AdminSupplierProfileViewSet,
    AdminResellerProfileViewSet,
    AdminStaffProfileViewSet,
    AdminCustomerProfileViewSet,
    AdminContactMessageViewSet,
    CurrentUserView,
    LogoutView,
    ChangePasswordView,
    SendEmailVerificationView,
    VerifyEmailView,
    RequestPasswordResetView,
    ResetPasswordView,
    ResetPasswordConfirmView,
    ActivateDeactivateAccountView,
    ApproveRejectSupplierView,
    RegisterResellerView,
    RegisterSupplierView,
    RegisterCustomerView,
    ContactMessageView,
)
from travel.views import (
    SupplierTourPackageViewSet,
    SupplierTourDateViewSet,
    SupplierTourImageViewSet,
    SupplierBookingViewSet,
    SupplierResellerGroupViewSet,
    ResellerBookingViewSet,
    CustomerBookingViewSet,
    AdminResellerTourCommissionViewSet,
    AdminResellerGroupViewSet,
    AdminBookingViewSet,
    AdminTourPackageViewSet,
    PublicTourPackageListView,
    PublicTourPackageDetailView,
    ResellerWithdrawalViewSet,
    AdminWithdrawalViewSet,
    CurrencyViewSet,
    AdminCurrencyViewSet,
)
from itinerary.views import CustomerItineraryTransactionViewSet
from travel.report_views import (
    sales_report_view,
    pax_report_view,
    total_amount_report_view,
    commission_payout_report_view,
    supplier_sales_report_view,
    supplier_pax_report_view,
    supplier_total_amount_report_view,
    supplier_commission_report_view,
)

router = DefaultRouter()
router.register(r"suppliers/me/profile", SupplierProfileViewSet, basename="supplier-profile")
router.register(r"resellers/me/profile", ResellerProfileViewSet, basename="reseller-profile")
router.register(r"admin/staff/me/profile", StaffProfileViewSet, basename="staff-profile")
router.register(r"customers/me/profile", CustomerProfileViewSet, basename="customer-profile")

# Supplier tour management endpoints
router.register(r"suppliers/me/tours", SupplierTourPackageViewSet, basename="supplier-tour-package")
router.register(r"suppliers/me/tour-dates", SupplierTourDateViewSet, basename="supplier-tour-date")
router.register(r"suppliers/me/tour-images", SupplierTourImageViewSet, basename="supplier-tour-image")
router.register(r"suppliers/me/bookings", SupplierBookingViewSet, basename="supplier-booking")
router.register(r"suppliers/me/reseller-groups", SupplierResellerGroupViewSet, basename="supplier-reseller-group")

# Reseller booking endpoints
router.register(r"resellers/me/bookings", ResellerBookingViewSet, basename="reseller-booking")
# Reseller withdrawal endpoints
router.register(r"resellers/me/withdrawals", ResellerWithdrawalViewSet, basename="reseller-withdrawal")

# Customer booking endpoints
router.register(r"customers/me/bookings", CustomerBookingViewSet, basename="customer-booking")
# Customer itinerary transaction endpoints
router.register(r"customers/me/itinerary-transactions", CustomerItineraryTransactionViewSet, basename="customer-itinerary-transaction")

# Currency endpoints (read-only for all authenticated users)
router.register(r"currencies", CurrencyViewSet, basename="currency")
# Admin currency management
router.register(
    r"admin/currencies", AdminCurrencyViewSet, basename="admin-currency"
)
router.register(
    r"admin/suppliers", AdminSupplierProfileViewSet, basename="admin-supplier-profile"
)
router.register(
    r"admin/resellers", AdminResellerProfileViewSet, basename="admin-reseller-profile"
)
router.register(
    r"admin/staff", AdminStaffProfileViewSet, basename="admin-staff-profile"
)
router.register(
    r"admin/customers", AdminCustomerProfileViewSet, basename="admin-customer-profile"
)
# Admin-only endpoints for managing contact messages
router.register(
    r"admin/contact-messages", AdminContactMessageViewSet, basename="admin-contact-message"
)
# Admin-only endpoints for managing reseller tour commissions
router.register(
    r"admin/reseller-tour-commissions",
    AdminResellerTourCommissionViewSet,
    basename="admin-reseller-tour-commission",
)
# Admin-only endpoints for managing reseller groups
router.register(
    r"admin/reseller-groups",
    AdminResellerGroupViewSet,
    basename="admin-reseller-group",
)
# Admin-only endpoints for managing bookings
router.register(
    r"admin/bookings",
    AdminBookingViewSet,
    basename="admin-booking",
)
# Admin-only endpoints for managing tour packages
router.register(
    r"admin/tours",
    AdminTourPackageViewSet,
    basename="admin-tour-package",
)
# Admin-only endpoints for managing withdrawal requests
router.register(
    r"admin/withdrawals",
    AdminWithdrawalViewSet,
    basename="admin-withdrawal",
)

# API Documentation endpoints
api_docs_patterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# API v1 endpoints
api_v1_patterns = [
    path("", include(router.urls)),
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("token/logout/", LogoutView.as_view(), name="token_logout"),
    path("token/me/", CurrentUserView.as_view(), name="token_me"),
    # Public registration endpoints
    path("register/reseller/", RegisterResellerView.as_view(), name="register-reseller"),
    path("register/supplier/", RegisterSupplierView.as_view(), name="register-supplier"),
    path("register/customer/", RegisterCustomerView.as_view(), name="register-customer"),
    # Public contact form endpoint
    path("contact/", ContactMessageView.as_view(), name="contact-message"),
    # Password change endpoint (works for all user types)
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    # Email verification endpoints
    path("users/<int:user_id>/send-verification-email/", SendEmailVerificationView.as_view(), name="send-verification-email"),
    path("verify-email/<str:uidb64>/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
    # Password reset endpoints
    path("request-password-reset/", RequestPasswordResetView.as_view(), name="request-password-reset"),
    path("users/<int:user_id>/reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("reset-password/<str:uidb64>/<str:token>/", ResetPasswordConfirmView.as_view(), name="reset-password-confirm"),
    # Activate/Deactivate account endpoint
    path("admin/<str:profile_type>/<int:profile_id>/activate-deactivate/", ActivateDeactivateAccountView.as_view(), name="activate-deactivate-account"),
    # Approve/Reject supplier endpoint
    path("admin/suppliers/<int:supplier_id>/approve-reject/", ApproveRejectSupplierView.as_view(), name="approve-reject-supplier"),
    # Admin report endpoints
    path("admin/reports/sales/", sales_report_view, name="admin-sales-report"),
    path("admin/reports/pax/", pax_report_view, name="admin-pax-report"),
    path("admin/reports/total-amount/", total_amount_report_view, name="admin-total-amount-report"),
    path("admin/reports/commission-payout/", commission_payout_report_view, name="admin-commission-payout-report"),
    # Supplier report endpoints
    path("suppliers/me/reports/sales/", supplier_sales_report_view, name="supplier-sales-report"),
    path("suppliers/me/reports/pax/", supplier_pax_report_view, name="supplier-pax-report"),
    path("suppliers/me/reports/total-amount/", supplier_total_amount_report_view, name="supplier-total-amount-report"),
    path("suppliers/me/reports/commission-payout/", supplier_commission_report_view, name="supplier-commission-payout-report"),
    # Public tour endpoints
    path("tours/", PublicTourPackageListView.as_view(), name="public-tour-list"),
    path("tours/<str:slug>/", PublicTourPackageDetailView.as_view(), name="public-tour-detail"),
    # Itinerary endpoints
    path("itinerary/", include("itinerary.urls")),
]

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health"),
    # API Documentation
    *api_docs_patterns,
    # API v1
    path("api/v1/", include(api_v1_patterns)),
    # Backward compatibility: keep old endpoints working
    path("api/", include(api_v1_patterns)),
    # REST framework auth URLs (for browsable API)
    path("api-auth/", include("rest_framework.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
