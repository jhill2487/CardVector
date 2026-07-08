
from pathlib import Path
import sqlite3
import csv
import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]

CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"

HTML = ROOT / "runtime_v0_8_3_coverage_analytics.html"
CSV_BY_SET = ROOT / "runtime_v0_8_3_coverage_by_set.csv"

catalog = sqlite3.connect(CATALOG_DB)
catalog.row_factory = sqlite3.Row

tcg = sqlite3.connect(TCG_DB)
tcg.row_factory = sqlite3.Row

cards = catalog.execute("""
select
  putnam_card_id,
  set_name,
  card_name,
  printed_number
from pokemon_cards
where game='pokemon'
""").fetchall()

# FIX: build lookup directly from actual link table
linked_cards = {
    str(r["putnam_card_id"]).strip()
    for r in tcg.execute("""
        select distinct putnam_card_id
        from putnam_tcgtracking_matches
        where putnam_card_id is not null
    """).fetchall()
}

multi_cards = {
    str(r["putnam_card_id"]).strip()
    for r in tcg.execute("""
        select putnam_card_id
        from putnam_tcgtracking_matches
        group by putnam_card_id
        having count(*) > 1
    """).fetchall()
}

image_cards = {
    str(r["putnam_card_id"]).strip()
    for r in tcg.execute("""
        select distinct putnam_card_id
        from putnam_tcgtracking_matches
        where coalesce(image_url,'') <> ''
    """).fetchall()
}

stats = defaultdict(lambda: {
    "cards":0,
    "linked":0,
    "multi":0,
    "images":0
})

total_cards = 0
total_linked = 0
total_multi = 0
total_images = 0

for card in cards:
    pid = str(card["putnam_card_id"]).strip()
    set_name = card["set_name"] or "UNKNOWN"

    s = stats[set_name]
    s["cards"] += 1
    total_cards += 1

    if pid in linked_cards:
        s["linked"] += 1
        total_linked += 1

    if pid in multi_cards:
        s["multi"] += 1
        total_multi += 1

    if pid in image_cards:
        s["images"] += 1
        total_images += 1

rows = []

for set_name, s in stats.items():
    pct = round((s["linked"] / s["cards"]) * 100, 2) if s["cards"] else 0
    rows.append([
        set_name,
        s["cards"],
        s["linked"],
        s["multi"],
        s["images"],
        pct
    ])

rows.sort(key=lambda r: r[5])

with open(CSV_BY_SET, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "set_name",
        "cards",
        "linked_cards",
        "multi_variant_cards",
        "image_cards",
        "linked_pct"
    ])
    w.writerows(rows)

best = sorted(rows, key=lambda r: r[5], reverse=True)[:30]
worst = sorted(rows, key=lambda r: r[5])[:30]

def table(title, data):
    html = [f"<h2>{title}</h2><table border='1' cellpadding='5'>"]
    html.append("<tr><th>Set</th><th>Cards</th><th>Linked</th><th>Multi</th><th>Images</th><th>Coverage</th></tr>")
    for r in data:
        html.append(
            f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}%</td></tr>"
        )
    html.append("</table>")
    return "\n".join(html)

overall_pct = round((total_linked / total_cards) * 100, 2) if total_cards else 0

HTML.write_text(f"""
<html>
<head>
<title>Putnam Coverage Analytics v0.8.3A</title>
</head>
<body>
<h1>Putnam Coverage Analytics v0.8.3A</h1>

<p>Generated: {datetime.datetime.now()}</p>

<h2>Summary</h2>

<ul>
<li>Total Cards: {total_cards}</li>
<li>Linked Cards: {total_linked}</li>
<li>Coverage: {overall_pct}%</li>
<li>Multi Variant Cards: {total_multi}</li>
<li>Image Cards: {total_images}</li>
</ul>

{table("Worst 30 Sets", worst)}

<br><br>

{table("Best 30 Sets", best)}

</body>
</html>
""", encoding="utf-8")

catalog.close()
tcg.close()

print("Coverage analytics rebuilt.")
print("Dashboard:", HTML)
print("CSV:", CSV_BY_SET)
print("Total cards:", total_cards)
print("Linked cards:", total_linked)
print("Coverage %:", overall_pct)
