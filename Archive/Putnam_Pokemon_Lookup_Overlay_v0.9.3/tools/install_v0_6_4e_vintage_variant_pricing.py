from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
PRICE_CACHE = ROOT / "backend" / "price_cache.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive = ROOT / "archive_old_versions"
archive.mkdir(exist_ok=True)

backup = archive / f"price_cache_before_v0_6_4e_{stamp}.py"
shutil.copy2(PRICE_CACHE, backup)

text = PRICE_CACHE.read_text(encoding="utf-8")

if "v0.6.4E vintage variant pricing" not in text:
    patch = r'''

# v0.6.4E vintage variant pricing
# Adds Base-era vintage variant metadata to price payloads.
# This prepares the UI to show Unlimited / Shadowless / 1st Edition price sections.

def _v064e_norm(value):
    import re
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _v064e_is_base_set_card(card):
    return _v064e_norm(card.get("set_name")) == "base"


def _v064e_variant_label(value):
    value = str(value or "").strip().lower()
    labels = {
        "unlimited": "Unlimited",
        "shadowless": "Shadowless",
        "first_edition": "1st Edition",
        "1st_edition": "1st Edition",
        "1st edition": "1st Edition",
    }
    return labels.get(value, value.replace("_", " ").title())


def _v064e_vintage_query(card, variant):
    name = str(card.get("card_name") or "").strip()
    set_name = str(card.get("set_name") or "").strip()
    printed = str(card.get("printed_number") or card.get("card_number") or "").strip()
    label = _v064e_variant_label(variant)

    parts = [name, set_name, printed, label]
    return " ".join(p for p in parts if p).strip()


def _v064e_add_vintage_variants(prices, card):
    if not prices or not isinstance(prices, dict):
        return prices

    if not _v064e_is_base_set_card(card):
        return prices

    variant_hint = str(card.get("variant_hint") or "").strip()

    vintage_variants = [
        {
            "key": "unlimited",
            "label": "Unlimited",
            "search_hint": _v064e_vintage_query(card, "unlimited"),
            "selected": variant_hint in ("", "unlimited"),
        },
        {
            "key": "shadowless",
            "label": "Shadowless",
            "search_hint": _v064e_vintage_query(card, "shadowless"),
            "selected": variant_hint == "shadowless",
        },
        {
            "key": "first_edition",
            "label": "1st Edition",
            "search_hint": _v064e_vintage_query(card, "first_edition"),
            "selected": variant_hint in ("first_edition", "1st_edition", "1st edition"),
        },
    ]

    prices["vintage_variants"] = vintage_variants
    prices["vintage_variant_hint"] = variant_hint
    prices["vintage_variant_note"] = (
        "Base Set variant pricing differs by Unlimited, Shadowless, and 1st Edition. "
        "Use these search hints to compare variant-specific TCGplayer listings."
    )

    # Also annotate each existing price variant with vintage context.
    for variant in prices.get("variants", []) or []:
        if isinstance(variant, dict):
            variant["vintage_variant_hint"] = variant_hint
            variant["vintage_variant_options"] = vintage_variants

    return prices


try:
    _v064e_previous_latest_prices_for_card = latest_prices_for_card
except NameError:
    _v064e_previous_latest_prices_for_card = None


def latest_prices_for_card(putnam_card_id: str):
    prices = _v064e_previous_latest_prices_for_card(putnam_card_id)

    try:
        from card_catalog import get_card_by_id
        card = get_card_by_id(putnam_card_id)
    except Exception:
        card = None

    if card:
        return _v064e_add_vintage_variants(prices, card)

    return prices
'''
    text = text.rstrip() + "\n" + patch + "\n"

PRICE_CACHE.write_text(text, encoding="utf-8")

print("Installed v0.6.4E Vintage Variant Pricing Metadata")
print(f"Patched: {PRICE_CACHE}")
print(f"Backup:  {backup}")