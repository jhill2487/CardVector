from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "extension" / "overlay.css"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

backup = archive / f"overlay_before_v0_6_5d_{stamp}.css"
shutil.copy2(CSS, backup)

css = CSS.read_text(encoding="utf-8")

css += r'''

/* v0.6.5D compact price spacing fix */
.ppo-compact-price-card {
  overflow: hidden;
  max-width: 100%;
}

.ppo-compact-price-row {
  display: grid !important;
  grid-template-columns: 58px 64px 64px 64px !important;
  gap: 6px !important;
  align-items: center;
  font-size: 10.5px !important;
  line-height: 1.35 !important;
  margin: 3px 0 !important;
}

.ppo-compact-variant-label {
  min-width: 0;
  font-weight: 800;
}

.ppo-compact-price-cell {
  display: inline-block;
  min-width: 58px;
  text-align: left;
  white-space: nowrap;
}

.ppo-live-meta {
  margin-top: 6px;
  font-size: 9.5px !important;
}
'''

CSS.write_text(css, encoding="utf-8")

print("Installed v0.6.5D Compact Price Spacing Fix")
print(f"Patched: {CSS}")
print(f"Backup:  {backup}")