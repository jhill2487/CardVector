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
    shutil.copy2(p, archive / f"{p.stem}_before_v0_7_5_{stamp}{p.suffix}")

text = CATALOG.read_text(encoding="utf-8")

if "v0.7.5 search index pro" not in text:
    patch = r'''

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
'''
    text = text.rstrip() + "\n" + patch + "\n"

CATALOG.write_text(text, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
old_version = manifest.get("version", "0.0.0")
manifest["version"] = "0.7.5"
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Installed v0.7.5 Search Index Pro")
print(f"Extension version: {old_version} -> {manifest['version']}")
print(f"Backups saved in: {archive}")
print("Patched:")
print(" - backend/card_catalog.py")
print(" - extension/manifest.json")