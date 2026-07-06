from pathlib import Path
import sqlite3, shutil, datetime, json, re, csv
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"
REPORT = ROOT / "runtime_v0_8_7_promo_number_normalization_report.csv"

PROMO_ALIASES = {
    "BW Black Star Promos": ["Black and White Promos"],
    "DP Black Star Promos": ["Diamond and Pearl Promos"],
    "HGSS Black Star Promos": ["HGSS Promos"],
    "Nintendo Black Star Promos": ["Nintendo Promos"],
    "SM Black Star Promos": ["SM Promos"],
    "SWSH Black Star Promos": ["SWSH: Sword & Shield Promo Cards"],
    "Scarlet and Violet Black Star Promos": ["SV: Scarlet & Violet Promo Cards"],
    "Wizards Black Star Promos": ["WoTC Promo"],
    "McDonalds Collection 2011": ["McDonald's Promos 2011"],
    "McDonalds Collection 2012": ["McDonald's Promos 2012"],
    "McDonalds Collection 2014": ["McDonald's Promos 2014"],
    "McDonalds Collection 2015": ["McDonald's Promos 2015"],
    "McDonalds Collection 2016": ["McDonald's Promos 2016"],
    "McDonalds Collection 2017": ["McDonald's Promos 2017"],
    "McDonalds Collection 2018": ["McDonald's Promos 2018"],
    "McDonalds Collection 2019": ["McDonald's Promos 2019"],
    "McDonalds Collection 2021": ["McDonald's 25th Anniversary Promos"],
    "McDonalds Collection 2022": ["McDonald's Promos 2022"],
}

BAD_TERMS = ["booster", "bundle", "case", "elite trainer", "collection box", "display", "pack", "poster", "code card", "tin", "blister", "binder"]

def norm(v):
    text = str(v or "").lower()
    text = text.replace("★", " gold star ").replace("δ", " delta species ").replace("poké", "poke")
    text = re.sub(r"\b([a-z0-9]+)[\-\s]+(gx|ex|vmax|vstar|v union|v|break)\b", r"\1 \2", text)
    text = text.replace("v union", "vunion")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def canonical_name(v):
    text = norm(v)
    for term in ["promo", "holofoil", "holo", "reverse holo", "cosmos", "stamped", "staff", "prerelease"]:
        text = text.replace(norm(term), " ")
    return re.sub(r"\s+", " ", text).strip()

def similarity(a, b):
    aa, bb = set(norm(a).split()), set(norm(b).split())
    return len(aa & bb) / max(len(aa), len(bb)) if aa and bb else 0

def promo_number(value):
    raw = str(value or "").lower()
    raw = raw.split("/", 1)[0]
    raw = raw.replace("black star promo", "")
    raw = re.sub(r"[^a-z0-9]+", "", raw)

    m = re.search(r"([a-z]*)(\d+)$", raw)
    if not m:
        return ("", raw)

    prefix, digits = m.groups()
    return (prefix, str(int(digits)) if digits else "")

def is_card_product(row):
    name = norm(row["product_name"])
    if any(t in name for t in BAD_TERMS):
        return False
    return bool(row["card_number"] or row["clean_number"])

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [TCG_DB, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_8_7_{stamp}{p.suffix}")

catalog = sqlite3.connect(CATALOG_DB)
catalog.row_factory = sqlite3.Row
tcg = sqlite3.connect(TCG_DB)
tcg.row_factory = sqlite3.Row
cur = tcg.cursor()

linked_ids = {
    str(r["putnam_card_id"])
    for r in cur.execute("select distinct putnam_card_id from putnam_tcgtracking_matches").fetchall()
}

products = cur.execute("""
select p.product_id,s.name as set_name,p.name as product_name,
       p.card_number,p.clean_number,p.image_url,p.tcgplayer_url
from tcgtracking_products p
left join tcgtracking_sets s on s.set_id=p.set_id
""").fetchall()

products_by_alias_num = defaultdict(list)
for p in products:
    if not is_card_product(p):
        continue
    num_key = promo_number(p["card_number"] or p["clean_number"])[1]
    if not num_key:
        continue
    products_by_alias_num[(p["set_name"], num_key)].append(p)

cards = catalog.execute("""
select putnam_card_id,set_name,card_name,card_number,printed_number
from pokemon_cards
where game='pokemon'
""").fetchall()

inserted = already_linked = no_candidate = skipped_name = 0
report = []

for c in cards:
    pid = str(c["putnam_card_id"])
    set_name = c["set_name"] or ""

    if pid in linked_ids:
        already_linked += 1
        continue

    aliases = PROMO_ALIASES.get(set_name)
    if not aliases:
        continue

    c_prefix, c_num = promo_number(c["card_number"] or c["printed_number"])
    if not c_num:
        no_candidate += 1
        continue

    c_name = canonical_name(c["card_name"])

    candidates = []
    seen = set()
    for alias in aliases:
        for p in products_by_alias_num.get((alias, c_num), []):
            product_id = str(p["product_id"])
            if product_id not in seen:
                seen.add(product_id)
                candidates.append(p)

    if not candidates:
        no_candidate += 1
        report.append([pid, set_name, c["card_name"], c["printed_number"], "", "", "NO_CANDIDATE", ""])
        continue

    for p in candidates:
        p_name = canonical_name(p["product_name"])
        sim = similarity(c_name, p_name)

        if c_name == p_name:
            confidence = 1.0
            reason = "v0.8.7 promo number exact canonical name"
        elif sim >= 0.72:
            confidence = round(0.82 + sim * 0.12, 3)
            reason = "v0.8.7 promo number relaxed name match"
        else:
            skipped_name += 1
            report.append([pid, set_name, c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "SKIP_NAME_MISMATCH", f"{sim:.2f}"])
            continue

        cur.execute("""
        insert or ignore into putnam_tcgtracking_matches
        (putnam_card_id,tcgtracking_product_id,match_confidence,match_reason,image_url,product_url,last_checked)
        values (?, ?, ?, ?, ?, ?, datetime('now'))
        """, [
            pid,
            str(p["product_id"]),
            confidence,
            reason,
            p["image_url"],
            p["tcgplayer_url"],
        ])

        inserted += 1
        linked_ids.add(pid)
        report.append([pid, set_name, c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "LINKED", f"{confidence:.2f}"])

tcg.commit()

with REPORT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["putnam_card_id","catalog_set","card_name","printed_number","product_id","product_name","status","score"])
    w.writerows(report)

catalog.close()
tcg.close()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.8.7"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.8.7 Promo Number Normalization")
print(f"Extension version: {old_version} -> 0.8.7")
print(f"Already linked skipped: {already_linked}")
print(f"New links inserted/kept: {inserted}")
print(f"No candidate: {no_candidate}")
print(f"Name mismatch skips: {skipped_name}")
print(f"Report: {REPORT}")
print(f"Backups saved in: {archive}")