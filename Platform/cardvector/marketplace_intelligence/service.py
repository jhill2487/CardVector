"""Dependency-injectable Marketplace Intelligence pricing service."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from . import pricing
from .business_profile import BusinessProfile
from .business_rules import BusinessRulesEngine
from .models import (
    ExistingListingRequest,
    FairMarketValue,
    Listing,
    MarketPrice,
    PriceRecommendation,
)


class PricingService:
    """Stable service facade; all calculations delegate to the proven engine."""

    def decimal_money(self, value: Any) -> Decimal:
        return pricing.decimal_money(value)

    def fair_market_value_from_market_report(
        self,
        market_report: dict[str, Any] | None,
    ):
        return pricing.fair_market_value_from_market_report(market_report)

    def fair_market_value_from_market_price(self, market: MarketPrice):
        return pricing.fair_market_value_from_market_price(market)

    def calculate_market_value(
        self,
        market_report: dict[str, Any] | None,
    ) -> Decimal:
        return pricing.calculate_market_value(market_report)

    def apply_pricing_strategy(
        self,
        market_value: Decimal,
        strategy: str = "market_match",
        export_floor: Decimal = pricing.DEFAULT_EXPORT_FLOOR,
    ) -> Decimal:
        return pricing.apply_pricing_strategy(
            market_value,
            strategy,
            export_floor=export_floor,
        )

    def build_pricing_decision_from_fmv(
        self,
        original_price: Any,
        fair_market_value: FairMarketValue,
        strategy: str = "market_match",
        review_threshold: int = 60,
        auto_apply_threshold: int = 80,
        export_floor: Decimal = pricing.DEFAULT_EXPORT_FLOOR,
        listing: Listing | None = None,
        business_profile: BusinessProfile | dict[str, Any] | None = None,
    ):
        decision = pricing.build_pricing_decision_from_fmv(
            original_price=original_price,
            fair_market_value=fair_market_value,
            strategy=strategy,
            review_threshold=review_threshold,
            auto_apply_threshold=auto_apply_threshold,
            export_floor=export_floor,
        )
        if listing is None or business_profile is None:
            return decision
        return self._apply_business_rules_to_decision(
            decision,
            listing,
            fair_market_value,
            business_profile,
        )

    def build_pricing_decision(
        self,
        original_price: Any,
        market_report: dict[str, Any] | None,
        strategy: str = "market_match",
        review_threshold: int = 60,
        auto_apply_threshold: int = 80,
        export_floor: Decimal = pricing.DEFAULT_EXPORT_FLOOR,
        listing: Listing | None = None,
        business_profile: BusinessProfile | dict[str, Any] | None = None,
    ):
        fair_market_value = pricing.fair_market_value_from_market_report(
            market_report
        )
        return self.build_pricing_decision_from_fmv(
            original_price=original_price,
            fair_market_value=fair_market_value,
            strategy=strategy,
            review_threshold=review_threshold,
            auto_apply_threshold=auto_apply_threshold,
            export_floor=export_floor,
            listing=listing,
            business_profile=business_profile,
        )

    def recommend_from_fmv(
        self,
        listing: Listing,
        fair_market_value: FairMarketValue,
        pricing_profile: dict[str, Any],
        business_profile: BusinessProfile | dict[str, Any] | None = None,
    ):
        recommendation = pricing.PricingEngine(
            pricing_profile
        ).recommend_from_fmv(
            listing,
            fair_market_value,
        )
        normalized = (
            business_profile
            if isinstance(business_profile, BusinessProfile)
            else BusinessProfile.from_mapping(
                business_profile,
                pricing_profile,
            )
        )
        return BusinessRulesEngine(normalized).apply(
            listing,
            fair_market_value,
            recommendation,
        )

    def _apply_business_rules_to_decision(
        self,
        decision,
        listing: Listing,
        fair_market_value: FairMarketValue,
        business_profile: BusinessProfile | dict[str, Any],
    ):
        recommended = (
            decision.recommended_listing_price
            or decision.recommended_price
        )
        difference = recommended - listing.current_price
        percent_change = Decimal("0.00")
        if listing.current_price > 0:
            percent_change = (
                difference / listing.current_price * Decimal("100")
            ).quantize(Decimal("0.01"))
        recommendation = PriceRecommendation(
            recommended_price=recommended,
            difference=difference,
            percent_change=percent_change,
            pricing_reason=(
                f"{decision.pricing_basis}: "
                f"{fair_market_value.reasoning}"
            ),
            review_required=decision.review_status in {
                "MANUAL_REVIEW_REQUIRED",
                "NO_MARKET_DATA",
            },
            review_reason=decision.review_status,
            fair_market_value=fair_market_value.value,
            fair_market_value_confidence=fair_market_value.confidence,
            fair_market_value_reasoning=fair_market_value.reasoning,
            recommended_listing_price=recommended,
            final_listing_price=decision.final_listing_price,
            market_evidence=fair_market_value.evidence,
            market_evidence_reference=fair_market_value.evidence_reference,
        )
        profile = (
            business_profile
            if isinstance(business_profile, BusinessProfile)
            else BusinessProfile.from_mapping(business_profile)
        )
        business_result = BusinessRulesEngine(profile).apply(
            listing,
            fair_market_value,
            recommendation,
        )
        review_status = decision.review_status
        if (
            business_result.business_recommendation
            in {"Manual Review", "Do Not List"}
            and review_status not in {"NO_MARKET_DATA", "MANUAL_REVIEW_REQUIRED"}
        ):
            review_status = "MANUAL_REVIEW_REQUIRED"
        return replace(
            decision,
            recommended_price=business_result.recommended_listing_price,
            recommended_listing_price=business_result.recommended_listing_price,
            final_listing_price=business_result.final_listing_price,
            review_status=review_status,
            marketplace=business_result.marketplace,
            profitability=business_result.profitability,
            business_recommendation=business_result.business_recommendation,
            business_rule_adjustments=(
                business_result.business_rule_adjustments
            ),
            business_profile_version=business_result.business_profile_version,
        )

    def optimized_export_price(
        self,
        market_price: Decimal,
        export_floor: Decimal = pricing.DEFAULT_EXPORT_FLOOR,
    ) -> Decimal:
        return pricing.optimized_export_price(
            market_price,
            export_floor=export_floor,
        )

    def normalize_price_ladder(self, ladder, *, parse_money, format_money):
        return pricing.normalize_price_ladder(
            ladder,
            parse_money=parse_money,
            format_money=format_money,
        )

    def apply_exact_price_ladder(
        self,
        records,
        ladder,
        *,
        parse_money,
        format_money,
    ):
        return pricing.apply_exact_price_ladder(
            records,
            ladder,
            parse_money=parse_money,
            format_money=format_money,
        )

    def evaluate_new_listing_price(
        self,
        source_price,
        ladder,
        *,
        floor,
        high_review_threshold,
        parse_money,
        format_money,
    ):
        return pricing.evaluate_new_listing_price(
            source_price,
            ladder,
            floor=floor,
            high_review_threshold=high_review_threshold,
            parse_money=parse_money,
            format_money=format_money,
        )

    def evaluate_existing_listing(
        self,
        request: ExistingListingRequest,
        *,
        engine=None,
    ):
        """Evaluate an existing listing without performing marketplace writes."""

        if engine is None:
            from Platform.Marketplace_Intelligence.marketplace_intelligence.engine import (
                MarketplaceIntelligenceEngine,
            )

            engine = MarketplaceIntelligenceEngine()
        return engine.evaluate_existing_listing(request)


PRICING_SERVICE = PricingService()

__all__ = ["PRICING_SERVICE", "PricingService"]
