from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

ROOT = Path.cwd()
EXT = ROOT / "extension"
JS = EXT / "overlay.js"
CSS = EXT / "overlay.css"
MANIFEST = EXT / "manifest.json"
ARCHIVE = ROOT / "archive_old_versions"
NOTES = ROOT / "docs" / "release_notes"

ARCHIVE.mkdir(exist_ok=True)
NOTES.mkdir(parents=True, exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

js = JS.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")
manifest_text = MANIFEST.read_text(encoding="utf-8")

(ARCHIVE / f"overlay_before_v0_5_2_{stamp}.js").write_text(js, encoding="utf-8")
(ARCHIVE / f"overlay_before_v0_5_2_{stamp}.css").write_text(css, encoding="utf-8")
(ARCHIVE / f"manifest_before_v0_5_2_{stamp}.json").write_text(manifest_text, encoding="utf-8")

# Add helper for clean image fallback.
if "function createNoImagePlaceholder" not in js:
    insert_before = "  function conditionCell(conditions, key) {"
    helper = '''  function createNoImagePlaceholder(label = "NO IMAGE") {
    return el("div", {
      className: "ppo-no-image",
      text: label
    });
  }

  function attachImageFallback(img, media) {
    img.addEventListener("error", () => {
      img.remove();
      if (!media.querySelector(".ppo-no-image")) {
        media.prepend(createNoImagePlaceholder());
      }
    }, { once: true });
  }

'''
    if insert_before not in js:
        raise SystemExit("ERROR: Could not find insertion point for image fallback helpers.")
    js = js.replace(insert_before, helper + insert_before)

# Patch main result thumbnail creation.
old_thumb = '''      if (imageUrl) {
        const thumb = el("img", {
          className: "ppo-thumb",
          attrs: { src: imageUrl, alt: card.card_name || "Pokemon card image", loading: "lazy" }
        });
        media.append(thumb);
      }
'''

new_thumb = '''      if (imageUrl) {
        const thumb = el("img", {
          className: "ppo-thumb",
          attrs: { src: imageUrl, alt: card.card_name || "Pokemon card image", loading: "lazy" }
        });
        attachImageFallback(thumb, media);
        media.append(thumb);
      } else {
        media.append(createNoImagePlaceholder());
      }
'''

if old_thumb in js:
    js = js.replace(old_thumb, new_thumb)
elif "attachImageFallback(thumb, media)" not in js:
    raise SystemExit("ERROR: Could not find thumbnail block to patch.")

# Patch lazy image update to clear placeholder when image later becomes available.
old_lazy_image = '''    const imageUrl = absoluteUrl(card.prices?.variants?.[0]?.image_url);
    if (imageUrl) {
      const resultRow = mount.closest(".ppo-result");
      const img = resultRow?.querySelector(".ppo-thumb");
      if (img) img.src = imageUrl;
    }
'''

new_lazy_image = '''    const imageUrl = absoluteUrl(card.prices?.variants?.[0]?.image_url);
    if (imageUrl) {
      const resultRow = mount.closest(".ppo-result");
      const media = resultRow?.querySelector(".ppo-media");
      const existingPlaceholder = media?.querySelector(".ppo-no-image");
      let img = resultRow?.querySelector(".ppo-thumb");

      if (!img && media) {
        img = el("img", {
          className: "ppo-thumb",
          attrs: { src: imageUrl, alt: card.card_name || "Pokemon card image", loading: "lazy" }
        });
        attachImageFallback(img, media);
        if (existingPlaceholder) existingPlaceholder.remove();
        media.prepend(img);
      } else if (img) {
        img.src = imageUrl;
      }
    }
'''

if old_lazy_image in js:
    js = js.replace(old_lazy_image, new_lazy_image)
elif "const imageUrl = absoluteUrl(card.prices?.variants?.[0]?.image_url);" not in js:
    raise SystemExit("ERROR: Could not find lazy image update block.")

# Add CSS for clean placeholder.
if "v0.5.2 - Image Fallback" not in css:
    css += r'''

/* v0.5.2 - Image Fallback */
.ppo-no-image {
  width: 92px;
  min-width: 92px;
  height: 128px;
  border-radius: 6px;
  background: #f3f4f6;
  border: 1px dashed #cbd5e1;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.ppo-media .ppo-no-image {
  margin-bottom: 6px;
}
'''

# Version bump.
manifest = json.loads(manifest_text)
manifest["version"] = "0.5.2"

JS.write_text(js, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

(NOTES / "v0.5.2.md").write_text("""# Putnam Pokemon Lookup Overlay v0.5.2

## Added
- Clean NO IMAGE placeholder for cards without available thumbnails.
- Broken image fallback handling.
- Lazy-loaded price images can now replace the placeholder when available.

## Improved
- Promo cards and catalog-only cards no longer show broken image icons.
- Overlay remains visually clean when thumbnails or price images are unavailable.

## Version
- Chrome extension manifest updated to v0.5.2.
""", encoding="utf-8")

print("v0.5.2 installed.")
print("Added broken image fallback and NO IMAGE placeholder.")
print("Manifest updated to v0.5.2.")
print("Backups saved to:", ARCHIVE)