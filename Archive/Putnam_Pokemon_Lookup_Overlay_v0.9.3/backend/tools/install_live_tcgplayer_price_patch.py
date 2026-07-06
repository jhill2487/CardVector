
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def find_backend_root() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here,
        here.parent,
        Path.cwd(),
        Path.cwd().parent,
    ]
    for candidate in candidates:
        if (candidate / "price_cache.py").exists() and (candidate / "viewer_server.py").exists():
            return candidate
    print("ERROR: Could not find backend folder containing price_cache.py and viewer_server.py.")
    print("Save this installer in:")
    print(r"C:\Users\JaredHill\OneDrive\PutnamCollectibles\Pokemon_Live_Price_Lookup\backend\tools")
    raise SystemExit(1)


BACKEND = find_backend_root()
TOOLS = BACKEND / "tools"
ARCHIVE = BACKEND / "archive_old_versions"
PRICE_CACHE = BACKEND / "price_cache.py"
LIVE_MODULE = BACKEND / "live_tcgplayer_prices.py"

TOOLS.mkdir(exist_ok=True)
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

price_src = PRICE_CACHE.read_text(encoding="utf-8")
(ARCHIVE / f"price_cache_before_live_tcgplayer_patch_{stamp}.py").write_text(price_src, encoding="utf-8")

