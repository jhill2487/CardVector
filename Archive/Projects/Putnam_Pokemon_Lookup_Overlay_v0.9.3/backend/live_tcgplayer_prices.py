
from __future__ import annotations

# Patch 2C.9: short-lived in-memory cache by TCGplayer product ID.
TCGPLAYER_PRODUCT_PRICE_CACHE = {}
TCGPLAYER_PRODUCT_PRICE_CACHE_TTL_SECONDS = 600


import datetime as dt
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TCGPLAYER_LISTINGS_URL = "https://mp-search-api.tcgplayer.com/v1/product/{product_id}/listings?mpfev=5245"
CONDITION_PRIORITY = [
    ("NM", "Near Mint"),
    ("LP", "Lightly Played"),
    ("MP", "Moderately Played"),
    ("HP", "Heavily Played"),
    ("DMG", "Damaged"),
]
DEFAULT_PAGE_SIZE = 25


def _money_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return number


def _printing_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("reverse holofoil", "reverse holo")
    text = text.replace("holofoil", "holo")
    text = text.replace("_", " ")
    text = " ".join(text.split())
    if text in {"", "normal"}:
        return "normal"
    return text


def _condition_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    mapping = {
        "near mint": "NM",
        "lightly played": "LP",
        "moderately played": "MP",
        "heavily played": "HP",
        "damaged": "DMG",
        "nm": "NM",
        "lp": "LP",
        "mp": "MP",
        "hp": "HP",
        "dmg": "DMG",
    }
    return mapping.get(text, text.upper())


def _base_payload(size: int = DEFAULT_PAGE_SIZE) -> dict[str, Any]:
    return {
        "filters": {
            "term": {
                "sellerStatus": "Live",
                "channelId": 0,
            },
            "range": {
                "quantity": {
                    "gte": 1,
                },
            },
            "exclude": {
                "channelExclusion": 0,
            },
        },
        "context": {
            "shippingCountry": "US",
            "cart": {},
        },
        "aggregations": ["listingType", "condition", "printing"],
        "size": size,
    }


def _condition_payload(condition_name: str, size: int = DEFAULT_PAGE_SIZE) -> dict[str, Any]:
    payload = _base_payload(size=size)
    payload["filters"]["term"]["condition"] = condition_name
    return payload


def _post_json(url: str, payload: dict[str, Any], timeout: int = 25) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.tcgplayer.com",
            "Referer": "https://www.tcgplayer.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
        },
    )
    with urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8", errors="replace")
        return json.loads(text)


def _rows_from_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = data.get("results") or []
    if not blocks:
        return []
    return list(blocks[0].get("results") or [])


def fetch_live_listing_rows(product_id: str, size: int = DEFAULT_PAGE_SIZE) -> list[dict[str, Any]]:
    url = TCGPLAYER_LISTINGS_URL.format(product_id=product_id)
    data = _post_json(url, _base_payload(size=size))
    return _rows_from_response(data)


def fetch_live_listing_rows_for_condition(
    product_id: str,
    condition_name: str,
    size: int = DEFAULT_PAGE_SIZE,
) -> list[dict[str, Any]]:
    url = TCGPLAYER_LISTINGS_URL.format(product_id=product_id)
    data = _post_json(url, _condition_payload(condition_name, size=size))
    return _rows_from_response(data)


def _listing_candidate(row: dict[str, Any], fetched_at: str) -> dict[str, Any] | None:
    seller_price = _money_number(row.get("sellerPrice") if row.get("sellerPrice") is not None else row.get("price"))
    shipping_price = _money_number(row.get("shippingPrice") if row.get("shippingPrice") is not None else row.get("sellerShippingPrice"))

    if seller_price is None:
        return None
    if shipping_price is None:
        shipping_price = 0.0

    total_price = round(seller_price + shipping_price, 2)

    return {
        "market": total_price,
        "item_price": round(seller_price, 2),
        "shipping_price": round(shipping_price, 2),
        "low": total_price,
        "high": total_price,
        "fetched_at": fetched_at,
        "source": "tcgplayer_live",
        "seller_name": row.get("sellerName"),
        "seller_sales": row.get("sellerSales"),
        "seller_rating": row.get("sellerRating"),
        "listing_id": row.get("listingId"),
        "quantity": row.get("quantity"),
        "condition": row.get("condition"),
        "printing": row.get("printing") or "Normal",
    }


