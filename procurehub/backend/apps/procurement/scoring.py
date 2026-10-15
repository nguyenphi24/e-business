"""Chấm điểm báo giá theo trọng số (SRS mục 5). Hàm thuần, không truy cập database.

Đây là weighted scoring có công bố công thức, không phải AI; điểm chỉ hỗ trợ Buyer, quyết định vẫn qua Manager duyệt.
"""
from decimal import Decimal, ROUND_HALF_UP

CRITERIA = ("price", "delivery", "rating", "payment_terms")
NEUTRAL_RATING = Decimal("3")
HUNDRED = Decimal("100")
FORMULA = (
    "Tổng = (w_price·S_price + w_delivery·S_delivery + w_rating·S_rating + w_terms·S_terms) / 100; "
    "S_price = 100·P_min/P; S_delivery = 100·(D_min+1)/(D+1); S_rating = 100·R/5 (chưa có đánh giá: R = 3); "
    "S_terms = 100·T/T_max"
)


def validate_weights(weights):
    """Trả về dict trọng số hợp lệ hoặc ném ValueError kèm field errors (FR-RFQ-08)."""
    if not isinstance(weights, dict):
        raise ValueError({"scoring_weights": ["Must be an object."]})
    errors = {}
    unknown = set(weights) - set(CRITERIA)
    if unknown:
        errors["scoring_weights"] = [f"Unknown criteria: {', '.join(sorted(unknown))}."]
    cleaned = {}
    for criterion in CRITERIA:
        value = weights.get(criterion)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            errors[criterion] = ["Must be an integer between 0 and 100."]
        else:
            cleaned[criterion] = value
    if not errors and sum(cleaned.values()) != 100:
        errors["scoring_weights"] = ["Weights must add up to 100."]
    if errors:
        raise ValueError(errors)
    return cleaned


def _round(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def score_quotations(entries, weights):
    """entries: list dict có `id`, `total` (Decimal), `delivery_days`, `payment_term_days`, `rating` (Decimal|None).

    Trả về list cùng thứ tự xếp hạng, mỗi phần tử có điểm thành phần, tổng điểm và hạng.
    """
    if not entries:
        return []
    totals = [Decimal(entry["total"]) for entry in entries]
    positive_totals = [value for value in totals if value > 0]
    min_price = min(positive_totals) if positive_totals else Decimal("0")
    delivery_values = [entry["delivery_days"] for entry in entries if entry["delivery_days"] is not None]
    min_delivery = min(delivery_values) if delivery_values else None
    term_values = [entry["payment_term_days"] for entry in entries if entry["payment_term_days"] is not None]
    max_terms = max(term_values) if term_values else None

    results = []
    for entry, total in zip(entries, totals):
        price_score = HUNDRED if total <= 0 or min_price == 0 else HUNDRED * min_price / total
        if entry["delivery_days"] is None:
            delivery_score = Decimal("0")
        else:
            delivery_score = HUNDRED * Decimal(min_delivery + 1) / Decimal(entry["delivery_days"] + 1)
        rating = entry.get("rating")
        rating_score = HUNDRED * (rating if rating is not None else NEUTRAL_RATING) / Decimal("5")
        if entry["payment_term_days"] is None:
            terms_score = Decimal("0")
        elif not max_terms:
            terms_score = HUNDRED
        else:
            terms_score = HUNDRED * Decimal(entry["payment_term_days"]) / Decimal(max_terms)
        components = {
            "price": _round(price_score),
            "delivery": _round(delivery_score),
            "rating": _round(rating_score),
            "payment_terms": _round(terms_score),
        }
        total_score = sum(Decimal(weights[key]) * components[key] for key in CRITERIA) / HUNDRED
        results.append({
            "quotation_id": entry["id"],
            "components": components,
            "rating_available": rating is not None,
            "total_score": _round(total_score),
        })
    results.sort(key=lambda item: item["total_score"], reverse=True)
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank
    return results
