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
    shutil.copy2(p, archive / f"{p.stem}_before_v0_8_2b_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

start = js.find("  async function loadLazyPrices(card, mount) {")
end = js.find("  function enqueueLazyPriceLoad(card, mount) {", start)

if start == -1 or end == -1:
    raise SystemExit("ERROR: Could not locate loadLazyPrices block. No changes written.")

new_block = r'''  function bestVariantImageUrl(prices) {
    const variants = Array.isArray(prices?.variants) ? prices.variants : [];
    const variant = variants.find((item) => item?.image_url);
    return absoluteUrl(variant?.image_url || "");
  }

  function hydrateResultThumbnail(card, mount) {
    const imageUrl = bestVariantImageUrl(card?.prices || {});
    if (!imageUrl || !mount) return;

    const resultRow = mount.closest(".ppo-result");
    const media = resultRow?.querySelector(".ppo-media");
    if (!media) return;

    let img = media.querySelector(".ppo-thumb");
    if (!img) {
      img = el("img", {
        className: "ppo-thumb",
        attrs: { alt: card.card_name || "Pokemon card image", loading: "eager" }
      });
      media.prepend(img);
    }

    media.querySelectorAll(".ppo-no-image").forEach((node) => node.remove());

    setImageSourceSafe(img, imageUrl);
    attachImageFallback(img, media);
    attachImageHoverPreview(img, card, card.prices || {});
  }

  async function loadLazyPrices(card, mount) {
    if (!card?.putnam_card_id) return;

    mount.replaceChildren(el("div", {
      className: "ppo-price-loading",
      text: "LOADING LIVE PRICE..."
    }));

    const url = `${backendUrl}/api/prices?id=${encodeURIComponent(card.putnam_card_id)}`;
    const response = await fetch(url, { cache: "no-store" });
    const payload = await response.json();

    if (!payload?.ok) {
      throw new Error(payload?.error || "Price lookup failed");
    }

    card.prices = payload.prices || null;

    hydrateResultThumbnail(card, mount);

    mount.replaceChildren(renderVariantPrices(card, card.prices || {}));

    hydrateResultThumbnail(card, mount);
  }

'''

js = js[:start] + new_block + js[end:]
JS.write_text(js, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.8.2.2"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.8.2B Thumbnail Hydration Reliability")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - extension/overlay.js")
print(" - extension/manifest.json")