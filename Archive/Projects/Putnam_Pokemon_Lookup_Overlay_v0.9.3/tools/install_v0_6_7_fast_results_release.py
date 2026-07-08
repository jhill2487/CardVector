from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]

JS = ROOT / "extension" / "overlay.js"
SERVER = ROOT / "backend" / "viewer_server.py"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [JS, SERVER, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_7_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

replacements = {
    "const INITIAL_LAZY_PRICE_LIMIT = 5;": "const INITIAL_LAZY_PRICE_LIMIT = 3;",
    "const BACKGROUND_LAZY_PRICE_LIMIT = 50;": "const BACKGROUND_LAZY_PRICE_LIMIT = 20;",
    "const LAZY_PRICE_CONCURRENCY = 2;": "const LAZY_PRICE_CONCURRENCY = 3;",
    "const LAZY_PRICE_BATCH_DELAY_MS = 250;": "const LAZY_PRICE_BATCH_DELAY_MS = 120;",
    "let activeLazyPriceLoads = 0;": "let activeLazyPriceLoads = 0;\n  const lazyPriceCardIdsQueued = new Set();"
}

for old, new in replacements.items():
    if old not in js:
        raise SystemExit(f"ERROR: Could not find expected JS text: {old}")
    js = js.replace(old, new, 1)

old_enqueue = '''  function enqueueLazyPriceLoad(card, mount) {
    if (!card?.putnam_card_id || !mount) return;

    lazyPriceQueue.push({ card, mount });
    processLazyPriceQueue();
  }'''

new_enqueue = '''  function enqueueLazyPriceLoad(card, mount) {
    if (!card?.putnam_card_id || !mount) return;

    const key = String(card.putnam_card_id);
    if (lazyPriceCardIdsQueued.has(key)) return;
    lazyPriceCardIdsQueued.add(key);

    lazyPriceQueue.push({ card, mount, key });
    processLazyPriceQueue();
  }'''

if old_enqueue not in js:
    raise SystemExit("ERROR: Could not find enqueueLazyPriceLoad block.")
js = js.replace(old_enqueue, new_enqueue, 1)

old_finally = '''        .finally(() => {
          activeLazyPriceLoads -= 1;
          setTimeout(processLazyPriceQueue, LAZY_PRICE_BATCH_DELAY_MS);
        });'''

new_finally = '''        .finally(() => {
          if (task.key) lazyPriceCardIdsQueued.delete(task.key);
          activeLazyPriceLoads -= 1;
          setTimeout(processLazyPriceQueue, LAZY_PRICE_BATCH_DELAY_MS);
        });'''

if old_finally not in js:
    raise SystemExit("ERROR: Could not find lazy queue finally block.")
js = js.replace(old_finally, new_finally, 1)

old_reset = '''      lazyPriceQueue = [];
      activeLazyPriceLoads = 0;
      resultsEl.replaceChildren();'''

new_reset = '''      lazyPriceQueue = [];
      lazyPriceCardIdsQueued.clear();
      activeLazyPriceLoads = 0;
      resultsEl.replaceChildren();'''

if old_reset not in js:
    raise SystemExit("ERROR: Could not find lazy queue reset block.")
js = js.replace(old_reset, new_reset, 1)

JS.write_text(js, encoding="utf-8")

server = SERVER.read_text(encoding="utf-8")
server = server.replace(
    'self.send_header("Cache-Control", "public, max-age=3600")',
    'self.send_header("Cache-Control", "public, max-age=86400, immutable")'
)
SERVER.write_text(server, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.6.7"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.6.7 Fast Results Release")
print(f"Extension version: {old_version} -> {manifest['version']}")
print("Patched:")
print(" - extension/overlay.js")
print(" - backend/viewer_server.py")
print(" - extension/manifest.json")