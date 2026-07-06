from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

ROOT = Path.cwd()
EXT = ROOT / "extension"
JS = EXT / "overlay.js"
MANIFEST = EXT / "manifest.json"
ARCHIVE = ROOT / "archive_old_versions"
NOTES_DIR = ROOT / "docs" / "release_notes"

ARCHIVE.mkdir(exist_ok=True)
NOTES_DIR.mkdir(parents=True, exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

js = JS.read_text(encoding="utf-8")
manifest_text = MANIFEST.read_text(encoding="utf-8")

(ARCHIVE / f"overlay_before_patch_2c_10_{stamp}.js").write_text(js, encoding="utf-8")
(ARCHIVE / f"manifest_before_patch_2c_10_{stamp}.json").write_text(manifest_text, encoding="utf-8")

# Replace old lazy limit with staged progressive constants.
js = js.replace(
    '  const LAZY_PRICE_LIMIT = 5;',
    '''  const INITIAL_LAZY_PRICE_LIMIT = 5;
  const BACKGROUND_LAZY_PRICE_LIMIT = 50;
  const LAZY_PRICE_CONCURRENCY = 2;
  const LAZY_PRICE_BATCH_DELAY_MS = 250;

  let lazyPriceQueue = [];
  let activeLazyPriceLoads = 0;'''
)

# Add queue processor after loadLazyPrices().
if "function enqueueLazyPriceLoad" not in js:
    marker = '''  function renderResults(results) {
'''
    queue_code = '''  function enqueueLazyPriceLoad(card, mount) {
    if (!card?.putnam_card_id || !mount) return;

    lazyPriceQueue.push({ card, mount });
    processLazyPriceQueue();
  }

  function processLazyPriceQueue() {
    while (activeLazyPriceLoads < LAZY_PRICE_CONCURRENCY && lazyPriceQueue.length) {
      const task = lazyPriceQueue.shift();
      activeLazyPriceLoads += 1;

      loadLazyPrices(task.card, task.mount)
        .catch((error) => {
          task.mount.replaceChildren(el("div", {
            className: "ppo-price-loading ppo-price-error",
            text: error.message || "PRICE LOOKUP FAILED"
          }));
        })
        .finally(() => {
          activeLazyPriceLoads -= 1;
          setTimeout(processLazyPriceQueue, LAZY_PRICE_BATCH_DELAY_MS);
        });
    }
  }

'''
    if marker not in js:
        raise SystemExit("ERROR: Could not find renderResults marker. No changes written.")
    js = js.replace(marker, queue_code + marker)

old_block = '''      const priceMount = el("div", { className: "ppo-price-mount" });
      const shouldLazyLoad = results.indexOf(card) < LAZY_PRICE_LIMIT;

      if (prices && Object.keys(prices).length) {
        priceMount.append(renderVariantPrices(card, prices));
      } else if (shouldLazyLoad && card.putnam_card_id) {
        priceMount.append(el("div", {
          className: "ppo-price-loading",
          text: "LOADING LIVE PRICE..."
        }));
        setTimeout(() => {
          loadLazyPrices(card, priceMount).catch((error) => {
            priceMount.replaceChildren(el("div", {
              className: "ppo-price-loading ppo-price-error",
              text: error.message || "PRICE LOOKUP FAILED"
            }));
          });
        }, 0);
      } else {
        priceMount.append(renderVariantPrices(card, prices));
      }

      details.append(priceMount);
'''

new_block = '''      const priceMount = el("div", { className: "ppo-price-mount" });
      const resultIndex = results.indexOf(card);
      const shouldLoadInitial = resultIndex < INITIAL_LAZY_PRICE_LIMIT;
      const shouldLoadBackground = resultIndex < BACKGROUND_LAZY_PRICE_LIMIT;

      if (prices && Object.keys(prices).length) {
        priceMount.append(renderVariantPrices(card, prices));
      } else if (shouldLoadInitial && card.putnam_card_id) {
        priceMount.append(el("div", {
          className: "ppo-price-loading",
          text: "LOADING LIVE PRICE..."
        }));
        enqueueLazyPriceLoad(card, priceMount);
      } else if (shouldLoadBackground && card.putnam_card_id) {
        priceMount.append(el("div", {
          className: "ppo-price-loading ppo-price-queued",
          text: "QUEUED LIVE PRICE..."
        }));
        enqueueLazyPriceLoad(card, priceMount);
      } else {
        priceMount.append(renderVariantPrices(card, prices));
      }

      details.append(priceMount);
'''

if old_block not in js:
    raise SystemExit("ERROR: Could not find lazy-loading render block. No changes written.")

js = js.replace(old_block, new_block)

# Clear queue at the beginning of each new result render.
js = js.replace(
    '''  function renderResults(results) {
    resultsEl.replaceChildren();
''',
    '''  function renderResults(results) {
    lazyPriceQueue = [];
    activeLazyPriceLoads = 0;
    resultsEl.replaceChildren();
'''
)

JS.write_text(js, encoding="utf-8")

# Bump extension version.
manifest = json.loads(manifest_text)
manifest["version"] = "0.4.0"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

release_notes = NOTES_DIR / "v0.4.0.md"
release_notes.write_text("""# Putnam Pokemon Lookup Overlay v0.4.0

## Added
- Patch 2C.10 Progressive Price/Image Loading.
- Top 5 results load live prices first.
- Remaining results continue loading in the background.
- Background price/image loading uses a small queue with concurrency control.

## Improved
- Search results appear quickly while prices continue filling in.
- More than five search results can now receive images and pricing without blocking the first screen.

## Version
- Extension manifest bumped to v0.4.0.
""", encoding="utf-8")

print("Patch 2C.10 installed.")
print("Extension version updated to v0.4.0.")
print("Top 5 load first; remaining results continue loading in background.")
print("Backups saved to:", ARCHIVE)
print("Release notes:", release_notes)
