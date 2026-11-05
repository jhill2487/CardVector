"""Read-only TCGdex catalog adapter.

TCGdex is a catalog source, never a source of inventory or transaction truth.
No network requests are made at import time.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.tcgdex.net/v2"


@dataclass(frozen=True)
class CatalogCard:
    provider: str
    provider_id: str
    name: str
    language: str
    set_id: str | None
    set_name: str | None
    local_id: str | None
    image_url: str | None


def normalize_card(payload: dict[str, Any], language: str = "en") -> CatalogCard:
    """Preserve provider identity; do not infer a finish or condition."""
    if not isinstance(payload, dict) or not payload.get("id") or not payload.get("name"):
        raise ValueError("TCGdex card must include id and name")
    card_set = payload.get("set") or {}
    if not isinstance(card_set, dict):
        card_set = {}
    image = payload.get("image")
    return CatalogCard(
        provider="tcgdex",
        provider_id=str(payload["id"]),
        name=str(payload["name"]),
        language=language,
        set_id=str(card_set["id"]) if card_set.get("id") else None,
        set_name=str(card_set["name"]) if card_set.get("name") else None,
        local_id=str(payload["localId"]) if payload.get("localId") else None,
        image_url=str(image) if image else None,
    )


class TCGdexCatalog:
    def __init__(self, *, timeout: float = 8.0, opener=None):
        self.timeout = timeout
        self._opener = opener or urlopen

    def _get(self, url: str) -> Any:
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "CardVector/1.0"})
        with self._opener(request, timeout=self.timeout) as response:
            return json.load(response)

    def get_card(self, provider_id: str, *, language: str = "en") -> CatalogCard:
        if not provider_id or not provider_id.replace("-", "").isalnum():
            raise ValueError("Invalid TCGdex card ID")
        if not language.isalpha() or len(language) > 5:
            raise ValueError("Invalid language")
        data = self._get(f"{BASE_URL}/{quote(language)}/cards/{quote(provider_id)}")
        return normalize_card(data, language)

    def search_cards(self, name: str, *, language: str = "en") -> list[CatalogCard]:
        if not name or not name.strip():
            raise ValueError("Search name is required")
        if not language.isalpha() or len(language) > 5:
            raise ValueError("Invalid language")
        query = urlencode({"name": name.strip()})
        data = self._get(f"{BASE_URL}/{quote(language)}/cards?{query}")
        if not isinstance(data, list):
            raise ValueError("Unexpected TCGdex search response")
        return [normalize_card(item, language) for item in data]
