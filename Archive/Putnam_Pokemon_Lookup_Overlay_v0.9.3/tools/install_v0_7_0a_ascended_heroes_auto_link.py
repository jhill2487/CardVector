from pathlib import Path
import sqlite3
import shutil
import datetime
import json
import re

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"
REPORT = ROOT / "runtime_ascended_heroes_auto_link_report.csv"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [TCG_DB, MANIFEST]:
    if p.exists():
        shutil.copy2(p, archive / f"{p.stem}_before_v0_7_0a_{stamp}{p.suffix}")

def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

def name_similarity(a, b):
    a_tokens = set(norm(a).split())
    b_tokens = set(norm(b).split())
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))

def is_card_product(row):
    name = norm(row["product_name"])
    if not row["clean_number"]:
        return False
    bad_terms = [
        "booster", "bundle", "case", "elite trainer", "mini tin",
        "collection", "display", "pack", "poster", "code card",
        "box", "tin", "costco"
    ]
    return not any(term in name for term in bad_terms)

catalog = sqlite3.connect(CATALOG_DB)
catalog.row_factory = sqlite3.Row
tcg = sqlite3.connect(TCG_DB)
tcg.row_factory = sqlite3.Row

tcg.execute("""
create table if not exists putnam_tcgtracking_matches (
  putnam_card_id text not null,
  tcgtracking_product_id text not null,
  match_confidence real default 0,
  match_reason text,
  created_at text default (datetime('now')),
  primary key (putnam_card_id, tcgtracking_product_id)
)
""")

cards = catalog.execute("""
select
  putnam_card_id,
  set_name,
  card_name,
  card_number,
  printed_number
from pokemon_cards
where lower(set_name) = 'ascended heroes'
order by card_number_sort, card_name
""").fetchall()

products = tcg.execute("""
select
  p.product_id,
  s.name as set_name,
  p.name as product_name,
  p.card_number,
  p.clean_number,
  p.image_url,
  p.tcgplayer_url
from tcgtracking_products p
left join tcgtracking_sets s on s.set_id = p.set_id
where lower(s.name) like '%ascended heroes%'
""").fetchall()

products_by_number = {}
for product in products:
    if not is_card_product(product):
        continue
    key = str(product["clean_number"] or "").lstrip("0")
    if not key:
        continue
    products_by_number.setdefault(key, []).append(product)

inserted = 0
skipped = 0
review = []

for card in cards:
    card_num = str(card["card_number"] or "").lstrip("0")
    candidates = products_by_number.get(card_num, [])

    if not candidates:
        skipped += 1
        review.append([card["putnam_card_id"], card["card_name"], card["printed_number"], "", "", "NO_CANDIDATES", ""])
        continue

    matched_any = False

    for product in candidates:
        sim = name_similarity(card["card_name"], product["product_name"])

        if sim < 0.50:
            review.append([
                card["putnam_card_id"],
                card["card_name"],
                card["printed_number"],
                product["product_id"],
                product["product_name"],
                "SKIPPED_LOW_NAME_SIMILARITY",
                f"{sim:.2f}",
            ])
            continue

        confidence = round(0.70 + min(sim, 1.0) * 0.30, 3)

        tcg.execute("""
        insert or replace into putnam_tcgtracking_matches
        (putnam_card_id, tcgtracking_product_id, match_confidence, match_reason)
        values (?, ?, ?, ?)
        """, [
            card["putnam_card_id"],
            str(product["product_id"]),
            confidence,
            "v0.7.0A ascended heroes set+number+name auto-link",
        ])

        inserted += 1
        matched_any = True
        review.append([
            card["putnam_card_id"],
            card["card_name"],
            card["printed_number"],
            product["product_id"],
            product["product_name"],
            "LINKED",
            f"{sim:.2f}",
        ])

    if not matched_any:
        skipped += 1

tcg.commit()
catalog.close()
tcg.close()

REPORT.write_text(
    "putnam_card_id,card_name,printed_number,product_id,product_name,status,name_similarity\n"
    + "\n".join(",".join('"' + str(v).replace('"', '""') + '"' for v in row) for row in review),
    encoding="utf-8"
)

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.0"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.0A Ascended Heroes Auto-Link Builder")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Cards scanned: {len(cards)}")
print(f"Products scanned: {len(products)}")
print(f"Links inserted/replaced: {inserted}")
print(f"Cards skipped/no confident match: {skipped}")
print(f"Report: {REPORT}")
print(f"Backups saved in: {archive}")