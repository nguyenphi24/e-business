from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count

from apps.suppliers.models import SupplierEvaluation


def rating_summary(buyer_company_id, supplier_ids):
    """Điểm uy tín 1–5 = trung bình (chất lượng + giao hàng) / 2 theo company mua (FR-EVAL-03)."""
    rows = (
        SupplierEvaluation.objects.filter(buyer_company_id=buyer_company_id, supplier_company_id__in=supplier_ids)
        .values("supplier_company_id")
        .annotate(quality=Avg("quality_score"), delivery=Avg("delivery_score"), count=Count("id"))
    )
    summary = {}
    for row in rows:
        average = (Decimal(str(row["quality"])) + Decimal(str(row["delivery"]))) / 2
        summary[row["supplier_company_id"]] = {
            "average": average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "count": row["count"],
        }
    return summary
