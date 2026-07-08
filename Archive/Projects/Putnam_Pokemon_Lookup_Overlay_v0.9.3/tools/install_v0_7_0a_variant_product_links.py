from pathlib import Path
import sqlite3
import datetime
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "backend" / "runtime" / "market_prices.sqlite"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

if DB.exists():
    shutil.copy2(DB, archive / f"market_prices_before_v0_7_0a_{stamp}.sqlite")
shutil.copy2(MANIFEST, archive / f"manifest_before_v0_7_0a_{stamp}.json")

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("""
create table if not exists variant_product_links (
  putnam_card_id text not null,
  provider text not null default 'tcgplayer',
  provider_product_id text not null,
  provider_url text,
  variant_key text not null,
  variant_label text not null,
  match_confidence real default 1.0,
  last_verified_at text default (datetime('now')),
  primary key (putnam_card_id, provider, provider_product_id, variant_key)
)
""")

rows = [
    (
        "pkm-ascended-heroes-55-217-d5d41bd728",
        "tcgplayer",
        "675867",
        "https://www.tcgplayer.com/product/675867/pokemon-me-ascended-heroes-pikachu",
        "normal",
        "NORMAL",
        1.0,
    ),
    (
        "pkm-ascended-heroes-55-217-d5d41bd728",
        "tcgplayer",
        "677037",
        "https://www.tcgplayer.com/product/677037/pokemon-me-ascended-heroes-pikachu-energy-symbol-pattern",
        "energy_symbol_pattern",
        "ENERGY SYMBOL",
        1.0,
    ),
    (
        "pkm-ascended-heroes-55-217-d5d41bd728",
        "tcgplayer",
        "676897",
        "https://www.tcgplayer.com/product/676897/pokemon-me-ascended-heroes-pikachu-friend-ball",
        "friend_ball",
        "FRIEND BALL",
        1.0,
    ),
]

cur.executemany("""
insert or replace into variant_product_links
(putnam_card_id, provider, provider_product_id, provider_url, variant_key, variant_label, match_confidence)
values (?, ?, ?, ?, ?, ?, ?)
""", rows)

con.commit()
con.close()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.0"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.0A Variant Product Link Architecture")
print(f"Extension version: {old_version} -> 0.7.0")
print("Seeded Ascended Heroes Pikachu 55/217 variant product links:")
for row in rows:
    print(f" - {row[5]}: {row[2]}")