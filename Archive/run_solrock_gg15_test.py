from pathlib import Path
import json
from datetime import datetime
import scanner_core_region_ocr

ROOT = Path(__file__).resolve().parent

IMAGE_PATH = ROOT / r"kaggle_dataset\Pokemon TCG\Pokemon TCG\crown-zenith\en_US-CZ-GG015-solrock.jpg"

OUTPUT_DIR = ROOT / "studio_results" / (
    "SOLROCK_GG15_TEST_" + datetime.now().strftime("%Y%m%d_%H%M%S")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Solrock GG15 Test")
print("Root:", ROOT)
print("Image:", IMAGE_PATH)

if not IMAGE_PATH.exists():
    raise SystemExit(f"ERROR: Image not found:\n{IMAGE_PATH}")

config = {
    "sqlite_path": "database/putnam_pokemon_cloud_ready.sqlite",
}

result = scanner_core_region_ocr.scan_image(
    str(IMAGE_PATH),
    config,
    str(OUTPUT_DIR)
)

result_path = OUTPUT_DIR / "solrock_gg15_result.json"
result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

print("\nSummary:")
print("Status:", result.get("status"))

ocr = result.get("ocr", {})
print("OCR Name:", ocr.get("name"))
print("OCR Number:", ocr.get("number"))
print("OCR Set Code:", ocr.get("setcode"))
print("OCR Bottom ID:", ocr.get("bottom_id"))

print("Match:", result.get("match"))

print("\nResult JSON:")
print(result_path)

print("\nDebug Crops:")
print(OUTPUT_DIR / "region_crops")
