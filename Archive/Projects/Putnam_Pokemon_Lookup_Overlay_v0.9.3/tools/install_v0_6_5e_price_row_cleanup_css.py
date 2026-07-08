from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "extension" / "overlay.css"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = ROOT / "archive_old_versions" / f"overlay_before_v0_6_5e_css_{stamp}.css"
backup.parent.mkdir(exist_ok=True)

shutil.copy2(TARGET, backup)

css = TARGET.read_text(encoding="utf-8")

css += """

/* v0.6.5E cleanup */

.ppo-compact-separator{
  display:inline-block;
  padding:0 6px;
  font-weight:700;
  opacity:.75;
}

.ppo-compact-price-row{
  column-gap:10px !important;
}

"""

TARGET.write_text(css, encoding="utf-8")

print("Installed v0.6.5E CSS Cleanup")
print("Patched:", TARGET)
print("Backup :", backup)