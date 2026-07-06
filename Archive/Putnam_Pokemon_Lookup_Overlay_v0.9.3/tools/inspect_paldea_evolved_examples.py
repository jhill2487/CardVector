import sqlite3

tcg = sqlite3.connect("price_cache/tcgtracking_cache.sqlite")
tcg.row_factory = sqlite3.Row
cur = tcg.cursor()

terms = ["Tinkatink", "Dendra", "Iono", "Magikarp"]

for term in terms:
    print("\n===", term, "===")
    rows = cur.execute("""
    select
      p.product_id,
      s.name as set_name,
      p.name as product_name,
      p.card_number,
      p.clean_number,
      p.image_url
    from tcgtracking_products p
    left join tcgtracking_sets s on s.set_id=p.set_id
    where lower(s.name) like '%paldea%'
      and lower(p.name) like ?
    order by p.clean_number, p.name
    limit 20
    """, [f"%{term.lower()}%"]).fetchall()

    for r in rows:
        print(dict(r))

tcg.close()