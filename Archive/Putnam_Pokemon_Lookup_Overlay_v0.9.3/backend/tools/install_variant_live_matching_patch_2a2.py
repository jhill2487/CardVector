
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def find_backend_root() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here,
        here.parent,
        Path.cwd(),
        Path.cwd().parent,
    ]
    for candidate in candidates:
        if (candidate / "price_cache.py").exists() and (candidate / "card_catalog.py").exists():
            return candidate
    print("ERROR: Could not find backend folder containing price_cache.py and card_catalog.py.")
    print("Save this installer in:")
    print(r"C:\Users\JaredHill\OneDrive\PutnamCollectibles\Pokemon_Live_Price_Lookup\backend\tools")
    raise SystemExit(1)


BACKEND = find_backend_root()
ARCHIVE = BACKEND / "archive_old_versions"
PRICE_CACHE = BACKEND / "price_cache.py"
CARD_CATALOG = BACKEND / "card_catalog.py"

ARCHIVE.mkdir(exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

price_src = PRICE_CACHE.read_text(encoding="utf-8")
card_src = CARD_CATALOG.read_text(encoding="utf-8")

(ARCHIVE / f"price_cache_before_variant_live_matching_2a2_patch_{stamp}.py").write_text(price_src, encoding="utf-8")
(ARCHIVE / f"card_catalog_before_variant_live_matching_2a2_patch_{stamp}.py").write_text(card_src, encoding="utf-8")


helper_func = '''
    def variant_match_score(card: dict[str, Any], product: dict[str, Any]) -> int:
        card_name = norm_text(card.get("card_name"))
        card_number = clean_number(card.get("card_number") or card.get("printed_number"))
        card_set = norm_text(card.get("set_name"))
        card_set_aliases = set_aliases(card.get("set_name"))

        product_name = norm_text(product.get("product_name") or product.get("name"))
        product_set = norm_text(product.get("set_name"))
        product_clean = clean_number(product.get("clean_number") or product.get("card_number"))
        product_finish = norm_text(product.get("finish"))

        combined = " ".join(part for part in [product_set, product_name, product_finish] if part)

        score = 0

        if card_number and product_clean == card_number:
            score += 500

        if product_set in card_set_aliases:
            score += 450
        elif any(alias and alias in product_set for alias in card_set_aliases):
            score += 250
        elif any(product_set and product_set in alias for alias in card_set_aliases):
            score += 200

        if card_name and product_name == card_name:
            score += 250
        elif card_name and card_name in product_name:
            score += 175
        elif product_name and product_name in card_name:
            score += 125

        card_wants_shadowless = "shadowless" in card_name or "shadowless" in card_set
        card_wants_red_cheeks = "red cheeks" in card_name
        card_wants_base_2 = card_set in {"base set 2", "base 2"}

        if card_set == "base":
            if product_set == "base set":
                score += 300
            if "base set shadowless" in product_set and not card_wants_shadowless:
                score -= 550
            if "red cheeks" in product_name and not card_wants_red_cheeks:
                score -= 550
            if product_set == "base set 2" and not card_wants_base_2:
                score -= 650

        variant_terms = [
            "shadowless",
            "red cheeks",
            "1st edition",
            "first edition",
            "reverse holo",
            "reverse holofoil",
            "holo",
            "holofoil",
            "cosmos holo",
            "cracked ice",
            "staff",
            "stamped",
        ]

        for term in variant_terms:
            card_has = term in card_name or term in card_set
            product_has = term in combined

            if card_has and product_has:
                score += 120
            elif product_has and not card_has:
                score -= 160

        return score

'''

if "def variant_match_score(" not in price_src:
    marker = '''    def set_aliases(set_name: object) -> set[str]:
        slug = norm_text(set_name)
        aliases = {slug}
        manual = {
            "base": {"base set"},
            "base set": {"base"},
            "151": {"sv scarlet violet 151", "scarlet violet 151", "sv 151"},
            "crown zenith galarian gallery": {"swsh crown zenith galarian gallery"},
        }
        aliases.update(manual.get(slug, set()))
        return {a for a in aliases if a}

'''
    if marker not in price_src:
        print("ERROR: Could not find set_aliases block in price_cache.py. No changes written.")
        raise SystemExit(1)
    price_src = price_src.replace(marker, marker + helper_func, 1)


old_scored_block = '''            scored: list[tuple[int, str]] = []
            for row in candidates:
                product_name = norm_text(row["product_name"])
                product_set = norm_text(row["set_name"])
                product_clean = clean_number(row["clean_number"] or row["card_number"])

                score = 0
                if card_name and card_name in product_name:
                    score += 40
                elif product_name and product_name in card_name:
                    score += 25

                if card_number and product_clean == card_number:
                    score += 35

                if product_set in set_names:
                    score += 35
                elif any(alias and alias in product_set for alias in set_names):
                    score += 25
                elif any(product_set and product_set in alias for alias in set_names):
                    score += 20

                if norm_text(card.get("set_name")) == "base" and "base set" in product_set:
                    score += 20

                if score >= 70:
                    scored.append((score, str(row["product_id"])))

            product_ids = [pid for _, pid in sorted(scored, reverse=True)[:12]]
'''

new_scored_block = '''            scored: list[tuple[int, str]] = []
            for row in candidates:
                product = dict(row)
                score = variant_match_score(card, product)

                if score >= 500:
                    scored.append((score, str(row["product_id"])))

            product_ids = [pid for _, pid in sorted(scored, key=lambda item: item[0], reverse=True)[:12]]
'''

if old_scored_block in price_src:
    price_src = price_src.replace(old_scored_block, new_scored_block, 1)
elif "variant_match_score(card, product)" not in price_src:
    print("ERROR: Could not find fallback scoring block in price_cache.py. No changes written.")
    raise SystemExit(1)


if "variant_match_rank" not in price_src:
    old_variants_point = '''    variants = list(grouped.values())

    # Patch 2A: enrich cached TCGTracking variants with live TCGplayer listing prices.
'''
    new_variants_point = '''    variants = list(grouped.values())

    for variant in variants:
        variant["variant_match_rank"] = variant_match_score(card, variant)

    variants.sort(
        key=lambda variant: (
            -int(variant.get("variant_match_rank") or 0),
            str(variant.get("set_name") or ""),
            str(variant.get("product_name") or ""),
        )
    )

    # Patch 2A: enrich cached TCGTracking variants with live TCGplayer listing prices.
'''
    if old_variants_point not in price_src:
        print("ERROR: Could not find variants creation point in price_cache.py. No changes written.")
        raise SystemExit(1)
    price_src = price_src.replace(old_variants_point, new_variants_point, 1)


PRICE_CACHE.write_text(price_src, encoding="utf-8")

print("Patch 2A.2 installed successfully.")
print("Patch name: Patch_2A_2_Improve_Variant_Live_Matching")
print("Backend:", BACKEND)
print("Patched:", PRICE_CACHE)
print("Backed up:", CARD_CATALOG, "(backup only; not modified)")
print("Backup folder:", ARCHIVE)
print("")
print("Test variant ranking:")
print(r'''& "C:\Users\JaredHill\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "import price_cache; p=price_cache.latest_prices_for_card('pkm-base-58-102-92e4a6a893'); [print(v.get('variant_match_rank'), v['product_id'], v['set_name'], v['product_name'], v.get('live_price_source'), v['conditions'].get('NM'), v['conditions'].get('LP')) for v in p['variants']]"''')
