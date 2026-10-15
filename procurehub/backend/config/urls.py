from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.identity.api import LoginView, LogoutView, MeView, RefreshView
from apps.audit.api import AuditEventListView
from apps.billing.api import InvoiceViewSet, PaymentViewSet
from apps.integrations.webhooks import EInvoiceWebhookView, ESignWebhookView, PaymentWebhookView
from apps.notifications.api import NotificationViewSet
from apps.notifications.stream import notification_stream
from apps.dashboard.api import DashboardView
from apps.procurement.api import (
    PurchaseRequestViewSet,
    PurchaseOrderViewSet,
    QuotationViewSet,
    RFQViewSet,
    SupplierSelectionViewSet,
)
from apps.suppliers.api import SupplierRelationshipListView


def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


router = DefaultRouter(trailing_slash=False)
router.register("purchase-requests", PurchaseRequestViewSet, basename="purchase-request")
router.register("rfqs", RFQViewSet, basename="rfq")
router.register("quotations", QuotationViewSet, basename="quotation")
router.register("selections", SupplierSelectionViewSet, basename="selection")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("payments", PaymentViewSet, basename="payment")
router.register("notifications", NotificationViewSet, basename="notification")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/v1/health", health),
    path("api/v1/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/v1/dashboard", DashboardView.as_view(), name="dashboard"),
    path("api/v1/audit-events", AuditEventListView.as_view(), name="audit-event-list"),
    path("api/v1/auth/login", LoginView.as_view()),
    path("api/v1/auth/refresh", RefreshView.as_view()),
    path("api/v1/auth/logout", LogoutView.as_view()),
    path("api/v1/auth/me", MeView.as_view()),
    path("api/v1/suppliers", SupplierRelationshipListView.as_view(), name="supplier-relationship-list"),
    # Đặt trước router để "stream" không bị hiểu là notification id.
    path("api/v1/notifications/stream", notification_stream, name="notification-stream"),
    path("api/v1/webhooks/payment", PaymentWebhookView.as_view(), name="payment-webhook"),
    path("api/v1/webhooks/einvoice", EInvoiceWebhookView.as_view(), name="einvoice-webhook"),
    path("api/v1/webhooks/esign", ESignWebhookView.as_view(), name="esign-webhook"),
    path("api/v1/", include(router.urls)),
]
