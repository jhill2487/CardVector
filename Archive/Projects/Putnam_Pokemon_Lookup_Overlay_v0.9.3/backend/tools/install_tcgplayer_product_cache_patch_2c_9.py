from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
BACKEND = ROOT / "backend"
LIVE = BACKEND / "live_tcgplayer_prices.py"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

if not LIVE.exists():
    raise SystemExit(f"ERROR: Missing {LIVE}")

text = LIVE.read_text(encoding="utf-8")
(ARCHIVE / f"live_tcgplayer_prices_before_patch_2c_9_{stamp}.py").write_text(text, encoding="utf-8")

if "import time" not in text:
    text = text.replace("import json", "import json\nimport time", 1)

if "TCGPLAYER_PRODUCT_PRICE_CACHE" not in text:
    insert_after_imports = text.find("\n\n")
    if insert_after_imports == -1:
        raise SystemExit("ERROR: Could not find import section. No changes written.")

    cache_block = """

# Patch 2C.9: short-lived in-memory cache by TCGplayer product ID.
TCGPLAYER_PRODUCT_PRICE_CACHE = {}
TCGPLAYER_PRODUCT_PRICE_CACHE_TTL_SECONDS = 600
"""
    text = text[:insert_after_imports] + cache_block + text[insert_after_imports:]

if "def summarize_live_listing_prices_uncached(" not in text:
    if "def summarize_live_listing_prices(" not in text:
        raise SystemExit("ERROR: Could not find summarize_live_listing_prices function. No changes written.")
    text = text.replace(
        "def summarize_live_listing_prices(",
        "def summarize_live_listing_prices_uncached(",
        1
    )

if "def summarize_live_listing_prices(product_id, size=25):" not in text:
    marker = "\ndef enrich_variants_with_live_prices"
    if marker not in text:
        raise SystemExit("ERROR: Could not find enrich_variants_with_live_prices function. No changes written.")

    wrapper = '''
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

'''
    text = text.replace(marker, "\n" + wrapper + marker)

LIVE.write_text(text, encoding="utf-8")

print("Patch 2C.9 installed.")
print("Added 10-minute TCGplayer product-level live price cache.")
print("Cache key: product_id:size")
print("Backup saved to:", ARCHIVE)