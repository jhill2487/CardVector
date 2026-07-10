from decimal import Decimal

from Platform.Putnam_OS.System.MarketIntelligence.Pricing import (
    build_pricing_decision,
)

report = {
    "accepted_count": 10,
    "confidence": 85,
    "median": "5.00",
    "last3_avg": "5.50",
    "last_sale": "4.50",
}

decision = build_pricing_decision(
    original_price="3.99",
    market_report=report,
    strategy="market_match",
)

assert decision.market_value == Decimal("5.10"), decision
assert decision.recommended_price == Decimal("5.10"), decision
assert decision.review_status == "AUTO_APPLIED", decision

print("Pricing Engine package test passed.")
print(decision)
