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
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_5f_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

old = '''      const details = el("div", { className: "ppo-result-details" });'''
new = '''      const contentWrap = el("div", { className: "ppo-result-content" });
      const topRow = el("div", { className: "ppo-result-toprow" });
      const details = el("div", { className: "ppo-result-details" });'''

js = js.replace(old, new, 1)

js = js.replace(
'''      details.append(
        favButton,
        el("strong", { text: String(card.card_name || card.name || "UNKNOWN CARD").toUpperCase() }),''',
'''      details.append(
        el("strong", { text: String(card.card_name || card.name || "UNKNOWN CARD").toUpperCase() }),''',
1
)

js = js.replace(
'''      details.append(priceMount);
      row.append(media, details);
      resultsEl.append(row);''',
'''      topRow.append(media, details, favButton);
      contentWrap.append(topRow, priceMount);
      row.append(contentWrap);
      resultsEl.append(row);''',
1
)

JS.write_text(js, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
css += r'''

/* v0.6.5F result card layout refinement */
.ppo-result {
  display: block !important;
  position: relative;
}

.ppo-result-content {
  width: 100%;
}

.ppo-result-toprow {
  display: grid;
  grid-template-columns: 94px 1fr auto;
  gap: 10px;
  align-items: start;
  width: 100%;
}

.ppo-result-toprow .ppo-media {
  width: 94px;
  min-width: 94px;
}

.ppo-result-toprow .ppo-thumb,
.ppo-result-toprow .ppo-no-image {
  width: 94px;
  max-width: 94px;
}

.ppo-result-toprow .ppo-result-details {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ppo-result-toprow .ppo-fav-button {
  justify-self: end;
  align-self: start;
  margin: 0;
  white-space: nowrap;
}

.ppo-price-mount {
  width: 100%;
  margin-top: 8px;
}

.ppo-price-mount .ppo-live-price-card {
  width: 100%;
  box-sizing: border-box;
}

.ppo-compact-price-row {
  grid-template-columns: minmax(78px, 1.15fr) repeat(3, minmax(68px, 0.9fr)) !important;
  column-gap: 10px !important;
}

.ppo-compact-variant-label {
  text-overflow: clip;
}
'''

CSS.write_text(css, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.6.5"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.6.5F Result Card Layout Refinement")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/overlay.css")
print(" - extension/manifest.json")