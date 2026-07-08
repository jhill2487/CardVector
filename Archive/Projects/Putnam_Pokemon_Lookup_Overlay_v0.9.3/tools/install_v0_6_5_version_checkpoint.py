from pathlib import Path
import json
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = ROOT / "archive_old_versions" / f"manifest_before_v0_6_5_{stamp}.json"
backup.parent.mkdir(exist_ok=True)

shutil.copy2(MANIFEST, backup)

data = json.loads(MANIFEST.read_text(encoding="utf-8"))
old = data.get("version")
data["version"] = "0.6.5"

MANIFEST.write_text(json.dumps(data, indent=2), encoding="utf-8")

print(f"Updated extension version: {old} -> 0.6.5")
print("Patched:", MANIFEST)
print("Backup :", backup)