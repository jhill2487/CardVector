from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
CARD_CATALOG = ROOT / "backend" / "card_catalog.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

backup = archive / f"card_catalog_before_v0_6_4d_{stamp}.py"
shutil.copy2(CARD_CATALOG, backup)

text = CARD_CATALOG.read_text(encoding="utf-8")

if "v0.6.4D vintage variant parsing" not in text:
    patch = r'''

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
'''
    text = text.rstrip() + "\n" + patch + "\n"

CARD_CATALOG.write_text(text, encoding="utf-8")

print("Installed v0.6.4D Vintage Variant Parsing")
print(f"Patched: {CARD_CATALOG}")
print(f"Backup:  {backup}")