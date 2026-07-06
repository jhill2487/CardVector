from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "extension" / "overlay.js"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [JS, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_7_0d_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

old = '''  function compactVariantLabel(variant) {
    const name = String(variant?.product_name || "").toLowerCase();
    const finish = String(variant?.finish || "").toLowerCase();

    if (name.includes("1st edition") || name.includes("first edition")) return "1ST EDITION";
    if (name.includes("shadowless")) return "SHADOWLESS";
    if (name.includes("unlimited")) return "UNLIMITED";

    if (!finish || finish === "normal") return "NORMAL";
    if (finish.includes("reverse")) return "REVERSE";
    if (finish.includes("holo")) return "HOLO";
    if (finish.includes("cosmos")) return "COSMOS";
    return formatFinish(finish);
  }'''

new = '''  function compactVariantLabel(variant) {
    const name = String(variant?.product_name || "").toLowerCase();
    const finish = String(variant?.finish || "").toLowerCase();

    if (name.includes("energy symbol pattern")) return "ENERGY SYMBOL";
    if (name.includes("friend ball")) return "FRIEND BALL";
    if (name.includes("love ball")) return "LOVE BALL";
    if (name.includes("poke ball") || name.includes("poké ball")) return "POKE BALL";
    if (name.includes("team rocket")) return "TEAM ROCKET";

    if (name.includes("1st edition") || name.includes("first edition")) return "1ST EDITION";
    if (name.includes("shadowless")) return "SHADOWLESS";
    if (name.includes("unlimited")) return "UNLIMITED";

    if (!finish || finish === "normal") return "NORMAL";
    if (finish.includes("reverse")) return "REVERSE";
    if (finish.includes("holo")) return "HOLO";
    if (finish.includes("cosmos")) return "COSMOS";
    return formatFinish(finish);
  }'''

if old not in js:
    raise SystemExit("ERROR: Could not find compactVariantLabel block. No changes written.")

js = js.replace(old, new, 1)
JS.write_text(js, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.0.3"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.0D Variant Label Renderer Fix")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/manifest.json")