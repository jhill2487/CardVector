import sqlite3

TARGET_SETS = [
    "HGSS Black Star Promos",
    "Nintendo Black Star Promos",
    "SM Black Star Promos",
    "SWSH Black Star Promos",
]

catalog = sqlite3.connect("database/putnam_pokemon_cloud_ready.sqlite")
catalog.row_factory = sqlite3.Row

tcg = sqlite3.connect("price_cache/tcgtracking_cache.sqlite")
tcg.row_factory = sqlite3.Row

linked = {
    r[0]
    for r in tcg.execute(
        "select distinct putnam_card_id from putnam_tcgtracking_matches"
    ).fetchall()
}

for target_set in TARGET_SETS:

    print("\n" + "=" * 120)
    print(target_set.upper())
    print("=" * 120)

    rows = catalog.execute("""
        select
            putnam_card_id,
            card_name,
            card_number,
            printed_number,
            rarity
        from pokemon_cards
        where set_name=?
        order by card_number
    """, [target_set]).fetchall()

    shown = 0

    for row in rows:

        if row["putnam_card_id"] in linked:
            continue

        print({
            "card_name": row["card_name"],
            "card_number": row["card_number"],
            "printed_number": row["printed_number"],
            "rarity": row["rarity"]
        })

        shown += 1

        if shown >= 25:
            break

    print()
    print("Unlinked shown:", shown)

catalog.close()
tcg.close()