from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
CARD_CATALOG = ROOT / "backend" / "card_catalog.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

backup = archive / f"card_catalog_before_v0_6_4c3_{stamp}.py"
shutil.copy2(CARD_CATALOG, backup)

text = CARD_CATALOG.read_text(encoding="utf-8")

if "v0.6.4C3 exact identifier resolution" not in text:
    patch = r'''

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
'''
    text = text.rstrip() + "\n" + patch + "\n"

CARD_CATALOG.write_text(text, encoding="utf-8")

print("Installed v0.6.4C3 Exact Identifier Resolution")
print(f"Patched: {CARD_CATALOG}")
print(f"Backup:  {backup}")