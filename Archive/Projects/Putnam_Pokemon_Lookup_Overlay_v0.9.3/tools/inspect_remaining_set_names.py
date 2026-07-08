import sqlite3

con = sqlite3.connect("price_cache/tcgtracking_cache.sqlite")
cur = con.cursor()

queries = {
    "BASE": """
        select name
        from tcgtracking_sets
        where lower(name) like '%base%'
        order by name
    """,
    "EXPEDITION": """
        select name
        from tcgtracking_sets
        where lower(name) like '%expedition%'
        order by name
    """,
    "SUN_MOON": """
        select name
        from tcgtracking_sets
        where lower(name) like '%sun%'
           or lower(name) like '%moon%'
        order by name
    """,
    "XY": """
        select name
        from tcgtracking_sets
        where lower(name) like 'xy%'
        order by name
    """
}

for title, sql in queries.items():
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    rows = cur.execute(sql).fetchall()

    for row in rows:
        print(row[0])

con.close()