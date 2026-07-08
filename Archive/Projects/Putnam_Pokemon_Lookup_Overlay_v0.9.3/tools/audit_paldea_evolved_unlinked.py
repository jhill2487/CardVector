import sqlite3

con = sqlite3.connect("database/putnam_pokemon_cloud_ready.sqlite")
con.row_factory = sqlite3.Row

tcg = sqlite3.connect("price_cache/tcgtracking_cache.sqlite")
tcg.row_factory = sqlite3.Row

linked = {
    r[0]
    for r in tcg.execute(
        "select distinct putnam_card_id from putnam_tcgtracking_matches"
    ).fetchall()
}

rows = con.execute("""
select
    putnam_card_id,
    card_name,
    printed_number
from pokemon_cards
where set_name='Paldea Evolved'
order by card_number
""").fetchall()

shown = 0

for row in rows:
    if row["putnam_card_id"] in linked:
        continue

    print({
        "card_name": row["card_name"],
        "printed_number": row["printed_number"]
    })

    shown += 1
    if shown >= 50:
        break

print()
print("Unlinked shown:", shown)