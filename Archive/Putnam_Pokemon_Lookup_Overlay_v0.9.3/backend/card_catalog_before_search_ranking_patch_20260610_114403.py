from __future__ import annotations

import csv
import json
import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "data_sources.json"
RUNTIME = ROOT / "runtime"
CATALOG_STATUS_PATH = RUNTIME / "catalog_status.json"


@dataclass(frozen=True)
class CatalogConfig:
    sqlite_path: Path
    kaggle_visual_index_csv: Path
    kaggle_image_root: Path


def load_config() -> CatalogConfig:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return CatalogConfig(
        sqlite_path=Path(data["sqlite_path"]),
        kaggle_visual_index_csv=Path(data["kaggle_visual_index_csv"]),
        kaggle_image_root=Path(data["kaggle_image_root"]),
    )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def slugify(value: str) -> str:
    value = value.lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


@lru_cache(maxsize=1)
def catalog_status() -> dict[str, Any]:
    config = load_config()
    status: dict[str, Any] = {
        "sqlite_path": str(config.sqlite_path),
        "sqlite_exists": config.sqlite_path.exists(),
        "kaggle_visual_index_csv": str(config.kaggle_visual_index_csv),
        "kaggle_visual_index_exists": config.kaggle_visual_index_csv.exists(),
        "kaggle_image_root": str(config.kaggle_image_root),
        "kaggle_image_root_exists": config.kaggle_image_root.exists(),
        "sets": 0,
        "cards": 0,
        "fingerprints": 0,
        "visual_index_rows": 0,
        "ready": False,
    }

    if config.sqlite_path.exists():
        con = sqlite3.connect(config.sqlite_path)
        try:
            cur = con.cursor()
            status["sets"] = cur.execute("select count(*) from pokemon_sets").fetchone()[0]
            status["cards"] = cur.execute("select count(*) from pokemon_cards").fetchone()[0]
            status["fingerprints"] = cur.execute("select count(*) from kaggle_ocr_fingerprints").fetchone()[0]
        finally:
            con.close()

    if config.kaggle_visual_index_csv.exists():
        with config.kaggle_visual_index_csv.open("r", encoding="utf-8", newline="") as handle:
            status["visual_index_rows"] = max(sum(1 for _ in handle) - 1, 0)

    status["ready"] = bool(status["sqlite_exists"] and status["kaggle_visual_index_exists"])
    return status


