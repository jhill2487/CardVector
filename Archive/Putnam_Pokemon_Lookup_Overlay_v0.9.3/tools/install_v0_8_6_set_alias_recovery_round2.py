from pathlib import Path
import sqlite3, shutil, datetime, json, re, csv
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"
REPORT = ROOT / "runtime_v0_8_6_set_alias_recovery_round2_report.csv"

ROUND2_SET_ALIASES = {
    "Base": ["Base Set"],
    "Expedition Base Set": ["Expedition"],
    "Sun and Moon": ["SM Base Set"],
    "XY": ["XY Base Set"],
    "Scarlet and Violet Energies": ["SVE: Scarlet & Violet Energies"],
    "EX Trainer Kit 2 Minun": ["EX Trainer Kit 2: Plusle & Minun"],
    "EX Trainer Kit 2 Plusle": ["EX Trainer Kit 2: Plusle & Minun"],
    "EX Trainer Kit Latias": ["EX Trainer Kit 1: Latias & Latios"],
    "EX Trainer Kit Latios": ["EX Trainer Kit 1: Latias & Latios"],
    "HSTriumphant": ["Triumphant"],
    "HSUndaunted": ["Undaunted"],
    "HSUnleashed": ["Unleashed"],
}

VARIANT_TERMS = [
    "secret", "full art", "alternate art", "special illustration rare",
    "illustration rare", "ultra rare", "rainbow rare", "reverse holofoil",
    "reverse holo", "holofoil", "cosmos holo", "cosmos", "promo"
]

BAD_TERMS = [
    "booster", "bundle", "case", "elite trainer", "collection", "display",
    "pack", "poster", "code card", " box", " tin", "blister", "binder"
]

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [TCG_DB, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_8_6_{stamp}{p.suffix}")

def norm(v):
    text = str(v or "").lower()
    text = text.replace("★", " gold star ").replace("☆", " gold star ")
    text = text.replace("δ", " delta species ").replace("poké", "poke")
    text = re.sub(r"\b([a-z0-9]+)[\-\s]+(gx|ex|vmax|vstar|v union|v|break)\b", r"\1 \2", text)
    text = text.replace("v union", "vunion")
    text = re.sub(r"\bstar\b", " gold star ", text)
    text = text.replace("lv.x", " lvx ").replace("lv x", " lvx ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def canonical_name(v):
    text = norm(v)
    for term in VARIANT_TERMS:
        text = text.replace(norm(term), " ")
    return re.sub(r"\s+", " ", text).strip()

def clean_num(v):
    raw = str(v or "").strip().lower()
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    return raw.lstrip("0") or raw

def similarity(a, b):
    aa, bb = set(norm(a).split()), set(norm(b).split())
    return len(aa & bb) / max(len(aa), len(bb)) if aa and bb else 0

def is_card_product(row):
    if not clean_num(row["clean_number"] or row["card_number"]):
        return False
    n = norm(row["product_name"])
    return not any(t.strip() in n for t in BAD_TERMS)

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
where coalesce(p.clean_number,'') <> ''
""").fetchall()

products_by_set_num = defaultdict(list)
for p in products:
    if is_card_product(p):
        products_by_set_num[(p["set_name"], clean_num(p["clean_number"] or p["card_number"]))].append(p)

cards = catalog.execute("""
select putnam_card_id,set_name,card_name,card_number,printed_number
from pokemon_cards
where game='pokemon'
""").fetchall()

inserted = skipped_name = no_candidate = already_linked = 0
report = []

for c in cards:
    pid = str(c["putnam_card_id"])
    if pid in linked_ids:
        already_linked += 1
        continue

    aliases = ROUND2_SET_ALIASES.get(c["set_name"] or "")
    if not aliases:
        continue

    c_num = clean_num(c["card_number"] or c["printed_number"])
    c_name = canonical_name(c["card_name"])

    candidates = []
    seen = set()
    for alias in aliases:
        for p in products_by_set_num.get((alias, c_num), []):
            product_id = str(p["product_id"])
            if product_id not in seen:
                seen.add(product_id)
                candidates.append(p)

    if not candidates:
        no_candidate += 1
        report.append([pid, c["set_name"], c["card_name"], c["printed_number"], "", "", "NO_CANDIDATE", ""])
        continue

    for p in candidates:
        p_name = canonical_name(p["product_name"])
        sim = similarity(c_name, p_name)

        if c_name == p_name:
            confidence = 1.0
            reason = "v0.8.6 round2 set-alias exact canonical name"
        elif sim >= 0.80:
            confidence = round(0.80 + sim * 0.15, 3)
            reason = "v0.8.6 round2 set-alias relaxed exact-number match"
        else:
            skipped_name += 1
            report.append([pid, c["set_name"], c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "SKIP_NAME_MISMATCH", f"{sim:.2f}"])
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
        report.append([pid, c["set_name"], c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "LINKED", f"{confidence:.2f}"])

tcg.commit()

with REPORT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["putnam_card_id","catalog_set","card_name","printed_number","product_id","product_name","status","score"])
    w.writerows(report)

catalog.close()
tcg.close()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.8.6"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.8.6 Set Alias Recovery Round 2")
print(f"Extension version: {old_version} -> 0.8.6")
print(f"Already linked skipped: {already_linked}")
print(f"New links inserted/kept: {inserted}")
print(f"No candidate: {no_candidate}")
print(f"Name mismatch skips: {skipped_name}")
print(f"Report: {REPORT}")
print(f"Backups saved in: {archive}")