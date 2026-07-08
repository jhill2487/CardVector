from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

ROOT = Path.cwd()
VIEWER = ROOT / "backend" / "viewer_server.py"
OVERLAY = ROOT / "extension" / "overlay.js"
MANIFEST = ROOT / "extension" / "manifest.json"
ARCHIVE = ROOT / "archive_old_versions"
NOTES = ROOT / "docs" / "release_notes"

ARCHIVE.mkdir(exist_ok=True)
NOTES.mkdir(parents=True, exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

viewer = VIEWER.read_text(encoding="utf-8")
overlay = OVERLAY.read_text(encoding="utf-8")
manifest_text = MANIFEST.read_text(encoding="utf-8")

(ARCHIVE / f"viewer_server_before_v0_6_3_{stamp}.py").write_text(viewer, encoding="utf-8")
(ARCHIVE / f"overlay_before_v0_6_3_{stamp}.js").write_text(overlay, encoding="utf-8")
(ARCHIVE / f"manifest_before_v0_6_3_{stamp}.json").write_text(manifest_text, encoding="utf-8")

# Backend: ensure /api/card preserves direct catalog image URLs.
old_backend = '''            card["thumbnail_url"] = f"/api/thumb-card?id={card['putnam_card_id']}"
            card["tcgplayer_search_url"] = tcgplayer_search_url(card)
            card["prices"] = None
'''

new_backend = '''            card["thumbnail_url"] = f"/api/thumb-card?id={card['putnam_card_id']}"
            card["image_url"] = card.get("image_small_url") or card.get("image_large_url") or card.get("image_url") or ""
            card["small_image_url"] = card.get("image_small_url") or card.get("small_image_url") or ""
            card["large_image_url"] = card.get("image_large_url") or card.get("large_image_url") or ""
            card["tcgplayer_search_url"] = tcgplayer_search_url(card)
            card["prices"] = None
'''

if old_backend not in viewer:
    raise SystemExit("ERROR: Could not find /api/card image block in viewer_server.py.")

viewer = viewer.replace(old_backend, new_backend, 1)

# Overlay: prefer direct catalog image URLs before thumbnail endpoint.
old_overlay = '''      const imageUrl = absoluteUrl(prices?.variants?.[0]?.image_url || card.thumbnail_url || card.image_url || card.small_image_url);
'''

new_overlay = '''      const imageUrl = absoluteUrl(
        prices?.variants?.[0]?.image_url ||
        card.image_small_url ||
        card.small_image_url ||
        card.image_url ||
        card.image_large_url ||
        card.large_image_url ||
        card.thumbnail_url
      );
'''

if old_overlay not in overlay:
    raise SystemExit("ERROR: Could not find imageUrl priority block in overlay.js.")

overlay = overlay.replace(old_overlay, new_overlay)

manifest = json.loads(manifest_text)
manifest["version"] = "0.6.3"

VIEWER.write_text(viewer, encoding="utf-8")
OVERLAY.write_text(overlay, encoding="utf-8")
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

(NOTES / "v0.6.3.md").write_text("""# Putnam Pokemon Lookup Overlay v0.6.3

## Improved
- Exact autocomplete selections now prefer catalog image URLs before thumbnail endpoint fallback.
- Card image can display before live price data finishes loading.
- Faster perceived loading for autocomplete-selected cards.

## Version
- Chrome extension manifest updated to v0.6.3.
""", encoding="utf-8")

print("v0.6.3 installed.")
print("Exact card selections now preload catalog image URLs before lazy pricing.")
print("Manifest updated to v0.6.3.")
print("Backups saved to:", ARCHIVE)