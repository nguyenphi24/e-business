from django.db.models import Count
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.scope import get_scoped_audit_queryset, get_scoped_querysets, is_global_user
from apps.audit.api import serialize_event
from apps.billing.models import Invoice
from apps.dashboard.kpis import compute_kpis
from apps.identity.permissions import IsAuthenticatedCompanyMember, has_any_role
from apps.procurement.models import PurchaseRequest, Quotation, RFQ, RFQInvitation, SupplierSelection
from apps.purchase_orders.models import PurchaseOrder


def status_counts(queryset, choices):
    counts = {value: 0 for value, _ in choices}
    for row in queryset.values("status").annotate(total=Count("id")):
        counts[row["status"]] = row["total"]
    return counts


def action_item(item_type, instance, number, label):
    return {
        "type": item_type,
        "id": str(instance.id),
        "number": number,
        "status": instance.status,
        "label": label,
        "updated_at": instance.updated_at,
    }


def pending_actions(user, querysets):
    items = []
    if has_any_role(user, "SUPPLIER") and not is_global_user(user):
        invitations = RFQInvitation.objects.filter(
            supplier_company_id=user.company_id,
            rfq__status=RFQ.Status.OPEN,
            status__in=[RFQInvitation.Status.INVITED, RFQInvitation.Status.VIEWED],
        ).select_related("rfq")
        for invitation in invitations.order_by("-updated_at")[:10]:
            items.append(action_item("RFQ_RESPONSE", invitation.rfq, invitation.rfq.number, "RFQ cần báo giá"))

        for order in querysets["purchase_orders"].filter(status=PurchaseOrder.Status.ISSUED).order_by("-updated_at")[:10]:
            items.append(action_item("PO_RESPONSE", order, order.number, "PO chờ xác nhận hoặc từ chối"))
        uninvoiced = querysets["purchase_orders"].filter(
            status__in=[PurchaseOrder.Status.DELIVERED, PurchaseOrder.Status.COMPLETED]
        ).exclude(invoices__status__in=Invoice.OPEN_STATUSES + (Invoice.Status.PAID,))
        for order in uninvoiced.order_by("-updated_at")[:10]:
            items.append(action_item("INVOICE_CREATE", order, order.number, "PO đã giao, cần lập hóa đơn"))
        return sorted(items, key=lambda item: item["updated_at"], reverse=True)[:20]

    if has_any_role(user, "FINANCE") or is_global_user(user):
        for invoice in querysets["invoices"].filter(status__in=Invoice.OPEN_STATUSES).order_by("due_date")[:10]:
            label = "Hóa đơn quá hạn" if invoice.is_overdue else "Hóa đơn chờ thanh toán"
            items.append(action_item("INVOICE_PAYMENT", invoice, invoice.number, label))

    if has_any_role(user, "MANAGER") or is_global_user(user):
        for request in querysets["purchase_requests"].filter(
            status=PurchaseRequest.Status.PENDING_APPROVAL
        ).order_by("-updated_at")[:10]:
            items.append(action_item("PR_APPROVAL", request, request.number, "Purchase Request chờ duyệt"))
        for selection in querysets["selections"].filter(
            status=SupplierSelection.Status.PROPOSED
        ).select_related("rfq").order_by("-updated_at")[:10]:
            items.append(action_item("SELECTION_APPROVAL", selection, selection.rfq.number, "Lựa chọn nhà cung cấp chờ duyệt"))

    if has_any_role(user, "BUYER", "COMPANY_ADMIN") or is_global_user(user):
        request_filter = {"status__in": [PurchaseRequest.Status.DRAFT, PurchaseRequest.Status.REJECTED]}
        if not is_global_user(user):
            request_filter["requester_id"] = user.id
        for request in querysets["purchase_requests"].filter(**request_filter).order_by("-updated_at")[:10]:
            items.append(action_item("PR_EDIT", request, request.number, "Purchase Request cần hoàn thiện"))
        unrated = querysets["purchase_orders"].filter(
            status=PurchaseOrder.Status.COMPLETED, evaluation__isnull=True
        ).order_by("-updated_at")[:10]
        for order in unrated:
            items.append(action_item("SUPPLIER_EVALUATION", order, order.number, "PO hoàn tất, cần đánh giá nhà cung cấp"))

    return sorted(items, key=lambda item: item["updated_at"], reverse=True)[:20]


class DashboardView(APIView):
    permission_classes = [IsAuthenticatedCompanyMember]

    def get(self, request):
        querysets = get_scoped_querysets(request.user)
        recent_activity = get_scoped_audit_queryset(request.user).select_related("actor").order_by(
            "-occurred_at", "-id"
        )[:20]
        pending = pending_actions(request.user, querysets)
        supplier_view = has_any_role(request.user, "SUPPLIER") and not is_global_user(request.user)

        return Response({
            "scope": {
                "company_id": str(request.user.company_id) if request.user.company_id else None,
                "global": is_global_user(request.user),
                "supplier_view": supplier_view,
            },
            "counts": {
                "purchase_requests": status_counts(querysets["purchase_requests"], PurchaseRequest.Status.choices),
                "rfqs": status_counts(querysets["rfqs"], RFQ.Status.choices),
                "quotations": status_counts(querysets["quotations"], Quotation.Status.choices),
                "selections": status_counts(querysets["selections"], SupplierSelection.Status.choices),
                "purchase_orders": status_counts(querysets["purchase_orders"], PurchaseOrder.Status.choices),
                "invoices": status_counts(querysets["invoices"], Invoice.Status.choices),
            },
            "receivables": {
                "open_balance": str(sum((invoice.balance for invoice in querysets["invoices"].filter(status__in=Invoice.OPEN_STATUSES)), 0)),
                "overdue_count": sum(1 for invoice in querysets["invoices"].filter(status__in=Invoice.OPEN_STATUSES) if invoice.is_overdue),
            },
            "kpis": None if supplier_view else compute_kpis(querysets),
            "pending_actions": pending,
            "pending_count": len(pending),
            "recent_activity": [serialize_event(event) for event in recent_activity],
            "generated_at": timezone.now(),
        })
