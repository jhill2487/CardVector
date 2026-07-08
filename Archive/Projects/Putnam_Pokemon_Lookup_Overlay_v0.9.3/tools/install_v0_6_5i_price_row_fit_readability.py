from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "extension" / "overlay.css"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [CSS, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_5i_{stamp}{p.suffix}")

css = CSS.read_text(encoding="utf-8")

css += r'''

/* v0.6.5I price row fit + readability */
.ppo-compact-price-row {
  display: flex !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  gap: 4px !important;
  width: 100% !important;
  font-size: 10.5px !important;
  line-height: 1.35 !important;
  margin: 3px 0 !important;
}

.ppo-compact-variant-label {
  flex: 0 0 72px !important;
  max-width: 72px !important;
  font-weight: 800 !important;
  color: #111827 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: clip !important;
}

.ppo-compact-price-cell {
  flex: 0 0 auto !important;
  min-width: 0 !important;
  color: #000000 !important;
  font-weight: 800 !important;
  white-space: nowrap !important;
}

.ppo-compact-price-cell a {
  color: #000000 !important;
  font-weight: 800 !important;
  text-decoration: none !important;
}

.ppo-compact-separator {
  flex: 0 0 auto !important;
  padding: 0 2px !important;
  color: #111827 !important;
  opacity: .7 !important;
  font-weight: 800 !important;
}

.ppo-live-source,
.ppo-cache-source {
  color: #000000 !important;
  font-weight: 800 !important;
}

.ppo-live-meta {
  font-weight: 500 !important;
}
'''

CSS.write_text(css, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.6.5.3"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.6.5I Price Row Fit + Readability")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.css")
print(" - extension/manifest.json")