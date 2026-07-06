from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
SERVER = ROOT / "viewer_server.py"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
text = SERVER.read_text(encoding="utf-8")
(ARCHIVE / f"viewer_server_before_patch_2c_3_{stamp}.py").write_text(text, encoding="utf-8")

# Add time import.
if "import time" not in text:
    text = text.replace("import json\n", "import json\nimport time\n")

# Add cache globals after PORT.
if "PRICE_SESSION_CACHE" not in text:
    text = text.replace(
        "PORT = 8790\n",
        """PORT = 8790

# Patch 2C.3: short-lived in-memory price cache.
PRICE_SESSION_CACHE = {}
PRICE_SESSION_CACHE_TTL_SECONDS = 600
"""
    )

# Add helper function before class.
if "def cached_latest_prices_for_card" not in text:
    marker = "class ViewerHandler"
    helper = '''
def cached_latest_prices_for_card(putnam_card_id: str):
    now = time.time()
    cached = PRICE_SESSION_CACHE.get(putnam_card_id)
    if cached and now - cached["time"] < PRICE_SESSION_CACHE_TTL_SECONDS:
        prices = dict(cached["prices"] or {})
        prices["session_cache_hit"] = True
        return prices

    prices = latest_prices_for_card(putnam_card_id)
    PRICE_SESSION_CACHE[putnam_card_id] = {
        "time": now,
        "prices": prices,
    }

    if isinstance(prices, dict):
        prices = dict(prices)
        prices["session_cache_hit"] = False

    return prices


'''
    text = text.replace(marker, helper + marker)

# Replace direct calls.
text = text.replace(
    'latest_prices_for_card(card["putnam_card_id"])',
    'cached_latest_prices_for_card(card["putnam_card_id"])'
)

text = text.replace(
    '"prices": latest_prices_for_card(putnam_card_id),',
    '"prices": cached_latest_prices_for_card(putnam_card_id),'
)

SERVER.write_text(text, encoding="utf-8")

print("Patch 2C.3 installed.")
print("Added 10-minute in-memory session price cache.")
print("Repeated price lookups for the same card should now be much faster.")
print("Backup saved to:", ARCHIVE)