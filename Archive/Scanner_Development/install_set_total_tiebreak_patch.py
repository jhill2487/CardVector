from pathlib import Path

TARGET = Path("scanner_core_region_ocr.py")
BACKUP = Path("scanner_core_region_ocr_before_set_total_tiebreak_patch.py")

if not TARGET.exists():
    raise SystemExit(f"ERROR: {TARGET} not found. Run this from the PutnamCollectibles project folder.")

s = TARGET.read_text(encoding="utf-8")

# This patch targets the current matcher block after the previous unique-exact patch.
old = '        if len(exact) == 1:\n            top = exact[0]\n            return ({\n                "status": "Auto Match",\n                "card_name": top.get("card_name", ""),\n                "set_name": top.get("set_name", ""),\n                "card_number": top.get("card_number", ""),\n                "confidence": 0.99,\n                "reason": "Unique exact name+number match using known-good geometry crops",\n            }, candidates)\n\n        top = candidates[0]\n'

new = '        # If there are multiple exact name+number matches, use the printed denominator\n        # from OCR (example: 036/086 -> 86) to resolve by database set_total.\n        denom = ""\n        m = re.search(r"/\\s*0*(\\d{1,3})", str(number or ""))\n        if m:\n            denom = m.group(1)\n\n        if len(exact) > 1 and denom:\n            exact_with_total = []\n            for c in exact:\n                total_raw = str(c.get("set_total", "") or "")\n                total_digits = re.sub(r"\\D", "", total_raw).lstrip("0")\n                if total_digits == denom:\n                    exact_with_total.append(c)\n\n            if len(exact_with_total) == 1:\n                top = exact_with_total[0]\n                return ({\n                    "status": "Auto Match",\n                    "card_name": top.get("card_name", ""),\n                    "set_name": top.get("set_name", ""),\n                    "card_number": top.get("card_number", ""),\n                    "confidence": 0.99,\n                    "reason": f"Exact name+number match; set_total {denom} resolved tie",\n                }, candidates)\n\n        if len(exact) == 1:\n            top = exact[0]\n            return ({\n                "status": "Auto Match",\n                "card_name": top.get("card_name", ""),\n                "set_name": top.get("set_name", ""),\n                "card_number": top.get("card_number", ""),\n                "confidence": 0.99,\n                "reason": "Unique exact name+number match using known-good geometry crops",\n            }, candidates)\n\n        top = candidates[0]\n'

if "set_total {denom} resolved tie" in s:
    print("Patch already appears to be installed. No changes made.")
    raise SystemExit(0)

if old not in s:
    raise SystemExit(
        "ERROR: Patch target block not found. No changes made. "
        "Your scanner_core_region_ocr.py may have changed from the expected version."
    )

BACKUP.write_text(s, encoding="utf-8")
TARGET.write_text(s.replace(old, new), encoding="utf-8")

print("SUCCESS: set_total denominator tie-break patch installed.")
print(f"Backup created: {BACKUP}")
print("Changed file: scanner_core_region_ocr.py")
print("")
print("Next steps:")
print("1. Run: python verify_project_locks.py")
print("2. Restart Studio: Ctrl+C then python scanner_server.py")
print("3. Test IMG_7506 again.")
print("")
print("Expected for IMG_7506:")
print("Auto Match: Woobat | White Flare | 36")
print("Reason: Exact name+number match; set_total 86 resolved tie")
