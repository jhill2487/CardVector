from pathlib import Path
from datetime import datetime
import re

TARGET = Path("card_catalog.py")

if not TARGET.exists():
    print("ERROR: card_catalog.py not found.")
    print("Run this from:")
    print(r"C:\Users\JaredHill\OneDrive\PutnamCollectibles\Pokemon_Live_Price_Lookup\backend")
    raise SystemExit(1)

src = TARGET.read_text(encoding="utf-8")
backup = Path(f"card_catalog_before_search_ranking_patch_{datetime.now():%Y%m%d_%H%M%S}.py")
backup.write_text(src, encoding="utf-8")

if "import re" not in src:
    src = src.replace("import json\n", "import json\nimport re\n", 1)

new_func = 'def search_cards(\n    name: str | None = None,\n    number: str | None = None,\n    set_slug_or_name: str | None = None,\n    limit: int = 10,\n) -> list[dict[str, Any]]:\n    """Search Pokemon cards with exact set/number/name matches ranked first.\n\n    This function intentionally keeps the same public signature and return shape.\n    Patch scope: search ranking only.\n    """\n    config = load_config()\n    if not config.sqlite_path.exists():\n        return []\n\n    def norm_text(value: object) -> str:\n        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()\n\n    def norm_slug(value: object) -> str:\n        return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")\n\n    def norm_number(value: object) -> str:\n        text = str(value or "").strip().lower()\n        if "/" in text:\n            text = text.split("/", 1)[0]\n        return text.lstrip("0") or text\n\n    def sort_number(value: object) -> tuple[int, str]:\n        text = str(value or "").strip().lower()\n        match = re.search(r"\\d+", text)\n        if match:\n            return (int(match.group(0)), text)\n        return (999999, text)\n\n    clauses = ["game = \'pokemon\'"]\n    params: list[Any] = []\n\n    clean_name = str(name or "").strip()\n    clean_number = str(number or "").strip()\n    clean_set = str(set_slug_or_name or "").strip()\n\n    if clean_name:\n        clauses.append("lower(card_name) like lower(?)")\n        params.append(f"%{clean_name}%")\n\n    if clean_number:\n        normalized = clean_number.lstrip("0") or clean_number\n        clauses.append("(card_number = ? or card_number = ? or printed_number like ?)")\n        params.extend([clean_number, normalized, f"{normalized}/%"])\n\n    if clean_set:\n        clauses.append("(lower(set_slug) = lower(?) or lower(set_name) like lower(?))")\n        params.extend([clean_set, f"%{clean_set}%"])\n\n    query_limit = max(limit * 8, 80)\n\n    sql = f"""\n        select\n          putnam_card_id,\n          set_name,\n          set_slug,\n          set_code,\n          series,\n          card_name,\n          card_number,\n          set_total,\n          printed_number,\n          rarity,\n          lookup_key,\n          pokemontcg_id,\n          image_small_url,\n          image_large_url,\n          tcgplayer_url,\n          tcgplayer_product_id,\n          card_number_sort\n        from pokemon_cards\n        where {\' and \'.join(clauses)}\n        order by set_name, card_number_sort, card_name\n        limit ?\n    """\n    params.append(query_limit)\n\n    con = sqlite3.connect(config.sqlite_path)\n    con.row_factory = sqlite3.Row\n    try:\n        rows = [row_to_dict(row) for row in con.execute(sql, params).fetchall()]\n    finally:\n        con.close()\n\n    name_q = norm_text(clean_name)\n    number_q = norm_number(clean_number)\n    set_q_text = norm_text(clean_set)\n    set_q_slug = norm_slug(clean_set)\n\n    def score(row: dict[str, Any]) -> tuple[int, tuple[int, str], str, str]:\n        points = 0\n\n        card_name = norm_text(row.get("card_name"))\n        card_number = norm_number(row.get("card_number"))\n        printed_number = norm_number(row.get("printed_number"))\n        set_name = norm_text(row.get("set_name"))\n        set_slug = norm_slug(row.get("set_slug"))\n\n        if name_q:\n            if card_name == name_q:\n                points += 300\n            elif card_name.startswith(name_q):\n                points += 220\n            elif name_q in card_name:\n                points += 120\n\n        if number_q:\n            if card_number == number_q:\n                points += 420\n            elif printed_number == number_q:\n                points += 380\n\n        if set_q_text or set_q_slug:\n            if set_slug == set_q_slug:\n                points += 520\n            elif set_name == set_q_text:\n                points += 500\n            elif set_name.startswith(set_q_text):\n                points += 320\n            elif set_q_text and set_q_text in set_name:\n                points += 180\n\n            if set_q_slug == "base":\n                if set_slug == "base" or set_name == "base":\n                    points += 250\n                if set_slug == "base-set-2" or set_name == "base set 2":\n                    points -= 300\n\n        return (\n            -points,\n            sort_number(row.get("card_number_sort") or row.get("card_number")),\n            str(row.get("set_name") or ""),\n            str(row.get("card_name") or ""),\n        )\n\n    rows.sort(key=score)\n\n    for row in rows:\n        row.pop("card_number_sort", None)\n\n    return rows[:limit]\n'

pattern = re.compile(
    r"def search_cards\(\n"
    r".*?\n(?=def get_card_by_id\()",
    re.S,
)

if not pattern.search(src):
    print("ERROR: Could not locate search_cards() boundary. No changes written.")
    raise SystemExit(1)

src = pattern.sub(lambda m: new_func + "\n\n", src)
TARGET.write_text(src, encoding="utf-8")

print("Search ranking patch installed successfully.")
print("Patched only:", TARGET)
print("Backup created:", backup)
print("")
print("Recommended tests:")
print(r"""python -c "import card_catalog; [print(c['set_name'], c['card_name'], c['printed_number']) for c in card_catalog.search_cards('pikachu', set_slug_or_name='base', limit=10)]" """)
print(r"""python -c "import card_catalog; [print(c['set_name'], c['card_name'], c['printed_number']) for c in card_catalog.search_cards('pikachu', number='58', set_slug_or_name='base', limit=10)]" """)

