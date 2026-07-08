from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .config import decimal_setting
from .models import Listing, MarketPrice, PriceRecommendation


class PricingEngine:
    """Configurable pricing calculator reusable by Putnam OS."""

    def __init__(self, pricing_profile: dict):
        self.profile = pricing_profile

    def recommend(self, listing: Listing, market: MarketPrice) -> PriceRecommendation:
        current = listing.current_price
        if not market.matched or market.market_price is None:
            return PriceRecommendation(
                recommended_price=current,
                difference=Decimal("0.00"),
                percent_change=Decimal("0.00"),
                pricing_reason="No market price available.",
                review_required=True,
                review_reason="Unmatched listing.",
            )

        target = self.apply_market_strategy(current, market.market_price)
        target = self.apply_change_limits(current, target)
        target = self.apply_minimum_price(target)
        target = self.apply_rounding(target)
        difference = (target - current).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        percent_change = Decimal("0.00")
        if current > 0:
            percent_change = ((difference / current) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ignore = decimal_setting(self.profile, "ignore_changes_under", "0.00")
        if abs(difference) < ignore:
            target = current
            difference = Decimal("0.00")
            percent_change = Decimal("0.00")
            reason = f"Change below ignore threshold ${ignore}."
        else:
            reason = f"Market ${market.market_price}; configurable strategy target ${target}."
        review_required, review_reason = self.review_check(current, target, market.market_price)
        return PriceRecommendation(
            recommended_price=target,
            difference=difference,
            percent_change=percent_change,
            pricing_reason=reason,
            review_required=review_required,
            review_reason=review_reason,
        )

    def apply_market_strategy(self, current: Decimal, market_price: Decimal) -> Decimal:
        mode = str(self.profile.get("market_strategy", "match_market")).lower()
        if mode == "undercut_market":
            amount = decimal_setting(self.profile, "undercut_amount", "0.00")
            return market_price - amount
        if mode == "hold_if_within_band":
            band = decimal_setting(self.profile, "hold_band_percent", "5.00")
            if current > 0:
                delta = abs((market_price - current) / current) * Decimal("100")
                if delta <= band:
                    return current
        return market_price

    def apply_minimum_price(self, value: Decimal) -> Decimal:
        minimum = decimal_setting(self.profile, "minimum_price", "0.01")
        return max(value, minimum)

    def apply_change_limits(self, current: Decimal, target: Decimal) -> Decimal:
        max_increase_pct = decimal_setting(self.profile, "maximum_increase_percent", "9999")
        max_decrease_pct = decimal_setting(self.profile, "maximum_decrease_percent", "9999")
        max_increase_amt = decimal_setting(self.profile, "maximum_increase_amount", "999999")
        max_decrease_amt = decimal_setting(self.profile, "maximum_decrease_amount", "999999")
        increase_cap = min(current + max_increase_amt, current * (Decimal("1") + (max_increase_pct / Decimal("100"))))
        decrease_floor = max(current - max_decrease_amt, current * (Decimal("1") - (max_decrease_pct / Decimal("100"))))
        if target > current:
            return min(target, increase_cap)
        if target < current:
            return max(target, decrease_floor)
        return target

    def apply_rounding(self, value: Decimal) -> Decimal:
        mode = str(self.profile.get("rounding_rule", "nearest_cent")).lower()
        if mode == "nearest_99":
            whole = int(value)
            candidate = Decimal(whole) + Decimal("0.99")
            if candidate < value:
                candidate += Decimal("1.00")
            return candidate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if mode == "down_to_99":
            whole = int(value)
            candidate = Decimal(whole) + Decimal("0.99")
            if candidate > value and whole > 0:
                candidate -= Decimal("1.00")
            return self.apply_minimum_price(candidate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def review_check(self, current: Decimal, recommended: Decimal, market: Decimal) -> tuple[bool, str]:
        high_price = decimal_setting(self.profile, "review_price_over", "999999")
        review_delta = decimal_setting(self.profile, "review_change_percent_over", "999999")
        if recommended >= high_price:
            return True, f"Recommended price is above review threshold ${high_price}."
        if current > 0:
            delta = abs((recommended - current) / current) * Decimal("100")
            if delta >= review_delta:
                return True, f"Change exceeds review threshold {review_delta}%."
        if market <= 0:
            return True, "Invalid market price."
        return False, ""
