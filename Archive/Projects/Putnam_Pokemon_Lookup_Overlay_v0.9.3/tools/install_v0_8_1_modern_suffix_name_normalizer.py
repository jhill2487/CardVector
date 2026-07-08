from pathlib import Path
import sqlite3, shutil, datetime, json, re, csv
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"
REPORT = ROOT / "runtime_v0_8_1_global_link_report.csv"
SUMMARY = ROOT / "runtime_v0_8_1_global_link_summary.csv"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [TCG_DB, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_8_1_{stamp}{p.suffix}")

VARIANT_TERMS = [
    "secret", "full art", "alternate art", "special illustration rare",
    "illustration rare", "ultra rare", "rainbow rare",
    "energy symbol pattern", "friend ball", "love ball", "poke ball", "poké ball",
    "master ball", "ultra ball", "great ball", "team rocket",
    "reverse holofoil", "reverse holo", "holofoil", "cosmos holo", "cosmos",
    "stamped", "stamp", "prerelease", "pre release", "staff", "league", "promo"
]

BAD_PRODUCT_TERMS = [
    "booster", "bundle", "case", "elite trainer", "mini tin", "collection",
    "display", "pack", "poster", "code card", " box", " tin", "costco",
    "sleeved", "blister", "portfolio", "binder", "playmat"
]

def norm(v):
    text = str(v or "").lower()
    text = text.replace("★", " gold star ")
    text = text.replace("☆", " gold star ")
    text = text.replace("δ", " delta species ")
    text = text.replace("poké", "poke")

    # v0.8.1: normalize hyphenated modern suffixes.
    text = re.sub(r"\b([a-z0-9]+)[\-\s]+(gx|ex|vmax|vstar|v union|v|break)\b", r"\1 \2", text)
    text = text.replace("v union", "vunion")

    text = re.sub(r"\bstar\b", " gold star ", text)
    text = text.replace("lv.x", " lvx ").replace("lv x", " lvx ")

    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    text = text.replace("gold gold star", "gold star")
    text = text.replace("gold star gold star", "gold star")
    text = text.replace("delta species delta species", "delta species")
    return text

def set_keys(v):
    raw = norm(v)
    keys = {raw}
    raw_no_prefix = raw
    for prefix in ["sm ", "sv ", "swsh ", "xy ", "bw ", "me ", "ex "]:
        if raw_no_prefix.startswith(prefix):
            keys.add(raw_no_prefix[len(prefix):])
    if ":" in str(v or ""):
        keys.add(norm(str(v).split(":", 1)[1]))
    return {k for k in keys if k}

def canonical_name(v):
    text = norm(v)
    for term in VARIANT_TERMS:
        text = text.replace(norm(term), " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def similarity(a, b):
    aa, bb = set(norm(a).split()), set(norm(b).split())
    if not aa or not bb:
        return 0
    return len(aa & bb) / max(len(aa), len(bb))

def clean_num(v):
    raw = str(v or "").strip().lower()
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    return raw.lstrip("0") or raw

def is_card_product(pname, clean_number):
    if not clean_number:
        return False
    n = norm(pname)
    return not any(term.strip() in n for term in BAD_PRODUCT_TERMS)

catalog = sqlite3.connect(CATALOG_DB)
catalog.row_factory = sqlite3.Row
tcg = sqlite3.connect(TCG_DB)
tcg.row_factory = sqlite3.Row
cur = tcg.cursor()

cur.execute("drop table if exists putnam_tcgtracking_matches_v081")
cur.execute("""
create table putnam_tcgtracking_matches_v081 (
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

old_rows = cur.execute("select * from putnam_tcgtracking_matches").fetchall()
preserved = 0
for r in old_rows:
    keys = r.keys()
    cur.execute("""
    insert or ignore into putnam_tcgtracking_matches_v081
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
    preserved += 1

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

products_by_key = defaultdict(list)
for p in products:
    if not is_card_product(p["product_name"], p["clean_number"]):
        continue
    num = clean_num(p["clean_number"] or p["card_number"])
    for sk in set_keys(p["set_name"]):
        products_by_key[(sk, num)].append(p)

report = []
summary = defaultdict(lambda: {"cards": 0, "linked": 0, "no_candidate": 0, "name_mismatch": 0})
inserted = no_candidate = name_mismatch = 0

for c in cards:
    set_name = c["set_name"] or ""
    summary[set_name]["cards"] += 1

    c_num = clean_num(c["card_number"] or c["printed_number"])
    c_name = canonical_name(c["card_name"])

    candidates = []
    seen = set()
    for sk in set_keys(set_name):
        for p in products_by_key.get((sk, c_num), []):
            pid = str(p["product_id"])
            if pid not in seen:
                seen.add(pid)
                candidates.append(p)

    if not candidates:
        no_candidate += 1
        summary[set_name]["no_candidate"] += 1
        continue

    linked_this = 0
    for p in candidates:
        p_name = canonical_name(p["product_name"])
        sim = similarity(c_name, p_name)

        if c_name == p_name:
            confidence = 1.0
            reason = "v0.8.1 exact set+number+modern-suffix-normalized-name"
        elif sim >= 0.88:
            confidence = round(0.88 + (sim * 0.10), 3)
            reason = "v0.8.1 fuzzy set+number+modern-suffix-normalized-name"
        else:
            name_mismatch += 1
            summary[set_name]["name_mismatch"] += 1
            report.append([c["putnam_card_id"], set_name, c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "SKIP_NAME_MISMATCH", f"{sim:.2f}", c_name, p_name])
            continue

        cur.execute("""
        insert or ignore into putnam_tcgtracking_matches_v081
        (putnam_card_id,tcgtracking_product_id,match_confidence,match_reason,image_url,product_url,last_checked)
        values (?, ?, ?, ?, ?, ?, datetime('now'))
        """, [
            c["putnam_card_id"],
            str(p["product_id"]),
            confidence,
            reason,
            p["image_url"],
            p["tcgplayer_url"],
        ])
        inserted += 1
        linked_this += 1
        report.append([c["putnam_card_id"], set_name, c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "LINKED", f"{confidence:.2f}", c_name, p_name])

    if linked_this:
        summary[set_name]["linked"] += 1

cur.execute("drop table if exists putnam_tcgtracking_matches")
cur.execute("alter table putnam_tcgtracking_matches_v081 rename to putnam_tcgtracking_matches")
tcg.commit()

with REPORT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["putnam_card_id","set_name","card_name","printed_number","product_id","product_name","status","score","catalog_norm","product_norm"])
    w.writerows(report)

with SUMMARY.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["set_name","cards","linked_cards","no_candidate","name_mismatch"])
    for set_name, s in sorted(summary.items()):
        w.writerow([set_name, s["cards"], s["linked"], s["no_candidate"], s["name_mismatch"]])

catalog.close()
tcg.close()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.8.1"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.8.1 Modern Suffix Name Normalizer")
print(f"Extension version: {old_version} -> 0.8.1")
print(f"Existing links preserved: {preserved}")
print(f"New high-confidence links inserted/kept: {inserted}")
print(f"No candidate cards: {no_candidate}")
print(f"Name mismatch skips: {name_mismatch}")
print(f"Report: {REPORT}")
print(f"Summary: {SUMMARY}")
print(f"Backups saved in: {archive}")