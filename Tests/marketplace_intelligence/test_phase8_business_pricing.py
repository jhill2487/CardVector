from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

from Platform.cardvector.application.pricing import PricingApplication
from Platform.cardvector.marketplace_intelligence import (
    BusinessProfile,
    BusinessRulesEngine,
    ExistingListingRequest,
    FairMarketValue,
    Listing,
    ListingIdentity,
    MarketPrice,
    PricingService,
    PricingPipeline,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.config import (
    CONFIG_DIR,
    load_app_config,
    save_pricing_profile,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.decision_engine import (
    DecisionEngine,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.pricing_engine import (
    PricingEngine,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.pricing_repository import (
    PricingDecisionRepository,
    pricing_record_from_result,
)
from Platform.Marketplace_Intelligence.marketplace_intelligence.reports import (
    ANALYSIS_FIELDS,
    result_row,
)


def canonical_profile() -> BusinessProfile:
    config = load_app_config()
    return BusinessProfile.from_mapping(
        config.business_profile,
        config.pricing_profile,
    )


class FixedIdentity:
    def identify(self, listing: Listing) -> ListingIdentity:
        return ListingIdentity(
            lookup_key=listing.sku or listing.title,
            match_method="fixture",
            confidence="high",
            details={"parsed_card_name": listing.title},
        )


class FixedMarket:
    def __init__(self, value: str = "1.49") -> None:
        self.value = Decimal(value)

    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        return MarketPrice(
            matched=True,
            market_price=self.value,
            provider="Phase 8 fixture",
            source="fixture_sold_comps",
            confidence="high",
            reason="Fixture evidence.",
            metadata={
                "marketplace": "ebay",
                "accepted_comps": 5,
                "median": str(self.value),
                "average": str(self.value),
                "captured_at": "2026-07-19T12:00:00+00:00",
            },
        )


def build_pipeline(value: str = "1.49") -> PricingPipeline:
    profile = canonical_profile()
    return PricingPipeline(
        identity=FixedIdentity(),
        market=FixedMarket(value),
        price_vector=PricingEngine(profile.price_vector_profile()),
        decision=DecisionEngine(profile.to_dict()),
        pricing_profile=profile.price_vector_profile(),
        business_profile=profile,
    )


class BusinessProfileTests(unittest.TestCase):
    def test_canonical_profile_contains_business_shipping_and_marketplace_rules(self):
        profile = canonical_profile()

        self.assertEqual("Putnam Collectibles", profile.business_name)
        self.assertEqual("USD", profile.currency)
        self.assertEqual(Decimal("0.05"), profile.default_acquisition_cost)
        self.assertEqual(
            Decimal("0.15"),
            profile.packaging_cost("standard_envelope"),
        )
        self.assertEqual(
            Decimal("0.78"),
            profile.shipping("ebay_standard_envelope_1oz").postage_cost,
        )
        self.assertEqual(
            Decimal("1.07"),
            profile.shipping("ebay_standard_envelope_2oz").postage_cost,
        )
        self.assertEqual(
            Decimal("1.36"),
            profile.shipping("ebay_standard_envelope_3oz").postage_cost,
        )
        self.assertTrue(profile.marketplace("ebay").active)
        self.assertTrue(profile.marketplace("tcgplayer").active)
        self.assertFalse(profile.marketplace("whatnot").active)

    def test_legacy_profiles_remain_behaviorally_compatible(self):
        legacy = BusinessProfile.from_mapping(
            {"business_name": "Legacy"},
            {"minimum_price": "0.99", "rounding_rule": "nearest_cent"},
        )
        listing = Listing(1, {}, "", "Legacy", Decimal("1.00"))
        recommendation = PricingEngine(
            legacy.price_vector_profile()
        ).recommend_from_fmv(
            listing,
            FairMarketValue(Decimal("1.50"), confidence="high"),
        )

        result = BusinessRulesEngine(legacy).apply(
            listing,
            FairMarketValue(Decimal("1.50"), confidence="high"),
            recommendation,
        )

        self.assertEqual(Decimal("1.50"), result.final_listing_price)
        self.assertIsNone(result.profitability)
        self.assertIn(
            "BUSINESS_PROFILE_LEGACY_COMPATIBILITY",
            result.business_rule_adjustments,
        )

    def test_pricing_settings_save_updates_only_canonical_business_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            business = json.loads(
                (CONFIG_DIR / "business_profile.json").read_text(encoding="utf-8")
            )
            legacy = {"minimum_price": "0.99", "rounding_rule": "nearest_cent"}
            (directory / "business_profile.json").write_text(
                json.dumps(business),
                encoding="utf-8",
            )
            (directory / "pricing_profile.json").write_text(
                json.dumps(legacy),
                encoding="utf-8",
            )

            save_pricing_profile(
                {
                    **business["pricing_policy"]["price_vector"],
                    "minimum_price": "2.25",
                },
                directory,
            )

            saved_business = json.loads(
                (directory / "business_profile.json").read_text(encoding="utf-8")
            )
            saved_legacy = json.loads(
                (directory / "pricing_profile.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "2.25",
                saved_business["pricing_policy"]["price_vector"]["minimum_price"],
            )
            self.assertEqual("2.25", saved_business["pricing_policy"]["minimum_price"])
            self.assertEqual(legacy, saved_legacy)


class BusinessRulesTests(unittest.TestCase):
    def test_ebay_recommendation_includes_all_costs_and_minimum_viable_price(self):
        listing = Listing(
            1,
            {"Marketplace": "ebay"},
            "",
            "Low Value Card",
            Decimal("0.99"),
        )
        result = build_pipeline("1.49").analyze_listing(listing)
        economics = result.pricing.profitability

        self.assertEqual(Decimal("1.77"), result.pricing.final_listing_price)
        self.assertEqual(Decimal("0.53"), economics.estimated_fees)
        self.assertEqual(Decimal("0.78"), economics.estimated_shipping)
        self.assertEqual(Decimal("0.15"), economics.estimated_packaging)
        self.assertEqual(Decimal("0.05"), economics.acquisition_cost)
        self.assertEqual(Decimal("0.26"), economics.estimated_net_profit)
        self.assertEqual(Decimal("1.77"), economics.minimum_viable_price)
        self.assertTrue(economics.free_shipping)
        self.assertEqual("Manual Review", result.pricing.business_recommendation)
        self.assertIn(
            "MINIMUM_VIABLE_PRICE",
            result.pricing.business_rule_adjustments,
        )

    def test_free_shipping_threshold_is_configurable_and_not_hardcoded(self):
        profile_data = canonical_profile().to_dict()
        profile_data["marketplaces"]["ebay"]["free_shipping_threshold"] = "5.00"
        profile = BusinessProfile.from_mapping(profile_data)
        listing = Listing(
            1,
            {"Marketplace": "ebay"},
            "",
            "Threshold Card",
            Decimal("6.00"),
        )
        recommendation = PricingEngine(
            profile.price_vector_profile()
        ).recommend_from_fmv(
            listing,
            FairMarketValue(Decimal("6.00"), confidence="high"),
        )

        result = BusinessRulesEngine(profile).apply(
            listing,
            FairMarketValue(Decimal("6.00"), confidence="high"),
            recommendation,
        )

        self.assertFalse(result.profitability.free_shipping)
        self.assertEqual(Decimal("0.00"), result.profitability.estimated_shipping)

    def test_listing_weight_selects_configured_standard_envelope_rate(self):
        profile = canonical_profile()
        listing = Listing(
            1,
            {"Marketplace": "ebay", "Shipping Weight Oz": "3"},
            "",
            "Three Ounce Card",
            Decimal("3.00"),
        )
        recommendation = PricingEngine(
            profile.price_vector_profile()
        ).recommend_from_fmv(
            listing,
            FairMarketValue(Decimal("3.00"), confidence="high"),
        )

        result = BusinessRulesEngine(profile).apply(
            listing,
            FairMarketValue(Decimal("3.00"), confidence="high"),
            recommendation,
        )

        self.assertEqual(
            "ebay_standard_envelope_3oz",
            result.profitability.shipping_profile,
        )
        self.assertEqual(
            Decimal("1.36"),
            result.profitability.estimated_shipping,
        )

    def test_tcgplayer_profile_applies_commission_and_processing_fees(self):
        profile = canonical_profile()
        listing = Listing(
            1,
            {"Marketplace": "tcgplayer"},
            "",
            "TCGplayer Card",
            Decimal("5.00"),
            source_type="tcgplayer_existing_listing",
        )
        recommendation = PricingEngine(
            profile.price_vector_profile()
        ).recommend_from_fmv(
            listing,
            FairMarketValue(Decimal("5.00"), confidence="high"),
        )

        result = BusinessRulesEngine(profile).apply(
            listing,
            FairMarketValue(Decimal("5.00"), confidence="high"),
            recommendation,
        )

        economics = result.profitability
        self.assertEqual("tcgplayer", economics.marketplace)
        self.assertEqual(Decimal("0.96"), economics.estimated_fees)
        self.assertEqual(Decimal("0.15"), economics.estimated_packaging)
        self.assertEqual(Decimal("0.00"), economics.estimated_shipping)
        self.assertEqual(Decimal("3.84"), economics.estimated_net_profit)

    def test_card_level_acquisition_cost_overrides_default(self):
        profile = canonical_profile()
        listing = Listing(
            1,
            {"Marketplace": "ebay"},
            "",
            "Costly Card",
            Decimal("0.99"),
            acquisition_cost=Decimal("1.50"),
            acquisition_method="collection",
            acquisition_cost_confidence="high",
        )
        recommendation = PricingEngine(
            profile.price_vector_profile()
        ).recommend_from_fmv(
            listing,
            FairMarketValue(Decimal("1.49"), confidence="high"),
        )

        result = BusinessRulesEngine(profile).apply(
            listing,
            FairMarketValue(Decimal("1.49"), confidence="high"),
            recommendation,
        )

        self.assertEqual(
            Decimal("1.50"),
            result.profitability.acquisition_cost,
        )
        self.assertGreater(result.final_listing_price, Decimal("1.77"))

    def test_marketplace_profit_margin_override_changes_minimum_viable_price(self):
        profile_data = canonical_profile().to_dict()
        profile_data["marketplaces"]["ebay"]["pricing_overrides"] = {
            "minimum_profit_margin": "0.25"
        }
        profile = BusinessProfile.from_mapping(profile_data)
        listing = Listing(
            1,
            {"Marketplace": "ebay"},
            "",
            "Margin Card",
            Decimal("0.99"),
        )
        fmv = FairMarketValue(Decimal("1.49"), confidence="high")
        recommendation = PricingEngine(
            profile.price_vector_profile()
        ).recommend_from_fmv(listing, fmv)

        result = BusinessRulesEngine(profile).apply(
            listing,
            fmv,
            recommendation,
        )

        self.assertGreaterEqual(
            result.profitability.profit_margin,
            Decimal("0.25"),
        )
        self.assertGreater(result.profitability.minimum_viable_price, Decimal("1.77"))

    def test_no_market_data_stays_manual_review(self):
        profile = canonical_profile()
        listing = Listing(1, {"Marketplace": "ebay"}, "", "Unknown", Decimal("3.00"))
        fmv = FairMarketValue(None, confidence="none")
        recommendation = PricingEngine(
            profile.price_vector_profile()
        ).recommend_from_fmv(listing, fmv)

        result = BusinessRulesEngine(profile).apply(listing, fmv, recommendation)

        self.assertEqual(Decimal("3.00"), result.final_listing_price)
        self.assertEqual("Manual Review", result.business_recommendation)
        self.assertTrue(result.review_required)
        self.assertIsNotNone(result.profitability)

    def test_no_market_data_still_enforces_business_floor(self):
        profile = canonical_profile()
        listing = Listing(
            1,
            {"Marketplace": "ebay"},
            "",
            "Unknown Low Value",
            Decimal("0.99"),
        )
        fmv = FairMarketValue(None, confidence="none")
        recommendation = PricingEngine(
            profile.price_vector_profile()
        ).recommend_from_fmv(listing, fmv)

        result = BusinessRulesEngine(profile).apply(listing, fmv, recommendation)

        self.assertEqual(Decimal("1.77"), result.final_listing_price)
        self.assertEqual("Manual Review", result.business_recommendation)
        self.assertIn("MINIMUM_VIABLE_PRICE", result.business_rule_adjustments)


class UnifiedWorkflowAndPersistenceTests(unittest.TestCase):
    def test_pipeline_always_invokes_business_rules_before_decision(self):
        profile = BusinessProfile.from_mapping(
            {},
            {"minimum_price": "0.99"},
        )
        listing = Listing(1, {}, "", "Stage Card", Decimal("1.00"))
        business_rules = Mock()
        recommendation = PricingEngine(
            profile.price_vector_profile()
        ).recommend_from_fmv(
            listing,
            FairMarketValue(Decimal("2.00"), confidence="high"),
        )
        business_rules.apply.return_value = recommendation
        pipeline = PricingPipeline(
            identity=FixedIdentity(),
            market=FixedMarket("2.00"),
            price_vector=PricingEngine(profile.price_vector_profile()),
            decision=DecisionEngine({}),
            pricing_profile=profile.price_vector_profile(),
            business_profile=profile,
            business_rules=business_rules,
        )

        pipeline.analyze_listing(listing)

        business_rules.apply.assert_called_once()

    def test_existing_and_carduploader_inventory_use_same_pricing_pipeline(self):
        pipeline = build_pipeline("4.00")
        new_listing = Listing(
            1,
            {},
            "",
            "Unified Card",
            Decimal("3.00"),
            source_type="carduploader_export",
            sku="UNIFIED-1",
        )

        new_result = pipeline.analyze_listing(new_listing)
        existing_result = pipeline.evaluate_existing_listing(
            ExistingListingRequest(
                marketplace="ebay",
                listing_title="Unified Card",
                current_price=Decimal("3.00"),
                sku="UNIFIED-1",
            )
        )

        self.assertEqual(
            new_result.pricing.final_listing_price,
            existing_result.recommended_price,
        )
        self.assertEqual(
            new_result.pricing.profitability.to_dict(),
            existing_result.estimated_profitability.to_dict(),
        )

    def test_application_market_report_path_applies_business_profile(self):
        profile = canonical_profile()
        listing = Listing(
            1,
            {"Marketplace": "ebay"},
            "",
            "Application Card",
            Decimal("0.99"),
            source_type="carduploader_ebay_export",
        )
        decision = PricingApplication(PricingService()).build_pricing_decision(
            original_price=listing.current_price,
            market_report={
                "marketplace": "ebay",
                "accepted_count": 5,
                "confidence": 90,
                "median": "1.49",
                "last3_avg": "1.49",
                "last_sale": "1.49",
            },
            strategy="market_match",
            review_threshold=60,
            auto_apply_threshold=80,
            export_floor=Decimal("0.99"),
            listing=listing,
            business_profile=profile,
        )

        self.assertEqual(Decimal("1.77"), decision.final_listing_price)
        self.assertEqual(Decimal("0.26"), decision.profitability.estimated_net_profit)
        self.assertEqual("ebay", decision.marketplace)
        self.assertIn("MINIMUM_VIABLE_PRICE", decision.business_rule_adjustments)

    def test_reports_and_repository_preserve_profitability(self):
        result = build_pipeline("1.49").analyze_listing(
            Listing(
                1,
                {"Marketplace": "ebay"},
                "ITEM-8",
                "Persisted Card",
                Decimal("0.99"),
            )
        )
        row = result_row(result)
        for field in (
            "estimated_fees",
            "estimated_shipping",
            "estimated_packaging",
            "acquisition_cost",
            "estimated_net_profit",
            "profit_margin",
            "minimum_viable_price",
            "business_recommendation",
        ):
            self.assertIn(field, ANALYSIS_FIELDS)
            self.assertTrue(row[field])

        with tempfile.TemporaryDirectory() as temporary:
            repository = PricingDecisionRepository(
                Path(temporary) / "pricing.sqlite"
            )
            record = pricing_record_from_result(
                result,
                decision_id="PHASE8-1",
            )
            repository.save(record)
            loaded = repository.get("PHASE8-1")

        self.assertEqual(Decimal("0.53"), loaded.estimated_fees)
        self.assertEqual(Decimal("0.78"), loaded.estimated_shipping)
        self.assertEqual(Decimal("0.15"), loaded.estimated_packaging)
        self.assertEqual(Decimal("0.05"), loaded.acquisition_cost)
        self.assertEqual(Decimal("0.26"), loaded.estimated_net_profit)
        self.assertEqual("Manual Review", loaded.business_recommendation)


if __name__ == "__main__":
    unittest.main()