if LIVE_MODULE.exists():
    (ARCHIVE / f"live_tcgplayer_prices_before_patch_{stamp}.py").write_text(
        LIVE_MODULE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

LIVE_MODULE.write_text('\nfrom __future__ import annotations\n\nimport datetime as dt\nimport json\nfrom typing import Any\nfrom urllib.error import HTTPError, URLError\nfrom urllib.request import Request, urlopen\n\n\nTCGPLAYER_LISTINGS_URL = "https://mp-search-api.tcgplayer.com/v1/product/{product_id}/listings?mpfev=5245"\n\n\ndef _money_number(value: Any) -> float | None:\n    try:\n        number = float(value)\n    except (TypeError, ValueError):\n        return None\n    if number < 0:\n        return None\n    return number\n\n\ndef _printing_key(value: Any) -> str:\n    text = str(value or "").strip().lower()\n    text = text.replace("reverse holofoil", "reverse holo")\n    text = text.replace("holofoil", "holo")\n    text = text.replace("_", " ")\n    text = " ".join(text.split())\n    if text in {"", "normal"}:\n        return "normal"\n    return text\n\n\ndef _condition_key(value: Any) -> str:\n    text = str(value or "").strip().lower()\n    mapping = {\n        "near mint": "NM",\n        "lightly played": "LP",\n        "moderately played": "MP",\n        "heavily played": "HP",\n        "damaged": "DMG",\n        "nm": "NM",\n        "lp": "LP",\n        "mp": "MP",\n        "hp": "HP",\n        "dmg": "DMG",\n    }\n    return mapping.get(text, text.upper())\n\n\ndef _post_json(url: str, payload: dict[str, Any], timeout: int = 25) -> dict[str, Any]:\n    body = json.dumps(payload).encode("utf-8")\n    request = Request(\n        url,\n        data=body,\n        method="POST",\n        headers={\n            "Accept": "application/json, text/plain, */*",\n            "Content-Type": "application/json",\n            "Origin": "https://www.tcgplayer.com",\n            "Referer": "https://www.tcgplayer.com/",\n            "User-Agent": (\n                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "\n                "AppleWebKit/537.36 (KHTML, like Gecko) "\n                "Chrome/149.0.0.0 Safari/537.36"\n            ),\n        },\n    )\n    with urlopen(request, timeout=timeout) as response:\n        text = response.read().decode("utf-8", errors="replace")\n        return json.loads(text)\n\n\ndef fetch_live_listing_rows(product_id: str, size: int = 100) -> list[dict[str, Any]]:\n    payload = {\n        "filters": {\n            "term": {\n                "sellerStatus": "Live",\n                "channelId": 0,\n            },\n            "range": {\n                "quantity": {\n                    "gte": 1,\n                },\n            },\n            "exclude": {\n                "channelExclusion": 0,\n            },\n        },\n        "context": {\n            "shippingCountry": "US",\n            "cart": {},\n        },\n        "aggregations": ["listingType", "condition", "printing"],\n        "size": size,\n    }\n\n    url = TCGPLAYER_LISTINGS_URL.format(product_id=product_id)\n    data = _post_json(url, payload)\n    blocks = data.get("results") or []\n    if not blocks:\n        return []\n    return list(blocks[0].get("results") or [])\n\n\ndef summarize_live_listing_prices(product_id: str, size: int = 100) -> dict[str, Any]:\n    rows = fetch_live_listing_rows(product_id, size=size)\n    fetched_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")\n\n    summary: dict[str, Any] = {\n        "source": "tcgplayer_live",\n        "product_id": str(product_id),\n        "fetched_at": fetched_at,\n        "listing_count_sampled": len(rows),\n        "by_printing": {},\n    }\n\n    by_printing: dict[str, dict[str, Any]] = summary["by_printing"]\n\n    for row in rows:\n        printing_raw = row.get("printing") or "Normal"\n        printing = _printing_key(printing_raw)\n        condition = _condition_key(row.get("condition"))\n\n        seller_price = _money_number(row.get("sellerPrice") if row.get("sellerPrice") is not None else row.get("price"))\n        shipping_price = _money_number(row.get("shippingPrice") if row.get("shippingPrice") is not None else row.get("sellerShippingPrice"))\n\n        if seller_price is None:\n            continue\n        if shipping_price is None:\n            shipping_price = 0.0\n\n        total_price = round(seller_price + shipping_price, 2)\n\n        printing_bucket = by_printing.setdefault(printing, {\n            "printing": printing_raw,\n            "conditions": {},\n        })\n        conditions = printing_bucket["conditions"]\n\n        existing = conditions.get(condition)\n        candidate = {\n            "market": total_price,\n            "item_price": round(seller_price, 2),\n            "shipping_price": round(shipping_price, 2),\n            "low": total_price,\n            "high": total_price,\n            "fetched_at": fetched_at,\n            "source": "tcgplayer_live",\n            "seller_name": row.get("sellerName"),\n            "seller_sales": row.get("sellerSales"),\n            "seller_rating": row.get("sellerRating"),\n            "listing_id": row.get("listingId"),\n            "quantity": row.get("quantity"),\n            "condition": row.get("condition"),\n            "printing": printing_raw,\n        }\n\n        if existing is None or total_price < float(existing.get("market") or 999999):\n            conditions[condition] = candidate\n\n    return summary\n\n\ndef enrich_variants_with_live_prices(variants: list[dict[str, Any]], size: int = 100) -> list[dict[str, Any]]:\n    for variant in variants:\n        product_id = variant.get("product_id")\n        if not product_id:\n            continue\n\n        try:\n            live = summarize_live_listing_prices(str(product_id), size=size)\n        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:\n            variant["live_price_error"] = str(exc)\n            continue\n\n        variant["live_price_source"] = "tcgplayer_live"\n        variant["live_fetched_at"] = live.get("fetched_at")\n        variant["live_listing_count_sampled"] = live.get("listing_count_sampled")\n\n        wanted_printing = _printing_key(variant.get("finish") or "normal")\n        by_printing = live.get("by_printing") or {}\n\n        live_bucket = by_printing.get(wanted_printing)\n\n        if live_bucket is None and wanted_printing == "normal" and len(by_printing) == 1:\n            live_bucket = next(iter(by_printing.values()))\n\n        if not live_bucket:\n            continue\n\n        for condition, live_condition in (live_bucket.get("conditions") or {}).items():\n            conditions = variant.setdefault("conditions", {})\n            old_condition = conditions.get(condition)\n\n            if old_condition:\n                old_sources = list(old_condition.get("sources") or [])\n                old_sources.append({\n                    "market": old_condition.get("market"),\n                    "low": old_condition.get("low"),\n                    "high": old_condition.get("high"),\n                    "fetched_at": old_condition.get("fetched_at"),\n                    "source": old_condition.get("source") or "cached",\n                })\n                live_condition["sources"] = old_sources\n                live_condition["cached_market"] = old_condition.get("market")\n                live_condition["cached_low"] = old_condition.get("low")\n                live_condition["cached_high"] = old_condition.get("high")\n                live_condition["cached_fetched_at"] = old_condition.get("fetched_at")\n                live_condition["cached_source"] = old_condition.get("source")\n\n            conditions[condition] = live_condition\n\n    return variants\n\n\nif __name__ == "__main__":\n    import argparse\n\n    parser = argparse.ArgumentParser(description="Read-only live TCGplayer listing price probe.")\n    parser.add_argument("product_id", help="TCGplayer product id, e.g. 42402")\n    parser.add_argument("--size", type=int, default=100)\n    args = parser.parse_args()\n\n    print(json.dumps(summarize_live_listing_prices(args.product_id, size=args.size), indent=2))\n', encoding="utf-8")

if "enrich_variants_with_live_prices" not in price_src:
    old = "    variants = list(grouped.values())\n\n    prices: dict[str, Any] = {"
    new = '''    variants = list(grouped.values())

    # Patch 2A: enrich cached TCGTracking variants with live TCGplayer listing prices.
    # If the live request fails, keep cached prices and continue.
    try:
        from live_tcgplayer_prices import enrich_variants_with_live_prices
        enrich_variants_with_live_prices(variants, size=100)
    except Exception as exc:
        for variant in variants:
            variant["live_price_error"] = str(exc)

    prices: dict[str, Any] = {'''

    if old not in price_src:
        print("ERROR: Could not find insertion point in price_cache.py. No changes written.")
        raise SystemExit(1)

    price_src = price_src.replace(old, new, 1)
    PRICE_CACHE.write_text(price_src, encoding="utf-8")
else:
    print("price_cache.py already appears to include live TCGplayer enrichment. Module refreshed only.")

print("Patch 2A installed successfully.")
print("Backend:", BACKEND)
print("Created/updated:", LIVE_MODULE)
print("Patched only:", PRICE_CACHE)
print("Backup folder:", ARCHIVE)
print("")
print("Test live module:")
print(r'& "C:\Users\JaredHill\AppData\Local\Python\pythoncore-3.14-64\python.exe" live_tcgplayer_prices.py 42402 --size 10')
print("")
print("Test existing price pipeline now enriched with live listings:")
print(r'& "C:\Users\JaredHill\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "import price_cache; p=price_cache.latest_prices_for_card(\'pkm-base-58-102-92e4a6a893\'); print(p[\'source\']); print(p[\'variants\'][0].get(\'live_price_source\'), p[\'variants\'][0].get(\'live_fetched_at\')); print(p[\'variants\'][0][\'conditions\'].get(\'NM\'))"')
