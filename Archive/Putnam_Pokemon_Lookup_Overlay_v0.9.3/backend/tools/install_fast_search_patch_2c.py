from datetime import datetime
from pathlib import Path
import re

ROOT = Path.cwd()
SERVER = ROOT / "viewer_server.py"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

text = SERVER.read_text(encoding="utf-8")
(ARCHIVE / f"viewer_server_before_patch_2c_{stamp}.py").write_text(text, encoding="utf-8")

old_pattern = re.compile(
    r'''            for card in results:\n'''
    r'''                card\["thumbnail_url"\] = f"/api/thumb-card\?id=\{card\['putnam_card_id'\]\}"\n'''
    r'''                card\["tcgplayer_search_url"\] = tcgplayer_search_url\(card\)\n'''
    r'''                card\["prices"\] = latest_prices_for_card\(card\["putnam_card_id"\]\)\n''',
    re.MULTILINE,
)

new_block = '''            # Patch 2C: fast search.
            # Only enrich the first few results with live/current price data.
            # This prevents broad searches from calling live TCGplayer pricing for every match.
            try:
                price_limit = int(params.get("price_limit", ["3"])[0] or 3)
            except ValueError:
                price_limit = 3

            for index, card in enumerate(results):
                card["thumbnail_url"] = f"/api/thumb-card?id={card['putnam_card_id']}"
                card["tcgplayer_search_url"] = tcgplayer_search_url(card)
                if index < price_limit:
                    card["prices"] = latest_prices_for_card(card["putnam_card_id"])
                else:
                    card["prices"] = None
'''

if "Patch 2C: fast search" in text:
    print("Patch 2C already appears to be installed. No changes made.")
else:
    text, count = old_pattern.subn(new_block, text)

    if count != 1:
        raise SystemExit("ERROR: Could not find expected pricing loop in viewer_server.py. No changes written.")

    SERVER.write_text(text, encoding="utf-8")
    print("Patch 2C installed.")
    print("Search now enriches live prices only for top 3 results by default.")
    print("Backup saved to:", ARCHIVE)