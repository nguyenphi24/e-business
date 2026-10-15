"""KPI mua sắm (SRS mục 6). Dùng trung vị vì cỡ mẫu nhỏ; mỗi KPI trả kèm cỡ mẫu `n`."""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import median

from apps.procurement.models import Quotation, QuotationRevision, RFQInvitation
from apps.purchase_orders.models import PurchaseOrder

EXCLUDED_PO_STATUSES = {PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.CANCELLED, PurchaseOrder.Status.DECLINED}


def _kpi(value, n, unit, definition):
    return {"value": value, "n": n, "unit": unit, "definition": definition}


def _median_hours(durations):
    if not durations:
        return None
    return round(median(duration.total_seconds() for duration in durations) / 3600, 2)


def approval_lead_time(purchase_requests):
    rows = purchase_requests.filter(submitted_at__isnull=False, decided_at__isnull=False).values_list("submitted_at", "decided_at")
    durations = [decided - submitted for submitted, decided in rows if decided >= submitted]
    return _kpi(_median_hours(durations), len(durations), "hours", "Trung vị (thời điểm duyệt/từ chối − thời điểm gửi PR)")


def rfq_response_time(rfqs):
    rows = QuotationRevision.objects.filter(
        revision=1, quotation__rfq__in=rfqs, quotation__rfq__published_at__isnull=False
    ).values_list("submitted_at", "quotation__rfq__published_at")
    durations = [submitted - published for submitted, published in rows if submitted >= published]
    return _kpi(_median_hours(durations), len(durations), "hours", "Trung vị (lần nộp báo giá đầu − thời điểm publish RFQ)")


def quote_participation(rfqs):
    invited = set(
        RFQInvitation.objects.filter(rfq__in=rfqs, rfq__published_at__isnull=False).values_list("rfq_id", "supplier_company_id")
    )
    quoted = set(
        Quotation.objects.filter(rfq__in=rfqs, revision__gte=1).values_list("rfq_id", "supplier_company_id")
    )
    answered = len(invited & quoted)
    rate = round(answered / len(invited), 4) if invited else None
    return _kpi(rate, len(invited), "ratio", "Số lời mời đã có báo giá nộp / số lời mời của RFQ đã publish")


def procurement_cycle_time(purchase_orders):
    rows = purchase_orders.filter(
        issued_at__isnull=False, selection__rfq__request__submitted_at__isnull=False
    ).values_list("issued_at", "selection__rfq__request__submitted_at")
    durations = [issued - submitted for issued, submitted in rows if issued >= submitted]
    value = round(_median_hours(durations) / 24, 2) if durations else None
    return _kpi(value, len(durations), "days", "Trung vị (thời điểm phát hành PO − thời điểm gửi PR gốc)")


def on_time_delivery(purchase_orders):
    rows = purchase_orders.filter(
        delivered_at__isnull=False, issued_at__isnull=False, delivery_days__isnull=False
    ).values_list("issued_at", "delivered_at", "delivery_days")
    total = len(rows)
    on_time = sum(1 for issued, delivered, days in rows if delivered <= issued + timedelta(days=days))
    return _kpi(round(on_time / total, 4) if total else None, total, "ratio", "PO giao đủ trước hạn (phát hành + số ngày giao) / PO đã giao đủ")


def estimated_savings(purchase_orders):
    rows = purchase_orders.exclude(status__in=EXCLUDED_PO_STATUSES).filter(
        selection__rfq__request__estimated_budget__isnull=False
    ).values_list("total", "selection__rfq__request__estimated_budget")
    budget_sum = sum((budget for _, budget in rows), Decimal("0"))
    savings = sum((budget - total for total, budget in rows), Decimal("0"))
    rate = float((savings / budget_sum).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)) if budget_sum else None
    return {
        **_kpi(str(savings.quantize(Decimal("0.01"))) if rows else None, len(rows), "currency", "Σ (ngân sách ước tính của PR − tổng PO)"),
        "rate": rate,
    }


def compute_kpis(querysets):
    return {
        "approval_lead_time_hours": approval_lead_time(querysets["purchase_requests"]),
        "rfq_response_time_hours": rfq_response_time(querysets["rfqs"]),
        "quote_participation_rate": quote_participation(querysets["rfqs"]),
        "procurement_cycle_time_days": procurement_cycle_time(querysets["purchase_orders"]),
        "on_time_delivery_rate": on_time_delivery(querysets["purchase_orders"]),
        "estimated_savings": estimated_savings(querysets["purchase_orders"]),
    }
