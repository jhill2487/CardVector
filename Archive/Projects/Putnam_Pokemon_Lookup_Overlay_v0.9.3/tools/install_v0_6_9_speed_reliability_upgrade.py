from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "extension" / "overlay.js"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [JS, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_9_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

replacements = {
    "const INITIAL_LAZY_PRICE_LIMIT = 3;": "const INITIAL_LAZY_PRICE_LIMIT = 6;",
    "const BACKGROUND_LAZY_PRICE_LIMIT = 20;": "const BACKGROUND_LAZY_PRICE_LIMIT = 9999;",
    "const BACKGROUND_LAZY_PRICE_LIMIT = 50;": "const BACKGROUND_LAZY_PRICE_LIMIT = 9999;",
    "const LAZY_PRICE_CONCURRENCY = 3;": "const LAZY_PRICE_CONCURRENCY = 4;",
    "const LAZY_PRICE_BATCH_DELAY_MS = 120;": "const LAZY_PRICE_BATCH_DELAY_MS = 60;",
    'loading: "lazy"': 'loading: "eager"'
}

for old, new in replacements.items():
    if old in js:
        js = js.replace(old, new)

old_enqueue = '''  function enqueueLazyPriceLoad(card, mount) {
    if (!card?.putnam_card_id || !mount) return;

    const key = String(card.putnam_card_id);
    if (lazyPriceCardIdsQueued.has(key)) return;
    lazyPriceCardIdsQueued.add(key);

    lazyPriceQueue.push({ card, mount, key });
    processLazyPriceQueue();
  }'''

new_enqueue = '''  function enqueueLazyPriceLoad(card, mount) {
    if (!card?.putnam_card_id || !mount) return;

    // v0.6.9: do not skip duplicate card IDs.
    // Duplicate skipping caused some rendered rows to never receive prices.
    lazyPriceQueue.push({ card, mount, key: String(card.putnam_card_id) });
    processLazyPriceQueue();
  }'''

if old_enqueue in js:
    js = js.replace(old_enqueue, new_enqueue, 1)

old_finally = '''        .finally(() => {
          if (task.key) lazyPriceCardIdsQueued.delete(task.key);
          activeLazyPriceLoads -= 1;
          setTimeout(processLazyPriceQueue, LAZY_PRICE_BATCH_DELAY_MS);
        });'''

new_finally = '''        .finally(() => {
          activeLazyPriceLoads -= 1;
          setTimeout(processLazyPriceQueue, LAZY_PRICE_BATCH_DELAY_MS);
        });'''

if old_finally in js:
    js = js.replace(old_finally, new_finally, 1)

JS.write_text(js, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.6.9"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.6.9 Speed + Reliability Upgrade")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/manifest.json")
print("Changes:")
print(" - continuous background price loading")
print(" - duplicate queue blocking removed")
print(" - concurrency increased")
print(" - eager thumbnail loading")