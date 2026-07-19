"""Application-layer pricing orchestration over an injected canonical service."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol


class PricingOperations(Protocol):
    def optimized_export_price(
        self,
        market_price: Decimal,
        export_floor: Decimal,
    ) -> Decimal: ...

    def calculate_market_value(
        self,
        market_report: dict[str, Any] | None,
    ) -> Decimal: ...

    def apply_pricing_strategy(
        self,
        market_value: Decimal,
        strategy: str,
        export_floor: Decimal,
    ) -> Decimal: ...

    def build_pricing_decision(
        self,
        original_price: Any,
        market_report: dict[str, Any] | None,
        strategy: str,
        review_threshold: int,
        auto_apply_threshold: int,
        export_floor: Decimal,
        listing=None,
        business_profile=None,
    ) -> Any: ...

    def evaluate_existing_listing(self, request, *, engine=None) -> Any: ...


class PricingApplication:
    """Coordinates pricing requests without containing pricing mathematics."""

    def __init__(self, pricing: PricingOperations) -> None:
        self._pricing = pricing

    def optimized_export_price(
        self,
        market_price: Decimal,
        *,
        export_floor: Decimal,
    ) -> Decimal:
        return self._pricing.optimized_export_price(
            market_price,
            export_floor=export_floor,
        )

    def calculate_market_value(
        self,
        market_report: dict[str, Any] | None,
    ) -> Decimal:
        return self._pricing.calculate_market_value(market_report)

    def apply_pricing_strategy(
        self,
        market_value: Decimal,
        strategy: str,
        *,
        export_floor: Decimal,
    ) -> Decimal:
        return self._pricing.apply_pricing_strategy(
            market_value,
            strategy,
            export_floor=export_floor,
        )

    def build_pricing_decision(
        self,
        *,
        original_price: Any,
        market_report: dict[str, Any] | None,
        strategy: str,
        review_threshold: int,
        auto_apply_threshold: int,
        export_floor: Decimal,
        listing=None,
        business_profile=None,
    ) -> Any:
        return self._pricing.build_pricing_decision(
            original_price=original_price,
            market_report=market_report,
            strategy=strategy,
            review_threshold=review_threshold,
            auto_apply_threshold=auto_apply_threshold,
            export_floor=export_floor,
            listing=listing,
            business_profile=business_profile,
        )

    def evaluate_existing_listing(self, request, *, engine=None) -> Any:
        return self._pricing.evaluate_existing_listing(
            request,
            engine=engine,
        )


__all__ = ["PricingApplication", "PricingOperations"]
