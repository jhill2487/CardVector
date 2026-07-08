from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
JS = ROOT / "overlay.js"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
js = JS.read_text(encoding="utf-8")
(ARCHIVE / f"overlay_before_patch_2c_2_{stamp}.js").write_text(js, encoding="utf-8")

# Lazy-load prices/images for top 3 results instead of only top 1.
js = js.replace(
    "const isFirstResult = results.indexOf(card) === 0;",
    "const shouldLazyLoad = results.indexOf(card) < 3;"
)

js = js.replace(
    "else if (isFirstResult && card.putnam_card_id) {",
    "else if (shouldLazyLoad && card.putnam_card_id) {"
)

# After lazy prices load, update broken thumbnail from returned TCGplayer image.
old = '''    card.prices = payload.prices || null;
    mount.replaceChildren(renderVariantPrices(card, card.prices || {}));
'''

new = '''    card.prices = payload.prices || null;

    const imageUrl = absoluteUrl(card.prices?.variants?.[0]?.image_url);
    if (imageUrl) {
      const resultRow = mount.closest(".ppo-result");
      const img = resultRow?.querySelector(".ppo-thumb");
      if (img) img.src = imageUrl;
    }

    mount.replaceChildren(renderVariantPrices(card, card.prices || {}));
'''

if old not in js:
    raise SystemExit("ERROR: Could not find lazy price update block. No changes written.")

js = js.replace(old, new)

JS.write_text(js, encoding="utf-8")

print("Patch 2C.2 installed.")
print("Top 3 results now lazy-load prices and restore TCGplayer images.")
print("Backup saved to:", ARCHIVE)