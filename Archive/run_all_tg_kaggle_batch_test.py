from pathlib import Path
import csv
import json
import shutil
from datetime import datetime
from PIL import Image
import scanner_core_region_ocr

ROOT = Path(__file__).resolve().parent
KAGGLE_ROOT = ROOT / r"kaggle_dataset\Pokemon TCG\Pokemon TCG"

TEST_IMAGE_DIR = ROOT / "kaggle_test_images"
LABEL_DIR = ROOT / "border_training_labels"
RUN_ID = "KAGGLE_TG_BATCH_" + datetime.now().strftime("%Y%m%d_%H%M%S")
RESULT_ROOT = ROOT / "studio_results" / RUN_ID

TEST_IMAGE_DIR.mkdir(exist_ok=True)
LABEL_DIR.mkdir(exist_ok=True)
RESULT_ROOT.mkdir(parents=True, exist_ok=True)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Trainer Gallery patterns found in Kaggle filenames/folders.
# Examples:
# en_US-SWSH9-TG001-flareon.jpg
# en_US-SWSH11-TG005-pikachu.jpg
def is_tg_image(path: Path) -> bool:
    s = str(path).lower()
    name = path.name.lower()
    return (
        "-tg" in name
        or "_tg" in name
        or "trainer-gallery" in s
        or "trainer_gallery" in s
    ) and path.suffix.lower() in IMAGE_EXTS


def make_full_card_label(image_path: Path, label_path: Path) -> None:
    with Image.open(image_path) as im:
        w, h = im.size

    label = {
        "filename": image_path.name,
        "trainer_version": "kaggle_tg_batch_full_card_auto_label",
        "timestamp": datetime.now().isoformat(),
        "image_size": {"width": w, "height": h},
        "regions": {
            "card": [
                {"x": 0, "y": 0},
                {"x": w - 1, "y": 0},
                {"x": w - 1, "y": h - 1},
                {"x": 0, "y": h - 1}
            ],
            "name": [],
            "number": [],
            "setcode": []
        }
    }
    label_path.write_text(json.dumps(label, indent=2), encoding="utf-8")


def safe_stem(src: Path, idx: int) -> str:
    # Keep it stable and Windows-safe.
    return f"KAGGLE_TG_BATCH_{idx:04d}_{src.stem[:80]}"


def main():
    print("Putnam Kaggle TG Batch Test")
    print("Root:", ROOT)
    print("Kaggle root:", KAGGLE_ROOT)

    if not KAGGLE_ROOT.exists():
        raise SystemExit(f"ERROR: Kaggle root not found:\n{KAGGLE_ROOT}")

    tg_files = sorted([p for p in KAGGLE_ROOT.rglob("*") if p.is_file() and is_tg_image(p)], key=lambda p: str(p).lower())

    if not tg_files:
        raise SystemExit("ERROR: No Trainer Gallery images found.")

    print(f"TG images found: {len(tg_files)}")
    print("Output:", RESULT_ROOT)

    config = {
        "sqlite_path": "database/putnam_pokemon_cloud_ready.sqlite",
        "template_label": "known_good/IMG_7505.json",
        "target_labels": "border_training_labels",
        "strict_mode": True
    }

    summary_rows = []

    for idx, src in enumerate(tg_files, start=1):
        stem = safe_stem(src, idx)
        test_img = TEST_IMAGE_DIR / (stem + src.suffix.lower())
        label_path = LABEL_DIR / (stem + ".json")
        out_dir = RESULT_ROOT / stem
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(src, test_img)
            make_full_card_label(test_img, label_path)

            result = scanner_core_region_ocr.scan_image(str(test_img), config, str(out_dir))
            result_path = out_dir / "result.json"
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

            ocr = result.get("ocr") or {}
            match = result.get("match") or {}
            candidates = result.get("candidates") or []
            top = candidates[0] if candidates else {}

            row = {
                "idx": idx,
                "source_file": str(src),
                "test_file": str(test_img),
                "status": result.get("status", ""),
                "geometry_status": result.get("geometry_status", ""),
                "ocr_name": ocr.get("name", ""),
                "ocr_number": ocr.get("number", ""),
                "ocr_bottom_id": ocr.get("bottom_id", ""),
                "match_status": match.get("status", ""),
                "match_card_name": match.get("card_name", ""),
                "match_set_name": match.get("set_name", ""),
                "match_card_number": match.get("card_number", ""),
                "match_confidence": match.get("confidence", ""),
                "match_reason": match.get("reason", ""),
                "top_candidate_name": top.get("card_name", ""),
                "top_candidate_set": top.get("set_name", ""),
                "top_candidate_number": top.get("card_number", ""),
                "top_candidate_score": top.get("score", ""),
                "result_json": str(result_path),
                "crop_folder": str(out_dir / "region_crops"),
            }
            summary_rows.append(row)

            print(f"[{idx}/{len(tg_files)}] {src.name} -> {row['match_status'] or row['status']} | OCR {row['ocr_name']} | {row['ocr_number'] or row['ocr_bottom_id']}")

        except Exception as exc:
            row = {
                "idx": idx,
                "source_file": str(src),
                "test_file": str(test_img),
                "status": "ERROR",
                "geometry_status": "",
                "ocr_name": "",
                "ocr_number": "",
                "ocr_bottom_id": "",
                "match_status": "ERROR",
                "match_card_name": "",
                "match_set_name": "",
                "match_card_number": "",
                "match_confidence": "",
                "match_reason": str(exc),
                "top_candidate_name": "",
                "top_candidate_set": "",
                "top_candidate_number": "",
                "top_candidate_score": "",
                "result_json": "",
                "crop_folder": str(out_dir / "region_crops"),
            }
            summary_rows.append(row)
            print(f"[{idx}/{len(tg_files)}] ERROR {src.name}: {exc}")

    csv_path = RESULT_ROOT / "tg_batch_summary.csv"
    fields = list(summary_rows[0].keys()) if summary_rows else []
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    auto = sum(1 for r in summary_rows if r["match_status"] == "Auto Match")
    needs = sum(1 for r in summary_rows if r["match_status"] == "Needs Review" or r["status"] == "Needs Review")
    errors = sum(1 for r in summary_rows if r["status"] == "ERROR")

    print("")
    print("Batch complete.")
    print("Total TG images:", len(summary_rows))
    print("Auto Match:", auto)
    print("Needs Review:", needs)
    print("Errors:", errors)
    print("")
    print("Summary CSV:")
    print(csv_path)
    print("")
    print("Result folder:")
    print(RESULT_ROOT)


if __name__ == "__main__":
    main()
