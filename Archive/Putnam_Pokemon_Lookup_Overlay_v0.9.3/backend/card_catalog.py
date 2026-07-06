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


def _safe_existing_file(path) -> bool:
    try:
        if path is None:
            return False
        s = str(path).strip()
        if not s or s == ".":
            return False
        p = Path(s).expanduser()
        return p.exists() and p.is_file()
    except Exception:
        return False


def catalog_status() -> dict[str, Any]:
    config = load_config()

    sqlite_exists = _safe_existing_file(config.sqlite_path)
    kaggle_visual_index_exists = _safe_existing_file(config.kaggle_visual_index_csv)

    image_root_text = str(config.kaggle_image_root).strip()
    kaggle_image_root_exists = bool(
        image_root_text
        and image_root_text != "."
        and config.kaggle_image_root.exists()
        and config.kaggle_image_root.is_dir()
    )

    status: dict[str, Any] = {
        "sqlite_path": str(config.sqlite_path),
        "sqlite_exists": sqlite_exists,
        "kaggle_visual_index_csv": str(config.kaggle_visual_index_csv),
        "kaggle_visual_index_exists": kaggle_visual_index_exists,
        "kaggle_image_root": str(config.kaggle_image_root),
        "kaggle_image_root_exists": kaggle_image_root_exists,
        "sets": 0,
        "cards": 0,
        "fingerprints": 0,
        "visual_index_rows": 0,
        "ready": False,
    }

    if sqlite_exists:
        con = sqlite3.connect(config.sqlite_path)
        try:
            cur = con.cursor()
            status["sets"] = cur.execute("select count(*) from pokemon_sets").fetchone()[0]
            status["cards"] = cur.execute("select count(*) from pokemon_cards").fetchone()[0]
            try:
                status["fingerprints"] = cur.execute("select count(*) from kaggle_ocr_fingerprints").fetchone()[0]
            except sqlite3.Error:
                status["fingerprints"] = 0
        finally:
            con.close()

    if kaggle_visual_index_exists:
        with config.kaggle_visual_index_csv.open("r", encoding="utf-8", newline="") as handle:
            status["visual_index_rows"] = max(sum(1 for _ in handle) - 1, 0)

    status["ready"] = bool(status["sqlite_exists"] and status["cards"] > 0)
    return status


