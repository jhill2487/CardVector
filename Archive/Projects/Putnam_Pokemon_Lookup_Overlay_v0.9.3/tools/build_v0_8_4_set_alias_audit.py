from pathlib import Path
import sqlite3
import csv
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]

CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"

OUT = ROOT / "runtime_v0_8_4_set_alias_audit.csv"

catalog = sqlite3.connect(CATALOG_DB)
catalog.row_factory = sqlite3.Row

tcg = sqlite3.connect(TCG_DB)
tcg.row_factory = sqlite3.Row

linked_cards = {
    str(r["putnam_card_id"])
    for r in tcg.execute("""
        select distinct putnam_card_id
        from putnam_tcgtracking_matches
    """).fetchall()
}

catalog_sets = defaultdict(lambda: {
    "cards": 0,
    "linked": 0
})

for r in catalog.execute("""
    select putnam_card_id,set_name
    from pokemon_cards
    where game='pokemon'
"""):
    s = r["set_name"] or ""
    catalog_sets[s]["cards"] += 1

    if str(r["putnam_card_id"]) in linked_cards:
        catalog_sets[s]["linked"] += 1

tcg_sets = defaultdict(int)

for r in tcg.execute("""
    select s.name,count(*) as cnt
    from tcgtracking_products p
    join tcgtracking_sets s on s.set_id=p.set_id
    group by s.name
    order by cnt desc
"""):
    tcg_sets[r["name"]] = r["cnt"]

rows = []

for set_name, stats in sorted(catalog_sets.items()):
    coverage = round(
        stats["linked"] / stats["cards"] * 100,
        2
    ) if stats["cards"] else 0

    if coverage > 0:
        continue

    candidates = []

    set_words = set(
        str(set_name)
        .lower()
        .replace("&", "and")
        .replace("-", " ")
        .split()
    )

    for tcg_name, count in tcg_sets.items():
        tcg_words = set(
            str(tcg_name)
            .lower()
            .replace("&", "and")
            .replace("-", " ")
            .split()
        )

        overlap = len(set_words & tcg_words)

        if overlap:
            candidates.append(
                (overlap, count, tcg_name)
            )

    candidates.sort(reverse=True)

    top = "; ".join(
        c[2] for c in candidates[:5]
    )

    rows.append([
        set_name,
        stats["cards"],
        coverage,
        top
    ])

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)

    w.writerow([
        "catalog_set",
        "card_count",
        "coverage_pct",
        "top_tcgtracking_candidates"
    ])

    w.writerows(rows)

catalog.close()
tcg.close()

print("Alias audit complete")
print("Report:", OUT)
print("Sets needing review:", len(rows))