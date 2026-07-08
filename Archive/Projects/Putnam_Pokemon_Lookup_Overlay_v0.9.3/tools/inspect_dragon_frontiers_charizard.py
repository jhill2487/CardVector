import sqlite3
from pathlib import Path

DB = Path("price_cache/tcgtracking_cache.sqlite")
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

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
left join tcgtracking_sets s on s.set_id = p.set_id
where lower(s.name) like '%dragon frontiers%'
  and (
    lower(p.name) like '%charizard%'
    or p.clean_number = '100'
    or p.card_number like '100/%'
  )
order by p.clean_number, p.name
limit 50
""").fetchall()

print(f"Rows found: {len(rows)}")
for r in rows:
    print(dict(r))

con.close()