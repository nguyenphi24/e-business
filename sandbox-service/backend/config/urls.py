from django.contrib import admin
from django.urls import include, path

from core.views import health
from einvoice import pages as einvoice_pages
from einvoice.api import EInvoiceCreateView, EInvoiceDetailView
from esign import pages as esign_pages
from esign.api import CertificateAuthorityView, SignRequestCreateView, SignRequestDetailView
from gateway import pages as gateway_pages
from gateway.api import TransactionDetailView, TransactionListCreateView, TransactionResendIpnView

api_patterns = [
	path("gateway/transactions", TransactionListCreateView.as_view(), name="gateway-transactions"),
	path("gateway/transactions/<uuid:pk>", TransactionDetailView.as_view(), name="gateway-transaction"),
	path("gateway/transactions/<uuid:pk>/resend-ipn", TransactionResendIpnView.as_view(), name="gateway-resend-ipn"),
	path("einvoices", EInvoiceCreateView.as_view(), name="einvoices"),
	path("einvoices/<uuid:pk>", EInvoiceDetailView.as_view(), name="einvoice"),
	path("esign/ca", CertificateAuthorityView.as_view(), name="esign-ca"),
	path("esign/requests", SignRequestCreateView.as_view(), name="esign-requests"),
	path("esign/requests/<uuid:pk>", SignRequestDetailView.as_view(), name="esign-request"),
]

urlpatterns = [
	path("admin/", admin.site.urls),
	path("health/", health, name="health"),
	path("api/v1/", include(api_patterns)),
	# Trang trình duyệt (người dùng thao tác) — trang thanh toán, ký OTP, tra cứu hóa đơn.
	path("gateway/checkout/<uuid:pk>/", gateway_pages.checkout, name="gateway-checkout"),
	path("einvoice/lookup/", einvoice_pages.lookup, name="einvoice-lookup"),
	path("einvoice/<str:lookup_code>/xml/", einvoice_pages.xml, name="einvoice-xml"),
	path("esign/sign/<uuid:pk>/", esign_pages.sign_page, name="esign-sign"),
	# Latency histogram + request count theo status — django_prometheus tự
	# dùng resolver_match.view_name làm label (không phải path đã điền giá
	# trị) nên không lo cardinality nổ. Xem stacks/django.md mục "Metrics".
	path("", include("django_prometheus.urls")),
]
