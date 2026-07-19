from __future__ import annotations

import csv
import json
import re
import statistics
from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Any

from .models import ListingIdentity, MarketPrice
from .utils import decimal_money, normalize_title, read_csv_rows


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
NAME_MATCH_SCORE_THRESHOLD = 90
GRADED_EXCLUDE_TERMS = {"psa", "bgs", "cgc", "tag", "sgc", "graded", "slab", "ace"}
NON_SINGLE_EXCLUDE_TERMS = {
    "lot", "lots", "playset", "4x", "x4", "pack", "packs", "booster", "box", "deck",
    "sealed", "case", "bundle", "binder", "complete set", "master set",
}
EXCLUDE_TERMS = GRADED_EXCLUDE_TERMS.union(NON_SINGLE_EXCLUDE_TERMS).union({
    "world championship", "worlds", "theme deck", "starter deck", "proxy", "custom",
    "reprint", "metal", "gold foil", "jumbo", "oversized", "wrapper",
})
PRICE_COLUMNS = [
    "market_price", "Market Price", "recommended_price", "Recommended Price", "Price",
    "*StartPrice", "StartPrice", "Current price", "Current Price", "BuyItNowPrice",
]
TITLE_COLUMNS = ["Title", "*Title", "Item title", "ItemTitle", "title"]
SKU_COLUMNS = ["Catalog SKU", "CustomLabel", "Custom label (SKU)", "Custom Label", "SKU", "User SKU"]
CARD_NAME_COLUMNS = ["*C:Card Name", "Card Name", "card_name"]
SET_COLUMNS = ["*C:Set", "Set", "set"]
NUMBER_COLUMNS = ["*C:Card Number", "Card Number", "card_number", "number"]


class MarketProvider(ABC):
    name = "base"

    @abstractmethod
    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        raise NotImplementedError


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    for base in [PACKAGE_ROOT, REPO_ROOT]:
        candidate = base / path
        if candidate.exists():
            return candidate
    return REPO_ROOT / path


def first_value(row: dict[str, str], candidates: list[str]) -> str:
    normalized = {normalize_column_name(key): key for key in row.keys()}
    for candidate in candidates:
        key = normalized.get(normalize_column_name(candidate))
        if key:
            return str(row.get(key, "") or "").strip()
    return ""


def normalize_column_name(value: str) -> str:
    return "".join(ch for ch in str(value or "").lower().strip() if ch.isalnum())


def card_key(name: str, set_name: str, number: str) -> str:
    parts = [normalize_title(part) for part in [name, set_name, normalized_card_number(number)] if part]
    return "cardkey:" + "|".join(parts) if parts else ""


def identity_keys(identity: ListingIdentity) -> list[str]:
    details = identity.details
    keys = [
        str(identity.lookup_key or "").lower().strip(),
        normalize_title(identity.lookup_key),
        normalize_title(details.get("title_key", "")),
    ]
    parsed_key = card_key(
        str(details.get("parsed_card_name", "")),
        str(details.get("parsed_set", "")),
        str(details.get("parsed_card_number", "")),
    )
    if parsed_key:
        keys.append(parsed_key)
    query = normalize_title(details.get("provider_query", ""))
    if query:
        keys.append(query)
    return [key for key in dict.fromkeys(keys) if key]


