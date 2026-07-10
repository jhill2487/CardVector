from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PricingDecision:
    original_price: Decimal
    market_value: Decimal
    recommended_price: Decimal
    accepted_count: int
    confidence: int
    strategy: str
    pricing_basis: str
    review_status: str
