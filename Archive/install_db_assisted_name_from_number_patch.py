from pathlib import Path
import os
import stat

TARGET = Path("scanner_core_region_ocr.py")
BACKUP = Path("scanner_core_region_ocr_before_db_assisted_name_patch.py")

if not TARGET.exists():
    raise SystemExit("ERROR: scanner_core_region_ocr.py not found. Run this from the PutnamCollectibles project folder.")

s = TARGET.read_text(encoding="utf-8")

if "DB_ASSISTED_NAME_FROM_NUMBER_PATCH_V1" in s:
    print("DB-assisted name patch already appears to be installed. No changes made.")
    raise SystemExit(0)

try:
    os.chmod(TARGET, stat.S_IWRITE | stat.S_IREAD)
except Exception:
    pass

BACKUP.write_text(s, encoding="utf-8")

append = '\n# --- DB_ASSISTED_NAME_FROM_NUMBER_PATCH_V1 ---\n# Purpose:\n# If geometry/OCR found a strong special number such as GG15/GG70 but name OCR is fuzzy\n# such as "Solroc a", use the database rows matching that exact number to correct the\n# card name and safely auto-match only when evidence is strong.\n#\n# This patch intentionally does NOT change:\n# - known_good geometry\n# - scanner_studio.html layout\n# - scanner_server.py\n# - crop generation\n\n_previous_scan_image_before_db_assisted_name_patch = scan_image\n\ndef _db_assist_clean_num_v1(s):\n    import re\n    return re.sub(r"[^A-Z0-9/]", "", str(s or "").upper())\n\ndef _db_assist_norm_name_v1(s):\n    import re\n    s = str(s or "").lower().replace("Ã©", "e")\n    s = re.sub(r"[^a-z0-9\' ]", " ", s)\n    return re.sub(r"\\s+", " ", s).strip()\n\ndef _db_assist_load_rows_v1(sqlite_path):\n    import sqlite3\n    from pathlib import Path\n\n    p = Path(sqlite_path)\n    if not p.exists():\n        return []\n\n    con = sqlite3.connect(str(p))\n    con.row_factory = sqlite3.Row\n    cur = con.cursor()\n    rows = [dict(r) for r in cur.execute("select * from pokemon_cards").fetchall()]\n    con.close()\n    return rows\n\ndef _db_assist_match_from_number_v1(rows, ocr_name, ocr_number):\n    from difflib import SequenceMatcher\n\n    num_full = _db_assist_clean_num_v1(ocr_number)\n    if not num_full:\n        return None, []\n\n    num_left = num_full.split("/")[0]\n    name_n = _db_assist_norm_name_v1(ocr_name)\n\n    exact_number_rows = []\n    for r in rows:\n        db_card_number = _db_assist_clean_num_v1(r.get("card_number", ""))\n        db_printed = _db_assist_clean_num_v1(r.get("printed_number", ""))\n\n        number_match = (\n            db_card_number == num_full\n            or db_printed == num_full\n            or (num_left and db_card_number == num_left)\n            or (num_left and db_printed == num_left)\n        )\n\n        if number_match:\n            db_name = r.get("card_name", "")\n            sim = SequenceMatcher(None, name_n, _db_assist_norm_name_v1(db_name)).ratio() if name_n and db_name else 0.0\n            item = dict(r)\n            item["score"] = round(0.80 + (0.20 * sim), 3)\n            item["name_similarity"] = round(sim, 3)\n            item["number_evidence"] = num_full\n            exact_number_rows.append(item)\n\n    exact_number_rows.sort(key=lambda x: x.get("score", 0), reverse=True)\n\n    if not exact_number_rows:\n        return None, []\n\n    top = exact_number_rows[0]\n    second_score = exact_number_rows[1]["score"] if len(exact_number_rows) > 1 else 0\n    top_sim = top.get("name_similarity", 0)\n\n    unique_number = len(exact_number_rows) == 1\n    clear_lead = (top.get("score", 0) - second_score) >= 0.08\n\n    if (unique_number and top_sim >= 0.55) or (top_sim >= 0.78 and clear_lead):\n        return {\n            "status": "Auto Match",\n            "card_name": top.get("card_name", ""),\n            "set_name": top.get("set_name", ""),\n            "card_number": top.get("card_number", ""),\n            "confidence": 0.99 if unique_number else min(0.98, top.get("score", 0)),\n            "reason": f"Database-assisted name correction from exact number {num_full}; OCR name was \'{ocr_name}\'",\n        }, exact_number_rows[:10]\n\n    return None, exact_number_rows[:10]\n\ndef scan_image(image_path, config, output_dir):\n    result = _previous_scan_image_before_db_assisted_name_patch(image_path, config, output_dir)\n\n    try:\n        match_status = ((result.get("match") or {}).get("status") or "")\n        if match_status == "Auto Match":\n            return result\n\n        ocr = result.get("ocr") or {}\n        ocr_name = ocr.get("name", "")\n        ocr_number = ocr.get("number", "") or ocr.get("bottom_id", "")\n\n        clean_num = _db_assist_clean_num_v1(ocr_number)\n        if not clean_num:\n            return result\n\n        special_prefixes = ("GG", "TG", "SVP", "SWSH", "SM", "XY", "BW")\n        looks_special = clean_num.startswith(special_prefixes)\n        has_slash_number = "/" in clean_num and any(ch.isdigit() for ch in clean_num)\n\n        if not (looks_special or has_slash_number):\n            return result\n\n        from pathlib import Path\n        root = Path(__file__).resolve().parent\n        sqlite_path = (config or {}).get("sqlite_path", "database/putnam_pokemon_cloud_ready.sqlite")\n        rows = _db_assist_load_rows_v1(root / sqlite_path)\n\n        match, candidates = _db_assist_match_from_number_v1(rows, ocr_name, clean_num)\n        if candidates:\n            result["candidates"] = candidates\n\n        if match:\n            result["match"] = match\n            result["status"] = match.get("status", "Auto Match")\n            result.setdefault("ocr", {})\n            result["ocr"]["database_corrected_name"] = match.get("card_name", "")\n\n        return result\n\n    except Exception as exc:\n        result.setdefault("debug", {})\n        result["debug"]["db_assisted_name_patch_error"] = str(exc)\n        return result\n'

TARGET.write_text(s + "\n" + append, encoding="utf-8")

print("SUCCESS: DB-assisted name correction patch installed.")
print(f"Backup created: {BACKUP}")
print("Changed file: scanner_core_region_ocr.py")
print("")
print("What changed:")
print("- Adds a fallback after the existing scan result")
print("- If OCR number is strong, such as GG15/GG70, database rows with that exact number are checked")
print("- Fuzzy name OCR like 'Solroc a' can be corrected to the database card name")
print("- Auto Match only happens when exact number evidence plus name similarity is strong")
print("")
print("Files intentionally NOT changed:")
print("- known_good/template_region_warp_matcher_v0_7.py")
print("- known_good/IMG_7505.json")
print("- known_good/IMG_7507.json")
print("- scanner_studio.html")
print("- scanner_server.py")
print("")
print("Next steps:")
print("1. Run: python verify_project_locks.py")
print("2. Restart Studio if running")
print("3. Re-run: python run_solrock_gg15_labeled_test.py")
