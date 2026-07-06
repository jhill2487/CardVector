from pathlib import Path

TARGET = Path("scanner_core_region_ocr.py")
BACKUP = Path("scanner_core_region_ocr_before_denominator_tiebreak_patch.py")

if not TARGET.exists():
    raise SystemExit(f"ERROR: {TARGET} not found. Run this from the PutnamCollectibles project folder.")

s = TARGET.read_text(encoding="utf-8")

old = '    if candidates:\n        top = candidates[0]\n        second = candidates[1]["score"] if len(candidates) > 1 else 0\n        top_sim = top.get("name_similarity", 0)\n        top_num_ok = _number_left(top.get("card_number", "")) == num_left\n        # Conservative: name must be quite close and number must agree.\n        if top_num_ok and top_sim >= 0.88 and (top["score"] - second >= 0.08 or len(candidates) == 1):\n            return ({\n                "status": "Auto Match",\n                "card_name": top.get("card_name", ""),\n                "set_name": top.get("set_name", ""),\n                "card_number": top.get("card_number", ""),\n                "confidence": min(0.99, top.get("score", 0)),\n                "reason": "Strict name+number agreement using known-good geometry crops",\n            }, candidates)\n'

new = '    if candidates:\n        exact = [\n            c for c in candidates\n            if c.get("name_similarity", 0) >= 0.99\n            and _number_left(c.get("card_number", "")) == num_left\n        ]\n\n        # If OCR read a denominator such as 036/086, use it as a tie-breaker.\n        denom = ""\n        m = re.search(r"/\\s*0*(\\d{1,3})", str(number or ""))\n        if m:\n            denom = m.group(1)\n\n        if len(exact) > 1 and denom:\n            exact_with_total = []\n            for c in exact:\n                total = str(\n                    c.get("set_total", "")\n                    or c.get("total_cards", "")\n                    or c.get("printed_total", "")\n                    or c.get("set_card_count", "")\n                    or ""\n                )\n                total_digits = re.sub(r"\\D", "", total).lstrip("0")\n                if total_digits == denom:\n                    exact_with_total.append(c)\n\n            if len(exact_with_total) == 1:\n                top = exact_with_total[0]\n                return ({\n                    "status": "Auto Match",\n                    "card_name": top.get("card_name", ""),\n                    "set_name": top.get("set_name", ""),\n                    "card_number": top.get("card_number", ""),\n                    "confidence": 0.99,\n                    "reason": f"Exact name+number match; denominator /{denom} resolved set tie",\n                }, candidates)\n\n        if len(exact) == 1:\n            top = exact[0]\n            return ({\n                "status": "Auto Match",\n                "card_name": top.get("card_name", ""),\n                "set_name": top.get("set_name", ""),\n                "card_number": top.get("card_number", ""),\n                "confidence": 0.99,\n                "reason": "Unique exact name+number match using known-good geometry crops",\n            }, candidates)\n\n        top = candidates[0]\n        second = candidates[1]["score"] if len(candidates) > 1 else 0\n        top_sim = top.get("name_similarity", 0)\n        top_num_ok = _number_left(top.get("card_number", "")) == num_left\n\n        # Conservative fallback: name must be quite close, number must agree, and lead must be clear.\n        if top_num_ok and top_sim >= 0.88 and (top["score"] - second >= 0.08 or len(candidates) == 1):\n            return ({\n                "status": "Auto Match",\n                "card_name": top.get("card_name", ""),\n                "set_name": top.get("set_name", ""),\n                "card_number": top.get("card_number", ""),\n                "confidence": min(0.99, top.get("score", 0)),\n                "reason": "Strict name+number agreement using known-good geometry crops",\n            }, candidates)\n'

if old not in s:
    if "denominator /{denom} resolved set tie" in s:
        print("Patch already appears to be installed. No changes made.")
        raise SystemExit(0)
    raise SystemExit(
        "ERROR: Patch target block not found. No changes made. "
        "Your scanner_core_region_ocr.py may have changed from the expected version."
    )

BACKUP.write_text(s, encoding="utf-8")
TARGET.write_text(s.replace(old, new), encoding="utf-8")

print("SUCCESS: Denominator tie-break patch installed.")
print(f"Backup created: {BACKUP}")
print("Changed file: scanner_core_region_ocr.py")
print("")
print("Next steps:")
print("1. Run: python verify_project_locks.py")
print("2. Restart Studio: Ctrl+C then python scanner_server.py")
print("3. Test IMG_7506 again.")
