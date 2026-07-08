from pathlib import Path
import sqlite3
import shutil
import datetime
import json
import re

ROOT = Path(__file__).resolve().parents[1]
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"

CARD_ID = "pkm-ascended-heroes-55-217-d5d41bd728"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

shutil.copy2(TCG_DB, archive / f"tcgtracking_cache_before_v0_7_0c_{stamp}.sqlite")
shutil.copy2(MANIFEST, archive / f"manifest_before_v0_7_0c_{stamp}.json")

def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

def base_name(product_name):
    return norm(re.sub(r"\([^)]*\)", "", str(product_name or "")))

con = sqlite3.connect(TCG_DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

old_rows = []
try:
    old_rows = cur.execute("select * from putnam_tcgtracking_matches").fetchall()
except Exception:
    old_rows = []

cur.execute("drop table if exists putnam_tcgtracking_matches_v070c")
cur.execute("""
create table putnam_tcgtracking_matches_v070c (
  putnam_card_id text not null,
  tcgtracking_product_id text not null,
  match_confidence real default 0,
  match_reason text,
  image_url text,
  product_url text,
  last_checked text,
  primary key (putnam_card_id, tcgtracking_product_id)
)
""")

old_inserted = 0
for row in old_rows:
    keys = row.keys()
    cur.execute("""
    insert or ignore into putnam_tcgtracking_matches_v070c
    (putnam_card_id, tcgtracking_product_id, match_confidence, match_reason, image_url, product_url, last_checked)
    values (?, ?, ?, ?, ?, ?, ?)
    """, [
        row["putnam_card_id"] if "putnam_card_id" in keys else None,
        row["tcgtracking_product_id"] if "tcgtracking_product_id" in keys else None,
        row["match_confidence"] if "match_confidence" in keys else 0,
        row["match_reason"] if "match_reason" in keys else None,
        row["image_url"] if "image_url" in keys else None,
        row["product_url"] if "product_url" in keys else None,
        row["last_checked"] if "last_checked" in keys else None,
    ])
    old_inserted += 1

cur.execute("drop table if exists putnam_tcgtracking_matches")
cur.execute("alter table putnam_tcgtracking_matches_v070c rename to putnam_tcgtracking_matches")

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
        "v0.7.0C multi-product match table",
        p["image_url"],
        p["tcgplayer_url"],
    ])
    inserted += 1
    print(f"Linked {p['product_id']} -> {p['product_name']}")

con.commit()
con.close()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.0.2"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.0C Multi-Product Match Table Fix")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Preserved old rows attempted: {old_inserted}")
print(f"Pikachu variant links inserted/replaced: {inserted}")