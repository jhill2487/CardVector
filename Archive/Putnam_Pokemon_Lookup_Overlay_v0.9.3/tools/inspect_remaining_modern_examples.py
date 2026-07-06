import sqlite3

tcg = sqlite3.connect("price_cache/tcgtracking_cache.sqlite")
tcg.row_factory = sqlite3.Row
cur = tcg.cursor()

tests = [
    ("Temporal Forces", "Gengar", "104"),
    ("Temporal Forces", "Raging Bolt", "123"),
    ("Twilight Masquerade", "Greninja", "106"),
    ("Twilight Masquerade", "Dragapult", "130"),
    ("Paldean Fates", "Pikachu", "131"),
    ("Paldean Fates", "Charmander", "109"),
]

for set_hint, name_hint, clean_number in tests:
    print("\n" + "=" * 90)
    print(set_hint, "|", name_hint, "|", clean_number)
    print("=" * 90)

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
    where lower(s.name) like ?
      and lower(p.name) like ?
      and p.clean_number = ?
    order by p.name
    limit 20
    """, [f"%{set_hint.lower().split()[0]}%", f"%{name_hint.lower()}%", clean_number]).fetchall()

    print("Rows:", len(rows))
    for r in rows:
        print(dict(r))

tcg.close()