def _search_cards_exact(
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
    if not _safe_existing_file(config.kaggle_visual_index_csv):
        return ()

    with config.kaggle_visual_index_csv.open("r", encoding="utf-8", newline="") as handle:
        import csv
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


# Patch 2C.11A - Token Search Recall
# Keeps exact search results first, then adds broader token matches.
# Example: "charizard ex" can also find "Mega Charizard Y ex".
def _search_recall_norm(value):
    import re
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _search_recall_tokens(value):
    tokens = _search_recall_norm(value).split()
    stop = {"the", "and", "of", "pokemon", "card"}
    return [t for t in tokens if t not in stop]


def _search_recall_key(card):
    return str(card.get("putnam_card_id") or card.get("lookup_key") or f"{card.get('set_name')}|{card.get('card_name')}|{card.get('printed_number')}")


def search_cards(name=None, number=None, set_slug_or_name=None, limit=20):
    exact_results = _search_cards_exact(
        name=name,
        number=number,
        set_slug_or_name=set_slug_or_name,
        limit=limit,
    )

    if not name:
        return exact_results

    query_tokens = _search_recall_tokens(name)

    # Only broaden multi-token searches such as "charizard ex", "mewtwo ex", "mega charizard".
    if len(query_tokens) < 2:
        return exact_results

    # Use the most distinctive non-suffix token as the broad search seed.
    suffix_tokens = {"ex", "gx", "v", "vmax", "vstar", "lv", "x"}
    seed_tokens = [t for t in query_tokens if t not in suffix_tokens]
    seed = seed_tokens[-1] if seed_tokens else query_tokens[0]

    broad_limit = max(int(limit or 20) * 10, 200)

    try:
        broad_results = _search_cards_exact(
            name=seed,
            number=number,
            set_slug_or_name=set_slug_or_name,
            limit=broad_limit,
        )
    except TypeError:
        return exact_results

    seen = set()
    merged = []

    for card in exact_results:
        key = _search_recall_key(card)
        seen.add(key)
        merged.append(card)

    for card in broad_results:
        card_name_norm = _search_recall_norm(card.get("card_name") or card.get("name"))
        if all(token in card_name_norm.split() for token in query_tokens):
            key = _search_recall_key(card)
            if key not in seen:
                seen.add(key)
                merged.append(card)

    return merged[:limit]


# v0.6.4B relevance/image coverage
# Improves search ordering while preserving Patch 2C.11A broad recall behavior.
# Adds safe image metadata enrichment when Kaggle visual index paths are available.

def _v064b_norm(value):
    import re
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _v064b_tokens(value):
    stop = {"the", "and", "of", "pokemon", "card"}
    return [t for t in _v064b_norm(value).split() if t and t not in stop]


def _v064b_number_head(value):
    raw = str(value or "").strip()
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    return raw.lower().lstrip("0") or raw.lower()


def _v064b_is_promo_query(query):
    q = _v064b_norm(query)
    promo_terms = [
        "promo",
        "promos",
        "black star",
        "black star promos",
        "svp",
        "swsh",
        "smp",
        "sm",
        "xy",
        "bw",
        "dp",
    ]
    return any(term in q for term in promo_terms)


def _v064b_relevance_score(card, query=None, number=None, set_slug_or_name=None):
    query_norm = _v064b_norm(query)
    query_tokens = _v064b_tokens(query)
    card_name = _v064b_norm(card.get("card_name") or card.get("name"))
    set_name = _v064b_norm(card.get("set_name") or card.get("set"))
    set_slug = _v064b_norm(card.get("set_slug"))
    printed = str(card.get("printed_number") or "")
    card_number = str(card.get("card_number") or "")
    rarity = _v064b_norm(card.get("rarity"))

    score = 0

    if query_norm:
        if card_name == query_norm:
            score += 10000
        elif card_name.startswith(query_norm):
            score += 8000
        elif query_norm in card_name:
            score += 6000

        if query_tokens:
            card_tokens = card_name.split()
            matched = sum(1 for t in query_tokens if t in card_tokens or t in card_name)
            score += matched * 900

            if all(t in card_tokens or t in card_name for t in query_tokens):
                score += 2500

            if card_tokens and query_tokens and card_tokens[0] == query_tokens[0]:
                score += 600

        if query_norm == set_name or query_norm == set_slug:
            score += 1500
        elif query_norm and (query_norm in set_name or query_norm in set_slug):
            score += 700

        if query_norm in _v064b_norm(printed) or query_norm == _v064b_number_head(card_number):
            score += 2500

        if _v064b_is_promo_query(query_norm):
            if "promo" in set_name or "promos" in set_name:
                score += 1800
            if any(str(card_number).lower().startswith(prefix) for prefix in ("svp", "swsh", "sm", "xy", "bw", "dp")):
                score += 1200

    if number:
        wanted = _v064b_number_head(number)
        printed_head = _v064b_number_head(printed)
        card_head = _v064b_number_head(card_number)
        if wanted and wanted in {printed_head, card_head}:
            score += 7000

    if set_slug_or_name:
        wanted_set = _v064b_norm(set_slug_or_name)
        if wanted_set and wanted_set in {set_name, set_slug}:
            score += 5000
        elif wanted_set and (wanted_set in set_name or wanted_set in set_slug):
            score += 2000

    # Prefer named/base card matches before variants when query is simple.
    if query_norm and len(query_tokens) == 1:
        if card_name == query_norm:
            score += 1000
        elif card_name.startswith(query_norm + " "):
            score += 400

    # Slightly boost cards that already have image/product data.
    if card.get("image_small_url") or card.get("image_large_url"):
        score += 80
    if card.get("tcgplayer_product_id") or card.get("tcgplayer_url"):
        score += 50

    return score


def _v064b_card_sort_tuple(card, query=None, number=None, set_slug_or_name=None):
    score = _v064b_relevance_score(card, query=query, number=number, set_slug_or_name=set_slug_or_name)
    set_name = str(card.get("set_name") or "")
    sort_number = str(card.get("card_number") or "")
    try:
        number_sort = int(re.sub(r"[^0-9]", "", sort_number) or "999999")
    except Exception:
        number_sort = 999999
    return (-score, set_name.lower(), number_sort, str(card.get("card_name") or "").lower())


def _v064b_enrich_card_image(card):
    try:
        if not card or not card.get("putnam_card_id"):
            return card

        # Keep existing image URLs first.
        if card.get("image_small_url") or card.get("image_large_url") or card.get("thumbnail_url"):
            return card

        resolved = resolve_thumbnail_for_card(card)
        if resolved and resolved.get("resolved_image_exists"):
            # Browser cannot load local file paths directly from content scripts safely,
            # so keep the canonical backend thumbnail route.
            card["thumbnail_url"] = f"/api/thumb-card?id={card['putnam_card_id']}"
            card["image_source"] = "kaggle_visual_index"
        return card
    except Exception:
        return card


try:
    _v064b_previous_search_cards = search_cards
except NameError:
    _v064b_previous_search_cards = None


def search_cards(name=None, number=None, set_slug_or_name=None, limit=20):
    # Pull a larger candidate pool, then relevance-rank locally.
    requested_limit = int(limit or 20)
    candidate_limit = max(requested_limit * 8, 160)

    if _v064b_previous_search_cards:
        try:
            candidates = _v064b_previous_search_cards(
                name=name,
                number=number,
                set_slug_or_name=set_slug_or_name,
                limit=candidate_limit,
            )
        except TypeError:
            candidates = _search_cards_exact(
                name=name,
                number=number,
                set_slug_or_name=set_slug_or_name,
                limit=candidate_limit,
            )
    else:
        candidates = _search_cards_exact(
            name=name,
            number=number,
            set_slug_or_name=set_slug_or_name,
            limit=candidate_limit,
        )

    seen = set()
    unique = []
    for card in candidates or []:
        key = _search_recall_key(card) if "_search_recall_key" in globals() else str(card.get("putnam_card_id") or card)
        if key in seen:
            continue
        seen.add(key)
        unique.append(_v064b_enrich_card_image(card))

    unique.sort(key=lambda c: _v064b_card_sort_tuple(c, query=name, number=number, set_slug_or_name=set_slug_or_name))
    return unique[:requested_limit]


# v0.6.4C smart query parser
# Understands collector-style searches:
# 151 pikachu, pikachu 25/165, bw54 pikachu, gg30 pikachu,
# base set charizard, shadowless charizard, 1st edition charizard.

def _v064c_norm(value):
    import re
    return re.sub(r"[^a-z0-9/]+", " ", str(value or "").lower()).strip()


def _v064c_tokens(value):
    return [t for t in _v064c_norm(value).split() if t]


def _v064c_is_number_token(token):
    import re
    t = str(token or "").lower().strip()
    return bool(
        re.match(r"^\d+/\d+$", t)
        or re.match(r"^[a-z]{1,5}\d{1,4}(/\d+)?$", t)
        or re.match(r"^\d{1,4}$", t)
    )


def _v064c_clean_card_terms(tokens):
    remove = {
        "first", "edition", "ed", "1st", "1e",
        "shadowless", "shadow", "unlimited",
        "holo", "reverse", "foil",
    }
    return [t for t in tokens if t not in remove and not _v064c_is_number_token(t)]


def _v064c_parse_query(query):
    tokens = _v064c_tokens(query)
    q = " ".join(tokens)

    parsed = {
        "original": str(query or "").strip(),
        "name": str(query or "").strip(),
        "set": "",
        "number": "",
        "variant": "",
        "attempts": [],
    }

    if not tokens:
        return parsed

    # Variants / vintage hints
    if "shadowless" in tokens:
        parsed["variant"] = "shadowless"

    if (
        "1st" in tokens
        or "1e" in tokens
        or ("first" in tokens and "edition" in tokens)
        or ("1st" in q and "edition" in q)
    ):
        parsed["variant"] = "first_edition"

    # Number / promo / gallery tokens
    number_tokens = [t for t in tokens if _v064c_is_number_token(t)]
    if number_tokens:
        parsed["number"] = number_tokens[0]

    # Known set phrases collectors actually type
    set_aliases = [
        ("base set 2", "base set 2"),
        ("base 2", "base set 2"),
        ("base set", "base"),
        ("pokemon 151", "151"),
        ("scarlet violet 151", "151"),
        ("sv 151", "151"),
        ("151", "151"),
        ("crown zenith galarian gallery", "crown zenith galarian gallery"),
        ("galarian gallery", "galarian gallery"),
        ("trainer gallery", "trainer gallery"),
        ("crown zenith", "crown zenith"),
        ("brilliant stars", "brilliant stars"),
        ("evolving skies", "evolving skies"),
        ("fusion strike", "fusion strike"),
        ("lost origin", "lost origin"),
        ("silver tempest", "silver tempest"),
        ("paldea evolved", "paldea evolved"),
        ("obsidian flames", "obsidian flames"),
        ("paldean fates", "paldean fates"),
        ("prismatic evolutions", "prismatic evolutions"),
        ("black star promos", "black star promos"),
        ("bw black star promos", "bw black star promos"),
        ("swsh black star promos", "swsh black star promos"),
        ("scarlet violet promos", "scarlet violet promos"),
        ("sv promos", "scarlet violet promos"),
        ("chaos rising", "chaos rising"),
        ("ascended heroes", "ascended heroes"),
    ]

    remaining = q
    for phrase, canonical in set_aliases:
        if phrase in q:
            parsed["set"] = canonical
            remaining = (" " + q + " ").replace(" " + phrase + " ", " ").strip()
            break

    cleaned_tokens = _v064c_clean_card_terms(remaining.split())
    parsed["name"] = " ".join(cleaned_tokens).strip()

    # If the query was just number + name, keep only name after removing number.
    if not parsed["name"]:
        parsed["name"] = " ".join(_v064c_clean_card_terms(tokens)).strip()

    # Fallback to original if cleaning removed too much.
    if not parsed["name"] and not parsed["number"] and not parsed["set"]:
        parsed["name"] = parsed["original"]

    # Build search attempts in priority order.
    attempts = []

    def add_attempt(name=None, number=None, set_name=None):
        attempt = {
            "name": name or None,
            "number": number or None,
            "set_slug_or_name": set_name or None,
        }
        if attempt not in attempts:
            attempts.append(attempt)

    # Best structured attempts first.
    if parsed["name"] and parsed["number"] and parsed["set"]:
        add_attempt(parsed["name"], parsed["number"], parsed["set"])

    if parsed["name"] and parsed["set"]:
        add_attempt(parsed["name"], None, parsed["set"])

    if parsed["name"] and parsed["number"]:
        add_attempt(parsed["name"], parsed["number"], None)

    if parsed["number"] and parsed["set"]:
        add_attempt(None, parsed["number"], parsed["set"])

    if parsed["number"]:
        add_attempt(None, parsed["number"], None)

    if parsed["name"]:
        add_attempt(parsed["name"], None, None)

    # Last resort: original behavior.
    add_attempt(parsed["original"], None, None)

    parsed["attempts"] = attempts
    return parsed


try:
    _v064c_previous_search_cards = search_cards
except NameError:
    _v064c_previous_search_cards = None


def search_cards(name=None, number=None, set_slug_or_name=None, limit=20):
    requested_limit = int(limit or 20)

    # If frontend already passed structured values, preserve normal behavior.
    if number or set_slug_or_name:
        return _v064c_previous_search_cards(
            name=name,
            number=number,
            set_slug_or_name=set_slug_or_name,
            limit=requested_limit,
        )

    parsed = _v064c_parse_query(name)

    seen = set()
    merged = []

    candidate_limit = max(requested_limit * 6, 120)

    for attempt in parsed.get("attempts", []):
        try:
            rows = _v064c_previous_search_cards(
                name=attempt.get("name"),
                number=attempt.get("number"),
                set_slug_or_name=attempt.get("set_slug_or_name"),
                limit=candidate_limit,
            )
        except Exception:
            rows = []

        for card in rows or []:
            key = str(card.get("putnam_card_id") or card.get("lookup_key") or card)
            if key in seen:
                continue
            seen.add(key)
            card["_query_parse"] = {
                "set": parsed.get("set"),
                "number": parsed.get("number"),
                "variant": parsed.get("variant"),
            }
            merged.append(card)

        if len(merged) >= requested_limit and attempt.get("set_slug_or_name"):
            break

    # Let v0.6.4B score/rank if helpers exist.
    try:
        merged.sort(key=lambda c: _v064b_card_sort_tuple(
            c,
            query=parsed.get("name") or name,
            number=parsed.get("number"),
            set_slug_or_name=parsed.get("set"),
        ))
    except Exception:
        pass

    return merged[:requested_limit]


# v0.6.4C2 smart query parser hotfix
# Fixes 151 being treated as both set and number.
# Adds stricter set filtering for parsed set queries.

def _v064c2_is_set_number_token(token):
    return str(token or "").strip().lower() in {"151"}


def _v064c2_card_matches_parsed_set(card, parsed_set):
    wanted = _v064c_norm(parsed_set)
    if not wanted:
        return True

    set_name = _v064c_norm(card.get("set_name"))
    set_slug = _v064c_norm(card.get("set_slug"))

    aliases = {
        "151": {"151"},
        "base": {"base"},
        "base set": {"base"},
        "base set 2": {"base set 2"},
        "crown zenith": {"crown zenith"},
        "galarian gallery": {"crown zenith galarian gallery", "galarian gallery"},
        "trainer gallery": {"trainer gallery"},
        "chaos rising": {"chaos rising"},
        "ascended heroes": {"ascended heroes"},
        "black star promos": {"black star promos"},
        "bw black star promos": {"bw black star promos"},
        "swsh black star promos": {"swsh black star promos"},
        "scarlet violet promos": {"scarlet violet promos"},
    }

    allowed = aliases.get(wanted, {wanted})

    for value in allowed:
        v = _v064c_norm(value)
        if set_name == v or set_slug == v:
            return True
        if wanted not in {"151", "base"} and (v in set_name or v in set_slug):
            return True

    return False


try:
    _v064c2_previous_parse_query = _v064c_parse_query
except NameError:
    _v064c2_previous_parse_query = None


def _v064c_parse_query(query):
    parsed = _v064c2_previous_parse_query(query)

    if not parsed:
        return parsed

    tokens = _v064c_tokens(query)
    parsed_set = parsed.get("set") or ""

    # If token is a known set alias like 151, do not also treat it as card number.
    if parsed_set and parsed.get("number") and _v064c2_is_set_number_token(parsed.get("number")):
        parsed["number"] = ""

    # Rebuild attempts after correcting number/set collision.
    attempts = []

    def add_attempt(name=None, number=None, set_name=None):
        attempt = {
            "name": name or None,
            "number": number or None,
            "set_slug_or_name": set_name or None,
        }
        if attempt not in attempts:
            attempts.append(attempt)

    name = parsed.get("name") or ""
    number = parsed.get("number") or ""
    set_name = parsed.get("set") or ""

    if name and number and set_name:
        add_attempt(name, number, set_name)

    if name and set_name:
        add_attempt(name, None, set_name)

    if name and number:
        add_attempt(name, number, None)

    if number and set_name:
        add_attempt(None, number, set_name)

    if number:
        add_attempt(None, number, None)

    if name:
        add_attempt(name, None, None)

    add_attempt(parsed.get("original"), None, None)

    parsed["attempts"] = attempts
    return parsed


try:
    _v064c2_previous_search_cards = search_cards
except NameError:
    _v064c2_previous_search_cards = None


def search_cards(name=None, number=None, set_slug_or_name=None, limit=20):
    requested_limit = int(limit or 20)

    # Preserve structured frontend/backend calls.
    if number or set_slug_or_name:
        rows = _v064c2_previous_search_cards(
            name=name,
            number=number,
            set_slug_or_name=set_slug_or_name,
            limit=max(requested_limit * 4, 80),
        )
        return rows[:requested_limit]

    parsed = _v064c_parse_query(name)
    parsed_set = parsed.get("set") or ""

    seen = set()
    merged = []
    candidate_limit = max(requested_limit * 8, 160)

    for attempt in parsed.get("attempts", []):
        try:
            rows = _v064c2_previous_search_cards(
                name=attempt.get("name"),
                number=attempt.get("number"),
                set_slug_or_name=attempt.get("set_slug_or_name"),
                limit=candidate_limit,
            )
        except Exception:
            rows = []

        for card in rows or []:
            if parsed_set and not _v064c2_card_matches_parsed_set(card, parsed_set):
                continue

            key = str(card.get("putnam_card_id") or card.get("lookup_key") or card)
            if key in seen:
                continue

            seen.add(key)
            card["_query_parse"] = {
                "set": parsed_set,
                "number": parsed.get("number") or "",
                "variant": parsed.get("variant") or "",
            }
            merged.append(card)

        if len(merged) >= requested_limit and parsed_set:
            break

    try:
        merged.sort(key=lambda c: _v064b_card_sort_tuple(
            c,
            query=parsed.get("name") or name,
            number=parsed.get("number"),
            set_slug_or_name=parsed_set,
        ))
    except Exception:
        pass

    return merged[:requested_limit]


# v0.6.4C3 exact identifier resolution
# Tightens searches like:
# pikachu 25/165, charizard 4/102, bw54 pikachu, gg30 pikachu, svp001 pikachu.

def _v064c3_norm_identifier(value):
    raw = str(value or "").lower().strip()
    raw = raw.replace(" ", "")
    return raw


def _v064c3_identifier_parts(value):
    raw = _v064c3_norm_identifier(value)
    if not raw:
        return {"raw": "", "head": "", "total": ""}

    if "/" in raw:
        head, total = raw.split("/", 1)
        return {
            "raw": raw,
            "head": head.lstrip("0") or head,
            "total": total.lstrip("0") or total,
        }

    return {
        "raw": raw,
        "head": raw.lstrip("0") or raw,
        "total": "",
    }


def _v064c3_card_identifier_parts(card):
    printed = str(card.get("printed_number") or "")
    card_number = str(card.get("card_number") or "")

    printed_parts = _v064c3_identifier_parts(printed)
    card_parts = _v064c3_identifier_parts(card_number)

    return {
        "printed_raw": printed_parts["raw"],
        "printed_head": printed_parts["head"],
        "printed_total": printed_parts["total"],
        "card_raw": card_parts["raw"],
        "card_head": card_parts["head"],
    }


def _v064c3_identifier_match_level(card, wanted_identifier):
    wanted = _v064c3_identifier_parts(wanted_identifier)
    ids = _v064c3_card_identifier_parts(card)

    if not wanted["raw"]:
        return 0

    # Full printed match: 25/165 == 25/165
    if wanted["total"] and ids["printed_raw"] == wanted["raw"]:
        return 100

    # Promo/gallery exact card number: BW54 == BW54, GG30 == GG30
    if ids["card_raw"] == wanted["raw"]:
        return 90

    # Printed head exact with same total if query had total.
    if wanted["total"]:
        if ids["printed_head"] == wanted["head"] and ids["printed_total"] == wanted["total"]:
            return 85
        return 0

    # No total in query: allow exact head/card number match.
    if ids["printed_head"] == wanted["head"] or ids["card_head"] == wanted["head"]:
        return 60

    return 0


def _v064c3_card_name_matches_query(card, parsed_name):
    name = _v064c_norm(parsed_name)
    if not name:
        return True

    card_name = _v064c_norm(card.get("card_name") or card.get("name"))
    tokens = [t for t in name.split() if t]

    if card_name == name:
        return True

    return all(t in card_name for t in tokens)


try:
    _v064c3_previous_search_cards = search_cards
except NameError:
    _v064c3_previous_search_cards = None


def search_cards(name=None, number=None, set_slug_or_name=None, limit=20):
    requested_limit = int(limit or 20)

    # Structured calls from frontend/backend should still benefit from exact identifier sorting.
    if number or set_slug_or_name:
        rows = _v064c3_previous_search_cards(
            name=name,
            number=number,
            set_slug_or_name=set_slug_or_name,
            limit=max(requested_limit * 8, 160),
        )

        if number:
            exact = []
            weak = []
            for card in rows or []:
                level = _v064c3_identifier_match_level(card, number)
                if level >= 85:
                    exact.append(card)
                elif level > 0:
                    weak.append(card)
            ranked = exact + weak
            return ranked[:requested_limit]

        return (rows or [])[:requested_limit]

    parsed = _v064c_parse_query(name)
    parsed_number = parsed.get("number") or ""
    parsed_name = parsed.get("name") or ""
    parsed_set = parsed.get("set") or ""

    rows = _v064c3_previous_search_cards(
        name=name,
        number=None,
        set_slug_or_name=None,
        limit=max(requested_limit * 10, 200),
    )

    exact_identifier = []
    weak_identifier = []
    fallback = []

    for card in rows or []:
        if parsed_set and not _v064c2_card_matches_parsed_set(card, parsed_set):
            continue

        if parsed_name and not _v064c3_card_name_matches_query(card, parsed_name):
            continue

        if parsed_number:
            level = _v064c3_identifier_match_level(card, parsed_number)
            if level >= 85:
                exact_identifier.append(card)
            elif level > 0:
                weak_identifier.append(card)
            else:
                continue
        else:
            fallback.append(card)

    if parsed_number:
        exact_identifier.sort(key=lambda c: _v064b_card_sort_tuple(
            c,
            query=parsed_name or name,
            number=parsed_number,
            set_slug_or_name=parsed_set,
        ))
        weak_identifier.sort(key=lambda c: _v064b_card_sort_tuple(
            c,
            query=parsed_name or name,
            number=parsed_number,
            set_slug_or_name=parsed_set,
        ))

        merged = exact_identifier + weak_identifier
    else:
        fallback.sort(key=lambda c: _v064b_card_sort_tuple(
            c,
            query=parsed_name or name,
            number=None,
            set_slug_or_name=parsed_set,
        ))
        merged = fallback

    for card in merged:
        card["_query_parse"] = {
            "set": parsed_set,
            "number": parsed_number,
            "variant": parsed.get("variant") or "",
        }

    return merged[:requested_limit]


# v0.6.4D vintage variant parsing
# Adds collector variant intent for:
# shadowless charizard, 1st edition charizard, 1st ed machamp,
# base set shadowless pikachu, unlimited base set charizard.

def _v064d_variant_from_query(query):
    q = _v064c_norm(query)
    tokens = q.split()

    if "shadowless" in tokens:
        return "shadowless"

    if "unlimited" in tokens:
        return "unlimited"

    if (
        "1st" in tokens
        or "1e" in tokens
        or ("first" in tokens and "edition" in tokens)
        or ("1st" in tokens and "ed" in tokens)
    ):
        return "first_edition"

    return ""


def _v064d_strip_variant_terms(query):
    tokens = _v064c_tokens(query)
    remove = {
        "shadowless",
        "unlimited",
        "1st",
        "1e",
        "first",
        "edition",
        "ed",
    }
    return " ".join(t for t in tokens if t not in remove).strip()


def _v064d_is_vintage_set(card):
    set_name = _v064c_norm(card.get("set_name"))
    set_slug = _v064c_norm(card.get("set_slug"))

    vintage = {
        "base",
        "base set",
        "jungle",
        "fossil",
        "team rocket",
        "gym heroes",
        "gym challenge",
        "neo genesis",
        "neo discovery",
        "neo revelation",
        "neo destiny",
    }

    return set_name in vintage or set_slug in vintage


def _v064d_variant_score(card, variant):
    if not variant:
        return 0

    set_name = _v064c_norm(card.get("set_name"))
    rarity = _v064c_norm(card.get("rarity"))
    card_name = _v064c_norm(card.get("card_name"))

    score = 0

    # Database may not have separate shadowless / 1st edition records yet.
    # For now, attach variant intent and favor Base-era cards.
    if variant in {"shadowless", "first_edition", "unlimited"}:
        if set_name == "base":
            score += 10000
        elif set_name in {"jungle", "fossil", "team rocket", "gym heroes", "gym challenge"}:
            score += 4000
        elif _v064d_is_vintage_set(card):
            score += 2500

    if variant == "first_edition":
        # Machamp is the classic special case users search as 1st Edition.
        if card_name == "machamp" and set_name == "base":
            score += 5000

    if variant == "shadowless":
        # Shadowless only applies to Base Set, not Base Set 2.
        if set_name == "base":
            score += 6000
        if "base set 2" in set_name:
            score -= 8000

    if variant == "unlimited":
        if set_name == "base":
            score += 3000

    return score


try:
    _v064d_previous_parse_query = _v064c_parse_query
except NameError:
    _v064d_previous_parse_query = None


def _v064c_parse_query(query):
    parsed = _v064d_previous_parse_query(query)
    variant = _v064d_variant_from_query(query)

    if variant:
        parsed["variant"] = variant

        stripped = _v064d_strip_variant_terms(query)
        reparsed = _v064d_previous_parse_query(stripped)

        if reparsed.get("name"):
            parsed["name"] = reparsed.get("name")
        if reparsed.get("set"):
            parsed["set"] = reparsed.get("set")
        if reparsed.get("number"):
            parsed["number"] = reparsed.get("number")

        parsed["variant_query"] = stripped

        # Rebuild attempts using cleaned query while preserving variant.
        attempts = []

        def add_attempt(name=None, number=None, set_name=None):
            attempt = {
                "name": name or None,
                "number": number or None,
                "set_slug_or_name": set_name or None,
            }
            if attempt not in attempts:
                attempts.append(attempt)

        name = parsed.get("name") or ""
        number = parsed.get("number") or ""
        set_name = parsed.get("set") or ""

        # Vintage variant searches should prefer Base if no set supplied.
        if variant in {"shadowless", "first_edition", "unlimited"} and not set_name:
            set_name = "base"
            parsed["set"] = "base"

        if name and number and set_name:
            add_attempt(name, number, set_name)
        if name and set_name:
            add_attempt(name, None, set_name)
        if name and number:
            add_attempt(name, number, None)
        if number and set_name:
            add_attempt(None, number, set_name)
        if number:
            add_attempt(None, number, None)
        if name:
            add_attempt(name, None, None)
        add_attempt(stripped, None, None)

        parsed["attempts"] = attempts

    return parsed


try:
    _v064d_previous_search_cards = search_cards
except NameError:
    _v064d_previous_search_cards = None


def search_cards(name=None, number=None, set_slug_or_name=None, limit=20):
    requested_limit = int(limit or 20)

    # If structured inputs are supplied, preserve prior behavior.
    if number or set_slug_or_name:
        return _v064d_previous_search_cards(
            name=name,
            number=number,
            set_slug_or_name=set_slug_or_name,
            limit=requested_limit,
        )

    parsed = _v064c_parse_query(name)
    variant = parsed.get("variant") or ""

    rows = _v064d_previous_search_cards(
        name=name,
        number=None,
        set_slug_or_name=None,
        limit=max(requested_limit * 8, 160),
    )

    filtered = []
    for card in rows or []:
        if variant:
            # Keep vintage candidates only for variant-specific searches.
            if not _v064d_is_vintage_set(card):
                continue

        card["_query_parse"] = {
            "set": parsed.get("set") or "",
            "number": parsed.get("number") or "",
            "variant": variant,
        }
        card["variant_hint"] = variant
        filtered.append(card)

    try:
        filtered.sort(key=lambda c: (
            -_v064d_variant_score(c, variant),
            _v064b_card_sort_tuple(
                c,
                query=parsed.get("name") or name,
                number=parsed.get("number"),
                set_slug_or_name=parsed.get("set"),
            )
        ))
    except Exception:
        pass

    return filtered[:requested_limit]


# v0.6.6 search ux query intelligence
# Collector-style query upgrades without changing UI:
# base charizard / charizard base
# 151 pikachu / pikachu 151
# reverse holo pikachu / holo dark charizard
# shadowless / first edition / unlimited hints remain compatible with previous parser patches.

def _v066_query_norm(value):
    import re
    return re.sub(r"[^a-z0-9/]+", " ", str(value or "").lower()).strip()


def _v066_strip_finish_terms(query):
    tokens = _v066_query_norm(query).split()
    finish_terms = {
        "reverse", "holo", "holofoil", "foil",
        "normal", "cosmos", "stamped", "stamp",
    }
    return " ".join(t for t in tokens if t not in finish_terms).strip()


def _v066_finish_hint(query):
    q = _v066_query_norm(query)
    if "reverse holo" in q or "reverse" in q:
        return "reverse_holo"
    if "cosmos" in q:
        return "cosmos_holo"
    if "holo" in q or "holofoil" in q:
        return "holo"
    if "normal" in q:
        return "normal"
    return ""


try:
    _v066_previous_parse_query = _v064c_parse_query
except NameError:
    _v066_previous_parse_query = None


def _v064c_parse_query(query):
    if _v066_previous_parse_query is None:
        return {
            "original": str(query or "").strip(),
            "name": str(query or "").strip(),
            "set": "",
            "number": "",
            "variant": "",
            "attempts": [{"name": str(query or "").strip(), "number": None, "set_slug_or_name": None}],
        }

    original = str(query or "").strip()
    q = _v066_query_norm(original)
    stripped = _v066_strip_finish_terms(original)

    parsed = _v066_previous_parse_query(stripped or original)

    finish_hint = _v066_finish_hint(original)
    if finish_hint:
        parsed["finish_hint"] = finish_hint
        if not parsed.get("variant"):
            parsed["variant"] = finish_hint

    # Standalone collector set aliases that earlier parser versions may miss.
    tokens = q.split()

    if "base" in tokens and not parsed.get("set"):
        parsed["set"] = "base"
        parsed["name"] = " ".join(t for t in tokens if t != "base").strip()

    if "151" in tokens and not parsed.get("set"):
        parsed["set"] = "151"
        parsed["name"] = " ".join(t for t in tokens if t != "151").strip()

    # Rebuild attempts when we added or corrected set/name.
    attempts = []

    def add_attempt(name=None, number=None, set_name=None):
        attempt = {
            "name": name or None,
            "number": number or None,
            "set_slug_or_name": set_name or None,
        }
        if attempt not in attempts:
            attempts.append(attempt)

    name = parsed.get("name") or ""
    number = parsed.get("number") or ""
    set_name = parsed.get("set") or ""

    if name and number and set_name:
        add_attempt(name, number, set_name)
    if name and set_name:
        add_attempt(name, None, set_name)
    if name and number:
        add_attempt(name, number, None)
    if number and set_name:
        add_attempt(None, number, set_name)
    if number:
        add_attempt(None, number, None)
    if name:
        add_attempt(name, None, None)
    add_attempt(stripped or original, None, None)

    parsed["attempts"] = attempts
    parsed["original"] = original

    return parsed


# v0.6.8 search cache upgrade
# Short-lived backend cache for repeated live-stream searches.
# No search behavior changes; only avoids recomputing identical queries.

import time as _v068_time

_V068_SEARCH_CACHE_TTL_SECONDS = 300
_V068_SEARCH_CACHE_MAX_ITEMS = 256
_v068_search_cache = {}

try:
    _v068_previous_search_cards = search_cards
except NameError:
    _v068_previous_search_cards = None


def _v068_search_cache_key(name=None, number=None, set_slug_or_name=None, limit=20):
    return (
        str(name or "").strip().lower(),
        str(number or "").strip().lower(),
        str(set_slug_or_name or "").strip().lower(),
        int(limit or 20),
    )


def _v068_cache_get(key):
    item = _v068_search_cache.get(key)
    if not item:
        return None

    created_at, value = item
    if _v068_time.time() - created_at > _V068_SEARCH_CACHE_TTL_SECONDS:
        _v068_search_cache.pop(key, None)
        return None

    # Return shallow copies so callers can safely add thumbnail/prices fields.
    return [dict(row) for row in value]


def _v068_cache_set(key, value):
    if len(_v068_search_cache) >= _V068_SEARCH_CACHE_MAX_ITEMS:
        oldest = sorted(_v068_search_cache.items(), key=lambda item: item[1][0])[:32]
        for old_key, _ in oldest:
            _v068_search_cache.pop(old_key, None)

    _v068_search_cache[key] = (_v068_time.time(), [dict(row) for row in (value or [])])


def clear_search_cache():
    _v068_search_cache.clear()


def search_cards(name=None, number=None, set_slug_or_name=None, limit=20):
    key = _v068_search_cache_key(name=name, number=number, set_slug_or_name=set_slug_or_name, limit=limit)

    cached = _v068_cache_get(key)
    if cached is not None:
        for row in cached:
            row["_search_cache_hit"] = True
        return cached

    rows = _v068_previous_search_cards(
        name=name,
        number=number,
        set_slug_or_name=set_slug_or_name,
        limit=limit,
    ) if _v068_previous_search_cards else []

    _v068_cache_set(key, rows)

    return rows


try:
    _v068_previous_write_catalog_status = write_catalog_status

    def write_catalog_status():
        clear_search_cache()
        return _v068_previous_write_catalog_status()
except NameError:
    pass


# v0.6.9C backend search index lite
# Speeds up low-level exact search by keeping lightweight card records in memory.
# Preserves all higher-level search/ranking wrappers.

from functools import lru_cache as _v069c_lru_cache

_V069C_CARD_FIELDS = (
    "putnam_card_id",
    "set_name",
    "set_slug",
    "set_code",
    "series",
    "card_name",
    "card_number",
    "set_total",
    "printed_number",
    "rarity",
    "lookup_key",
    "pokemontcg_id",
    "image_small_url",
    "image_large_url",
    "tcgplayer_url",
    "tcgplayer_product_id",
    "card_number_sort",
)


def _v069c_norm(value):
    import re
    return re.sub(r"[^a-z0-9/]+", " ", str(value or "").lower()).strip()


def _v069c_number_head(value):
    raw = str(value or "").strip().lower()
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    return raw.lstrip("0") or raw


@_v069c_lru_cache(maxsize=1)
def _v069c_all_cards():
    config = load_config()
    if not config.sqlite_path.exists():
        return tuple()

    con = sqlite3.connect(config.sqlite_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
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
              tcgplayer_product_id,
              card_number_sort
            from pokemon_cards
            where game = 'pokemon'
            order by set_name, card_number_sort, card_name
            """
        ).fetchall()

        cards = []
        for row in rows:
            card = row_to_dict(row)
            card["_v069c_name_norm"] = _v069c_norm(card.get("card_name"))
            card["_v069c_set_name_norm"] = _v069c_norm(card.get("set_name"))
            card["_v069c_set_slug_norm"] = _v069c_norm(card.get("set_slug"))
            card["_v069c_printed_norm"] = _v069c_norm(card.get("printed_number"))
            card["_v069c_card_number_norm"] = _v069c_norm(card.get("card_number"))
            card["_v069c_number_head"] = _v069c_number_head(card.get("printed_number") or card.get("card_number"))
            cards.append(card)

        return tuple(cards)
    finally:
        con.close()


try:
    _v069c_previous_search_cards_exact = _search_cards_exact
except NameError:
    _v069c_previous_search_cards_exact = None


def _v069c_public_card(card):
    return {k: v for k, v in card.items() if not k.startswith("_v069c_") and k != "card_number_sort"}


def _search_cards_exact(name=None, number=None, set_slug_or_name=None, limit=10):
    try:
        cards = _v069c_all_cards()
        if not cards:
            raise RuntimeError("empty in-memory card index")

        name_norm = _v069c_norm(name)
        set_norm = _v069c_norm(set_slug_or_name)
        number_raw = str(number or "").strip().lower()
        number_norm = _v069c_norm(number_raw)
        number_head = _v069c_number_head(number_raw)

        results = []

        for card in cards:
            if name_norm and name_norm not in card.get("_v069c_name_norm", ""):
                continue

            if set_norm:
                if set_norm != card.get("_v069c_set_slug_norm") and set_norm not in card.get("_v069c_set_name_norm", ""):
                    continue

            if number_norm:
                card_number = card.get("_v069c_card_number_norm", "")
                printed = card.get("_v069c_printed_norm", "")
                card_head = card.get("_v069c_number_head", "")

                if not (
                    number_norm == card_number
                    or number_norm == printed
                    or number_head == card_head
                    or printed.startswith(number_head + "/")
                ):
                    continue

            results.append(_v069c_public_card(card))

            if len(results) >= int(limit or 10):
                break

        return results

    except Exception:
        if _v069c_previous_search_cards_exact:
            return _v069c_previous_search_cards_exact(
                name=name,
                number=number,
                set_slug_or_name=set_slug_or_name,
                limit=limit,
            )
        return []


try:
    _v069c_previous_write_catalog_status = write_catalog_status

    def write_catalog_status():
        _v069c_all_cards.cache_clear()
        if "clear_search_cache" in globals():
            clear_search_cache()
        return _v069c_previous_write_catalog_status()
except NameError:
    pass


# v0.7.5 search index pro
# Faster indexed replacement for low-level _search_cards_exact.
# Preserves existing high-level query parser/ranking wrappers.

from functools import lru_cache as _v075_lru_cache
import re as _v075_re

def _v075_norm(value):
    return _v075_re.sub(r"[^a-z0-9/]+", " ", str(value or "").lower()).strip()

def _v075_tokens(value):
    return [t for t in _v075_norm(value).split() if t]

def _v075_num(value):
    raw = str(value or "").strip().lower()
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    return raw.lstrip("0") or raw

@_v075_lru_cache(maxsize=1)
def _v075_index():
    config = load_config()
    if not config.sqlite_path.exists():
        return {"cards": [], "name": {}, "number": {}, "set": {}}

    con = sqlite3.connect(config.sqlite_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("""
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
              tcgplayer_product_id,
              card_number_sort
            from pokemon_cards
            where game = 'pokemon'
            order by set_name, card_number_sort, card_name
        """).fetchall()
    finally:
        con.close()

    cards = []
    name_index = {}
    number_index = {}
    set_index = {}

    for idx, row in enumerate(rows):
        card = row_to_dict(row)
        name_norm = _v075_norm(card.get("card_name"))
        set_norm = _v075_norm(card.get("set_name"))
        slug_norm = _v075_norm(card.get("set_slug"))
        number_norm = _v075_num(card.get("card_number") or card.get("printed_number"))
        printed_head = _v075_num(card.get("printed_number"))

        card["_v075_name_norm"] = name_norm
        card["_v075_set_norm"] = set_norm
        card["_v075_slug_norm"] = slug_norm
        card["_v075_number_norm"] = number_norm
        card["_v075_printed_head"] = printed_head

        cards.append(card)

        for token in set(_v075_tokens(name_norm)):
            name_index.setdefault(token, set()).add(idx)

        for token in set(_v075_tokens(set_norm) + _v075_tokens(slug_norm)):
            set_index.setdefault(token, set()).add(idx)

        for token in {number_norm, printed_head}:
            if token:
                number_index.setdefault(token, set()).add(idx)

    return {
        "cards": cards,
        "name": name_index,
        "number": number_index,
        "set": set_index,
    }

try:
    _v075_previous_search_cards_exact = _search_cards_exact
except NameError:
    _v075_previous_search_cards_exact = None

def _v075_public(card):
    return {k: v for k, v in card.items() if not k.startswith("_v075_") and k != "card_number_sort"}

def _v075_intersection(groups):
    groups = [g for g in groups if g is not None]
    if not groups:
        return None
    result = set(groups[0])
    for g in groups[1:]:
        result &= set(g)
    return result

def _search_cards_exact(name=None, number=None, set_slug_or_name=None, limit=10):
    try:
        idx = _v075_index()
        cards = idx["cards"]
        if not cards:
            raise RuntimeError("empty search index")

        candidate_sets = []

        name_norm = _v075_norm(name)
        if name_norm:
            name_groups = []
            for token in _v075_tokens(name_norm):
                name_groups.append(idx["name"].get(token, set()))
            candidate_sets.append(_v075_intersection(name_groups) or set())

        set_norm = _v075_norm(set_slug_or_name)
        if set_norm:
            set_groups = []
            for token in _v075_tokens(set_norm):
                set_groups.append(idx["set"].get(token, set()))
            candidate_sets.append(_v075_intersection(set_groups) or set())

        number_norm = _v075_num(number)
        if number_norm:
            candidate_sets.append(idx["number"].get(number_norm, set()))

        if candidate_sets:
            candidate_ids = _v075_intersection(candidate_sets)
        else:
            candidate_ids = range(len(cards))

        results = []
        max_results = int(limit or 10)

        for i in candidate_ids:
            card = cards[i]

            if name_norm and name_norm not in card.get("_v075_name_norm", ""):
                continue

            if set_norm:
                set_text = card.get("_v075_set_norm", "")
                slug_text = card.get("_v075_slug_norm", "")
                if set_norm != slug_text and set_norm not in set_text and set_norm not in slug_text:
                    continue

            if number_norm:
                if number_norm not in {
                    card.get("_v075_number_norm", ""),
                    card.get("_v075_printed_head", ""),
                }:
                    continue

            results.append(_v075_public(card))
            if len(results) >= max_results:
                break

        return results

    except Exception:
        if _v075_previous_search_cards_exact:
            return _v075_previous_search_cards_exact(
                name=name,
                number=number,
                set_slug_or_name=set_slug_or_name,
                limit=limit,
            )
        return []

try:
    _v075_previous_write_catalog_status = write_catalog_status

    def write_catalog_status():
        _v075_index.cache_clear()
        if "clear_search_cache" in globals():
            clear_search_cache()
        return _v075_previous_write_catalog_status()
except NameError:
    pass

