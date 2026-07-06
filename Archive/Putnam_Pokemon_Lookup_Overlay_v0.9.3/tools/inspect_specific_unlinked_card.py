import sqlite3

CARD_NAME = "Gengar ex"
SET_NAME = "Temporal Forces"

catalog = sqlite3.connect("database/putnam_pokemon_cloud_ready.sqlite")
catalog.row_factory = sqlite3.Row

rows = catalog.execute("""
select *
from pokemon_cards
where set_name=?
and card_name=?
""", [SET_NAME, CARD_NAME]).fetchall()

print("Rows:", len(rows))

for r in rows:
    print(dict(r))

catalog.close()