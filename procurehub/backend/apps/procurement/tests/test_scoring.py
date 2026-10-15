from decimal import Decimal

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.procurement.models import SupplierSelection
from apps.procurement.scoring import score_quotations, validate_weights
from apps.procurement.tests.flow import ProcurementFlowMixin

WEIGHTS = {"price": 45, "delivery": 25, "rating": 20, "payment_terms": 10}


class ScoringFormulaTests(SimpleTestCase):
    def test_components_and_total_follow_published_formula(self):
        results = score_quotations([
            {"id": "a", "total": Decimal("18000000"), "delivery_days": 10, "payment_term_days": 30, "rating": None},
            {"id": "b", "total": Decimal("20000000"), "delivery_days": 3, "payment_term_days": 45, "rating": Decimal("5")},
        ], WEIGHTS)
        by_id = {item["quotation_id"]: item for item in results}
        self.assertEqual(by_id["a"]["components"]["price"], Decimal("100.00"))
        self.assertEqual(by_id["b"]["components"]["price"], Decimal("90.00"))
        # S_delivery = 100 * (3 + 1) / (10 + 1)
        self.assertEqual(by_id["a"]["components"]["delivery"], Decimal("36.36"))
        self.assertEqual(by_id["a"]["components"]["rating"], Decimal("60.00"))
        self.assertFalse(by_id["a"]["rating_available"])
        self.assertEqual(by_id["a"]["components"]["payment_terms"], Decimal("66.67"))
        expected_a = (45 * Decimal("100") + 25 * Decimal("36.36") + 20 * Decimal("60") + 10 * Decimal("66.67")) / 100
        self.assertEqual(by_id["a"]["total_score"], expected_a.quantize(Decimal("0.01")))
        self.assertEqual([item["rank"] for item in results], [1, 2])

    def test_missing_optional_values_score_zero(self):
        results = score_quotations([
            {"id": "a", "total": Decimal("10"), "delivery_days": None, "payment_term_days": None, "rating": None},
        ], WEIGHTS)
        self.assertEqual(results[0]["components"]["delivery"], Decimal("0.00"))
        self.assertEqual(results[0]["components"]["payment_terms"], Decimal("0.00"))

    def test_weights_must_be_integers_summing_to_100(self):
        self.assertEqual(validate_weights(WEIGHTS), WEIGHTS)
        for invalid in (
            {**WEIGHTS, "price": 50},
            {**WEIGHTS, "price": "45"},
            {**WEIGHTS, "speed": 0},
            {"price": 100},
        ):
            with self.assertRaises(ValueError):
                validate_weights(invalid)


class ScoringApiTests(ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()

    def test_invalid_weights_return_422(self):
        rfq = self.open_rfq()
        response = self.client.post(f"/api/v1/rfqs/{rfq['id']}/scoring-weights", {"scoring_weights": {**WEIGHTS, "price": 60}}, format="json")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["code"], "validation_error")

    def test_comparison_returns_scoring_and_selection_keeps_snapshot(self):
        rfq, tech_quote, _ = self.closed_rfq_with_quotes()
        self.ok(self.client.post(f"/api/v1/rfqs/{rfq['id']}/scoring-weights", {"scoring_weights": {"price": 90, "delivery": 0, "rating": 5, "payment_terms": 5}}, format="json"))
        comparison = self.ok(self.client.get(f"/api/v1/rfqs/{rfq['id']}/comparison"))
        scoring = comparison["scoring"]
        self.assertEqual(scoring["weights"]["price"], 90)
        self.assertIn("formula", scoring)
        top = scoring["results"][0]
        self.assertEqual(top["quotation_id"], tech_quote["id"])
        self.assertEqual(Decimal(top["components"]["price"]), Decimal("100.00"))

        selection = self.ok(self.client.post(f"/api/v1/rfqs/{rfq['id']}/selection", {
            "quotation_id": tech_quote["id"], "rationale": "Điểm cao nhất",
        }, format="json"), status.HTTP_201_CREATED)
        snapshot = SupplierSelection.objects.get(pk=selection["id"]).score_snapshot
        self.assertEqual(snapshot["weights"]["price"], 90)
        self.assertEqual(snapshot["selected"]["rank"], 1)
        self.assertEqual(len(snapshot["ranking"]), 2)

    def test_weights_locked_after_award(self):
        po = self.issued_po()
        rfq_id = SupplierSelection.objects.get(pk=po["selection"]).rfq_id
        self.as_user(self.buyer)
        response = self.client.post(f"/api/v1/rfqs/{rfq_id}/scoring-weights", {"scoring_weights": WEIGHTS}, format="json")
        self.assertEqual(response.status_code, 409)
