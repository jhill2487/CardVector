import sqlite3

con = sqlite3.connect("price_cache/tcgtracking_cache.sqlite")
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute("""
select *
from putnam_tcgtracking_matches
where putnam_card_id = 'pkm-ascended-heroes-55-217-d5d41bd728'
order by match_confidence desc
""").fetchall()

print(f"Rows found: {len(rows)}\n")

for row in rows:
    print(dict(row))

con.close()