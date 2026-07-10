from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

@dataclass
class MarketSnapshot:
    """Canonical market evidence for one CardUploader row.

    This model contains facts only. It does not calculate prices or choose
    marketplaces.
    """

    # CardUploader identity (system of record)
    card_name: str
    set_name: str
    card_number: str
    title: str = ""
    language: str = "EN"
    condition: str = "NM"

    # Evidence from providers
    sold: dict[str, Any] = field(default_factory=dict)
    ebay_active: dict[str, Any] = field(default_factory=dict)
    tcgtracking: dict[str, Any] = field(default_factory=dict)
    internal_history: dict[str, Any] = field(default_factory=dict)

    def add_provider(self, provider: str, evidence: dict[str, Any]) -> None:
        provider = provider.lower()
        if provider == "sold":
            self.sold.update(evidence)
        elif provider == "ebay_active":
            self.ebay_active.update(evidence)
        elif provider == "tcgtracking":
            self.tcgtracking.update(evidence)
        elif provider == "internal_history":
            self.internal_history.update(evidence)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    @property
    def provider_count(self) -> int:
        return sum(
            1 for section in (
                self.sold,
                self.ebay_active,
                self.tcgtracking,
                self.internal_history,
            ) if section
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "identity": {
                "card_name": self.card_name,
                "set_name": self.set_name,
                "card_number": self.card_number,
                "title": self.title,
                "language": self.language,
                "condition": self.condition,
            },
            "sold": self.sold,
            "ebay_active": self.ebay_active,
            "tcgtracking": self.tcgtracking,
            "internal_history": self.internal_history,
            "provider_count": self.provider_count,
        }
