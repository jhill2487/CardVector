from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from Platform.Putnam_OS.System.MarketIntelligence.Models.market_snapshot import MarketSnapshot


@dataclass
class MarketIntelligenceReport:
    card: dict[str, Any]
    provider_summary: dict[str, Any]
    pricing_summary: dict[str, Any]
    marketplace_summary: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    confidence: str = "UNKNOWN"

    def summary(self) -> str:
        return (
            f"{self.card['card_name']} | {self.card['set_name']} {self.card['card_number']}\n"
            f"Providers: {self.provider_summary['provider_count']}\n"
            f"Confidence: {self.confidence}\n"
            f"Warnings: {', '.join(self.warnings) if self.warnings else 'None'}"
        )


def build_market_report(snapshot: MarketSnapshot) -> MarketIntelligenceReport:
    warnings = []

    if not snapshot.sold:
        warnings.append("Missing sold market data")
    if not snapshot.tcgtracking:
        warnings.append("Missing TCGTracking data")
    if not snapshot.ebay_active:
        warnings.append("Missing eBay Active data")

    provider_count = snapshot.provider_count
    confidence = (
        "A" if provider_count >= 4 else
        "B" if provider_count == 3 else
        "C" if provider_count == 2 else
        "D"
    )

    return MarketIntelligenceReport(
        card={
            "card_name": snapshot.card_name,
            "set_name": snapshot.set_name,
            "card_number": snapshot.card_number,
        },
        provider_summary={
            "provider_count": provider_count,
            "providers": {
                "sold": bool(snapshot.sold),
                "ebay_active": bool(snapshot.ebay_active),
                "tcgtracking": bool(snapshot.tcgtracking),
                "internal_history": bool(snapshot.internal_history),
            },
        },
        pricing_summary={
            "sold": snapshot.sold,
            "ebay_active": snapshot.ebay_active,
            "tcgtracking": snapshot.tcgtracking,
        },
        marketplace_summary={},
        warnings=warnings,
        confidence=confidence,
    )
