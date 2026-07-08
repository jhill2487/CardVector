from pathlib import Path
import json
import shutil
import sys
from datetime import datetime
from PIL import Image

ROOT = Path(__file__).resolve().parent

DEFAULT_KAGGLE_ROOTS = [
    ROOT / "kaggle_dataset" / "Pokemon TCG" / "Pokemon TCG",
    ROOT.parent / "kaggle_dataset" / "Pokemon TCG" / "Pokemon TCG",
    Path(r"C:\Users\JaredHill\Personal\Ebay-TCGPlayer Inventory Sync Project\kaggle_dataset\Pokemon TCG\Pokemon TCG"),
    Path(r"C:\Users\user\Desktop\Scanner Interface Dev\kaggle_dataset\Pokemon TCG\Pokemon TCG"),
]

OUT_IMAGES = ROOT / "kaggle_test_images"
OUT_LABELS = ROOT / "border_training_labels"
OUT_RESULTS = ROOT / "studio_results"

GG_TERMS = [
    "galarian",
    "gallery",
    "gg",
    "crown",
    "zenith",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def find_kaggle_root() -> Path:
    for p in DEFAULT_KAGGLE_ROOTS:
        if p.exists():
            return p

    # Fallback: shallow search under project folder and parent
    search_roots = [ROOT, ROOT.parent]
    for base in search_roots:
        for p in base.rglob("Pokemon TCG"):
            if p.is_dir():
                imgs = list(p.rglob("*.jpg"))[:5]
                if imgs:
                    return p

    raise SystemExit(
        "ERROR: Could not find Kaggle Pokemon TCG image folder.\n"
        "Edit this script and add your Kaggle root to DEFAULT_KAGGLE_ROOTS."
    )


def score_gg_file(path: Path) -> int:
    s = str(path).lower()
    name = path.name.lower()
    score = 0

    # Strong preference for actual Galarian Gallery naming.
    if "galarian" in s:
        score += 100
    if "gallery" in s:
        score += 100
    if "gg" in name:
        score += 80
    if "crown" in s:
        score += 30
    if "zenith" in s:
        score += 30

    # Prefer likely card scan files, not thumbs.
    if path.suffix.lower() in IMAGE_EXTS:
        score += 10

    return score


def find_gg_image(kaggle_root: Path) -> Path:
    candidates = []
    for p in kaggle_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            sc = score_gg_file(p)
            if sc >= 80:
                candidates.append((sc, p))

    if not candidates:
        raise SystemExit(
            f"ERROR: No likely GG/Galarian Gallery images found under:\n{kaggle_root}\n"
            "Try searching manually for Crown Zenith / Galarian Gallery images."
        )

    candidates.sort(key=lambda x: (-x[0], str(x[1]).lower()))
    return candidates[0][1]


def make_full_card_label(image_path: Path, label_path: Path) -> None:
    with Image.open(image_path) as im:
        w, h = im.size

    # Kaggle card scans are already full-card images, so card border = full image.
    # Regions are left empty because scanner uses known_good template regions after warping.
    label = {
        "filename": image_path.name,
        "trainer_version": "kaggle_full_card_auto_label",
        "timestamp": datetime.now().isoformat(),
        "image_size": {"width": w, "height": h},
        "regions": {
            "card": [
                {"x": 0, "y": 0},
                {"x": w - 1, "y": 0},
                {"x": w - 1, "y": h - 1},
                {"x": 0, "y": h - 1},
            ],
            "name": [],
            "number": [],
            "setcode": [],
        },
    }
    label_path.write_text(json.dumps(label, indent=2), encoding="utf-8")


def main():
    print("Putnam Kaggle GG Scanner Test")
    print("Root:", ROOT)

    kaggle_root = find_kaggle_root()
    print("Kaggle root:", kaggle_root)

    gg_src = find_gg_image(kaggle_root)
    print("Selected GG image:", gg_src)

    OUT_IMAGES.mkdir(exist_ok=True)
    OUT_LABELS.mkdir(exist_ok=True)
    OUT_RESULTS.mkdir(exist_ok=True)

    test_name = "KAGGLE_GG_TEST" + gg_src.suffix.lower()
    test_img = OUT_IMAGES / test_name
    shutil.copy2(gg_src, test_img)

    label_path = OUT_LABELS / "KAGGLE_GG_TEST.json"
    make_full_card_label(test_img, label_path)
    print("Created label:", label_path)

    # Run scanner engine directly.
    import scanner_core_region_ocr

    out_dir = OUT_RESULTS / ("KAGGLE_GG_TEST_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    out_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "sqlite_path": "database/putnam_pokemon_cloud_ready.sqlite",
        "template_label": "known_good/IMG_7505.json",
        "target_labels": "border_training_labels",
        "strict_mode": True,
    }

    result = scanner_core_region_ocr.scan_image(str(test_img), config, str(out_dir))

    result_path = out_dir / "kaggle_gg_scan_result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("")
    print("Scan complete.")
    print("Result JSON:", result_path)
    print("Output folder:", out_dir)
    print("")
    print("Summary:")
    print("Status:", result.get("status"))
    print("OCR Name:", (result.get("ocr") or {}).get("name"))
    print("OCR Number:", (result.get("ocr") or {}).get("number"))
    print("OCR Bottom ID:", (result.get("ocr") or {}).get("bottom_id"))
    print("Match:", result.get("match"))
    print("")
    print("Open debug crops in:")
    print(out_dir / "region_crops")


if __name__ == "__main__":
    main()
