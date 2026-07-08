from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "extension" / "overlay.js"
MANIFEST = ROOT / "extension" / "manifest.json"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [JS, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_7_2_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

start = js.find("  function compactVariantLabel(variant) {")
end = js.find("  function samePrintedNumber(card, variant) {", start)

if start == -1 or end == -1:
    raise SystemExit("ERROR: Could not locate compactVariantLabel block. No changes written.")

new_block = '''  function compactVariantLabel(variant) {
    const name = String(variant?.product_name || "").toLowerCase();
    const finish = String(variant?.finish || "").toLowerCase();

    const variantPatterns = [
      ["energy symbol pattern", "ENERGY SYMBOL"],
      ["friend ball", "FRIEND BALL"],
      ["love ball", "LOVE BALL"],
      ["poke ball", "POKE BALL"],
      ["poké ball", "POKE BALL"],
      ["master ball", "MASTER BALL"],
      ["ultra ball", "ULTRA BALL"],
      ["great ball", "GREAT BALL"],
      ["team rocket", "TEAM ROCKET"],
      ["cosmos holo", "COSMOS"],
      ["cosmos", "COSMOS"],
      ["prerelease", "PRERELEASE"],
      ["pre-release", "PRERELEASE"],
      ["staff", "STAFF"],
      ["league", "LEAGUE"],
      ["stamped", "STAMPED"],
      ["stamp", "STAMPED"],
      ["promo", "PROMO"],
      ["1st edition", "1ST EDITION"],
      ["first edition", "1ST EDITION"],
      ["shadowless", "SHADOWLESS"],
      ["unlimited", "UNLIMITED"]
    ];

    for (const [needle, label] of variantPatterns) {
      if (name.includes(needle)) return label;
    }

    if (!finish || finish === "normal") return "NORMAL";
    if (finish.includes("reverse")) return "REVERSE";
    if (finish.includes("holo")) return "HOLO";
    if (finish.includes("cosmos")) return "COSMOS";

    return formatFinish(finish);
  }

'''

js = js[:start] + new_block + js[end:]
JS.write_text(js, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.2"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

release_notes = DOCS / "RELEASE_NOTES_v0_7_2.txt"
release_notes.write_text("""v0.7.2 Variant Label Expansion

Added variant label recognition for:
- Energy Symbol Pattern
- Friend Ball
- Love Ball
- Poke Ball
- Master Ball
- Ultra Ball
- Great Ball
- Team Rocket
- Cosmos
- Prerelease
- Staff
- League
- Stamped
- Promo
- 1st Edition
- Shadowless
- Unlimited

No UI layout changes.
""", encoding="utf-8")

print("Installed v0.7.2 Variant Label Expansion")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print(f"Release notes: {release_notes}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/manifest.json")