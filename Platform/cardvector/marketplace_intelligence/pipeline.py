"""Canonical Marketplace Intelligence analysis sequence."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable, Iterable, Protocol

from .explainability import build_pricing_explanation
from .models import (
    AnalysisResult,
    Decision,
    ExistingListingEvaluation,
    ExistingListingRequest,
    Listing,
    ListingIdentity,
    MarketPrice,
    PriceRecommendation,
    ReviewThresholds,
)
from .pricing import fair_market_value_from_market_price


class IdentityOperations(Protocol):
    def identify(self, listing: Listing) -> ListingIdentity: ...


class MarketOperations(Protocol):
    def get_market_price(self, identity: ListingIdentity) -> MarketPrice: ...


class PriceVectorOperations(Protocol):
    def recommend_from_fmv(self, listing, fair_market_value) -> PriceRecommendation: ...


class DecisionOperations(Protocol):
    def decide(
        self,
        listing: Listing,
        market: MarketPrice,
        pricing: PriceRecommendation,
    ) -> Decision: ...


class PricingPipeline:
    """Coordinates the one approved pricing path without owning provider math."""

    def __init__(
        self,
        *,
        identity: IdentityOperations,
        market: MarketOperations,
        price_vector: PriceVectorOperations,
        decision: DecisionOperations,
        pricing_profile: dict | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._identity = identity
        self._market = market
        self._price_vector = price_vector
        self._decision = decision
        self._thresholds = ReviewThresholds.from_profile(pricing_profile)
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    @property
    def thresholds(self) -> ReviewThresholds:
        return self._thresholds

    def analyze_listing(self, listing: Listing) -> AnalysisResult:
        identity = self._identity.identify(listing)
        market = self._market.get_market_price(identity)
        fair_market_value = fair_market_value_from_market_price(market)
        pricing = self._price_vector.recommend_from_fmv(
            listing,
            fair_market_value,
        )
        decision = self._decision.decide(listing, market, pricing)
        explanation = build_pricing_explanation(
            listing=listing,
            identity=identity,
            market=market,
            fair_market_value=fair_market_value,
            pricing=pricing,
            decision=decision,
            thresholds=self._thresholds,
            now=self._now_provider(),
        )
        pricing.reason_codes = explanation.reason_codes
        pricing.explanation = explanation
        return AnalysisResult(
            listing=listing,
            identity=identity,
            market=market,
            pricing=pricing,
            decision=decision,
            fair_market_value=fair_market_value,
            explanation=explanation,
        )

    def analyze_listings(self, listings: Iterable[Listing]) -> list[AnalysisResult]:
        return [self.analyze_listing(listing) for listing in listings]

    def evaluate_existing_listing(
        self,
        request: ExistingListingRequest,
    ) -> ExistingListingEvaluation:
        marketplace = str(request.marketplace or "").strip().lower()
        title = str(request.listing_title or "").strip()
        if not marketplace:
            raise ValueError("Marketplace is required.")
        if not title:
            raise ValueError("Listing title is required.")
        try:
            current_price = Decimal(str(request.current_price))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("Current price must be numeric.") from exc
        if current_price < 0:
            raise ValueError("Current price cannot be negative.")

        listing = Listing(
            row_number=1,
            raw={
                "Marketplace": marketplace,
                "Title": title,
                "Current Price": str(current_price),
                "Quantity": str(request.quantity or ""),
                "SKU": str(request.sku or ""),
                "Condition": str(request.condition or ""),
                "Set": str(request.set_name or ""),
                "Card Number": str(request.card_number or ""),
                "Variant": str(request.variant or ""),
                "Finish": str(request.finish or ""),
            },
            item_id=str(request.listing_id or ""),
            title=title,
            current_price=current_price,
            source_type=f"{marketplace}_existing_listing",
            sku=str(request.sku or ""),
            quantity=str(request.quantity or ""),
            condition=str(request.condition or ""),
            set_name=str(request.set_name or ""),
            card_number=str(request.card_number or ""),
            variant=str(request.variant or ""),
            finish=str(request.finish or ""),
        )
        result = self.analyze_listing(listing)
        explanation = result.explanation
        if explanation is None:
            raise RuntimeError("Pricing pipeline did not produce an explanation.")
        matched_card = str(
            result.identity.details.get("parsed_card_name")
            or result.identity.lookup_key
            or title
        )
        return ExistingListingEvaluation(
            marketplace=marketplace,
            listing_reference=str(request.listing_id or request.sku or title),
            matched_card=matched_card,
            match_confidence=result.identity.confidence,
            recommended_price=explanation.recommended_price,
            price_delta=result.pricing.difference,
            review_priority=explanation.review_priority,
            review_decision=explanation.review_decision,
            reason_codes=explanation.reason_codes,
            explanation=explanation,
        )


__all__ = [
    "DecisionOperations",
    "IdentityOperations",
    "MarketOperations",
    "PriceVectorOperations",
    "PricingPipeline",
]
