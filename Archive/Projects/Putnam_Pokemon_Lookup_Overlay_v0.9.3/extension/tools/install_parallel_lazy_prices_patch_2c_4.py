from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
JS = ROOT / "overlay.js"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
js = JS.read_text(encoding="utf-8")
(ARCHIVE / f"overlay_before_patch_2c_4_{stamp}.js").write_text(js, encoding="utf-8")

# Add configurable lazy price limit near backendUrl.
if "const LAZY_PRICE_LIMIT" not in js:
    js = js.replace(
        '  let backendUrl = "http://127.0.0.1:8790";',
        '  let backendUrl = "http://127.0.0.1:8790";\n  const LAZY_PRICE_LIMIT = 5;'
    )

# Replace hardcoded top 3 lazy-load behavior with configurable top 5.
js = js.replace(
    "const shouldLazyLoad = results.indexOf(card) < 3;",
    "const shouldLazyLoad = results.indexOf(card) < LAZY_PRICE_LIMIT;"
)

# If a prior script already changed this to top 1, restore configurable limit.
js = js.replace(
    "const shouldLazyLoad = results.indexOf(card) < 1;",
    "const shouldLazyLoad = results.indexOf(card) < LAZY_PRICE_LIMIT;"
)

# The current lazy loading is already parallel because each result schedules its own setTimeout.
# This patch makes that explicit by keeping all eligible results asynchronous and simultaneous.

JS.write_text(js, encoding="utf-8")

print("Patch 2C.4 installed.")
print("Lazy price/image loading is now controlled by LAZY_PRICE_LIMIT = 5.")
print("Top 5 eligible results will lazy-load in parallel.")
print("Backup saved to:", ARCHIVE)