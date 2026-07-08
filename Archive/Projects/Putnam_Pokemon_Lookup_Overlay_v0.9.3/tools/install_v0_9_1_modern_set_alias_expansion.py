from pathlib import Path
import sqlite3, shutil, datetime, json, re, csv
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"
REPORT = ROOT / "runtime_v0_9_1_modern_set_alias_expansion_report.csv"

TARGET_SETS = {
    "Temporal Forces": ["SV05: Temporal Forces"],
    "Twilight Masquerade": ["SV06: Twilight Masquerade"],
    "Paldean Fates": ["SV: Paldean Fates"],
}

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [TCG_DB, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_9_1_{stamp}{p.suffix}")

def norm(v):
    text = str(v or "").lower()
    text = text.replace("★", " gold star ").replace("δ", " delta species ").replace("poké", "poke")
    text = re.sub(r"\b([a-z0-9]+)[\-\s]+(gx|ex|vmax|vstar|v union|v|break)\b", r"\1 \2", text)
    text = text.replace("v union", "vunion")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def strip_product_number_suffix(v):
    text = str(v or "")
    text = re.sub(r"\s*-\s*[A-Z]*0*\d+[a-zA-Z]?\s*/\s*\d+\s*$", "", text, flags=re.I)
    text = re.sub(r"\s+[A-Z]*0*\d+[a-zA-Z]?\s*/\s*\d+\s*$", "", text, flags=re.I)
    return text.strip()

def canonical_name(v):
    text = strip_product_number_suffix(v)
    text = norm(text)
    for term in [
        "secret", "full art", "alternate art", "special illustration rare",
        "illustration rare", "ultra rare", "rainbow rare",
        "holofoil", "holo", "reverse holo", "cosmos", "stamped", "promo"
    ]:
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

def is_card_product(p):
    name = norm(p["product_name"])
    bad = ["booster", "bundle", "case", "elite trainer", "collection box", "display", "pack", "poster", "code card", "tin", "blister", "binder"]
    if any(term in name for term in bad):
        return False
    return bool(p["clean_number"] or p["card_number"])

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

inserted = already_linked = no_candidate = skipped_name = 0
report = []

for c in cards:
    pid = str(c["putnam_card_id"])

    if pid in linked_ids:
        already_linked += 1
        continue

    aliases = TARGET_SETS.get(c["set_name"] or "")
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
            reason = "v0.9.1 modern set alias exact suffix-stripped name"
        elif sim >= 0.88:
            confidence = round(0.88 + sim * 0.10, 3)
            reason = "v0.9.1 modern set alias fuzzy suffix-stripped name"
        else:
            skipped_name += 1
            report.append([pid, c["set_name"], c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "SKIP_NAME_MISMATCH", f"{sim:.2f}", c_name, p_name])
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
        report.append([pid, c["set_name"], c["card_name"], c["printed_number"], p["product_id"], p["product_name"], "LINKED", f"{confidence:.2f}", c_name, p_name])

tcg.commit()

with REPORT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["putnam_card_id","catalog_set","card_name","printed_number","product_id","product_name","status","score","catalog_norm","product_norm"])
    w.writerows(report)

catalog.close()
tcg.close()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.9.1"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.9.1 Modern Set Alias Expansion")
print(f"Extension version: {old_version} -> 0.9.1")
print(f"Already linked skipped: {already_linked}")
print(f"New links inserted/kept: {inserted}")
print(f"No candidate: {no_candidate}")
print(f"Name mismatch skips: {skipped_name}")
print(f"Report: {REPORT}")
print(f"Backups saved in: {archive}")