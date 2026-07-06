from __future__ import annotations

import sqlite3
import csv
import re
from pathlib import Path
from typing import Any

from card_catalog import load_config


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"
PRICE_DB_PATH = RUNTIME / "market_prices.sqlite"
TCGTRACKING_DB_PATH = ROOT.parent / "price_cache" / "tcgtracking_cache.sqlite"

DISPLAY_CONDITIONS = ("NM", "LP", "MARKET")
PROVIDER_PRIORITY = {
    "tcgplayer": 1,
    "tcgdex": 2,
    "manual": 2,
    "pricecharting": 3,
    "ebay": 4,
    "sample": 99,
}


def connect() -> sqlite3.Connection:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(PRICE_DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_price_db() -> None:
    with connect() as con:
        con.executescript(
            """
            create table if not exists market_price_links (
              putnam_card_id text not null,
              provider text not null,
              provider_product_id text,
              provider_url text,
              match_confidence real default 0,
              last_verified_at text,
              primary key (putnam_card_id, provider)
            );

            create table if not exists market_price_snapshots (
              snapshot_id integer primary key autoincrement,
              putnam_card_id text not null,
              provider text not null,
              condition text not null,
              market_price real,
              low_price real,
              high_price real,
              sample_size integer,
              as_of text not null default (datetime('now'))
            );

            create index if not exists idx_market_price_snapshots_card
              on market_price_snapshots (putnam_card_id, provider, condition, as_of);
            """
        )


def latest_prices_for_card(putnam_card_id: str) -> dict[str, Any] | None:
    from card_catalog import get_card_by_id

    def norm_text(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    def clean_number(value: object) -> str:
        text = str(value or "").lower().strip()
        if "/" in text:
            text = text.split("/", 1)[0]
        text = text.lstrip("0")
        return text or str(value or "").lower().strip()

    def set_aliases(set_name: object) -> set[str]:
        slug = norm_text(set_name)
        aliases = {slug}
        manual = {
            "base": {"base set"},
            "base set": {"base"},
            "151": {"sv scarlet violet 151", "scarlet violet 151", "sv 151"},
            "crown zenith galarian gallery": {"swsh crown zenith galarian gallery"},
        }
        aliases.update(manual.get(slug, set()))
        return {a for a in aliases if a}

    if not TCGTRACKING_DB_PATH.exists():
        init_price_db()
        with sqlite3.connect(PRICE_DB_PATH) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                """
                select condition, provider, market_price, low_price, high_price, sample_size, as_of
                from (
                  select *,
                         row_number() over (
                           partition by condition
                           order by
                             case provider
                               when 'tcgplayer' then 1
                               when 'tcgdex' then 2
                               when 'pricecharting' then 3
                               else 9
                             end,
                             as_of desc
                         ) as rn
                  from market_price_snapshots
                  where putnam_card_id = ?
                )
                where rn = 1
                """,
                [putnam_card_id],
            ).fetchall()

        prices: dict[str, Any] = {}
        for row in rows:
            prices[row["condition"]] = {
                "source": row["provider"],
                "market": row["market_price"],
                "low": row["low_price"],
                "high": row["high_price"],
                "sample_size": row["sample_size"],
                "as_of": row["as_of"],
            }
        return prices or None

    card = get_card_by_id(putnam_card_id)
    if not card:
        return None

    product_ids: list[str] = []

    with sqlite3.connect(TCGTRACKING_DB_PATH) as con:
        con.row_factory = sqlite3.Row

        bridge_rows = con.execute(
            """
            select tcgtracking_product_id
            from putnam_tcgtracking_matches
            where putnam_card_id = ?
            order by match_confidence desc
            limit 12
            """,
            [putnam_card_id],
        ).fetchall()
        product_ids = [str(r["tcgtracking_product_id"]) for r in bridge_rows if r["tcgtracking_product_id"]]

        if not product_ids:
            card_name = norm_text(card.get("card_name"))
            card_number = clean_number(card.get("card_number") or card.get("printed_number"))
            set_names = set_aliases(card.get("set_name"))

            candidates = con.execute(
                """
                select p.product_id, s.name as set_name, p.name as product_name,
                       p.card_number, p.clean_number, p.image_url, p.product_url, p.tcgplayer_url
                from tcgtracking_products p
                left join tcgtracking_sets s on s.set_id = p.set_id
                where lower(p.name) like ?
                limit 250
                """,
                [f"%{str(card.get('card_name') or '').lower()}%"],
            ).fetchall()

            scored: list[tuple[int, str]] = []
            for row in candidates:
                product_name = norm_text(row["product_name"])
                product_set = norm_text(row["set_name"])
                product_clean = clean_number(row["clean_number"] or row["card_number"])

                score = 0
                if card_name and card_name in product_name:
                    score += 40
                elif product_name and product_name in card_name:
                    score += 25

                if card_number and product_clean == card_number:
                    score += 35

                if product_set in set_names:
                    score += 35
                elif any(alias and alias in product_set for alias in set_names):
                    score += 25
                elif any(product_set and product_set in alias for alias in set_names):
                    score += 20

                if norm_text(card.get("set_name")) == "base" and "base set" in product_set:
                    score += 20

                if score >= 70:
                    scored.append((score, str(row["product_id"])))

            product_ids = [pid for _, pid in sorted(scored, reverse=True)[:12]]

        if not product_ids:
            return None

        placeholders = ",".join("?" for _ in product_ids)

        product_rows = {
            str(r["product_id"]): dict(r)
            for r in con.execute(
                f"""
                select p.product_id, s.name as set_name, p.name as product_name,
                       p.card_number, p.clean_number, p.image_url, p.product_url, p.tcgplayer_url
                from tcgtracking_products p
                left join tcgtracking_sets s on s.set_id = p.set_id
                where p.product_id in ({placeholders})
                """,
                product_ids,
            ).fetchall()
        }

        price_rows = con.execute(
            f"""
            select product_id, source, finish, condition, market, low, high, fetched_at
            from tcgtracking_prices
            where product_id in ({placeholders})
              and condition in ('NM', 'LP', 'MP', 'HP', 'DMG')
            order by product_id, finish, condition, fetched_at desc
            """,
            product_ids,
        ).fetchall()

    grouped: dict[tuple[str, str], dict[str, Any]] = {}

    for row in price_rows:
        product_id = str(row["product_id"])
        finish = str(row["finish"] or "normal")
        key = (product_id, finish)
        product = product_rows.get(product_id, {})

        if key not in grouped:
            grouped[key] = {
                "product_id": product_id,
                "set_name": product.get("set_name"),
                "product_name": product.get("product_name"),
                "card_number": product.get("card_number"),
                "clean_number": product.get("clean_number"),
                "image_url": product.get("image_url"),
                "product_url": product.get("product_url"),
                "tcgplayer_url": product.get("tcgplayer_url"),
                "finish": finish,
                "conditions": {},
            }

        condition = str(row["condition"] or "").upper()
        condition_obj = grouped[key]["conditions"].setdefault(
            condition,
            {
                "market": row["market"],
                "low": row["low"],
                "high": row["high"],
                "fetched_at": row["fetched_at"],
                "source": row["source"],
                "sources": [],
            },
        )
        condition_obj["sources"].append(
            {
                "market": row["market"],
                "low": row["low"],
                "high": row["high"],
                "fetched_at": row["fetched_at"],
                "source": row["source"],
            }
        )

    variants = list(grouped.values())

    prices: dict[str, Any] = {
        "source": "tcgtracking",
        "variants": variants,
    }

    for variant in variants:
        for condition in ("NM", "LP", "MP", "HP", "DMG"):
            if condition not in prices and condition in variant.get("conditions", {}):
                prices[condition] = variant["conditions"][condition]
        if "NM" in prices or "LP" in prices:
            break

    return prices if variants else None


def upsert_price_link(
    putnam_card_id: str,
    provider: str,
    provider_product_id: str | None = None,
    provider_url: str | None = None,
    match_confidence: float = 1.0,
) -> None:
    init_price_db()
    with connect() as con:
        con.execute(
            """
            insert or replace into market_price_links
              (putnam_card_id, provider, provider_product_id, provider_url, match_confidence, last_verified_at)
            values (?, ?, ?, ?, ?, datetime('now'))
            """,
            [putnam_card_id, provider, provider_product_id, provider_url, match_confidence],
        )


def insert_price_snapshot(
    putnam_card_id: str,
    provider: str,
    condition: str,
    market_price: float | None,
    low_price: float | None = None,
    high_price: float | None = None,
    sample_size: int | None = None,
) -> None:
    init_price_db()
    if condition not in DISPLAY_CONDITIONS:
        return

    with connect() as con:
        con.execute(
            """
            insert into market_price_snapshots
              (putnam_card_id, provider, condition, market_price, low_price, high_price, sample_size)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            [putnam_card_id, provider, condition, market_price, low_price, high_price, sample_size],
        )


def import_tcgplayer_csv(csv_path: Path) -> int:
    """Import a local TCGplayer price export.

    Preferred columns:
    putnam_card_id,tcgplayer_product_id,tcgplayer_url,NM_market,LP_market,NM_low,NM_high,LP_low,LP_high

    Also accepts aliases such as:
    TCGplayer ID, Product ID, Near Mint, Lightly Played, NM, LP
    """
    init_price_db()
    imported = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            putnam_card_id = value_for(row, "putnam_card_id", "Putnam Card ID", "card_id")
            if not putnam_card_id:
                continue

            upsert_price_link(
                putnam_card_id=putnam_card_id,
                provider="tcgplayer",
                provider_product_id=value_for(row, "tcgplayer_product_id", "TCGplayer ID", "Product ID") or None,
                provider_url=value_for(row, "tcgplayer_url", "TCGplayer URL", "Product URL", "URL") or None,
                match_confidence=1.0,
            )
            condition_columns = {
                "NM": ("NM_market", "NM", "Near Mint", "Near Mint Market"),
                "LP": ("LP_market", "LP", "Lightly Played", "Lightly Played Market"),
            }
            for condition, aliases in condition_columns.items():
                market = number_for(row, *aliases)
                if market is None:
                    continue
                insert_price_snapshot(
                    putnam_card_id=putnam_card_id,
                    provider="tcgplayer",
                    condition=condition,
                    market_price=market,
                    low_price=number_for(row, f"{condition}_low", f"{condition} Low", f"{condition}_low_price"),
                    high_price=number_for(row, f"{condition}_high", f"{condition} High", f"{condition}_high_price"),
                    sample_size=int(number_for(row, f"{condition}_sample_size", f"{condition} Sample Size") or 0) or None,
                )
                imported += 1
    return imported


def value_for(row: dict[str, str], *names: str) -> str:
    normalized = {key.strip().lower(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(name.strip().lower())
        if value not in (None, ""):
            return value.strip()
    return ""


def number_for(row: dict[str, str], *names: str) -> float | None:
    value = value_for(row, *names)
    if not value:
        return None
    value = value.replace("$", "").replace(",", "").strip()
    return float(value) if value else None


def sync_existing_tcgplayer_links() -> int:
    init_price_db()
    config = load_config()
    if not config.sqlite_path.exists():
        return 0

    source = sqlite3.connect(config.sqlite_path)
    source.row_factory = sqlite3.Row
    synced = 0
    try:
        rows = source.execute(
            """
            select putnam_card_id, tcgplayer_product_id, tcgplayer_url
            from pokemon_cards
            where coalesce(tcgplayer_product_id, '') <> ''
               or coalesce(tcgplayer_url, '') <> ''
            """
        ).fetchall()
        for row in rows:
            upsert_price_link(
                putnam_card_id=row["putnam_card_id"],
                provider="tcgplayer",
                provider_product_id=row["tcgplayer_product_id"],
                provider_url=row["tcgplayer_url"],
                match_confidence=1.0,
            )
            synced += 1
    finally:
        source.close()
    return synced


def seed_demo_prices(putnam_card_id: str) -> None:
    init_price_db()
    demo = {
        "NM": (125.0, 118.0, 132.0),
        "LP": (101.0, 92.0, 108.0),
    }
    with connect() as con:
        existing = con.execute(
            "select count(*) from market_price_snapshots where putnam_card_id = ?",
            [putnam_card_id],
        ).fetchone()[0]
        if existing:
            return

        con.execute(
            """
            insert or replace into market_price_links
              (putnam_card_id, provider, provider_product_id, provider_url, match_confidence, last_verified_at)
            values (?, 'sample', ?, '', 1.0, datetime('now'))
            """,
            [putnam_card_id, putnam_card_id],
        )
        con.executemany(
            """
            insert into market_price_snapshots
              (putnam_card_id, provider, condition, market_price, low_price, high_price, sample_size)
            values (?, 'sample', ?, ?, ?, ?, 0)
            """,
            [(putnam_card_id, condition, *values) for condition, values in demo.items()],
        )


if __name__ == "__main__":
    import sys

    init_price_db()
    if len(sys.argv) > 1 and sys.argv[1] == "--sync-links":
        count = sync_existing_tcgplayer_links()
        print(f"synced {count} existing TCGplayer product links")
    elif len(sys.argv) > 1:
        count = import_tcgplayer_csv(Path(sys.argv[1]))
        print(f"imported {count} TCGplayer NM/LP price rows")
    else:
        print(f"price db ready: {PRICE_DB_PATH}")