def normalized_card_number(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


class TCGtrackingProvider(MarketProvider):
    """Local TCGtracking-style provider.

    TCGtracking data can be useful context, but in the default Marketplace
    Intelligence profile it is reference-only so TCGplayer-like figures do not
    directly drive eBay repricing decisions.
    """

    name = "TCGtracking"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.actionable = bool(config.get("actionable", False))
        self.price_map = self._load_price_map()

    def _load_price_map(self) -> dict[str, Decimal]:
        source = str(self.config.get("price_file", "") or "").strip()
        if not source:
            return {}
        path = resolve_path(source)
        if not path.exists():
            return {}
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            entries = data.get("prices", data if isinstance(data, list) else [])
        else:
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
        for key in identity_keys(identity):
            if key in self.price_map:
                source = self.config.get("mode", "local_export")
                label = source if self.actionable else f"{source}_reference_only"
                return MarketPrice(
                    matched=True,
                    market_price=self.price_map[key],
                    provider=self.name,
                    source=label,
                    confidence=identity.confidence if self.actionable else "reference",
                    reason=f"Matched by {identity.match_method}.",
                    metadata={"reference_only": not self.actionable, "lookup_key": key},
                )
        return MarketPrice(
            matched=False,
            provider=self.name,
            source=self.config.get("mode", "local_export"),
            confidence="none",
            reason="No provider price found for lookup key.",
        )


class CardUploaderInventoryProvider(MarketProvider):
    """Reads local CardUploader inventory/export CSV prices as actionable evidence."""

    name = "CardUploader"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.price_map: dict[str, list[Decimal]] = {}
        self.source_map: dict[str, set[str]] = {}
        self._load_files()

    def _configured_files(self) -> list[Path]:
        files: list[Path] = []
        for pattern in self.config.get("files", []):
            path = resolve_path(pattern)
            if any(ch in str(pattern) for ch in ["*", "?"]):
                files.extend(sorted(path.parent.glob(path.name)))
            elif path.exists():
                files.append(path)
        return [path for path in dict.fromkeys(files) if path.is_file()]

    def _load_files(self) -> None:
        for path in self._configured_files():
            try:
                rows = read_csv_rows(path)
            except Exception:
                continue
            for row in rows:
                price = self._row_price(row)
                if price is None:
                    continue
                keys = self._row_keys(row)
                for key in keys:
                    self.price_map.setdefault(key, []).append(price)
                    self.source_map.setdefault(key, set()).add(str(path))

    def _row_price(self, row: dict[str, str]) -> Decimal | None:
        for column in PRICE_COLUMNS:
            value = first_value(row, [column])
            price = decimal_money(value)
            if price is not None:
                return price
        return None

    def _row_keys(self, row: dict[str, str]) -> list[str]:
        title = first_value(row, TITLE_COLUMNS)
        name = first_value(row, CARD_NAME_COLUMNS)
        set_name = first_value(row, SET_COLUMNS)
        number = first_value(row, NUMBER_COLUMNS)
        keys = []
        for sku in [first_value(row, SKU_COLUMNS)]:
            if sku:
                keys.extend([sku.lower(), normalize_title(sku)])
        if title:
            keys.append(normalize_title(title))
        structured = card_key(name, set_name, number)
        if structured:
            keys.append(structured)
        return [key for key in dict.fromkeys(keys) if key]

    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        for key in identity_keys(identity):
            prices = self.price_map.get(key)
            if not prices:
                continue
            price = Decimal(str(statistics.median(prices))).quantize(Decimal("0.01"))
            return MarketPrice(
                matched=True,
                market_price=price,
                provider=self.name,
                source="carduploader_inventory_price",
                confidence="medium" if len(prices) == 1 else "high",
                reason=f"Matched local CardUploader price by {identity.match_method}.",
                metadata={
                    "reference_only": False,
                    "lookup_key": key,
                    "price_count": len(prices),
                    "source_files": sorted(self.source_map.get(key, set()))[:5],
                },
            )
        return MarketPrice(
            matched=False,
            provider=self.name,
            source="carduploader_inventory_price",
            confidence="none",
            reason="No local CardUploader CSV price matched.",
        )


class CardUploaderSalesCacheProvider(MarketProvider):
    """Uses cached CardUploader/eBay sold comps when enough accepted comps exist."""

    name = "CardUploader eBay Sales"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.minimum_accepted = int(config.get("minimum_accepted_comps", 3))
        self.minimum_confidence = int(config.get("minimum_confidence", 65))
        self.cache_dirs = [resolve_path(path) for path in config.get("cache_dirs", [])]
        self._data_cache: dict[Path, tuple[int, dict[str, Any]]] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        details = identity.details
        name = str(details.get("parsed_card_name", "")).strip()
        set_name = str(details.get("parsed_set", "")).strip()
        number = str(details.get("parsed_card_number", "")).strip()
        query = str(details.get("provider_query") or " ".join(p for p in [name, set_name, number] if p)).strip()
        if not name or not number or not query:
            return MarketPrice(
                matched=False,
                provider=self.name,
                source="carduploader_sales_cache",
                confidence="none",
                reason="Not enough parsed card identity for sales comp lookup.",
            )
        cache_path = self._find_cache_file(query)
        if not cache_path:
            return MarketPrice(
                matched=False,
                provider=self.name,
                source="carduploader_sales_cache",
                confidence="none",
                reason="No local CardUploader sales cache file found.",
            )
        try:
            data = self._load_cache_data(cache_path)
        except Exception as exc:
            return MarketPrice(
                matched=False,
                provider=self.name,
                source="carduploader_sales_cache",
                confidence="none",
                reason=f"Could not read sales cache: {exc}",
            )
        accepted = []
        rejected = 0
        duplicate_comps = 0
        accepted_signatures: set[str] = set()
        for row in data.get("results", []):
            ok, _reason = comparable_reason(str(row.get("title", "")), name, set_name, number)
            price = decimal_money(row.get("price"))
            if ok and price is not None and price > 0:
                accepted.append(price)
                signature = "|".join(
                    [
                        normalize_title(str(row.get("title", ""))),
                        str(price),
                        str(
                            row.get("sold_at")
                            or row.get("sale_date")
                            or row.get("date")
                            or ""
                        ),
                    ]
                )
                if signature in accepted_signatures:
                    duplicate_comps += 1
                accepted_signatures.add(signature)
            else:
                rejected += 1
        if len(accepted) < self.minimum_accepted:
            return MarketPrice(
                matched=False,
                provider=self.name,
                source="carduploader_sales_cache",
                confidence="low",
                reason=f"Only {len(accepted)} accepted comps after validation.",
                metadata={"cache_file": str(cache_path), "accepted_comps": len(accepted), "rejected_comps": rejected},
            )
        median_price = Decimal(str(statistics.median(accepted[:20]))).quantize(Decimal("0.01"))
        last3 = accepted[:3]
        last3_avg = (sum(last3) / Decimal(len(last3))).quantize(Decimal("0.01")) if last3 else median_price
        average_price = (sum(accepted) / Decimal(len(accepted))).quantize(
            Decimal("0.01")
        )
        captured_at = str(
            data.get("captured_at")
            or data.get("fetched_at")
            or data.get("as_of")
            or ""
        )
        confidence = self._confidence(len(accepted), last3_avg, last3, bool(set_name))
        if confidence < self.minimum_confidence:
            return MarketPrice(
                matched=False,
                provider=self.name,
                source="carduploader_sales_cache",
                confidence=str(confidence),
                reason=f"Accepted comps found, but confidence {confidence} is below threshold {self.minimum_confidence}.",
                metadata={
                    "cache_file": str(cache_path),
                    "accepted_comps": len(accepted),
                    "rejected_comps": rejected,
                    "last3_avg": str(last3_avg),
                    "median": str(median_price),
                    "average": str(average_price),
                    "price_low": str(min(accepted)),
                    "price_high": str(max(accepted)),
                    "outliers_removed": 0,
                    "duplicate_comps": duplicate_comps,
                    "captured_at": captured_at,
                    "marketplace": "ebay",
                },
            )
        return MarketPrice(
            matched=True,
            market_price=median_price,
            provider=self.name,
            source="carduploader_ebay_sold_comps",
            confidence=str(confidence),
            reason=f"{len(accepted)} accepted CardUploader/eBay comps; median of latest comps used.",
            metadata={
                "reference_only": False,
                "cache_file": str(cache_path),
                "accepted_comps": len(accepted),
                "rejected_comps": rejected,
                "last_sale": str(accepted[0]),
                "last3_avg": str(last3_avg),
                "median": str(median_price),
                "average": str(average_price),
                "price_low": str(min(accepted)),
                "price_high": str(max(accepted)),
                "outliers_removed": 0,
                "duplicate_comps": duplicate_comps,
                "captured_at": captured_at,
                "marketplace": "ebay",
            },
        )

    def _load_cache_data(self, path: Path) -> dict[str, Any]:
        modified = path.stat().st_mtime_ns
        cached = self._data_cache.get(path)
        if cached is not None and cached[0] == modified:
            self.cache_hits += 1
            return cached[1]
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("Sales cache must contain a JSON object.")
        self._data_cache[path] = (modified, data)
        self.cache_misses += 1
        return data

    def _find_cache_file(self, query: str) -> Path | None:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", query)[:120]
        slug = normalize_title(query).replace(" ", "_").replace("/", "_")
        candidates = []
        for directory in self.cache_dirs:
            candidates.extend([
                directory / f"{safe}.json",
                directory / f"{slug}.json",
                directory / f"carduploader_sales_{slug}.json",
            ])
        for path in candidates:
            if path.exists():
                return path
        return None

    def _confidence(self, count: int, avg: Decimal, last3: list[Decimal], has_set: bool) -> int:
        count_score = min(45, count * 5)
        spread_score = 20
        if len(last3) == 3 and avg > 0:
            spread = max(last3) - min(last3)
            spread_score = max(0, 25 - int((spread / avg) * 25))
        identity_score = 25 if has_set else 15
        return min(100, count_score + spread_score + identity_score)


class CompositeProvider(MarketProvider):
    name = "Composite"

    def __init__(self, providers: list[MarketProvider]):
        self.providers = providers

    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        reference_match: MarketPrice | None = None
        reasons = []
        for provider in self.providers:
            result = provider.get_market_price(identity)
            if result.matched and not result.metadata.get("reference_only"):
                return result
            if result.matched and reference_match is None:
                reference_match = result
            reasons.append(f"{result.provider}: {result.reason}")
        if reference_match:
            return reference_match
        return MarketPrice(
            matched=False,
            provider=self.name,
            source="composite",
            confidence="none",
            reason=" | ".join(reasons)[:500] or "No provider matched.",
        )


class NullProvider(MarketProvider):
    name = "None"

    def get_market_price(self, identity: ListingIdentity) -> MarketPrice:
        return MarketPrice(matched=False, provider=self.name, reason="No market provider configured.")


def match_tokens(value: str) -> list[str]:
    return [token for token in normalize_title(value).split() if token]


def token_match_score(expected: str, candidate: str) -> int:
    expected_tokens = match_tokens(expected)
    candidate_tokens = set(match_tokens(candidate))
    if not expected_tokens:
        return 100
    matched = [token for token in expected_tokens if token in candidate_tokens]
    return round((len(matched) / len(expected_tokens)) * 100)


def find_card_number(title: str, number: str) -> bool:
    expected = normalized_card_number(number)
    if not expected:
        return True
    normalized_title = normalized_card_number(title)
    candidates = {expected}
    if expected.startswith("0"):
        candidates.add(expected.lstrip("0"))
    return any(candidate and candidate in normalized_title for candidate in candidates)


def excluded_terms_found(title: str) -> set[str]:
    normalized = f" {normalize_title(title)} "
    found = set()
    for term in EXCLUDE_TERMS:
        normalized_term = normalize_title(term)
        if normalized_term and f" {normalized_term} " in normalized:
            found.add(normalized_term)
    return found


def comparable_reason(title: str, name: str, set_name: str, number: str) -> tuple[bool, str]:
    try:
        from Platform.cardvector.marketplace_intelligence.evidence import (
            comparable_reason as canonical_comparable_reason,
        )
    except ModuleNotFoundError as exc:
        if exc.name != "Platform":
            raise
    else:
        accepted, reason, _diagnostics = canonical_comparable_reason(
            title,
            name,
            set_name,
            number,
        )
        return accepted, reason

    # Historical direct-launch compatibility until repository packaging lands.
    excluded = excluded_terms_found(title)
    if excluded.intersection(GRADED_EXCLUDE_TERMS):
        return False, "excluded graded term"
    if excluded.intersection(NON_SINGLE_EXCLUDE_TERMS):
        return False, "excluded lot/pack/playset/booster/deck/sealed term"
    if name and token_match_score(name, title) < NAME_MATCH_SCORE_THRESHOLD:
        return False, "card name mismatch"
    if number and not find_card_number(title, number):
        return False, "card number mismatch"
    if set_name:
        words = [word for word in re.split(r"\W+", set_name.lower()) if len(word) > 3]
        if words and not any(word in title.lower() for word in words):
            return False, "set not evident in title"
    return True, "accepted"


def build_provider(config: dict[str, Any]) -> MarketProvider:
    provider_name = str(config.get("provider", "composite")).strip().lower()
    if provider_name == "composite":
        providers = []
        for provider_config in config.get("providers", []):
            provider = build_provider(provider_config)
            if not isinstance(provider, NullProvider):
                providers.append(provider)
        return CompositeProvider(providers) if providers else NullProvider()
    if provider_name == "carduploader_inventory":
        return CardUploaderInventoryProvider(config)
    if provider_name == "carduploader_sales_cache":
        return CardUploaderSalesCacheProvider(config)
    if provider_name == "tcgtracking":
        return TCGtrackingProvider(config)
    return NullProvider()
