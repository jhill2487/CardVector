from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backend" / "card_catalog.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)
shutil.copy2(CATALOG, archive / f"card_catalog_before_visual_index_config_fix_{stamp}.py")

text = CATALOG.read_text(encoding="utf-8")

old = '''@lru_cache(maxsize=1)
def visual_index_rows() -> tuple[dict[str, str], ...]:
    if not _safe_existing_file(config.kaggle_visual_index_csv):
        return ()

    with config.kaggle_visual_index_csv.open("r", encoding="utf-8", newline="") as handle:
        import csv
        return tuple(csv.DictReader(handle))
'''

new = '''@lru_cache(maxsize=1)
def visual_index_rows() -> tuple[dict[str, str], ...]:
    config = load_config()
    if not _safe_existing_file(config.kaggle_visual_index_csv):
        return ()

    with config.kaggle_visual_index_csv.open("r", encoding="utf-8", newline="") as handle:
        import csv
        return tuple(csv.DictReader(handle))
'''

if old not in text:
    raise SystemExit("ERROR: Could not find visual_index_rows config bug block. No changes written.")

CATALOG.write_text(text.replace(old, new, 1), encoding="utf-8")

print("Fixed visual_index_rows config bug")
print(f"Backup saved in: {archive}")