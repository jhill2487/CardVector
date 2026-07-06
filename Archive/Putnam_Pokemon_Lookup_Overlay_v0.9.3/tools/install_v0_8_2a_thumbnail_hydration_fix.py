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
    shutil.copy2(p, archive / f"{p.stem}_before_v0_8_2a_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

old = '''      } else if (img) {
        setImageSourceSafe(img, imageUrl);
        attachImageHoverPreview(img, card, card.prices || {});
      }
    }

    mount.replaceChildren(renderVariantPrices(card, card.prices || {}));'''

new = '''      } else if (img) {
        setImageSourceSafe(img, imageUrl);
        attachImageHoverPreview(img, card, card.prices || {});
      }

      // v0.8.2A: hydrate missing thumbnail after prices reveal a product image.
      if (media && !media.querySelector(".ppo-thumb")) {
        const placeholder = media.querySelector(".ppo-no-image");
        const hydrated = el("img", {
          className: "ppo-thumb",
          attrs: { alt: card.card_name || "Pokemon card image", loading: "eager" }
        });
        setImageSourceSafe(hydrated, imageUrl);
        attachImageFallback(hydrated, media);
        attachImageHoverPreview(hydrated, card, card.prices || {});
        if (placeholder) placeholder.remove();
        media.prepend(hydrated);
      }
    }

    mount.replaceChildren(renderVariantPrices(card, card.prices || {}));'''

if old not in js:
    raise SystemExit("ERROR: Could not locate thumbnail update block. No changes written.")

js = js.replace(old, new, 1)

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.8.2.1"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

JS.write_text(js, encoding="utf-8")

print("Installed v0.8.2A Thumbnail Hydration Fix")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/manifest.json")