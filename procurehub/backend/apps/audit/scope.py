from django.db.models import Q

from apps.billing.models import Invoice, Payment
from apps.identity.permissions import has_any_role
from apps.procurement.models import PurchaseRequest, Quotation, RFQ, SupplierSelection
from apps.purchase_orders.models import PurchaseOrder
from apps.suppliers.models import SupplierEvaluation


ENTITY_QUERYSET_KEYS = {
    "procurement.purchaserequest": "purchase_requests",
    "procurement.rfq": "rfqs",
    "procurement.quotation": "quotations",
    "procurement.supplierselection": "selections",
    "purchase_orders.purchaseorder": "purchase_orders",
    "billing.invoice": "invoices",
    "billing.payment": "payments",
    "suppliers.supplierevaluation": "evaluations",
}


def is_global_user(user):
    return has_any_role(user, "SYSTEM_ADMIN") or user.is_superuser


def get_scoped_querysets(user):
    querysets = {
        "purchase_requests": PurchaseRequest.objects.all(),
        "rfqs": RFQ.objects.all(),
        "quotations": Quotation.objects.all(),
        "selections": SupplierSelection.objects.all(),
        "purchase_orders": PurchaseOrder.objects.all(),
        "invoices": Invoice.objects.all(),
        "payments": Payment.objects.all(),
        "evaluations": SupplierEvaluation.objects.all(),
    }
    if is_global_user(user):
        return querysets

    if not user.company_id:
        return {key: queryset.none() for key, queryset in querysets.items()}

    if has_any_role(user, "SUPPLIER"):
        return {
            "purchase_requests": querysets["purchase_requests"].none(),
            "rfqs": querysets["rfqs"].filter(invitations__supplier_company_id=user.company_id).distinct(),
            "quotations": querysets["quotations"].filter(supplier_company_id=user.company_id),
            "selections": querysets["selections"].none(),
            "purchase_orders": querysets["purchase_orders"].filter(supplier_company_id=user.company_id),
            "invoices": querysets["invoices"].filter(supplier_company_id=user.company_id),
            "payments": querysets["payments"].filter(invoice__supplier_company_id=user.company_id),
            "evaluations": querysets["evaluations"].none(),
        }

    return {
        "purchase_requests": querysets["purchase_requests"].filter(company_id=user.company_id),
        "rfqs": querysets["rfqs"].filter(company_id=user.company_id),
        "quotations": querysets["quotations"].filter(rfq__company_id=user.company_id).exclude(status=Quotation.Status.DRAFT),
        "selections": querysets["selections"].filter(rfq__company_id=user.company_id),
        "purchase_orders": querysets["purchase_orders"].filter(company_id=user.company_id),
        "invoices": querysets["invoices"].filter(buyer_company_id=user.company_id),
        "payments": querysets["payments"].filter(invoice__buyer_company_id=user.company_id),
        "evaluations": querysets["evaluations"].filter(buyer_company_id=user.company_id),
    }


def get_scoped_audit_queryset(user):
    from apps.audit.models import AuditEvent

    if is_global_user(user):
        return AuditEvent.objects.all()

    querysets = get_scoped_querysets(user)
    scope = Q()
    for entity_type, queryset_key in ENTITY_QUERYSET_KEYS.items():
        scope |= Q(entity_type=entity_type, entity_id__in=querysets[queryset_key].values("id"))
    return AuditEvent.objects.filter(scope)
