from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "extension" / "overlay.js"
CSS = ROOT / "extension" / "overlay.css"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [JS, CSS, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_7_3a_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

# Add generic preview helpers before attachImageHoverPreview.
old = '''  function attachImageHoverPreview(img, card, prices) {
    if (!img) return;
    const previewUrl = getBestPreviewImageUrl(card, prices);
    if (!previewUrl) return;

    img.addEventListener("mouseenter", () => {
      let preview = document.getElementById("ppo-image-preview");
      if (!preview) {
        preview = el("div", { id: "ppo-image-preview", className: "ppo-image-preview" });
        document.documentElement.appendChild(preview);
      }

      preview.replaceChildren(el("img", {
        attrs: {
          src: previewUrl,
          alt: card?.card_name || "Pokemon card preview"
        }
      }));

      preview.classList.add("ppo-image-preview-open");
    });

    img.addEventListener("mouseleave", () => {
      const preview = document.getElementById("ppo-image-preview");
      if (preview) preview.classList.remove("ppo-image-preview-open");
    });
  }

'''

new = '''  function openImagePreview(previewUrl, altText = "Pokemon card preview") {
    if (!previewUrl) return;

    let preview = document.getElementById("ppo-image-preview");
    if (!preview) {
      preview = el("div", { id: "ppo-image-preview", className: "ppo-image-preview" });
      document.documentElement.appendChild(preview);
    }

    preview.replaceChildren(el("img", {
      attrs: {
        src: previewUrl,
        alt: altText
      }
    }));

    preview.classList.add("ppo-image-preview-open");
  }

  function closeImagePreview() {
    const preview = document.getElementById("ppo-image-preview");
    if (preview) preview.classList.remove("ppo-image-preview-open");
  }

  function attachImageHoverPreview(img, card, prices) {
    if (!img) return;
    const previewUrl = getBestPreviewImageUrl(card, prices);
    if (!previewUrl) return;

    img.addEventListener("mouseenter", () => {
      openImagePreview(previewUrl, card?.card_name || "Pokemon card preview");
    });

    img.addEventListener("mouseleave", closeImagePreview);
  }

  function attachVariantRowHoverPreview(row, variant) {
    if (!row || !variant?.image_url) return;

    row.classList.add("ppo-variant-preview-row");
    row.addEventListener("mouseenter", () => {
      openImagePreview(
        absoluteUrl(variant.image_url),
        variant.product_name || "Pokemon card variant preview"
      );
    });
    row.addEventListener("mouseleave", closeImagePreview);
  }

'''

if old not in js:
    raise SystemExit("ERROR: Could not find existing attachImageHoverPreview block. No changes written.")

js = js.replace(old, new, 1)

old_row = '''      const row = el("div", { className: "ppo-compact-price-row" });
      row.append(el("span", { className: "ppo-compact-variant-label", text: compactVariantLabel(variant) }));'''

new_row = '''      const row = el("div", { className: "ppo-compact-price-row" });
      attachVariantRowHoverPreview(row, variant);
      row.append(el("span", { className: "ppo-compact-variant-label", text: compactVariantLabel(variant) }));'''

if old_row not in js:
    raise SystemExit("ERROR: Could not find compact price row creation block. No changes written.")

js = js.replace(old_row, new_row, 1)
JS.write_text(js, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
css += r'''

/* v0.7.3A variant hover preview polish */
.ppo-variant-preview-row {
  cursor: zoom-in;
  border-radius: 6px;
  transition: background .08s ease, transform .08s ease;
}

.ppo-variant-preview-row:hover {
  background: rgba(15, 23, 42, .06);
}

.ppo-image-preview {
  cursor: default;
}
'''

CSS.write_text(css, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.3.1"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.3A Variant Hover Preview Polish")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/overlay.css")
print(" - extension/manifest.json")