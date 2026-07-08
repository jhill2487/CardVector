import sqlite3
from pathlib import Path

DB = Path("database/putnam_pokemon_cloud_ready.sqlite")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

print("\n=== pokemon_cards matches ===")
rows = cur.execute("""
select
  putnam_card_id,
  set_name,
  card_name,
  card_number,
  printed_number,
  image_small_url,
  image_large_url,
  tcgplayer_product_id,
  tcgplayer_url
from pokemon_cards
where lower(card_name) = 'pikachu'
  and (
    lower(set_name) like '%ascended%'
    or printed_number like '55/%'
    or card_number = '55'
  )
order by set_name, card_number_sort
""").fetchall()

for r in rows:
    print(dict(r))

print("\n=== tcgtracking_products matches ===")
rows = cur.execute("""
select
  p.product_id,
  s.name as set_name,
  p.name as product_name,
  p.card_number,
  p.clean_number,
  p.image_url,
  p.product_url,
  p.tcgplayer_url
from tcgtracking_products p
left join tcgtracking_sets s on s.set_id = p.set_id
where lower(p.name) like '%pikachu%'
  and (
    lower(s.name) like '%ascended%'
    or p.card_number like '55/%'
    or p.clean_number = '55'
  )
order by s.name, p.name, p.card_number
limit 50
""").fetchall()

for r in rows:
    print(dict(r))

con.close()