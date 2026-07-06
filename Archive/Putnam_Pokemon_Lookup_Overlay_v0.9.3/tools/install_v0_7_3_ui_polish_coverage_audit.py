from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "extension" / "overlay.js"
CSS = ROOT / "extension" / "overlay.css"
MANIFEST = ROOT / "extension" / "manifest.json"
TOOLS = ROOT / "tools"
DOCS = ROOT / "docs"
TOOLS.mkdir(exist_ok=True)
DOCS.mkdir(exist_ok=True)

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [JS, CSS, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_7_3_{stamp}{p.suffix}")

js = JS.read_text(encoding="utf-8")

# Add hover preview helpers after productLink
marker = '''  function productLink(variant, card) {
    return variant?.tcgplayer_url || variant?.product_url || card?.tcgplayer_search_url || card?.tcgplayer_url || "";
  }

'''
insert = '''  function productLink(variant, card) {
    return variant?.tcgplayer_url || variant?.product_url || card?.tcgplayer_search_url || card?.tcgplayer_url || "";
  }

  function getBestPreviewImageUrl(card, prices) {
    return absoluteUrl(
      prices?.variants?.[0]?.image_url ||
      card?.image_large_url ||
      card?.large_image_url ||
      card?.image_small_url ||
      card?.small_image_url ||
      card?.image_url ||
      card?.thumbnail_url
    );
  }

  function attachImageHoverPreview(img, card, prices) {
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
if marker not in js:
    raise SystemExit("ERROR: Could not find productLink marker. No changes written.")
js = js.replace(marker, insert, 1)

# Attach hover preview to initial thumbnail.
old_thumb = '''        attachImageFallback(thumb, media);
        media.append(thumb);'''
new_thumb = '''        attachImageFallback(thumb, media);
        attachImageHoverPreview(thumb, card, prices);
        media.append(thumb);'''
if old_thumb in js:
    js = js.replace(old_thumb, new_thumb, 1)
else:
    raise SystemExit("ERROR: Could not patch initial thumbnail hover. No changes written.")

# Attach hover preview to lazy loaded thumbnail.
old_lazy = '''        attachImageFallback(img, media);
        if (existingPlaceholder) existingPlaceholder.remove();
        media.prepend(img);'''
new_lazy = '''        attachImageFallback(img, media);
        attachImageHoverPreview(img, card, card.prices || {});
        if (existingPlaceholder) existingPlaceholder.remove();
        media.prepend(img);'''
if old_lazy in js:
    js = js.replace(old_lazy, new_lazy, 1)

JS.write_text(js, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
css += r'''

/* v0.7.3 UI polish: image hover preview + progressive loading stability */
.ppo-image-preview {
  position: fixed;
  z-index: 2147483647;
  right: 390px;
  top: 92px;
  width: 260px;
  max-width: 38vw;
  padding: 8px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.96);
  box-shadow: 0 20px 50px rgba(0, 0, 0, .45);
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px) scale(.98);
  transition: opacity .08s ease, transform .08s ease;
}

.ppo-image-preview-open {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.ppo-image-preview img {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 9px;
}

.ppo-result {
  min-height: 178px;
}

.ppo-price-mount {
  min-height: 58px;
}

.ppo-price-loading {
  min-height: 36px;
  display: flex;
  align-items: center;
}
'''

CSS.write_text(css, encoding="utf-8")

# Create coverage audit tool.
audit = TOOLS / "audit_missing_links_v0_7_3.py"
audit.write_text(r'''import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
REPORT = ROOT / "runtime_v0_7_3_missing_link_audit.csv"

catalog = sqlite3.connect(CATALOG_DB)
catalog.row_factory = sqlite3.Row
tcg = sqlite3.connect(TCG_DB)
tcg.row_factory = sqlite3.Row

cards = catalog.execute("""
select putnam_card_id,set_name,card_name,printed_number,image_small_url,image_large_url,tcgplayer_product_id,tcgplayer_url
from pokemon_cards
where game='pokemon'
order by set_name, card_name, printed_number
""").fetchall()

links = {
    r["putnam_card_id"]: r["count_links"]
    for r in tcg.execute("""
        select putnam_card_id, count(*) as count_links
        from putnam_tcgtracking_matches
        group by putnam_card_id
    """).fetchall()
}

rows = []
for c in cards:
    has_image = bool(c["image_small_url"] or c["image_large_url"])
    has_direct_tcg = bool(c["tcgplayer_product_id"] or c["tcgplayer_url"])
    link_count = int(links.get(c["putnam_card_id"], 0))

    if not has_image or not has_direct_tcg or link_count == 0:
        rows.append([
            c["putnam_card_id"],
            c["set_name"],
            c["card_name"],
            c["printed_number"],
            "YES" if has_image else "NO",
            "YES" if has_direct_tcg else "NO",
            link_count,
        ])

with REPORT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["putnam_card_id","set_name","card_name","printed_number","has_catalog_image","has_direct_tcg_link","variant_link_count"])
    w.writerows(rows)

catalog.close()
tcg.close()

print(f"Audit complete.")
print(f"Cards needing review: {len(rows)}")
print(f"Report: {REPORT}")
''', encoding="utf-8")

release_notes = DOCS / "RELEASE_NOTES_v0_7_3.txt"
release_notes.write_text("""v0.7.3 UI Polish + Coverage Audit

Included:
- Image hover preview on card thumbnails
- Progressive loading stability/min-height polish
- Missing link coverage audit tool
- No price card redesign
- UI freeze preserved

Validation targets:
- pikachu 55/217
- erika's oddish
- broad searches like pikachu/charizard
""", encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.3"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.3 UI Polish + Coverage Audit")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print(f"Audit tool: {audit}")
print(f"Release notes: {release_notes}")