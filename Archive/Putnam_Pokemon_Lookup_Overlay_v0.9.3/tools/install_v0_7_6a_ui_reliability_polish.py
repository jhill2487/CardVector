from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "extension" / "overlay.js"
CSS = ROOT / "extension" / "overlay.css"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [JS, CSS, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_7_6a_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

old = '''    if (!rows.length && variants[0]) rows.push(variants[0]);

    for (const variant of rows) {'''

new = '''    if (!rows.length && variants[0]) {
      const fallback = el("div", { className: "ppo-compact-price-empty", text: "No NM / LP / MP price" });
      wrap.append(fallback);

      const firstFallback = variants[0];
      const fallbackUpdated = firstFallback?.live_fetched_at || priceObject(firstFallback, "NM")?.fetched_at || "";
      const fallbackLine = firstFallback?.live_price_source === "tcgplayer_live"
        ? `LIVE TCGPLAYER • UPDATED ${formatUpdated(fallbackUpdated) || fallbackUpdated || "NOW"}`
        : `NO USABLE CONDITION PRICE${fallbackUpdated ? ` • UPDATED ${formatUpdated(fallbackUpdated)}` : ""}`;
      wrap.append(el("div", { className: "ppo-live-meta", text: fallbackLine }));

      return wrap;
    }

    for (const variant of rows) {'''

if old not in js:
    raise SystemExit("ERROR: Could not find empty price-card guard location. No changes written.")

js = js.replace(old, new, 1)

js = js.replace(
    'function createNoImagePlaceholder(label = "NO IMAGE") {',
    'function createNoImagePlaceholder(label = "IMAGE MISSING") {',
    1
)

JS.write_text(js, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
css += r'''

/* v0.7.6A UI Reliability + Polish */
.ppo-live-price-card {
  align-content: start;
  padding-bottom: 8px;
}

.ppo-compact-price-card {
  width: 100%;
}

.ppo-compact-price-row {
  width: 100%;
  grid-template-columns: minmax(86px, 1.15fr) repeat(5, auto);
  column-gap: 6px;
  align-items: center;
}

.ppo-compact-variant-label {
  min-width: 82px;
  max-width: 112px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ppo-compact-price-cell {
  white-space: nowrap;
  font-weight: 800;
}

.ppo-compact-separator {
  opacity: .45;
}

.ppo-live-meta {
  margin-top: 4px;
  padding-top: 2px;
  line-height: 1.15;
}

.ppo-compact-price-empty {
  font-size: 11px;
  font-weight: 800;
  color: #64748b;
  padding: 4px 0 2px;
}

.ppo-no-image {
  font-size: 10px;
  line-height: 1.15;
}
'''

CSS.write_text(css, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.6.1"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.6A UI Reliability + Polish Bundle")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/overlay.css")
print(" - extension/manifest.json")