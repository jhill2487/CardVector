import sqlite3
from pathlib import Path

DB = Path("backend/runtime/market_prices.sqlite")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

print("\n=== tables ===")
for r in cur.execute("select name from sqlite_master where type='table' order by name").fetchall():
    print(r["name"])

print("\n=== pikachu-like rows ===")
for table in [r["name"] for r in cur.execute("select name from sqlite_master where type='table'").fetchall()]:
    cols = [c["name"] for c in cur.execute(f"pragma table_info({table})").fetchall()]
    text_cols = [c for c in cols if c.lower() in ("name", "product_name", "card_name", "set_name", "title")]
    if not text_cols:
        continue

    for col in text_cols:
        try:
            rows = cur.execute(f"select * from {table} where lower({col}) like '%pikachu%' limit 10").fetchall()
            if rows:
                print(f"\n--- {table}.{col} ---")
                for row in rows:
                    print(dict(row))
        except Exception:
            pass

con.close()