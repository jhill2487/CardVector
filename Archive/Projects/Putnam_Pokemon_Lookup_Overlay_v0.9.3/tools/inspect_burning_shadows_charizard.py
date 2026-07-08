import sqlite3

con = sqlite3.connect("price_cache/tcgtracking_cache.sqlite")
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute("""
select
    p.product_id,
    s.name as set_name,
    p.name as product_name,
    p.card_number,
    p.clean_number,
    p.image_url
from tcgtracking_products p
left join tcgtracking_sets s
    on s.set_id = p.set_id
where lower(s.name) like '%burning shadows%'
and lower(p.name) like '%charizard%'
order by p.clean_number
""").fetchall()

print("Rows:", len(rows))
for r in rows:
    print(dict(r))

con.close()