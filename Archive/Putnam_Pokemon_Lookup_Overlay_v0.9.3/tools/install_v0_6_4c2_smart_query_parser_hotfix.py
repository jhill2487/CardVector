from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
CARD_CATALOG = ROOT / "backend" / "card_catalog.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

backup = archive / f"card_catalog_before_v0_6_4c2_{stamp}.py"
shutil.copy2(CARD_CATALOG, backup)

text = CARD_CATALOG.read_text(encoding="utf-8")

if "v0.6.4C2 smart query parser hotfix" not in text:
    patch = r'''

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
'''
    text = text.rstrip() + "\n" + patch + "\n"

CARD_CATALOG.write_text(text, encoding="utf-8")

print("Installed v0.6.4C2 Smart Query Parser Hotfix")
print(f"Patched: {CARD_CATALOG}")
print(f"Backup:  {backup}")