def search_cards(
    name: str | None = None,
    number: str | None = None,
    set_slug_or_name: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    config = load_config()
    if not config.sqlite_path.exists():
        return []

    clauses = ["game = 'pokemon'"]
    params: list[Any] = []

    if name:
        clauses.append("lower(card_name) like lower(?)")
        params.append(f"%{name}%")

    if number:
        normalized = number.lstrip("0") or number
        clauses.append("(card_number = ? or card_number = ? or printed_number like ?)")
        params.extend([number, normalized, f"{normalized}/%"])

    if set_slug_or_name:
        clauses.append("(lower(set_slug) = lower(?) or lower(set_name) like lower(?))")
        params.extend([set_slug_or_name, f"%{set_slug_or_name}%"])

    sql = f"""
        select
          putnam_card_id,
          set_name,
          set_slug,
          set_code,
          series,
          card_name,
          card_number,
          set_total,
          printed_number,
          rarity,
          lookup_key,
          pokemontcg_id,
          image_small_url,
          image_large_url,
          tcgplayer_url,
          tcgplayer_product_id
        from pokemon_cards
        where {' and '.join(clauses)}
        order by set_name, card_number_sort, card_name
        limit ?
    """
    params.append(limit)

    con = sqlite3.connect(config.sqlite_path)
    con.row_factory = sqlite3.Row
    try:
        return [row_to_dict(row) for row in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def get_card_by_id(card_id: str) -> dict[str, Any] | None:
    config = load_config()
    if not config.sqlite_path.exists():
        return None

    con = sqlite3.connect(config.sqlite_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            """
            select
              putnam_card_id,
              set_name,
              set_slug,
              set_code,
              series,
              card_name,
              card_number,
              set_total,
              printed_number,
              rarity,
              lookup_key,
              pokemontcg_id,
              image_small_url,
              image_large_url,
              tcgplayer_url,
              tcgplayer_product_id
            from pokemon_cards
            where putnam_card_id = ?
            limit 1
            """,
            [card_id],
        ).fetchone()
        return row_to_dict(row) if row else None
    finally:
        con.close()


@lru_cache(maxsize=1)
def visual_index_rows() -> tuple[dict[str, str], ...]:
    config = load_config()
    if not config.kaggle_visual_index_csv.exists():
        return ()

    with config.kaggle_visual_index_csv.open("r", encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def candidate_set_folders(set_slug: str, set_name: str | None = None) -> set[str]:
    folders = {set_slug}
    if set_name:
        folders.add(slugify(set_name))

    suffixes = [
        "-trainer-gallery",
        "-galarian-gallery",
        "-radiant-collection",
    ]
    for suffix in suffixes:
        if set_slug.endswith(suffix):
            folders.add(set_slug[: -len(suffix)])

    aliases = {
        "bw-black-star-promos": "black-white-promos",
        "black-and-white-promos": "black-white-promos",
        "swsh-black-star-promos": "sword-shield-promos",
        "scarlet-and-violet-promos": "scarlet-violet-promos",
    }
    if set_slug in aliases:
        folders.add(aliases[set_slug])

    return {folder for folder in folders if folder}


def number_tokens(card_number: str, printed_number: str | None = None) -> set[str]:
    raw = (card_number or "").strip()
    tokens = {raw.lower()} if raw else set()
    if printed_number:
        tokens.add(printed_number.split("/", 1)[0].strip().lower())

    match = re.match(r"^([a-zA-Z]+)(\d+)$", raw)
    if match:
        prefix, digits = match.groups()
        tokens.add(f"{prefix.lower()}{digits}")
        tokens.add(f"{prefix.lower()}{int(digits):03d}")
    elif raw.isdigit():
        tokens.add(raw.zfill(3))

    return {token for token in tokens if token}


def resolve_thumbnail_for_card(card: dict[str, Any]) -> dict[str, Any] | None:
    config = load_config()
    folders = candidate_set_folders(card.get("set_slug", ""), card.get("set_name"))
    tokens = number_tokens(card.get("card_number", ""), card.get("printed_number"))
    name_slug = slugify(card.get("card_name", ""))

    if not folders or not tokens:
        return None

    best: dict[str, str] | None = None
    for row in visual_index_rows():
        if row.get("set_folder") not in folders:
            continue

        row_number = (row.get("card_number") or "").lower()
        filename = (row.get("filename") or "").lower()
        number_match = row_number in tokens or any(token in filename for token in tokens)
        name_match = not name_slug or name_slug in slugify(row.get("filename", ""))
        if number_match and name_match:
            best = row
            break

        if number_match and best is None:
            best = row

    if not best:
        return None

    image_path = config.kaggle_image_root / best["file_path"]
    return {
        **best,
        "resolved_image_path": str(image_path),
        "resolved_image_exists": image_path.exists(),
    }


def visual_index_lookup(set_folder: str, card_number: str) -> dict[str, Any] | None:
    config = load_config()
    if not config.kaggle_visual_index_csv.exists():
        return None

    normalized = card_number.zfill(3)
    for row in visual_index_rows():
        if row.get("set_folder") == set_folder and row.get("card_number") == normalized:
            image_path = config.kaggle_image_root / row["file_path"]
            return {
                **row,
                "resolved_image_path": str(image_path),
                "resolved_image_exists": image_path.exists(),
            }
    return None


def write_catalog_status() -> dict[str, Any]:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    catalog_status.cache_clear()
    status = catalog_status()
    CATALOG_STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


if __name__ == "__main__":
    written = write_catalog_status()
    print(
        "catalog ready={ready} sets={sets} cards={cards} fingerprints={fingerprints} visual_rows={visual_index_rows}".format(
            **written
        )
    )
