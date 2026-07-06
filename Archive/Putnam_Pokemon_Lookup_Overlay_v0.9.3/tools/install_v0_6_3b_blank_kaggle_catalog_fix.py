from pathlib import Path
import re
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "backend" / "card_catalog.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = TARGET.with_suffix(f".py.bak_v0_6_3b_{stamp}")
shutil.copy2(TARGET, backup)

text = TARGET.read_text(encoding="utf-8")

text = text.replace(
    "@lru_cache(maxsize=1)\n\ndef _safe_existing_file",
    "def _safe_existing_file"
)

text = re.sub(
    r"def _safe_existing_file\(path\) -> bool:\n.*?\n(?=def catalog_status\(\))",
    '''def _safe_existing_file(path) -> bool:
    try:
        if path is None:
            return False
        s = str(path).strip()
        if not s or s == ".":
            return False
        p = Path(s).expanduser()
        return p.exists() and p.is_file()
    except Exception:
        return False


''',
    text,
    flags=re.S,
)

text = re.sub(
    r"def catalog_status\(\) -> dict\[str, Any\]:\n.*?\n(?=\ndef _search_cards_exact)",
    '''def catalog_status() -> dict[str, Any]:
    config = load_config()

    sqlite_exists = _safe_existing_file(config.sqlite_path)
    kaggle_visual_index_exists = _safe_existing_file(config.kaggle_visual_index_csv)

    image_root_text = str(config.kaggle_image_root).strip()
    kaggle_image_root_exists = bool(
        image_root_text
        and image_root_text != "."
        and config.kaggle_image_root.exists()
        and config.kaggle_image_root.is_dir()
    )

    status: dict[str, Any] = {
        "sqlite_path": str(config.sqlite_path),
        "sqlite_exists": sqlite_exists,
        "kaggle_visual_index_csv": str(config.kaggle_visual_index_csv),
        "kaggle_visual_index_exists": kaggle_visual_index_exists,
        "kaggle_image_root": str(config.kaggle_image_root),
        "kaggle_image_root_exists": kaggle_image_root_exists,
        "sets": 0,
        "cards": 0,
        "fingerprints": 0,
        "visual_index_rows": 0,
        "ready": False,
    }

    if sqlite_exists:
        con = sqlite3.connect(config.sqlite_path)
        try:
            cur = con.cursor()
            status["sets"] = cur.execute("select count(*) from pokemon_sets").fetchone()[0]
            status["cards"] = cur.execute("select count(*) from pokemon_cards").fetchone()[0]
            try:
                status["fingerprints"] = cur.execute("select count(*) from kaggle_ocr_fingerprints").fetchone()[0]
            except sqlite3.Error:
                status["fingerprints"] = 0
        finally:
            con.close()

    if kaggle_visual_index_exists:
        with config.kaggle_visual_index_csv.open("r", encoding="utf-8", newline="") as handle:
            status["visual_index_rows"] = max(sum(1 for _ in handle) - 1, 0)

    status["ready"] = bool(status["sqlite_exists"] and status["cards"] > 0)
    return status

''',
    text,
    flags=re.S,
)

TARGET.write_text(text, encoding="utf-8")

print("Installed v0.6.3b blank Kaggle catalog fix")
print(f"Patched: {TARGET}")
print(f"Backup:  {backup}")