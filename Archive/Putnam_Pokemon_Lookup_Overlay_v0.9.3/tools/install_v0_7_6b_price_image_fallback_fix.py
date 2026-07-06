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
    shutil.copy2(p, archive / f"{p.stem}_before_v0_7_6b_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

old = '''    const imageUrl = absoluteUrl(card.prices?.variants?.[0]?.image_url);
    if (imageUrl) {'''

new = '''    const imageUrl = absoluteUrl(
      card.prices?.variants?.find((variant) => variant?.image_url)?.image_url ||
      card.prices?.variants?.[0]?.image_url
    );
    if (imageUrl) {'''

if old not in js:
    raise SystemExit("ERROR: Could not find price image fallback block. No changes written.")

js = js.replace(old, new, 1)

# Make sure hover preview also uses the newly loaded price image.
old2 = '''      } else if (img) {
        setImageSourceSafe(img, imageUrl);
      }'''

new2 = '''      } else if (img) {
        setImageSourceSafe(img, imageUrl);
        attachImageHoverPreview(img, card, card.prices || {});
      }'''

if old2 in js:
    js = js.replace(old2, new2, 1)

JS.write_text(js, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.6.2"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.6B Price Image Fallback Fix")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/manifest.json")