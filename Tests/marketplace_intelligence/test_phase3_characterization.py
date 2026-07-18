from __future__ import annotations

import json
import sys
import tempfile
import unittest
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "Platform" / "Putnam_OS" / "System" / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from Platform.Marketplace_Intelligence.marketplace_intelligence.models import (
    AnalysisResult,
    Decision,
    FairMarketValue,
    Listing,
    ListingIdentity,
    MarketEvidence,
    MarketPrice,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.pricing_engine import (
    LEGACY_DEFAULT_LADDER,
    PricingEngine,
    apply_exact_price_ladder,
    apply_pricing_strategy,
    build_pricing_decision,
    evaluate_new_listing_price,
    fair_market_value_from_market_price,
    fair_market_value_from_market_report,
    optimized_export_price,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.pricing_repository import (
    PricingDecisionRepository,
    pricing_record_from_result,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.providers import (
    CardUploaderSalesCacheProvider,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.reports import (
    ANALYSIS_FIELDS,
    result_row,
)
import putnam_os as legacy_putnam_os  # noqa: E402


def strict_money(value) -> Decimal:
    if value is None:
        raise InvalidOperation("None")
    raw = str(value).strip().replace("$", "").replace(",", "")
    if not raw:
        raise InvalidOperation("blank")
    return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def listing(price: str = "4.00") -> Listing:
    return Listing(
        row_number=1,
        raw={},
        item_id="EBAY-1",
        title="Fixture Card 001 Test Set",
        current_price=Decimal(price),
        sku="ETB-001-A",
        condition="Near Mint",
    )


def fmv(value: str = "5.00", confidence: str = "85") -> FairMarketValue:
    evidence = MarketEvidence(
        source="fixture_ebay_sold",
        evidence_type="sold_comps_summary",
        value=Decimal(value),
        marketplace="ebay",
        condition="Near Mint",
        captured_at="2026-07-18T00:00:00+00:00",
        source_reference="fixture:sold-001",
    )
    return FairMarketValue(
        value=Decimal(value),
        confidence=confidence,
        reasoning="Fixture-backed sold-comps FMV.",
        evidence=(evidence,),
        evidence_reference="fixture:sold-001",
        calculated_at="2026-07-18T00:00:00+00:00",
        accepted_count=10,
    )


def profile(**overrides) -> dict[str, str]:
    values = {
        "minimum_price": "0.99",
        "ignore_changes_under": "0.00",
        "maximum_increase_percent": "999.00",
        "maximum_decrease_percent": "999.00",
        "maximum_increase_amount": "999.00",
        "maximum_decrease_amount": "999.00",
        "shipping_assumption": "buyer_pays_shipping",
        "flat_shipping_cost": "0.00",
        "rounding_rule": "nearest_cent",
        "review_price_over": "999999",
        "review_change_percent_over": "999999",
    }
    values.update(overrides)
    return values


class LegacyFmvCharacterizationTests(unittest.TestCase):
    def test_no_data_missing_fields_and_one_comparable_produce_no_fmv(self):
        for report in (
            None,
            {},
            {"accepted_count": 1, "confidence": 100, "median": "5.00"},
            {"accepted_count": 10, "confidence": 100},
        ):
            with self.subTest(report=report):
                result = fair_market_value_from_market_report(report)
                self.assertIsNone(result.value)
                self.assertFalse(result.available)

    def test_weighted_multiple_comparable_summary_is_exact(self):
        result = fair_market_value_from_market_report(
            {
                "accepted_count": 10,
                "confidence": 85,
                "median": "5.00",
                "last3_avg": "5.50",
                "last_sale": "4.50",
                "snapshot_id": "fixture:weighted-001",
            }
        )

        self.assertEqual(Decimal("5.10"), result.value)
        self.assertEqual("85", result.confidence)
        self.assertEqual(3, len(result.evidence))
        self.assertEqual("fixture:weighted-001", result.evidence_reference)

    def test_missing_weighted_component_renormalizes_existing_weights(self):
        result = fair_market_value_from_market_report(
            {
                "accepted_count": 3,
                "confidence": 75,
                "median": "5.00",
                "last3_avg": "",
                "last_sale": "4.00",
            }
        )

        self.assertEqual(Decimal("4.86"), result.value)

    def test_active_tcgplayer_and_pricecharting_are_not_raw_fmv(self):
        cases = (
            MarketPrice(
                matched=True,
                market_price=Decimal("4.50"),
                provider="TCGplayer",
                source="tcgplayer_live",
                confidence="high",
                metadata={"evidence_type": "active_listing", "marketplace": "tcgplayer"},
            ),
            MarketPrice(
                matched=True,
                market_price=Decimal("7.00"),
                provider="PriceCharting",
                source="pricecharting",
                confidence="high",
            ),
        )

        for market in cases:
            with self.subTest(source=market.source):
                result = fair_market_value_from_market_price(market)
                self.assertIsNone(result.value)
                self.assertFalse(result.evidence[0].accepted_for_fmv)

    def test_ebay_sold_summary_remains_accepted_fmv(self):
        market = MarketPrice(
            matched=True,
            market_price=Decimal("5.25"),
            provider="CardUploader eBay Sales",
            source="carduploader_ebay_sold_comps",
            confidence="85",
            metadata={
                "marketplace": "ebay",
                "accepted_comps": 8,
                "cache_file": "fixture:sales-cache",
            },
        )

        result = fair_market_value_from_market_price(market)

        self.assertEqual(Decimal("5.25"), result.value)
        self.assertEqual(8, result.accepted_count)
        self.assertTrue(result.evidence[0].accepted_for_fmv)

    def test_currency_is_usd_without_conversion(self):
        result = fair_market_value_from_market_report(
            {"accepted_count": 3, "median": "5.00", "confidence": 75}
        )
        self.assertEqual("USD", result.currency)
        self.assertEqual(Decimal("5.00"), result.value)


class PriceVectorCharacterizationTests(unittest.TestCase):
    REPORT = {
        "accepted_count": 10,
        "confidence": 85,
        "median": "5.00",
        "last3_avg": "5.50",
        "last_sale": "4.50",
    }

    def test_low_and_high_confidence_statuses_are_exact(self):
        low = build_pricing_decision(
            "3.99",
            {**self.REPORT, "confidence": 59},
            strategy="market_match",
        )
        high = build_pricing_decision(
            "3.99",
            {**self.REPORT, "confidence": 80},
            strategy="market_match",
        )

        self.assertEqual(Decimal("3.99"), low.final_listing_price)
        self.assertEqual("MANUAL_REVIEW_REQUIRED", low.review_status)
        self.assertEqual(Decimal("5.10"), high.final_listing_price)
        self.assertEqual("AUTO_APPLIED", high.review_status)

    def test_strategy_floor_and_unknown_strategy_behavior_are_exact(self):
        self.assertEqual(
            Decimal("0.99"),
            apply_pricing_strategy(Decimal("0.10"), "fast_sell"),
        )
        self.assertEqual(
            Decimal("5.25"),
            apply_pricing_strategy(Decimal("5.00"), "profit"),
        )
        with self.assertRaisesRegex(ValueError, "Unknown pricing strategy"):
            apply_pricing_strategy(Decimal("5.00"), "unknown")

    def test_configurable_caps_floor_shipping_and_rounding_are_exact(self):
        engine = PricingEngine(
            profile(
                maximum_increase_percent="10",
                maximum_increase_amount="1.00",
                shipping_assumption="seller_pays_shipping",
                flat_shipping_cost="1.25",
                rounding_rule="nearest_99",
            )
        )

        recommendation = engine.recommend_from_fmv(listing("4.00"), fmv("10.00"))

        self.assertEqual(Decimal("4.99"), recommendation.final_listing_price)
        self.assertEqual(Decimal("0.99"), recommendation.difference)

    def test_change_ceiling_and_decrease_floor_are_exact(self):
        engine = PricingEngine(
            profile(
                maximum_increase_percent="25",
                maximum_increase_amount="2.00",
                maximum_decrease_percent="25",
                maximum_decrease_amount="2.00",
            )
        )

        increase = engine.recommend_from_fmv(listing("4.00"), fmv("20.00"))
        decrease = engine.recommend_from_fmv(listing("8.00"), fmv("1.00"))

        self.assertEqual(Decimal("5.00"), increase.final_listing_price)
        self.assertEqual(Decimal("6.00"), decrease.final_listing_price)

    def test_no_acquisition_margin_input_is_part_of_current_contract(self):
        recommendation = PricingEngine(profile()).recommend_from_fmv(
            listing("4.00"),
            fmv("5.00"),
        )

        self.assertEqual(Decimal("5.00"), recommendation.final_listing_price)
        self.assertNotIn("margin", recommendation.pricing_reason.lower())

    def test_optimized_export_boundaries_are_exact(self):
        cases = {
            "0.50": "0.99",
            "1.50": "0.99",
            "1.51": "1.49",
            "2.99": "1.49",
            "3.00": "2.99",
            "4.99": "2.99",
            "5.00": "5.00",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(
                    Decimal(expected),
                    optimized_export_price(Decimal(source)),
                )

    def test_bulk_ladder_partial_failure_is_exact(self):
        processed, invalid = apply_exact_price_ladder(
            [
                {"old_price_raw": "1.49", "title": "Change"},
                {"old_price_raw": "3.99", "title": "No change"},
                {"old_price_raw": "", "title": "Invalid"},
            ],
            LEGACY_DEFAULT_LADDER,
            parse_money=strict_money,
            format_money=money_text,
        )

        self.assertEqual(("CHANGE", "0.99"), (processed[0]["status"], processed[0]["new_price"]))
        self.assertEqual(("UNCHANGED", "3.99"), (processed[1]["status"], processed[1]["new_price"]))
        self.assertEqual("INVALID_PRICE", invalid[0]["status"])

    def test_new_listing_review_threshold_is_exact(self):
        result = evaluate_new_listing_price(
            "20.00",
            LEGACY_DEFAULT_LADDER,
            floor=Decimal("0.99"),
            high_review_threshold=Decimal("20.00"),
            parse_money=strict_money,
            format_money=money_text,
        )

        self.assertEqual("REVIEW", result["status"])
        self.assertTrue(result["high_review"])
        self.assertEqual(Decimal("20.00"), result["new_price"])


class StoredEvidenceAndPersistenceCharacterizationTests(unittest.TestCase):
    def test_sales_cache_uses_current_duplicate_and_outlier_behavior(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache_dir = Path(temporary)
            cache = cache_dir / "Fixture_Card_Test_Set_001.json"
            cache.write_text(
                json.dumps(
                    {
                        "results": [
                            {"title": "Fixture Card Test Set 001", "price": "1.00"},
                            {"title": "Fixture Card Test Set 001", "price": "1.00"},
                            {"title": "Fixture Card Test Set 001", "price": "100.00"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            provider = CardUploaderSalesCacheProvider(
                {
                    "cache_dirs": [str(cache_dir)],
                    "minimum_accepted_comps": 3,
                    "minimum_confidence": 0,
                }
            )
            identity = ListingIdentity(
                lookup_key="fixture",
                match_method="title",
                confidence="high",
                details={
                    "parsed_card_name": "Fixture Card",
                    "parsed_set": "Test Set",
                    "parsed_card_number": "001",
                    "provider_query": "Fixture Card Test Set 001",
                },
            )

            result = provider.get_market_price(identity)

        self.assertTrue(result.matched)
        self.assertEqual(Decimal("1.00"), result.market_price)
        self.assertEqual(3, result.metadata["accepted_comps"])
        self.assertEqual("34.00", result.metadata["last3_avg"])

    def test_serialization_fields_and_values_are_exact(self):
        market_fmv = fmv()
        recommendation = PricingEngine(profile()).recommend_from_fmv(
            listing(),
            market_fmv,
        )
        analysis = AnalysisResult(
            listing=listing(),
            identity=ListingIdentity("fixture", "sku", "high"),
            market=MarketPrice(
                matched=True,
                market_price=Decimal("5.00"),
                provider="fixture",
                source="fixture_sold",
                confidence="85",
            ),
            pricing=recommendation,
            decision=Decision("Increase", "Fixture.", True),
            fair_market_value=market_fmv,
        )

        row = result_row(analysis)

        self.assertEqual(list(ANALYSIS_FIELDS), list(row))
        self.assertEqual("5.00", row["fair_market_value"])
        self.assertEqual("5.00", row["recommended_listing_price"])
        self.assertEqual("5.00", row["final_listing_price"])
        self.assertIn('"accepted_for_fmv":true', row["normalized_market_evidence"])

    def test_pricing_repository_round_trip_is_exact(self):
        market_fmv = fmv()
        recommendation = PricingEngine(profile()).recommend_from_fmv(
            listing(),
            market_fmv,
        )
        analysis = AnalysisResult(
            listing=listing(),
            identity=ListingIdentity("fixture", "sku", "high"),
            market=MarketPrice(
                matched=True,
                market_price=Decimal("5.00"),
                provider="fixture",
                source="fixture_sold",
                confidence="85",
            ),
            pricing=recommendation,
            decision=Decision("Increase", "Fixture.", True),
            fair_market_value=market_fmv,
        )

        with tempfile.TemporaryDirectory() as temporary:
            repository = PricingDecisionRepository(Path(temporary) / "pricing.sqlite")
            record = pricing_record_from_result(
                analysis,
                decision_id="PHASE3-BASELINE",
                created_at="2026-07-18T00:00:00+00:00",
            )
            repository.save(record)
            loaded = repository.get("PHASE3-BASELINE")

        self.assertEqual(record, loaded)


class PutnamComparableCharacterizationTests(unittest.TestCase):
    def test_diagnostics_accept_and_reject_shapes_are_exact(self):
        accepted = legacy_putnam_os.comp_match_diagnostics(
            "Fixture Card Test Set 001 Near Mint",
            "Fixture Card",
            "Test Set",
            "001",
        )
        rejected = legacy_putnam_os.comp_match_diagnostics(
            "Fixture Card Test Set 001 PSA 10",
            "Fixture Card",
            "Test Set",
            "001",
        )

        self.assertEqual("accepted", accepted["final_rejection_reason"])
        self.assertEqual("yes", accepted["card_number_match"])
        self.assertEqual(100, accepted["name_match_score"])
        self.assertEqual("excluded graded term", rejected["final_rejection_reason"])
        self.assertIn("psa", rejected["excluded_terms_found"])

    def test_market_analysis_report_error_and_rejection_contracts_are_exact(self):
        rows = [
            {
                "*Title": "Fixture Card Test Set 001",
                "*StartPrice": "0.99",
                "*C:Card Name": "Fixture Card",
                "*C:Set": "Test Set",
                "*C:Card Number": "001",
            },
            {
                "*Title": "Broken Card Test Set 002",
                "*StartPrice": "2.99",
                "*C:Card Name": "Broken Card",
                "*C:Set": "Test Set",
                "*C:Card Number": "002",
            },
        ]

        def sales(query):
            if "Broken Card" in query:
                raise RuntimeError("fixture provider unavailable")
            return {
                "results": [
                    {"title": "Fixture Card Test Set 001", "price": "3.00"},
                    {"title": "Fixture Card Test Set 001", "price": "3.00"},
                    {"title": "Fixture Card Test Set 001", "price": "3.00"},
                    {"title": "Fixture Card Test Set 001 PSA 10", "price": "50.00"},
                ]
            }

        with patch.object(legacy_putnam_os, "fetch_carduploader_sales", side_effect=sales):
            reports, rejected, analytics = legacy_putnam_os.market_analyze(rows)

        self.assertEqual("NO_CHANGE", reports[0]["status"])
        self.assertEqual(3, reports[0]["accepted_count"])
        self.assertEqual(57, reports[0]["confidence"])
        self.assertEqual(Decimal("3.00"), reports[0]["median"])
        self.assertEqual("ERROR", reports[1]["status"])
        self.assertEqual("fixture provider unavailable", reports[1]["reason"])
        self.assertEqual("excluded graded term", rejected[0]["reject_reason"])
        self.assertEqual(1, analytics[0]["Rejected Candidates"])
        self.assertEqual(1, analytics[0]["Rejected: excluded graded term"])


if __name__ == "__main__":
    unittest.main()
