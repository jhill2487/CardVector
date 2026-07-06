import sqlite3

tcg = sqlite3.connect("price_cache/tcgtracking_cache.sqlite")
tcg.row_factory = sqlite3.Row
cur = tcg.cursor()

tests = [
    ("SWSH: Sword & Shield Promo Cards", "Grookey"),
    ("SM Promos", "Rowlet"),
    ("HGSS Promos", "Ho-Oh"),
    ("Nintendo Promos", "Kyogre"),
]

for set_name, name_hint in tests:
    print("\n" + "=" * 100)
    print(set_name, "|", name_hint)
    print("=" * 100)

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
    where s.name = ?
      and lower(p.name) like ?
    order by p.name
    limit 30
    """, [set_name, f"%{name_hint.lower()}%"]).fetchall()

    print("Rows:", len(rows))
    for r in rows:
        print(dict(r))

tcg.close()