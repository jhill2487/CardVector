from pathlib import Path
import sqlite3, csv, json, datetime, shutil
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"
DOCS = ROOT / "docs"
TOOLS = ROOT / "tools"
DOCS.mkdir(exist_ok=True)
TOOLS.mkdir(exist_ok=True)

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)
shutil.copy2(MANIFEST, archive / f"manifest_before_v0_8_3_{stamp}.json")

tool = TOOLS / "build_coverage_analytics_v0_8_3.py"

tool.write_text(r'''
from pathlib import Path
import sqlite3, csv, datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DB = ROOT / "database" / "putnam_pokemon_cloud_ready.sqlite"
TCG_DB = ROOT / "price_cache" / "tcgtracking_cache.sqlite"

HTML = ROOT / "runtime_v0_8_3_coverage_analytics.html"
BY_SET = ROOT / "runtime_v0_8_3_coverage_by_set.csv"
UNRESOLVED = ROOT / "runtime_v0_8_3_unresolved_cards.csv"

catalog = sqlite3.connect(CATALOG_DB)
catalog.row_factory = sqlite3.Row
tcg = sqlite3.connect(TCG_DB)
tcg.row_factory = sqlite3.Row

cards = catalog.execute("""
select putnam_card_id,set_name,card_name,printed_number,image_small_url,image_large_url
from pokemon_cards
where game='pokemon'
""").fetchall()

link_rows = tcg.execute("""
select putnam_card_id, tcgtracking_product_id, image_url, product_url
from putnam_tcgtracking_matches
""").fetchall()

links_by_card = defaultdict(list)
for r in link_rows:
    links_by_card[r["putnam_card_id"]].append(r)

price_product_ids = set()
try:
    price_cols = [r["name"] for r in tcg.execute("pragma table_info(tcgtracking_prices)").fetchall()]
    product_col = None
    for candidate in ["product_id", "tcgtracking_product_id", "provider_product_id"]:
        if candidate in price_cols:
            product_col = candidate
            break
    if product_col:
        for r in tcg.execute(f"select distinct {product_col} as product_id from tcgtracking_prices").fetchall():
            price_product_ids.add(str(r["product_id"]))
except Exception:
    pass

total = len(cards)
linked = priced = multi = linked_img = catalog_img = unresolved = 0
set_stats = defaultdict(lambda: {
    "cards": 0,
    "linked": 0,
    "priced": 0,
    "multi": 0,
    "linked_img": 0,
    "catalog_img": 0,
    "unresolved": 0,
})

unresolved_rows = []

for c in cards:
    sid = c["putnam_card_id"]
    set_name = c["set_name"] or "UNKNOWN"
    stat = set_stats[set_name]
    stat["cards"] += 1

    card_links = links_by_card.get(sid, [])
    has_catalog_img = bool(c["image_small_url"] or c["image_large_url"])
    has_link = bool(card_links)
    has_multi = len(card_links) > 1
    has_link_img = any(r["image_url"] for r in card_links)
    has_price = any(str(r["tcgtracking_product_id"]) in price_product_ids for r in card_links)

    if has_catalog_img:
        catalog_img += 1
        stat["catalog_img"] += 1
    if has_link:
        linked += 1
        stat["linked"] += 1
    if has_price:
        priced += 1
        stat["priced"] += 1
    if has_multi:
        multi += 1
        stat["multi"] += 1
    if has_link_img:
        linked_img += 1
        stat["linked_img"] += 1

    if not has_link:
        unresolved += 1
        stat["unresolved"] += 1
        unresolved_rows.append([
            sid, set_name, c["card_name"], c["printed_number"], "NO_VARIANT_LINK"
        ])

def pct(part, whole):
    return round((part / whole * 100), 2) if whole else 0

by_set_rows = []
for set_name, s in sorted(set_stats.items()):
    by_set_rows.append([
        set_name,
        s["cards"],
        s["linked"],
        s["priced"],
        s["multi"],
        s["linked_img"],
        s["catalog_img"],
        s["unresolved"],
        pct(s["linked"], s["cards"]),
        pct(s["priced"], s["cards"]),
    ])

with BY_SET.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "set_name","cards","linked_cards","priced_cards","multi_variant_cards",
        "linked_image_cards","catalog_image_cards","unresolved_cards",
        "linked_pct","priced_pct"
    ])
    w.writerows(by_set_rows)

with UNRESOLVED.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["putnam_card_id","set_name","card_name","printed_number","reason"])
    w.writerows(unresolved_rows)

worst = sorted(by_set_rows, key=lambda r: (r[8], -r[1]))[:30]
best = sorted(by_set_rows, key=lambda r: (-r[8], -r[1]))[:30]

def metric(label, value, sub=""):
    return f'<div class="card"><div>{label}</div><div class="big">{value}</div><div>{sub}</div></div>'

def table(title, rows):
    html = [f"<h2>{title}</h2><table><tr><th>Set</th><th>Cards</th><th>Linked</th><th>Priced</th><th>Multi</th><th>Linked Img</th><th>Unresolved</th><th>Linked %</th><th>Priced %</th></tr>"]
    for r in rows:
        html.append(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td><td>{r[7]}</td><td>{r[8]}%</td><td>{r[9]}%</td></tr>")
    html.append("</table>")
    return "\n".join(html)

HTML.write_text(f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Putnam Coverage Analytics v0.8.3</title>
<style>
body {{ font-family: Arial, sans-serif; margin:24px; color:#111827; }}
.card {{ display:inline-block; min-width:175px; margin:8px; padding:16px 18px; border:1px solid #d1d5db; border-radius:12px; vertical-align:top; }}
.big {{ font-size:28px; font-weight:800; }}
table {{ border-collapse:collapse; width:100%; margin:16px 0 32px; }}
th,td {{ border:1px solid #e5e7eb; padding:8px; text-align:left; }}
th {{ background:#f3f4f6; }}
</style>
</head>
<body>
<h1>Putnam Coverage Analytics v0.8.3</h1>
<p>Generated {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

{metric("Total Cards", total)}
{metric("Linked Cards", linked, str(pct(linked,total)) + "%")}
{metric("Priced Cards", priced, str(pct(priced,total)) + "%")}
{metric("Linked Images", linked_img, str(pct(linked_img,total)) + "%")}
{metric("Multi-Variant", multi, str(pct(multi,total)) + "%")}
{metric("Unresolved", unresolved, str(pct(unresolved,total)) + "%")}

{table("Worst 30 Sets by Linked Coverage", worst)}
{table("Best 30 Sets by Linked Coverage", best)}

<p>Reports:</p>
<ul>
<li>{BY_SET.name}</li>
<li>{UNRESOLVED.name}</li>
</ul>
</body>
</html>
""", encoding="utf-8")

catalog.close()
tcg.close()

print("Coverage analytics complete.")
print(f"Dashboard: {HTML}")
print(f"By-set CSV: {BY_SET}")
print(f"Unresolved CSV: {UNRESOLVED}")
print(f"Total cards: {total}")
print(f"Linked cards: {linked} ({pct(linked,total)}%)")
print(f"Priced cards: {priced} ({pct(priced,total)}%)")
print(f"Unresolved: {unresolved} ({pct(unresolved,total)}%)")
''', encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.8.3"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

notes = DOCS / "RELEASE_NOTES_v0_8_3.txt"
notes.write_text("""v0.8.3 Coverage Analytics

Adds:
- Coverage analytics builder
- HTML dashboard
- By-set coverage CSV
- Unresolved cards CSV

Metrics:
- Total cards
- Linked cards
- Priced cards
- Linked-image cards
- Multi-variant cards
- Unresolved cards
- Best/worst set coverage

No extension UI behavior changes.
""", encoding="utf-8")

print("Installed v0.8.3 Coverage Analytics")
print(f"Extension version: {old_version} -> 0.8.3")
print(f"Tool: {tool}")
print(f"Release notes: {notes}")
print(f"Backups saved in: {archive}")