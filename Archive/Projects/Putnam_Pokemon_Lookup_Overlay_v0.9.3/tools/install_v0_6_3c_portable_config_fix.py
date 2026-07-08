import json
import os
from pathlib import Path

ROOT = Path.cwd()
VERSION = "0.6.3c"

data_sources = {
    "sqlite_path": r"%USERPROFILE%\OneDrive\PutnamCollectibles\Pokemon_Live_Price_Lookup\database\putnam_pokemon_cloud_ready.sqlite",
    "kaggle_visual_index_csv": r"%USERPROFILE%\OneDrive\PutnamCollectibles\Pokemon_Live_Price_Lookup\kaggle_dataset\Pokemon TCG\kaggle_visual_index.csv",
    "kaggle_image_root": r"%USERPROFILE%\OneDrive\PutnamCollectibles\Pokemon_Live_Price_Lookup\kaggle_dataset\Pokemon TCG\Pokemon TCG"
}

# backup existing config
src = ROOT / "data_sources.json"
if src.exists():
    backup = ROOT / f"data_sources.backup_before_v{VERSION}.json"
    backup.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

src.write_text(json.dumps(data_sources, indent=2), encoding="utf-8")

# bump manifest version if present
manifest_paths = [
    ROOT / "extension" / "manifest.json",
    ROOT / "manifest.json",
]

for mp in manifest_paths:
    if mp.exists():
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        manifest["version"] = VERSION
        if "name" in manifest and "Putnam" in manifest["name"]:
            manifest["name"] = f"Putnam Pokemon Lookup Overlay v{VERSION}"
        mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Updated manifest: {mp}")
        break
else:
    print("WARNING: No manifest.json found to bump.")

print("")
print(f"Installed portable config patch v{VERSION}")
print("Wrote data_sources.json:")
print(src.read_text(encoding="utf-8"))

print("")
print("Expanded paths on this PC:")
for k, v in data_sources.items():
    print(f"{k}: {os.path.expandvars(v)}")
