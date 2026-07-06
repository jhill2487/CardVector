from pathlib import Path
import json
import shutil
from datetime import datetime
from PIL import Image
import scanner_core_region_ocr

ROOT = Path(__file__).resolve().parent

# Direct target: Flareon TG01/TG30
SRC_IMAGE = ROOT / r"kaggle_dataset\Pokemon TCG\Pokemon TCG\brilliant-stars\en_US-SWSH9-TG001-flareon.jpg"

# Fallback search if the exact file path/name differs
if not SRC_IMAGE.exists():
    search_root = ROOT / r"kaggle_dataset\Pokemon TCG\Pokemon TCG"
    matches = []
    if search_root.exists():
        for p in search_root.rglob("*flareon*"):
            s = str(p).lower()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                if "tg001" in s or "tg01" in s or "trainer" in s or "brilliant" in s:
                    matches.append(p)
    if matches:
        SRC_IMAGE = sorted(matches, key=lambda x: str(x).lower())[0]

TEST_STEM = "KAGGLE_FLAREON_TG01_TEST"
TEST_IMAGE_DIR = ROOT / "kaggle_test_images"
LABEL_DIR = ROOT / "border_training_labels"
RESULT_DIR = ROOT / "studio_results" / (TEST_STEM + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))

TEST_IMAGE_DIR.mkdir(exist_ok=True)
LABEL_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

print("Flareon TG01/TG30 Labeled Kaggle Test")
print("Root:", ROOT)
print("Source image:", SRC_IMAGE)

if not SRC_IMAGE.exists():
    raise SystemExit(
        "ERROR: Could not find Flareon TG01 image.\n"
        "Try running:\n"
        r'dir /s /b "kaggle_dataset\Pokemon TCG\Pokemon TCG\*flareon*"'
    )

test_image = TEST_IMAGE_DIR / (TEST_STEM + SRC_IMAGE.suffix.lower())
shutil.copy2(SRC_IMAGE, test_image)
print("Copied test image:", test_image)

with Image.open(test_image) as im:
    w, h = im.size

label = {
    "filename": test_image.name,
    "trainer_version": "kaggle_full_card_auto_label",
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

label_path = LABEL_DIR / (TEST_STEM + ".json")
label_path.write_text(json.dumps(label, indent=2), encoding="utf-8")
print("Created label:", label_path)

config = {
    "sqlite_path": "database/putnam_pokemon_cloud_ready.sqlite",
    "template_label": "known_good/IMG_7505.json",
    "target_labels": "border_training_labels",
    "strict_mode": True
}

result = scanner_core_region_ocr.scan_image(str(test_image), config, str(RESULT_DIR))

result_path = RESULT_DIR / "flareon_tg01_result.json"
result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

print("\nSummary:")
print("Status:", result.get("status"))

ocr = result.get("ocr") or {}
print("OCR Name:", ocr.get("name"))
print("OCR Number:", ocr.get("number"))
print("OCR Set Code:", ocr.get("setcode"))
print("OCR Bottom ID:", ocr.get("bottom_id"))

print("Match:", result.get("match"))

print("\nResult JSON:")
print(result_path)

print("\nDebug Crops:")
print(RESULT_DIR / "region_crops")
