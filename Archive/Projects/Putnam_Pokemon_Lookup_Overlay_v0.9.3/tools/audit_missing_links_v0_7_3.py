import csv
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
