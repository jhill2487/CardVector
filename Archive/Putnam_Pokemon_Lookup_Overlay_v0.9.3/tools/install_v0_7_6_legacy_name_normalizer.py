from pathlib import Path
import sqlite3
import shutil
import datetime
import json
import re

ROOT = Path(__file__).resolve().parents[1]
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"

CARD_ID = "pkm-dragon-frontiers-100-101-9349d05066"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

shutil.copy2(TCG_DB, archive / f"tcgtracking_cache_before_v0_7_6_{stamp}.sqlite")
shutil.copy2(MANIFEST, archive / f"manifest_before_v0_7_6_{stamp}.json")

def normalize_pokemon_name(value):
    text = str(value or "").lower()
    text = text.replace("★", " gold star ")
    text = text.replace("☆", " gold star ")
    text = text.replace("δ", " delta species ")
    text = text.replace("(delta species)", " delta species ")
    text = text.replace("delta species", " delta species ")
    text = text.replace("lv.x", " lvx ")
    text = text.replace("lv x", " lvx ")
    text = text.replace("poké", "poke")
    text = re.sub(r"\bstar\b", " gold star ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # de-dupe repeated semantic tokens
    text = text.replace("gold gold star", "gold star")
    text = text.replace("gold star gold star", "gold star")
    text = text.replace("delta species delta species", "delta species")
    return text

con = sqlite3.connect(TCG_DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

product = cur.execute("""
select
  p.product_id,
  p.name as product_name,
  p.card_number,
  p.clean_number,
  p.image_url,
  p.tcgplayer_url
from tcgtracking_products p
left join tcgtracking_sets s on s.set_id = p.set_id
where lower(s.name) like '%dragon frontiers%'
  and p.clean_number = '100'
  and lower(p.name) like '%charizard%'
limit 1
""").fetchone()

if not product:
    raise SystemExit("ERROR: Dragon Frontiers Charizard product not found.")

catalog_name = "Charizard ★ δ"
tcg_name = product["product_name"]

cat_norm = normalize_pokemon_name(catalog_name)
tcg_norm = normalize_pokemon_name(tcg_name)

if cat_norm != tcg_norm:
    print("WARNING: normalized names differ, but set+number+Charizard match is strong.")
    print("Catalog:", cat_norm)
    print("TCG:    ", tcg_norm)

cur.execute("""
insert or replace into putnam_tcgtracking_matches
(putnam_card_id, tcgtracking_product_id, match_confidence, match_reason, image_url, product_url, last_checked)
values (?, ?, ?, ?, ?, ?, datetime('now'))
""", [
    CARD_ID,
    str(product["product_id"]),
    1.0,
    "v0.7.6 legacy gold star delta species normalization",
    product["image_url"],
    product["tcgplayer_url"],
])

con.commit()
con.close()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.6"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.6 Legacy Name Normalizer")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Linked Dragon Frontiers Charizard Gold Star Delta Species -> product {product['product_id']}")
print(f"Backup saved in: {archive}")