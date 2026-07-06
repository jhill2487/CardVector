from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

ROOT = Path.cwd()
BACKEND = ROOT / "backend"
DATA_SOURCES = BACKEND / "data_sources.json"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

if not DATA_SOURCES.exists():
    raise SystemExit(f"ERROR: Missing {DATA_SOURCES}")

original = DATA_SOURCES.read_text(encoding="utf-8")
(ARCHIVE / f"data_sources_before_portability_p0_2_{stamp}.json").write_text(original, encoding="utf-8")

data = json.loads(original)

# Use project-relative database path.
database_path = ROOT / "database" / "putnam_pokemon_cards.sqlite"
if not database_path.exists():
    # Common alternate names used in the project.
    candidates = list((ROOT / "database").glob("*.sqlite")) + list((ROOT / "database").glob("*.db"))
    if candidates:
        database_path = candidates[0]

data["sqlite_path"] = str(database_path)

# Use project-relative Kaggle paths if present.
kaggle_root_candidates = [
    ROOT / "kaggle_dataset" / "Pokemon TCG" / "Pokemon TCG",
    ROOT.parent / "kaggle_dataset" / "Pokemon TCG" / "Pokemon TCG",
    ROOT.parent / "Pokemon TCG" / "Pokemon TCG",
]

for candidate in kaggle_root_candidates:
    if candidate.exists():
        data["kaggle_image_root"] = str(candidate)
        break
else:
    data["kaggle_image_root"] = ""

kaggle_index_candidates = [
    ROOT / "kaggle_dataset" / "Pokemon TCG" / "kaggle_visual_index.csv",
    ROOT.parent / "kaggle_dataset" / "Pokemon TCG" / "kaggle_visual_index.csv",
    ROOT / "kaggle_visual_index.csv",
]

for candidate in kaggle_index_candidates:
    if candidate.exists():
        data["kaggle_visual_index_csv"] = str(candidate)
        break
else:
    data["kaggle_visual_index_csv"] = ""

DATA_SOURCES.write_text(json.dumps(data, indent=2), encoding="utf-8")

print("P0.2 data_sources portability fix complete.")
print("Updated:", DATA_SOURCES)
print("sqlite_path:", data.get("sqlite_path"))
print("kaggle_visual_index_csv:", data.get("kaggle_visual_index_csv"))
print("kaggle_image_root:", data.get("kaggle_image_root"))
print("Backup saved to:", ARCHIVE)