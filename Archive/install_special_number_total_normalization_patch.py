from pathlib import Path
import os
import stat

TARGET = Path("scanner_core_region_ocr.py")
BACKUP = Path("scanner_core_region_ocr_before_special_number_total_norm_patch.py")

if not TARGET.exists():
    raise SystemExit("ERROR: scanner_core_region_ocr.py not found. Run this from the PutnamCollectibles project folder.")

s = TARGET.read_text(encoding="utf-8")

if "SPECIAL_NUMBER_TOTAL_NORMALIZATION_PATCH_V1" in s:
    print("Special-number total normalization patch already appears to be installed. No changes made.")
    raise SystemExit(0)

required = ["_db_assist_clean_num_v1", "_db_assist_match_from_number_v1"]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit("ERROR: Required DB-assisted helpers not found: " + ", ".join(missing))

try:
    os.chmod(TARGET, stat.S_IWRITE | stat.S_IREAD)
except Exception:
    pass

BACKUP.write_text(s, encoding="utf-8")

append = '\n# --- SPECIAL_NUMBER_TOTAL_NORMALIZATION_PATCH_V1 ---\n# Purpose:\n# Treat special numbering forms as equivalent during DB-assisted matching:\n#   TG01/TG30 == TG01/30\n#   GG15/GG70 == GG15/70\n#\n# This only overrides the DB-assisted number cleaning/matching helpers.\n# It does not change geometry, crops, Studio HTML, scanner_server, or database files.\n\n_previous_db_assist_clean_num_before_total_norm_patch = _db_assist_clean_num_v1\n_previous_db_assist_match_from_number_before_total_norm_patch = _db_assist_match_from_number_v1\n\ndef _db_assist_clean_num_v1(s):\n    import re\n    raw = _previous_db_assist_clean_num_before_total_norm_patch(s)\n    raw = raw.upper()\n\n    # Normalize OCR/database equivalent forms:\n    # TG01/TG30 -> TG01/30\n    # GG15/GG70 -> GG15/70\n    raw = re.sub(r"^(TG\\d{1,2})/TG(\\d{1,2})$", r"\\1/\\2", raw)\n    raw = re.sub(r"^(GG\\d{1,2})/GG(\\d{1,2})$", r"\\1/\\2", raw)\n\n    return raw\n\ndef _db_assist_num_equivalents_v1(s):\n    import re\n    base = _db_assist_clean_num_v1(s)\n    vals = {base}\n    m = re.match(r"^(TG\\d{1,2})/(\\d{1,2})$", base)\n    if m:\n        vals.add(f"{m.group(1)}/TG{m.group(2)}")\n        vals.add(m.group(1))\n    m = re.match(r"^(GG\\d{1,2})/(\\d{1,2})$", base)\n    if m:\n        vals.add(f"{m.group(1)}/GG{m.group(2)}")\n        vals.add(m.group(1))\n    if "/" in base:\n        vals.add(base.split("/")[0])\n    return vals\n\ndef _db_assist_match_from_number_v1(rows, ocr_name, ocr_number):\n    from difflib import SequenceMatcher\n\n    num_full = _db_assist_clean_num_v1(ocr_number)\n    if not num_full:\n        return None, []\n\n    wanted_nums = _db_assist_num_equivalents_v1(num_full)\n    name_n = _db_assist_norm_name_v1(ocr_name)\n\n    exact_number_rows = []\n    for r in rows:\n        db_card_number = _db_assist_clean_num_v1(r.get("card_number", ""))\n        db_printed = _db_assist_clean_num_v1(r.get("printed_number", ""))\n\n        db_vals = set()\n        db_vals.update(_db_assist_num_equivalents_v1(db_card_number))\n        db_vals.update(_db_assist_num_equivalents_v1(db_printed))\n\n        number_match = bool(wanted_nums.intersection(db_vals))\n\n        if number_match:\n            db_name = r.get("card_name", "")\n            sim = SequenceMatcher(None, name_n, _db_assist_norm_name_v1(db_name)).ratio() if name_n and db_name else 0.0\n            item = dict(r)\n            item["score"] = round(0.80 + (0.20 * sim), 3)\n            item["name_similarity"] = round(sim, 3)\n            item["number_evidence"] = num_full\n            item["number_equivalents"] = sorted(wanted_nums)\n            exact_number_rows.append(item)\n\n    exact_number_rows.sort(key=lambda x: x.get("score", 0), reverse=True)\n\n    if not exact_number_rows:\n        return None, []\n\n    top = exact_number_rows[0]\n    second_score = exact_number_rows[1]["score"] if len(exact_number_rows) > 1 else 0\n    top_sim = top.get("name_similarity", 0)\n\n    unique_number = len(exact_number_rows) == 1\n    clear_lead = (top.get("score", 0) - second_score) >= 0.08\n\n    if (unique_number and top_sim >= 0.50) or (top_sim >= 0.76 and clear_lead):\n        return {\n            "status": "Auto Match",\n            "card_name": top.get("card_name", ""),\n            "set_name": top.get("set_name", ""),\n            "card_number": top.get("card_number", ""),\n            "confidence": 0.99 if unique_number else min(0.98, top.get("score", 0)),\n            "reason": f"Database-assisted special-number match from {num_full}; OCR name was \'{ocr_name}\'",\n        }, exact_number_rows[:10]\n\n    return None, exact_number_rows[:10]\n'

TARGET.write_text(s + "\n" + append, encoding="utf-8")

print("SUCCESS: Special-number total normalization patch installed.")
print(f"Backup created: {BACKUP}")
print("Changed file: scanner_core_region_ocr.py")
print("")
print("What changed:")
print("- TG01/TG30 now matches database printed_number TG01/30")
print("- GG15/GG70 now matches database printed_number GG15/70")
print("- Also compares left-side forms such as TG01 and GG15")
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
print("2. Re-run: python run_flareon_tg01_labeled_test.py")
