from __future__ import annotations

import json
from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Any

from .models import ListingIdentity, MarketPrice
from .utils import decimal_money, normalize_title


class MarketProvider(ABC):
    name = "base"

    @abstractmethod
    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        raise NotImplementedError


class TCGtrackingProvider(MarketProvider):
    """Initial provider adapter.

    v1.0 intentionally supports a local TCGtracking-style JSON/CSV export instead
    of API login. Future API providers can implement the same interface.
    """

    name = "TCGtracking"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.price_map = self._load_price_map()

    def _load_price_map(self) -> dict[str, Decimal]:
        source = str(self.config.get("price_file", "") or "").strip()
        if not source:
            return {}
        path = Path(source)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / source
        if not path.exists():
            return {}
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            entries = data.get("prices", data if isinstance(data, list) else [])
        else:
            import csv

            with path.open("r", encoding="utf-8-sig", newline="") as f:
                entries = list(csv.DictReader(f))
        price_map: dict[str, Decimal] = {}
        for entry in entries:
            key = str(entry.get("sku") or entry.get("lookup_key") or entry.get("title_key") or "").strip()
            price = decimal_money(entry.get("market_price") or entry.get("price"))
            if key and price is not None:
                price_map[key.lower()] = price
                price_map[normalize_title(key)] = price
        return price_map

    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        keys = [
            identity.lookup_key.lower(),
            normalize_title(identity.lookup_key),
            normalize_title(identity.details.get("title_key", "")),
        ]
        for key in keys:
            if key and key in self.price_map:
                return MarketPrice(
                    matched=True,
                    market_price=self.price_map[key],
                    provider=self.name,
                    source=self.config.get("mode", "local_export"),
                    confidence=identity.confidence,
                    reason=f"Matched by {identity.match_method}.",
                )
        return MarketPrice(
            matched=False,
            provider=self.name,
            source=self.config.get("mode", "local_export"),
            confidence="none",
            reason="No provider price found for lookup key.",
        )


class NullProvider(MarketProvider):
    name = "None"

    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        return MarketPrice(matched=False, provider=self.name, reason="No market provider configured.")


def build_provider(config: dict[str, Any]) -> MarketProvider:
    provider_name = str(config.get("provider", "tcgtracking")).strip().lower()
    if provider_name == "tcgtracking":
        return TCGtrackingProvider(config)
    return NullProvider()

