from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

ROOT = Path.cwd()
CATALOG = ROOT / "backend" / "card_catalog.py"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

text = CATALOG.read_text(encoding="utf-8")
(ARCHIVE / f"card_catalog_before_v0_6_3a_{stamp}.py").write_text(text, encoding="utf-8")

if "v0.6.3A blank Kaggle guard" in text:
    print("v0.6.3A already installed.")
    raise SystemExit(0)

pattern = re.compile(
    r"(def visual_index_rows\(\).*?\n)(.*?config = load_config\(\)\n)(.*?)(\s*with config\.kaggle_visual_index_csv\.open\()",
    re.DOTALL,
)

match = pattern.search(text)
if not match:
    raise SystemExit("ERROR: Could not locate visual_index_rows open block. No changes written.")

insert = '''    # v0.6.3A blank Kaggle guard
    if (
        not str(config.kaggle_visual_index_csv).strip()
        or str(config.kaggle_visual_index_csv).strip() == "."
        or not config.kaggle_visual_index_csv.is_file()
    ):
        return []

'''

text = text[:match.start(4)] + insert + text[match.start(4):]

CATALOG.write_text(text, encoding="utf-8")

print("v0.6.3A installed.")
print("Blank or missing Kaggle visual index paths now safely return no visual rows.")
print("Backup saved to:", ARCHIVE)