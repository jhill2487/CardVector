from __future__ import annotations

import json
import inspect
import tempfile
import time
import tracemalloc
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

from Platform.cardvector.application import PricingApplication
from Platform.cardvector.marketplace_intelligence import (
    ExistingListingRequest,
    PricingPipeline,
    PricingReasonCode,
)
from Platform.cardvector.marketplace_intelligence import explainability, pipeline
from Platform.cardvector.marketplace_intelligence.evidence import comparable_reason
from Platform.Marketplace_Intelligence.marketplace_intelligence.bulk_export import (
    BULK_REVISE_FIELDS,
    bulk_revise_rows,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.decision_engine import (
    DecisionEngine,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.listing_parser import (
    ListingMatcher,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.models import (
    ExistingListingEvaluation,
    Listing,
    ListingIdentity,
    MarketPrice,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.pricing_engine import (
    PricingEngine,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.providers import (
    CardUploaderSalesCacheProvider,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.reports import (
    ANALYSIS_FIELDS,
    result_row,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "phase7_benchmark.json"
)
FIXED_NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)


def pricing_profile(**overrides) -> dict:
    profile = {
        "minimum_price": "0.99",
        "market_strategy": "match_market",
        "ignore_changes_under": "0.00",
        "maximum_increase_percent": "9999",
        "maximum_decrease_percent": "9999",
        "maximum_increase_amount": "999999",
        "maximum_decrease_amount": "999999",
        "rounding_rule": "nearest_cent",
        "review_price_over": "100.00",
        "review_change_percent_over": "999999",
        "shipping_assumption": "buyer_pays_shipping",
        "flat_shipping_cost": "0.00",
        "auto_approve_confidence": 80,
        "manual_review_below_confidence": 60,
        "warning_below_confidence": 70,
        "insufficient_data_comps": 3,
        "stale_market_days": 30,
        "price_spike_percent": "40.00",
        "price_collapse_percent": "40.00",
        "high_variance_percent": "35.00",
    }
    profile.update(overrides)
    return profile


class FixtureProvider:
    def __init__(self, cases: list[dict], captured_at: str) -> None:
        self.by_sku = {case["sku"]: case for case in cases}
        self.captured_at = captured_at
        self.calls = 0

    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        self.calls += 1
        case = self.by_sku.get(identity.lookup_key)
        if case is None:
            return MarketPrice(
                matched=False,
                provider="Phase 7 Fixture",
                source="fixture_ebay_sold_comps",
                confidence="none",
                reason="No fixture evidence.",
            )
        return MarketPrice(
            matched=True,
            market_price=Decimal(case["fmv"]),
            provider="Phase 7 Fixture",
            source="fixture_ebay_sold_comps",
            confidence=case["confidence"],
            reason="Fixture-backed eBay sold comparables.",
            metadata={
                "marketplace": "ebay",
                "accepted_comps": case["accepted_count"],
                "rejected_comps": case["rejected_count"],
                "median": case["fmv"],
                "average": case["average"],
                "price_low": case["price_low"],
                "price_high": case["price_high"],
                "outliers_removed": 0,
                "captured_at": self.captured_at,
                "variant": case["variant"],
                "finish": case["finish"],
                "evidence_type": "sold_comps_summary",
                "source_url": f"fixture:{case['id']}",
            },
        )


def load_benchmark() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def listing_from_case(case: dict) -> Listing:
    return Listing(
        row_number=1,
        raw={},
        item_id=f"ITEM-{case['id']}",
        title=case["title"],
        current_price=Decimal(case["current_price"]),
        sku=case["sku"],
        quantity="1",
        condition="Near Mint",
        variant=case["variant"],
        finish=case["finish"],
    )


def build_fixture_pipeline(data: dict, **profile_overrides):
    provider = FixtureProvider(data["cases"], data["captured_at"])
    profile = pricing_profile(**profile_overrides)
    pipeline = PricingPipeline(
        identity=ListingMatcher(),
        market=provider,
        price_vector=PricingEngine(profile),
        decision=DecisionEngine({}),
        pricing_profile=profile,
        now_provider=lambda: FIXED_NOW,
    )
    return pipeline, provider


class BenchmarkCoverageTests(unittest.TestCase):
    def test_benchmark_contains_all_required_market_segments(self):
        categories = {case["category"] for case in load_benchmark()["cases"]}
        required = {
            "modern Pokemon",
            "vintage Pokemon",
            "promos",
            "reverse holos",
            "special illustration rares",
            "trainer gallery",
            "EX",
            "GX",
            "V",
            "VMAX",
            "Illustration Rare",
            "Secret Rare",
            "low value",
            "high value",
            "high volatility",
            "stable market",
        }
        self.assertTrue(required.issubset(categories))

    def test_benchmark_is_exactly_repeatable(self):
        data = load_benchmark()
        snapshots = []
        for _run in range(5):
            pipeline, _provider = build_fixture_pipeline(data)
            snapshot = []
            for case in data["cases"]:
                result = pipeline.analyze_listing(listing_from_case(case))
                self.assertEqual(
                    Decimal(case["expected_price"]),
                    result.pricing.final_listing_price,
                )
                snapshot.append(
                    {
                        "id": case["id"],
                        "price": str(result.pricing.final_listing_price),
                        "confidence": result.explanation.confidence,
                        "reason_codes": result.explanation.reason_codes,
                        "review_decision": result.explanation.review_decision,
                    }
                )
            snapshots.append(snapshot)
        self.assertTrue(all(snapshot == snapshots[0] for snapshot in snapshots))


class ExplainabilityTests(unittest.TestCase):
    def test_every_benchmark_result_has_complete_explanation(self):
        data = load_benchmark()
        pipeline, _provider = build_fixture_pipeline(data)

        for case in data["cases"]:
            with self.subTest(case=case["id"]):
                result = pipeline.analyze_listing(listing_from_case(case))
                explanation = result.explanation
                self.assertIsNotNone(explanation)
                self.assertEqual(
                    result.pricing.final_listing_price,
                    explanation.recommended_price,
                )
                self.assertEqual(case["accepted_count"], explanation.comparable_count)
                self.assertEqual(Decimal(case["fmv"]), explanation.median_sold)
                self.assertTrue(explanation.reason_codes)
                self.assertTrue(explanation.summary)
                self.assertIs(result.pricing.explanation, explanation)
                self.assertEqual(
                    result.pricing.reason_codes,
                    explanation.reason_codes,
                )

    def test_promos_variance_confidence_and_review_codes_are_explicit(self):
        data = load_benchmark()
        pipeline, _provider = build_fixture_pipeline(data)
        by_id = {
            case["id"]: pipeline.analyze_listing(listing_from_case(case))
            for case in data["cases"]
        }

        self.assertIn(
            PricingReasonCode.PROMO_VARIANT.value,
            by_id["promo"].explanation.reason_codes,
        )
        self.assertIn(
            PricingReasonCode.HIGH_VARIANCE.value,
            by_id["high_volatility"].explanation.reason_codes,
        )
        self.assertEqual(
            "MANUAL_REVIEW",
            by_id["high_volatility"].explanation.review_decision,
        )
        self.assertIn(
            PricingReasonCode.LOW_CONFIDENCE.value,
            by_id["low_confidence"].explanation.reason_codes,
        )
        self.assertIn(
            PricingReasonCode.HIGH_CONFIDENCE.value,
            by_id["stable_market"].explanation.reason_codes,
        )
        self.assertEqual(
            "unknown",
            by_id["stable_market"].explanation.market_trend,
        )

    def test_missing_evidence_and_unverified_variant_never_look_confident(self):
        data = load_benchmark()
        pipeline, _provider = build_fixture_pipeline(data)
        missing = Listing(
            row_number=1,
            raw={},
            item_id="MISSING",
            title="Unknown Benchmark Card",
            current_price=Decimal("4.00"),
            sku="MISSING",
            variant="Reverse Holo",
        )
        result = pipeline.analyze_listing(missing)

        self.assertIn(
            PricingReasonCode.NO_MARKET_DATA.value,
            result.explanation.reason_codes,
        )
        self.assertIn(
            PricingReasonCode.VARIANT_UNVERIFIED.value,
            result.explanation.reason_codes,
        )
        self.assertEqual("INSUFFICIENT_DATA", result.explanation.review_decision)
        self.assertEqual(Decimal("4.00"), result.pricing.final_listing_price)

    def test_explainability_thresholds_are_configurable_without_changing_price(self):
        data = load_benchmark()
        case = next(case for case in data["cases"] if case["id"] == "vintage")
        default_pipeline, _ = build_fixture_pipeline(data)
        permissive_pipeline, _ = build_fixture_pipeline(
            data,
            auto_approve_confidence=70,
            warning_below_confidence=50,
        )

        default = default_pipeline.analyze_listing(listing_from_case(case))
        permissive = permissive_pipeline.analyze_listing(listing_from_case(case))

        self.assertEqual(
            default.pricing.final_listing_price,
            permissive.pricing.final_listing_price,
        )
        self.assertEqual("REVIEW_RECOMMENDED", default.explanation.review_decision)
        self.assertEqual("AUTO_APPROVE", permissive.explanation.review_decision)


class PipelineAndExistingListingTests(unittest.TestCase):
    def test_pipeline_calls_each_stage_once_in_order(self):
        listing = Listing(1, {}, "ITEM-1", "Fixture", Decimal("4.00"))
        identity = ListingIdentity("fixture", "test", "high")
        market = MarketPrice(
            True,
            Decimal("5.00"),
            "Fixture",
            "fixture_sold",
            "85",
            metadata={
                "accepted_comps": 5,
                "captured_at": "2026-07-18T12:00:00+00:00",
            },
        )
        matcher = Mock()
        provider = Mock()
        price_vector = Mock()
        decision_engine = Mock()
        matcher.identify.return_value = identity
        provider.get_market_price.return_value = market
        pricing = PricingEngine(pricing_profile()).recommend(
            listing,
            market,
        )
        decision = DecisionEngine({}).decide(listing, market, pricing)
        price_vector.recommend_from_fmv.return_value = pricing
        decision_engine.decide.return_value = decision
        pipeline = PricingPipeline(
            identity=matcher,
            market=provider,
            price_vector=price_vector,
            decision=decision_engine,
            pricing_profile=pricing_profile(),
            now_provider=lambda: FIXED_NOW,
        )

        result = pipeline.analyze_listing(listing)

        matcher.identify.assert_called_once_with(listing)
        provider.get_market_price.assert_called_once_with(identity)
        price_vector.recommend_from_fmv.assert_called_once()
        decision_engine.decide.assert_called_once_with(listing, market, pricing)
        self.assertIsNotNone(result.explanation)

    def test_existing_listing_api_is_read_only_and_serializable(self):
        data = load_benchmark()
        case = data["cases"][0]
        pipeline, provider = build_fixture_pipeline(data)
        request = ExistingListingRequest(
            marketplace="ebay",
            listing_title=case["title"],
            current_price=Decimal(case["current_price"]),
            quantity="2",
            sku=case["sku"],
            condition="Near Mint",
            listing_id="1234567890",
            variant=case["variant"],
            finish=case["finish"],
        )

        evaluation = pipeline.evaluate_existing_listing(request)
        serialized = evaluation.to_dict()

        self.assertIsInstance(evaluation, ExistingListingEvaluation)
        self.assertEqual("ebay", evaluation.marketplace)
        self.assertEqual("1234567890", evaluation.listing_reference)
        self.assertEqual(Decimal(case["expected_price"]), evaluation.recommended_price)
        self.assertEqual("high", evaluation.match_confidence)
        self.assertEqual("Benchmark Spark", evaluation.matched_card)
        self.assertEqual(1, provider.calls)
        self.assertEqual(
            str(evaluation.recommended_price),
            serialized["recommended_price"],
        )
        self.assertNotIn("action", serialized)

    def test_application_layer_delegates_existing_listing_evaluation(self):
        service = Mock()
        expected = object()
        service.evaluate_existing_listing.return_value = expected
        application = PricingApplication(service)
        request = ExistingListingRequest(
            marketplace="ebay",
            listing_title="Fixture",
            current_price=Decimal("1.00"),
        )

        actual = application.evaluate_existing_listing(request, engine="fixture")

        self.assertIs(expected, actual)
        service.evaluate_existing_listing.assert_called_once_with(
            request,
            engine="fixture",
        )

    def test_invalid_existing_listing_input_is_rejected_without_provider_call(self):
        data = load_benchmark()
        pipeline, provider = build_fixture_pipeline(data)
        with self.assertRaisesRegex(ValueError, "Marketplace is required"):
            pipeline.evaluate_existing_listing(
                ExistingListingRequest("", "Fixture", Decimal("1.00"))
            )
        self.assertEqual(0, provider.calls)

    def test_phase7_path_has_no_ui_inventory_capture_or_live_mutation_dependency(self):
        source = "\n".join(
            inspect.getsource(module).lower()
            for module in (pipeline, explainability)
        )
        for forbidden in (
            "tkinter",
            "filedialog",
            "cardvector.capture",
            "cardvector.inventory",
            "revise_listing",
            "publish_listing",
            "send_offer",
            "requests.",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


class ComparableAndExportContractTests(unittest.TestCase):
    def test_current_comparable_guards_remain_exact(self):
        accepted, reason, _details = comparable_reason(
            "Fixture Card Test Set 001",
            "Fixture Card",
            "Test Set",
            "001",
        )
        self.assertTrue(accepted)
        self.assertEqual("accepted", reason)

        for title, expected_reason in (
            ("Fixture Card Test Set 001 PSA 10", "excluded graded term"),
            ("Fixture Card Test Set 999", "card number mismatch"),
            ("Different Card Test Set 001", "card name mismatch"),
        ):
            with self.subTest(title=title):
                accepted, reason, _details = comparable_reason(
                    title,
                    "Fixture Card",
                    "Test Set",
                    "001",
                )
                self.assertFalse(accepted)
                self.assertEqual(expected_reason, reason)

    def test_analysis_export_is_additive_and_bulk_contract_is_unchanged(self):
        data = load_benchmark()
        case = data["cases"][0]
        pipeline, _provider = build_fixture_pipeline(data)
        result = pipeline.analyze_listing(listing_from_case(case))

        row = result_row(result)
        bulk_rows = bulk_revise_rows([result])

        for legacy_field in (
            "fair_market_value",
            "recommended_price",
            "recommended_listing_price",
            "final_listing_price",
            "review_required",
        ):
            self.assertIn(legacy_field, row)
        for explanation_field in (
            "primary_market",
            "comparable_count",
            "median_sold",
            "average_sold",
            "market_trend",
            "review_decision",
            "review_priority",
            "reason_codes",
            "pricing_explanation",
        ):
            self.assertIn(explanation_field, ANALYSIS_FIELDS)
            self.assertTrue(row[explanation_field])
        self.assertEqual(
            [
                "Action",
                "ItemID",
                "StartPrice",
                "Title",
                "CustomLabel",
                "MarketplaceIntelligenceReason",
            ],
            BULK_REVISE_FIELDS,
        )
        self.assertEqual(set(BULK_REVISE_FIELDS), set(bulk_rows[0]))


class CacheAndPerformanceTests(unittest.TestCase):
    def test_sales_cache_reuses_unchanged_json_and_preserves_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / "carduploader_sales_fixture_card_test_set_001.json"
            cache.write_text(
                json.dumps(
                    {
                        "captured_at": "2026-07-18T12:00:00+00:00",
                        "results": [
                            {"title": "Fixture Card Test Set 001", "price": "5.00"},
                            {"title": "Fixture Card Test Set 001", "price": "5.10"},
                            {"title": "Fixture Card Test Set 001", "price": "4.90"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            provider = CardUploaderSalesCacheProvider(
                {
                    "cache_dirs": [str(root)],
                    "minimum_accepted_comps": 3,
                    "minimum_confidence": 0,
                }
            )
            identity = ListingIdentity(
                "fixture",
                "fixture",
                "high",
                details={
                    "parsed_card_name": "Fixture Card",
                    "parsed_set": "Test Set",
                    "parsed_card_number": "001",
                    "provider_query": "Fixture Card Test Set 001",
                },
            )

            first = provider.get_market_price(identity)
            second = provider.get_market_price(identity)

        self.assertEqual(first, second)
        self.assertEqual(1, provider.cache_misses)
        self.assertEqual(1, provider.cache_hits)

    def test_fixture_pipeline_has_bounded_runtime_and_memory(self):
        data = load_benchmark()
        pipeline, provider = build_fixture_pipeline(data)
        listings = [
            listing_from_case(data["cases"][index % len(data["cases"])])
            for index in range(500)
        ]
        tracemalloc.start()
        started = time.perf_counter()
        results = pipeline.analyze_listings(listings)
        elapsed = time.perf_counter() - started
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.assertEqual(500, len(results))
        self.assertEqual(500, provider.calls)
        self.assertLess(elapsed, 5.0)
        self.assertLess(peak, 20 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
