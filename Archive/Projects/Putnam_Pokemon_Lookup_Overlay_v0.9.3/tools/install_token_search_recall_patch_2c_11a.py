from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
CATALOG = ROOT / "backend" / "card_catalog.py"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

if not CATALOG.exists():
    raise SystemExit(f"ERROR: Missing {CATALOG}")

text = CATALOG.read_text(encoding="utf-8")
(ARCHIVE / f"card_catalog_before_patch_2c_11a_{stamp}.py").write_text(text, encoding="utf-8")

if "Patch 2C.11A - Token Search Recall" in text:
    print("Patch 2C.11A already installed. No changes made.")
    raise SystemExit(0)

if "def search_cards(" not in text:
    raise SystemExit("ERROR: Could not find search_cards() in card_catalog.py. No changes written.")

# Rename the existing search_cards() implementation.
text = text.replace("def search_cards(", "def _search_cards_exact(", 1)

wrapper = r'''

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

'''

text = text.rstrip() + "\n" + wrapper + "\n"
CATALOG.write_text(text, encoding="utf-8")

print("Patch 2C.11A installed.")
print("Token recall added: searches like 'charizard ex' can now include Mega Charizard Y ex.")
print("Backup saved to:", ARCHIVE)