def _add_best_listing(summary: dict[str, Any], row: dict[str, Any], fetched_at: str) -> None:
    candidate = _listing_candidate(row, fetched_at)
    if candidate is None:
        return

    printing_raw = row.get("printing") or "Normal"
    printing = _printing_key(printing_raw)
    condition = _condition_key(row.get("condition"))

    by_printing: dict[str, dict[str, Any]] = summary["by_printing"]
    printing_bucket = by_printing.setdefault(
        printing,
        {
            "printing": printing_raw,
            "conditions": {},
        },
    )
    conditions = printing_bucket["conditions"]

    existing = conditions.get(condition)
    if existing is None or float(candidate["market"]) < float(existing.get("market") or 999999):
        conditions[condition] = candidate


def summarize_live_listing_prices_uncached(product_id: str, size: int = DEFAULT_PAGE_SIZE) -> dict[str, Any]:
    fetched_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary: dict[str, Any] = {
        "source": "tcgplayer_live",
        "product_id": str(product_id),
        "fetched_at": fetched_at,
        "listing_count_sampled": 0,
        "condition_fetch_errors": {},
        "by_printing": {},
    }

    seen_listing_ids: set[str] = set()

    def add_rows(rows: list[dict[str, Any]]) -> None:
        for row in rows:
            listing_id = str(row.get("listingId") or "")
            if listing_id and listing_id in seen_listing_ids:
                continue
            if listing_id:
                seen_listing_ids.add(listing_id)
            _add_best_listing(summary, row, fetched_at)

    global_rows = fetch_live_listing_rows(product_id, size=size)
    add_rows(global_rows)

    for _code, condition_name in CONDITION_PRIORITY:
        try:
            rows = fetch_live_listing_rows_for_condition(product_id, condition_name, size=size)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            summary["condition_fetch_errors"][condition_name] = str(exc)
            continue
        add_rows(rows)

    summary["listing_count_sampled"] = len(seen_listing_ids)
    return summary



def summarize_live_listing_prices(product_id, size=25):
    cache_key = f"{product_id}:{size}"
    now = time.time()

    cached = TCGPLAYER_PRODUCT_PRICE_CACHE.get(cache_key)
    if cached and now - cached["time"] < TCGPLAYER_PRODUCT_PRICE_CACHE_TTL_SECONDS:
        result = dict(cached["data"] or {})
        result["product_cache_hit"] = True
        return result

    result = summarize_live_listing_prices_uncached(product_id, size=size)

    if isinstance(result, dict):
        cached_result = dict(result)
        cached_result["product_cache_hit"] = False
        TCGPLAYER_PRODUCT_PRICE_CACHE[cache_key] = {
            "time": now,
            "data": cached_result,
        }
        return cached_result

    return result


def enrich_variants_with_live_prices(
    variants: list[dict[str, Any]],
    size: int = DEFAULT_PAGE_SIZE,
) -> list[dict[str, Any]]:
    for variant in variants:
        product_id = variant.get("product_id")
        if not product_id:
            continue

        try:
            live = summarize_live_listing_prices(str(product_id), size=size)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            variant["live_price_error"] = str(exc)
            continue

        variant["live_price_source"] = "tcgplayer_live"
        variant["live_fetched_at"] = live.get("fetched_at")
        variant["live_listing_count_sampled"] = live.get("listing_count_sampled")
        if live.get("condition_fetch_errors"):
            variant["live_condition_fetch_errors"] = live.get("condition_fetch_errors")

        wanted_printing = _printing_key(variant.get("finish") or "normal")
        by_printing = live.get("by_printing") or {}

        live_bucket = by_printing.get(wanted_printing)

        if live_bucket is None and wanted_printing == "normal" and len(by_printing) == 1:
            live_bucket = next(iter(by_printing.values()))

        if not live_bucket:
            continue

        for condition, live_condition in (live_bucket.get("conditions") or {}).items():
            conditions = variant.setdefault("conditions", {})
            old_condition = conditions.get(condition)

            if old_condition:
                old_sources = list(old_condition.get("sources") or [])
                old_sources.append({
                    "market": old_condition.get("market"),
                    "low": old_condition.get("low"),
                    "high": old_condition.get("high"),
                    "fetched_at": old_condition.get("fetched_at"),
                    "source": old_condition.get("source") or "cached",
                })
                live_condition["sources"] = old_sources
                live_condition["cached_market"] = old_condition.get("market")
                live_condition["cached_low"] = old_condition.get("low")
                live_condition["cached_high"] = old_condition.get("high")
                live_condition["cached_fetched_at"] = old_condition.get("fetched_at")
                live_condition["cached_source"] = old_condition.get("source")

            conditions[condition] = live_condition

    return variants


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Read-only live TCGplayer listing price probe.")
    parser.add_argument("product_id", help="TCGplayer product id, e.g. 42402")
    parser.add_argument("--size", type=int, default=DEFAULT_PAGE_SIZE)
    args = parser.parse_args()

    print(json.dumps(summarize_live_listing_prices(args.product_id, size=args.size), indent=2))
