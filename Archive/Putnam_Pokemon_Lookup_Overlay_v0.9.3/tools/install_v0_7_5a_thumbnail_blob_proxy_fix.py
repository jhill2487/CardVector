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
    shutil.copy2(p, archive / f"{p.stem}_before_v0_7_5a_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

# Add blob image cache after search cache.
js = js.replace(
    "const searchResultCache = new Map();",
    """const searchResultCache = new Map();
  const imageBlobUrlCache = new Map();""",
    1
)

# Insert safe image helpers after absoluteUrl.
marker = '''  function absoluteUrl(path) {
    if (!path) return "";
    if (/^https?:\\/\\//i.test(path)) return path;
    return `${backendUrl}${path.startsWith("/") ? "" : "/"}${path}`;
  }

'''

insert = '''  function absoluteUrl(path) {
    if (!path) return "";
    if (/^https?:\\/\\//i.test(path)) return path;
    return `${backendUrl}${path.startsWith("/") ? "" : "/"}${path}`;
  }

  function isLocalBackendUrl(url) {
    return /^http:\\/\\/(127\\.0\\.0\\.1|localhost):8790\\//i.test(String(url || ""));
  }

  async function safeImageUrl(url) {
    const full = absoluteUrl(url);
    if (!full) return "";

    if (!isLocalBackendUrl(full)) return full;

    const cached = imageBlobUrlCache.get(full);
    if (cached) return cached;

    const response = await fetch(full, { cache: "force-cache" });
    if (!response.ok) throw new Error("Image fetch failed");
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    imageBlobUrlCache.set(full, blobUrl);
    return blobUrl;
  }

  function setImageSourceSafe(img, url) {
    const full = absoluteUrl(url);
    if (!img || !full) return;

    safeImageUrl(full)
      .then((safeUrl) => {
        if (safeUrl) img.src = safeUrl;
      })
      .catch(() => {
        img.src = full;
      });
  }

'''

if marker not in js:
    raise SystemExit("ERROR: Could not find absoluteUrl block. No changes written.")
js = js.replace(marker, insert, 1)

# Patch preview open to use safe image URLs.
old_preview = '''  function openImagePreview(previewUrl, altText = "Pokemon card preview") {
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
  }'''

new_preview = '''  function openImagePreview(previewUrl, altText = "Pokemon card preview") {
    if (!previewUrl) return;

    let preview = document.getElementById("ppo-image-preview");
    if (!preview) {
      preview = el("div", { id: "ppo-image-preview", className: "ppo-image-preview" });
      document.documentElement.appendChild(preview);
    }

    const img = el("img", {
      attrs: {
        alt: altText
      }
    });
    setImageSourceSafe(img, previewUrl);

    preview.replaceChildren(img);
    preview.classList.add("ppo-image-preview-open");
  }'''

if old_preview not in js:
    raise SystemExit("ERROR: Could not find openImagePreview block. No changes written.")
js = js.replace(old_preview, new_preview, 1)

# Patch initial thumb creation: remove direct src and set safely after creation.
old_initial = '''        const thumb = el("img", {
          className: "ppo-thumb",
          attrs: { src: imageUrl, alt: card.card_name || "Pokemon card image", loading: "eager" }
        });
        attachImageFallback(thumb, media);
        attachImageHoverPreview(thumb, card, prices);
        media.append(thumb);'''

new_initial = '''        const thumb = el("img", {
          className: "ppo-thumb",
          attrs: { alt: card.card_name || "Pokemon card image", loading: "eager" }
        });
        setImageSourceSafe(thumb, imageUrl);
        attachImageFallback(thumb, media);
        attachImageHoverPreview(thumb, card, prices);
        media.append(thumb);'''

if old_initial not in js:
    raise SystemExit("ERROR: Could not find initial thumbnail block. No changes written.")
js = js.replace(old_initial, new_initial, 1)

# Patch lazy-loaded thumb creation.
old_lazy = '''        img = el("img", {
          className: "ppo-thumb",
          attrs: { src: imageUrl, alt: card.card_name || "Pokemon card image", loading: "eager" }
        });
        attachImageFallback(img, media);
        attachImageHoverPreview(img, card, card.prices || {});'''

new_lazy = '''        img = el("img", {
          className: "ppo-thumb",
          attrs: { alt: card.card_name || "Pokemon card image", loading: "eager" }
        });
        setImageSourceSafe(img, imageUrl);
        attachImageFallback(img, media);
        attachImageHoverPreview(img, card, card.prices || {});'''

if old_lazy in js:
    js = js.replace(old_lazy, new_lazy, 1)

# Patch existing img.src assignment during lazy image update.
js = js.replace(
    "img.src = imageUrl;",
    "setImageSourceSafe(img, imageUrl);"
)

JS.write_text(js, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.5.1"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.5A Thumbnail Blob Proxy Fix")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/manifest.json")
print("Fix:")
print(" - Local backend thumbnails are converted to blob URLs to avoid HTTPS mixed-content blocking.")