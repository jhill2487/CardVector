import sqlite3

con = sqlite3.connect("database/putnam_pokemon_cloud_ready.sqlite")
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute("""
select
    putnam_card_id,
    set_name,
    card_name,
    printed_number
from pokemon_cards
where lower(card_name) like '%charizard%'
  and printed_number='150/147'
""").fetchall()

print("Rows:", len(rows))
for r in rows:
    print(dict(r))

con.close()