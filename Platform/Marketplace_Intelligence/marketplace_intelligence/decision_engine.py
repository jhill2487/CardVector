from __future__ import annotations

from decimal import Decimal

from .models import Decision, Listing, MarketPrice, PriceRecommendation


class DecisionEngine:
    """Turns pricing calculations into seller-facing recommendations."""

    def __init__(self, business_profile: dict):
        self.profile = business_profile

    def decide(self, listing: Listing, market: MarketPrice, pricing: PriceRecommendation) -> Decision:
        if not market.matched:
            return Decision("Review", "Listing was not matched to market data.", False, True)
        if market.metadata.get("reference_only"):
            return Decision(
                "Review",
                f"{market.provider} price is reference-only for eBay repricing; manual review required.",
                False,
                True,
            )
        if pricing.review_required:
            return Decision("Review", pricing.review_reason or "Manual review threshold reached.", False, True)
        if pricing.difference == Decimal("0.00"):
            return Decision("No Change", pricing.pricing_reason, False, False)
        if pricing.difference > 0:
            return Decision("Increase", pricing.pricing_reason, True, False)
        return Decision("Decrease", pricing.pricing_reason, True, False)
