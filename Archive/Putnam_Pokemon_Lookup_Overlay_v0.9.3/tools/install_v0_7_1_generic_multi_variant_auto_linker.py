from pathlib import Path
import sqlite3, shutil, datetime, json, re, csv

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"
REPORT = ROOT / "runtime_v0_7_1_generic_auto_link_report.csv"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [TCG_DB, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_7_1_{stamp}{p.suffix}")

def norm(v):
    return re.sub(r"[^a-z0-9]+", " ", str(v or "").lower()).strip()

def base_name(v):
    return norm(re.sub(r"\([^)]*\)", "", str(v or "")))

def set_key(v):
    s = norm(v)
    s = s.replace("me ascended heroes", "ascended heroes")
    s = s.replace("pokemon ", "")
    return s

bad_terms = [
    "booster", "bundle", "case", "elite trainer", "mini tin", "collection",
    "display", "pack", "poster", "code card", "box", "tin", "costco"
]

catalog = sqlite3.connect(CATALOG_DB)
catalog.row_factory = sqlite3.Row
tcg = sqlite3.connect(TCG_DB)
tcg.row_factory = sqlite3.Row
cur = tcg.cursor()

cur.execute("drop table if exists putnam_tcgtracking_matches_v071")
cur.execute("""
create table putnam_tcgtracking_matches_v071 (
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

# Preserve existing links.
try:
    old_rows = cur.execute("select * from putnam_tcgtracking_matches").fetchall()
except Exception:
    old_rows = []

for r in old_rows:
    keys = r.keys()
    cur.execute("""
    insert or ignore into putnam_tcgtracking_matches_v071
    values (?, ?, ?, ?, ?, ?, ?)
    """, [
        r["putnam_card_id"],
        r["tcgtracking_product_id"],
        r["match_confidence"] if "match_confidence" in keys else 0.8,
        r["match_reason"] if "match_reason" in keys else "preserved existing link",
        r["image_url"] if "image_url" in keys else None,
        r["product_url"] if "product_url" in keys else None,
        r["last_checked"] if "last_checked" in keys else None,
    ])

cards = catalog.execute("""
select putnam_card_id,set_name,card_name,card_number,printed_number
from pokemon_cards
where game='pokemon'
""").fetchall()

products = cur.execute("""
select p.product_id,s.name as set_name,p.name as product_name,
       p.card_number,p.clean_number,p.image_url,p.tcgplayer_url
from tcgtracking_products p
left join tcgtracking_sets s on s.set_id=p.set_id
where coalesce(p.clean_number,'') <> ''
""").fetchall()

products_by_set_number = {}
for p in products:
    pname = norm(p["product_name"])
    if any(t in pname for t in bad_terms):
        continue
    key = (set_key(p["set_name"]), str(p["clean_number"] or "").lstrip("0"))
    products_by_set_number.setdefault(key, []).append(p)

linked = skipped = low_sim = 0
report = []

for c in cards:
    c_set = set_key(c["set_name"])
    c_num = str(c["card_number"] or "").lstrip("0")
    c_base = norm(c["card_name"])
    candidates = products_by_set_number.get((c_set, c_num), [])

    if not candidates:
        skipped += 1
        continue

    matched = 0
    for p in candidates:
        p_base = base_name(p["product_name"])

        # Require base product name to match card name.
        if p_base != c_base:
            low_sim += 1
            report.append([c["putnam_card_id"], c["set_name"], c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "SKIP_NAME_MISMATCH"])
            continue

        cur.execute("""
        insert or ignore into putnam_tcgtracking_matches_v071
        (putnam_card_id,tcgtracking_product_id,match_confidence,match_reason,image_url,product_url,last_checked)
        values (?, ?, ?, ?, ?, ?, datetime('now'))
        """, [
            c["putnam_card_id"],
            str(p["product_id"]),
            1.0,
            "v0.7.1 generic set+number+base-name multi-variant link",
            p["image_url"],
            p["tcgplayer_url"],
        ])
        linked += 1
        matched += 1
        report.append([c["putnam_card_id"], c["set_name"], c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "LINKED"])

    if not matched:
        skipped += 1

cur.execute("drop table if exists putnam_tcgtracking_matches")
cur.execute("alter table putnam_tcgtracking_matches_v071 rename to putnam_tcgtracking_matches")
tcg.commit()

with REPORT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["putnam_card_id","set_name","card_name","printed_number","product_id","product_name","status"])
    w.writerows(report)

catalog.close()
tcg.close()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.1"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.1 Generic Multi-Variant Auto-Linker")
print(f"Extension version: {old_version} -> 0.7.1")
print(f"Links inserted/kept: {linked}")
print(f"Cards skipped/no candidates: {skipped}")
print(f"Name mismatch skips: {low_sim}")
print(f"Report: {REPORT}")
print(f"Backups saved in: {archive}")