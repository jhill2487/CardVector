from pathlib import Path
import sqlite3
import datetime
import shutil
import json
import re

ROOT = Path(__file__).resolve().parents[1]
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"

CARD_ID = "pkm-ascended-heroes-55-217-d5d41bd728"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

shutil.copy2(TCG_DB, archive / f"tcgtracking_cache_before_v0_7_0b_{stamp}.sqlite")
shutil.copy2(MANIFEST, archive / f"manifest_before_v0_7_0b_{stamp}.json")

def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

def base_name(product_name):
    return norm(re.sub(r"\([^)]*\)", "", str(product_name or "")))

con = sqlite3.connect(TCG_DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

products = cur.execute("""
select
  p.product_id,
  p.name as product_name,
  p.card_number,
  p.clean_number,
  p.image_url,
  p.tcgplayer_url
from tcgtracking_products p
left join tcgtracking_sets s on s.set_id = p.set_id
where lower(s.name) like '%ascended heroes%'
  and p.clean_number = '55'
  and lower(p.name) like '%pikachu%'
order by p.product_id
""").fetchall()

inserted = 0

for p in products:
    if base_name(p["product_name"]) != "pikachu":
        continue

    cur.execute("""
    insert or replace into putnam_tcgtracking_matches
    (putnam_card_id, tcgtracking_product_id, match_confidence, match_reason, image_url, product_url, last_checked)
    values (?, ?, ?, ?, ?, ?, datetime('now'))
    """, [
        CARD_ID,
        str(p["product_id"]),
        1.0,
        "v0.7.0B ascended heroes variant parenthetical link",
        p["image_url"],
        p["tcgplayer_url"],
    ])
    inserted += 1
    print(f"Linked {p['product_id']} -> {p['product_name']}")

con.commit()
con.close()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.0.1"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print(f"Installed v0.7.0B Ascended Heroes Variant Link Fix")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Variant links inserted/replaced: {inserted}")