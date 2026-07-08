from pathlib import Path
import shutil
import datetime
import re

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
EXT = ROOT / "extension"

card_catalog = BACKEND / "card_catalog.py"
manifest = EXT / "manifest.json"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

for p in [card_catalog, manifest]:
    shutil.copy2(p, archive / f"{p.stem}_before_v0_6_4b_{stamp}{p.suffix}")

text = card_catalog.read_text(encoding="utf-8")

if "v0.6.4B relevance/image coverage" not in text:
    patch = r'''

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
'''
    text = text.rstrip() + "\n" + patch + "\n"

card_catalog.write_text(text, encoding="utf-8")

mj = manifest.read_text(encoding="utf-8")
mj = mj.replace('"version": "0.6.4"', '"version": "0.6.4"')
manifest.write_text(mj, encoding="utf-8")

print("Installed v0.6.4B Search Relevance + Image Coverage")
print(f"Backups saved in: {archive}")
print("Files patched:")
print(" - backend/card_catalog.py")
print(" - extension/manifest.json")