from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
CARD_CATALOG = ROOT / "backend" / "card_catalog.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

backup = archive / f"card_catalog_before_v0_6_4c_{stamp}.py"
shutil.copy2(CARD_CATALOG, backup)

text = CARD_CATALOG.read_text(encoding="utf-8")

if "v0.6.4C smart query parser" not in text:
    patch = r'''

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
'''

    text = text.rstrip() + "\n" + patch + "\n"

CARD_CATALOG.write_text(text, encoding="utf-8")

print("Installed v0.6.4C Smart Query Parser")
print(f"Patched: {CARD_CATALOG}")
print(f"Backup:  {backup}")