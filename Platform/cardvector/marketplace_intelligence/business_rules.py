"""Pure business-aware pricing rules applied after Fair Market Value."""

from __future__ import annotations

from decimal import (
    ROUND_CEILING,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Decimal,
)
from typing import Any

from .business_profile import BusinessProfile, MarketplaceProfile
from .models import (
    FairMarketValue,
    Listing,
    PriceRecommendation,
    ProfitabilityAnalysis,
)


CENT = Decimal("0.01")
HUNDRED = Decimal("100")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _ceil_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_CEILING)


def _listing_marketplace(listing: Listing, profile: BusinessProfile) -> str:
    raw_marketplace = str(
        listing.raw.get("Marketplace")
        or listing.raw.get("marketplace")
        or ""
    ).strip()
    if raw_marketplace:
        return raw_marketplace.lower()
    source = str(listing.source_type or "").lower()
    if source.startswith("ebay"):
        return "ebay"
    if source.startswith("tcgplayer"):
        return "tcgplayer"
    return profile.pricing_policy.default_marketplace


class BusinessRulesEngine:
    """Applies seller economics without recalculating FMV."""

    def __init__(self, profile: BusinessProfile | dict[str, Any] | None) -> None:
        self.profile = (
            profile
            if isinstance(profile, BusinessProfile)
            else BusinessProfile.from_mapping(profile)
        )

    def apply(
        self,
        listing: Listing,
        fair_market_value: FairMarketValue,
        recommendation: PriceRecommendation,
    ) -> PriceRecommendation:
        if not self.profile.business_rules_enabled:
            recommendation.business_profile_version = self.profile.profile_version
            recommendation.business_rule_adjustments = (
                "BUSINESS_PROFILE_LEGACY_COMPATIBILITY",
            )
            return recommendation

        marketplace_key = _listing_marketplace(listing, self.profile)
        marketplace = self.profile.marketplace(marketplace_key)
        if marketplace is None or not marketplace.active:
            recommendation.review_required = True
            recommendation.review_reason = (
                f"Marketplace profile '{marketplace_key}' is unavailable or inactive."
            )
            recommendation.business_recommendation = "Manual Review"
            recommendation.business_rule_adjustments = (
                "MARKETPLACE_PROFILE_REVIEW_REQUIRED",
            )
            recommendation.business_profile_version = self.profile.profile_version
            return recommendation

        acquisition_cost = (
            listing.acquisition_cost
            if listing.acquisition_cost is not None
            else self.profile.default_acquisition_cost
        )
        shipping_profile_key = self._shipping_profile_for_listing(
            listing,
            marketplace,
        )
        minimum_viable_price = self._minimum_viable_price(
            marketplace,
            acquisition_cost,
            shipping_profile_key,
        )
        baseline = (
            recommendation.final_listing_price
            or recommendation.recommended_listing_price
            or recommendation.recommended_price
        )
        target = baseline
        adjustments: list[str] = []
        if target < minimum_viable_price:
            target = minimum_viable_price
            adjustments.append("MINIMUM_VIABLE_PRICE")
        if target < self.profile.pricing_policy.minimum_price:
            target = self.profile.pricing_policy.minimum_price
            adjustments.append("MINIMUM_LISTING_PRICE")
        target = self._round_price(target)
        if target < minimum_viable_price:
            target = self._round_price(minimum_viable_price, upward=True)

        profitability = self._profitability(
            target,
            marketplace,
            acquisition_cost,
            minimum_viable_price,
            shipping_profile_key,
        )
        if profitability.free_shipping:
            adjustments.append("FREE_SHIPPING_BELOW_THRESHOLD")
        if recommendation.review_required or not fair_market_value.available:
            state = "Manual Review"
        elif profitability.estimated_net_profit < self.profile.pricing_policy.minimum_profit:
            state = "Do Not List"
            recommendation.review_required = True
            recommendation.review_reason = "Minimum profit requirement was not met."
            adjustments.append("MINIMUM_PROFIT_NOT_MET")
        elif target > listing.current_price:
            state = "Increase Price"
        elif target < listing.current_price:
            state = "Decrease Price"
        else:
            state = "No Change"

        difference = _money(target - listing.current_price)
        percent_change = Decimal("0.00")
        if listing.current_price > 0:
            percent_change = _money(
                difference / listing.current_price * HUNDRED
            )
        reason = recommendation.pricing_reason
        if adjustments:
            reason = (
                f"{reason} Business rules: {', '.join(adjustments)}; "
                f"minimum viable price ${minimum_viable_price}."
            )
        recommendation.recommended_price = target
        recommendation.recommended_listing_price = target
        recommendation.final_listing_price = target
        recommendation.difference = difference
        recommendation.percent_change = percent_change
        recommendation.pricing_reason = reason
        recommendation.profitability = profitability
        recommendation.marketplace = marketplace.key
        recommendation.business_recommendation = state
        recommendation.business_rule_adjustments = tuple(adjustments)
        recommendation.business_profile_version = self.profile.profile_version
        recommendation.reason_codes = tuple(
            dict.fromkeys((*recommendation.reason_codes, *adjustments))
        )
        return recommendation

    def _rounding(self, marketplace: MarketplaceProfile):
        if marketplace.fee_rounding == "half_even":
            return ROUND_HALF_EVEN
        return ROUND_HALF_UP

    def _fees(
        self,
        sale_price: Decimal,
        marketplace: MarketplaceProfile,
    ) -> tuple[Decimal, Decimal, Decimal]:
        rounding = self._rounding(marketplace)
        commission = marketplace.commission_fee_for(sale_price)
        if marketplace.commission_cap_per_item is not None:
            commission = min(commission, marketplace.commission_cap_per_item)
        commission = commission.quantize(CENT, rounding=rounding)
        processing = (sale_price * marketplace.processing_rate).quantize(
            CENT,
            rounding=rounding,
        )
        fixed = marketplace.fixed_fee_for(sale_price)
        return commission, processing, fixed

    def _costs_for_price(
        self,
        sale_price: Decimal,
        marketplace: MarketplaceProfile,
        acquisition_cost: Decimal,
        shipping_profile_key: str,
    ) -> tuple[Decimal, Decimal, str, bool]:
        shipping_profile = self.profile.shipping(shipping_profile_key)
        packaging_key = (
            shipping_profile.packaging_profile
            if shipping_profile is not None
            else marketplace.packaging_profile
        )
        packaging_cost = self.profile.packaging_cost(packaging_key)
        free_shipping = bool(
            marketplace.seller_pays_shipping_below_threshold
            and marketplace.free_shipping_threshold > 0
            and sale_price < marketplace.free_shipping_threshold
        )
        shipping_cost = (
            shipping_profile.postage_cost
            if free_shipping and shipping_profile is not None
            else Decimal("0.00")
        )
        return (
            _money(packaging_cost),
            _money(shipping_cost),
            shipping_profile.key if shipping_profile is not None else "",
            free_shipping,
        )

    def _profitability(
        self,
        sale_price: Decimal,
        marketplace: MarketplaceProfile,
        acquisition_cost: Decimal,
        minimum_viable_price: Decimal,
        shipping_profile_key: str,
    ) -> ProfitabilityAnalysis:
        commission, processing, fixed = self._fees(sale_price, marketplace)
        packaging, shipping, shipping_profile, free_shipping = (
            self._costs_for_price(
                sale_price,
                marketplace,
                acquisition_cost,
                shipping_profile_key,
            )
        )
        fees = _money(commission + processing + fixed)
        other = self.profile.pricing_policy.other_costs
        net = _money(
            sale_price
            - fees
            - shipping
            - packaging
            - acquisition_cost
            - other
        )
        margin = Decimal("0.00")
        if sale_price > 0:
            margin = (net / sale_price).quantize(
                Decimal("0.0001"),
                rounding=ROUND_HALF_UP,
            )
        return ProfitabilityAnalysis(
            marketplace=marketplace.key,
            estimated_fees=fees,
            estimated_shipping=shipping,
            estimated_packaging=packaging,
            acquisition_cost=_money(acquisition_cost),
            other_costs=_money(other),
            estimated_net_profit=net,
            profit_margin=margin,
            minimum_viable_price=minimum_viable_price,
            shipping_profile=shipping_profile,
            free_shipping=free_shipping,
            fee_components={
                "commission": commission,
                "payment_processing": processing,
                "fixed_order_fee": fixed,
            },
        )

    def _minimum_viable_price(
        self,
        marketplace: MarketplaceProfile,
        acquisition_cost: Decimal,
        shipping_profile_key: str,
    ) -> Decimal:
        policy = self.profile.pricing_policy
        minimum_price = Decimal(
            str(
                marketplace.pricing_overrides.get(
                    "minimum_price",
                    policy.minimum_price,
                )
            )
        )
        minimum_profit = Decimal(
            str(
                marketplace.pricing_overrides.get(
                    "minimum_profit",
                    policy.minimum_profit,
                )
            )
        )
        minimum_margin = Decimal(
            str(
                marketplace.pricing_overrides.get(
                    "minimum_profit_margin",
                    policy.minimum_profit_margin,
                )
            )
        )
        candidate = max(minimum_price, CENT)
        for _attempt in range(100):
            analysis = self._profitability(
                candidate,
                marketplace,
                acquisition_cost,
                candidate,
                shipping_profile_key,
            )
            profit_shortfall = minimum_profit - analysis.estimated_net_profit
            required_margin_profit = (
                candidate * minimum_margin
            )
            margin_shortfall = required_margin_profit - analysis.estimated_net_profit
            shortfall = max(profit_shortfall, margin_shortfall, Decimal("0.00"))
            if shortfall <= 0:
                return _ceil_money(candidate)
            rate = (
                marketplace.commission_rate_for(candidate)
                + marketplace.processing_rate
            )
            denominator = max(
                Decimal("0.01"),
                Decimal("1.00") - rate - minimum_margin,
            )
            candidate = _ceil_money(candidate + (shortfall / denominator))
        raise RuntimeError("Minimum viable price did not converge.")

    def _shipping_profile_for_listing(
        self,
        listing: Listing,
        marketplace: MarketplaceProfile,
    ) -> str:
        explicit = str(
            listing.raw.get("Shipping Profile")
            or listing.raw.get("shipping_profile")
            or ""
        ).strip()
        if explicit:
            profile = self.profile.shipping(explicit)
            if profile is not None and profile.enabled:
                return profile.key

        raw_weight = (
            listing.raw.get("Shipping Weight Oz")
            or listing.raw.get("shipping_weight_oz")
            or listing.raw.get("Weight Oz")
            or listing.raw.get("weight_oz")
        )
        try:
            weight_oz = int(str(raw_weight).strip()) if raw_weight else 0
        except (TypeError, ValueError):
            weight_oz = 0
        default_profile = self.profile.shipping(
            marketplace.default_shipping_profile
        )
        if weight_oz > 0 and default_profile is not None:
            for profile in self.profile.shipping_profiles.values():
                if (
                    profile.enabled
                    and profile.service == default_profile.service
                    and profile.weight_oz == weight_oz
                ):
                    return profile.key
        return marketplace.default_shipping_profile

    def _round_price(self, value: Decimal, *, upward: bool = False) -> Decimal:
        rule = self.profile.pricing_policy.rounding_rule.lower()
        if rule == "nearest_99":
            whole = int(value)
            candidate = Decimal(whole) + Decimal("0.99")
            if candidate < value:
                candidate += Decimal("1.00")
            return _money(candidate)
        if rule == "down_to_99" and not upward:
            whole = int(value)
            candidate = Decimal(whole) + Decimal("0.99")
            if candidate > value and whole > 0:
                candidate -= Decimal("1.00")
            return _money(max(candidate, self.profile.pricing_policy.minimum_price))
        if upward:
            return _ceil_money(value)
        return _money(value)


__all__ = ["BusinessRulesEngine"]
