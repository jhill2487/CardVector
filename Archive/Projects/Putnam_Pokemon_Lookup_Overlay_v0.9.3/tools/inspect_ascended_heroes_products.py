import sqlite3
from pathlib import Path

DB = Path("price_cache/tcgtracking_cache.sqlite")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

print("=== TABLES ===")
for row in cur.execute(
    "select name from sqlite_master where type='table' order by name"
):
    print(row["name"])

print("\n=== ASCENDED HEROES PRODUCTS ===")

rows = cur.execute("""
select
    p.product_id,
    s.name as set_name,
    p.name as product_name,
    p.card_number,
    p.clean_number,
    p.image_url,
    p.tcgplayer_url
from tcgtracking_products p
left join tcgtracking_sets s
    on s.set_id = p.set_id
where lower(s.name) like '%ascended%'
order by p.card_number
limit 50
""").fetchall()

print(f"Found {len(rows)} products\n")

for row in rows:
    print(dict(row))

con.close()