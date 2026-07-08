from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backend" / "card_catalog.py"
MANIFEST = ROOT / "extension" / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [CATALOG, MANIFEST]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_9c_{stamp}{p.suffix}")

text = CATALOG.read_text(encoding="utf-8")

if "v0.6.9C backend search index lite" not in text:
    patch = r'''

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
'''
    text = text.rstrip() + "\n" + patch + "\n"

CATALOG.write_text(text, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.6.9.2"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.6.9C Backend Search Index Lite")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - backend/card_catalog.py")
print(" - extension/manifest.json")
print("Speed upgrade:")
print(" - _search_cards_exact now uses in-memory card records with SQLite fallback")