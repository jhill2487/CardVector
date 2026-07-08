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
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_5h_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

old = '''      row.append(renderCompactConditionCell(variant, "NM", url));
      row.append(renderCompactConditionCell(variant, "LP", url));
      row.append(el("span",{className:"ppo-compact-separator",text:"|"}));
      // MP hidden in compact mode'''

new = '''      row.append(renderCompactConditionCell(variant, "NM", url));
      row.append(el("span", { className: "ppo-compact-separator", text: "|" }));
      row.append(renderCompactConditionCell(variant, "LP", url));
      row.append(el("span", { className: "ppo-compact-separator", text: "|" }));
      row.append(renderCompactConditionCell(variant, "MP", url));'''

if old not in js:
    raise SystemExit("ERROR: Could not find MP hidden block. No changes written.")

js = js.replace(old, new, 1)
JS.write_text(js, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
css += r'''

/* v0.6.5H restore MP column */
.ppo-compact-price-row {
  grid-template-columns: minmax(86px, 1.15fr) auto minmax(72px, .85fr) auto minmax(72px, .85fr) auto minmax(72px, .85fr) !important;
  column-gap: 6px !important;
}

.ppo-compact-separator {
  opacity: .6;
  font-weight: 700;
  text-align: center;
}
'''

CSS.write_text(css, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.6.5.2"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.6.5H Restore MP Column")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/overlay.css")
print(" - extension/manifest.json")