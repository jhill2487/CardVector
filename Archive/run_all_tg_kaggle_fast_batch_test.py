from pathlib import Path
import argparse
import csv
import json
import shutil
import time
from datetime import datetime
from PIL import Image
import scanner_core_region_ocr

ROOT = Path(__file__).resolve().parent
KAGGLE_ROOT = ROOT / r"kaggle_dataset\Pokemon TCG\Pokemon TCG"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

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
    # Only write label if missing to avoid repeated disk work.
    if label_path.exists():
        return

    with Image.open(image_path) as im:
        w, h = im.size

    label = {
        "filename": image_path.name,
        "trainer_version": "kaggle_tg_fast_batch_full_card_auto_label",
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
    return f"KAGGLE_TG_FAST_{idx:04d}_{src.stem[:80]}"

def maybe_patch_db_loader_once():
    """
    Speed win: scanner_core_region_ocr may reload SQLite rows for every card.
    This monkey-patches known DB loader helpers inside the current process only,
    so rows are loaded once and reused for the batch.

    This does not change scanner_core_region_ocr.py on disk.
    """
    cached_rows = {}

    def load_rows_cached(sqlite_path):
        import sqlite3
        p = Path(sqlite_path)
        key = str(p.resolve()) if p.exists() else str(p)
        if key not in cached_rows:
            con = sqlite3.connect(str(p))
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cached_rows[key] = [dict(r) for r in cur.execute("select * from pokemon_cards").fetchall()]
            con.close()
        return cached_rows[key]

    patched = []
    for fn_name in [
        "_bottom_id_load_rows",
        "_db_assist_load_rows_v1",
    ]:
        if hasattr(scanner_core_region_ocr, fn_name):
            setattr(scanner_core_region_ocr, fn_name, load_rows_cached)
            patched.append(fn_name)

    return patched

def main():
    ap = argparse.ArgumentParser(description="Fast TG Kaggle batch test for Putnam Scanner")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of TG images processed. 0 = all.")
    ap.add_argument("--start", type=int, default=1, help="1-based start index.")
    ap.add_argument("--no-copy", action="store_true", help="Use Kaggle images in place instead of copying to kaggle_test_images.")
    ap.add_argument("--no-json", action="store_true", help="Do not save full per-card JSON results. CSV still saved.")
    ap.add_argument("--quiet", action="store_true", help="Print fewer per-card details.")
    args = ap.parse_args()

    test_image_dir = ROOT / "kaggle_test_images"
    label_dir = ROOT / "border_training_labels"
    run_id = "KAGGLE_TG_FAST_BATCH_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    result_root = ROOT / "studio_results" / run_id

    test_image_dir.mkdir(exist_ok=True)
    label_dir.mkdir(exist_ok=True)
    result_root.mkdir(parents=True, exist_ok=True)

    print("Putnam Fast Kaggle TG Batch Test")
    print("Root:", ROOT)
    print("Kaggle root:", KAGGLE_ROOT)

    if not KAGGLE_ROOT.exists():
        raise SystemExit(f"ERROR: Kaggle root not found:\n{KAGGLE_ROOT}")

    patched = maybe_patch_db_loader_once()
    if patched:
        print("Speed patch active: cached DB loaders:", ", ".join(patched))
    else:
        print("Speed patch note: no known DB loader helpers found to patch.")

    tg_files = sorted([p for p in KAGGLE_ROOT.rglob("*") if p.is_file() and is_tg_image(p)], key=lambda p: str(p).lower())

    if args.start > 1:
        tg_files = tg_files[args.start - 1:]
    if args.limit and args.limit > 0:
        tg_files = tg_files[:args.limit]

    if not tg_files:
        raise SystemExit("ERROR: No Trainer Gallery images selected.")

    print(f"TG images selected: {len(tg_files)}")
    print("Output:", result_root)
    print("Options:", {"limit": args.limit, "start": args.start, "no_copy": args.no_copy, "no_json": args.no_json})
    print("")

    config = {
        "sqlite_path": "database/putnam_pokemon_cloud_ready.sqlite",
        "template_label": "known_good/IMG_7505.json",
        "target_labels": "border_training_labels",
        "strict_mode": True
    }

    summary_rows = []
    t0_all = time.perf_counter()

    for idx, src in enumerate(tg_files, start=args.start):
        t0 = time.perf_counter()
        stem = safe_stem(src, idx)

        if args.no_copy:
            test_img = src
            # Scanner label lookup is based on image stem. Create label using the actual source stem.
            label_path = label_dir / (src.stem + ".json")
        else:
            test_img = test_image_dir / (stem + src.suffix.lower())
            label_path = label_dir / (stem + ".json")
            if not test_img.exists():
                shutil.copy2(src, test_img)

        out_dir = result_root / stem
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            make_full_card_label(test_img, label_path)

            result = scanner_core_region_ocr.scan_image(str(test_img), config, str(out_dir))

            result_path = out_dir / "result.json"
            if not args.no_json:
                result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            else:
                result_path = ""

            ocr = result.get("ocr") or {}
            match = result.get("match") or {}
            candidates = result.get("candidates") or []
            top = candidates[0] if candidates else {}
            elapsed = time.perf_counter() - t0

            row = {
                "idx": idx,
                "elapsed_sec": round(elapsed, 3),
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

            if not args.quiet:
                print(
                    f"[{len(summary_rows)}/{len(tg_files)}] {src.name} "
                    f"-> {row['match_status'] or row['status']} | "
                    f"OCR {row['ocr_name']} | {row['ocr_number'] or row['ocr_bottom_id']} | "
                    f"{elapsed:.2f}s"
                )

        except KeyboardInterrupt:
            print("\nStopped by user. Writing partial CSV...")
            break
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            row = {
                "idx": idx,
                "elapsed_sec": round(elapsed, 3),
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
            if not args.quiet:
                print(f"[{len(summary_rows)}/{len(tg_files)}] ERROR {src.name}: {exc} | {elapsed:.2f}s")

    csv_path = result_root / "tg_fast_batch_summary.csv"
    if summary_rows:
        fields = list(summary_rows[0].keys())
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(summary_rows)

    total_elapsed = time.perf_counter() - t0_all
    auto = sum(1 for r in summary_rows if r["match_status"] == "Auto Match")
    needs = sum(1 for r in summary_rows if r["match_status"] == "Needs Review" or r["status"] == "Needs Review")
    errors = sum(1 for r in summary_rows if r["status"] == "ERROR")
    avg = (sum(float(r["elapsed_sec"]) for r in summary_rows) / len(summary_rows)) if summary_rows else 0

    print("")
    print("Fast batch complete.")
    print("Total processed:", len(summary_rows))
    print("Auto Match:", auto)
    print("Needs Review:", needs)
    print("Errors:", errors)
    print("Total elapsed sec:", round(total_elapsed, 2))
    print("Avg sec/card:", round(avg, 3))
    print("")
    print("Summary CSV:")
    print(csv_path)
    print("")
    print("Result folder:")
    print(result_root)

if __name__ == "__main__":
    main()
