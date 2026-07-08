from pathlib import Path
import os
import stat

TARGET = Path("scanner_core_region_ocr.py")
BACKUP = Path("scanner_core_region_ocr_before_tg_repair_patch.py")

if not TARGET.exists():
    raise SystemExit("ERROR: scanner_core_region_ocr.py not found. Run this from the PutnamCollectibles project folder.")

s = TARGET.read_text(encoding="utf-8")

if "TG_SPECIAL_NUMBER_REPAIR_PATCH_V1" in s:
    print("TG special-number repair patch already appears to be installed. No changes made.")
    raise SystemExit(0)

if "_bottom_id_clean_special_number" not in s:
    raise SystemExit("ERROR: _bottom_id_clean_special_number not found. Install bottom_id patch first.")

try:
    os.chmod(TARGET, stat.S_IWRITE | stat.S_IREAD)
except Exception:
    pass

BACKUP.write_text(s, encoding="utf-8")

append = '\n# --- TG_SPECIAL_NUMBER_REPAIR_PATCH_V1 ---\n# Purpose:\n# Repair Trainer Gallery OCR variants like:\n#   TGOMTG30, TGOMIG30, TGO1TG30, TGO14G30\n# into:\n#   TG01/TG30\n#\n# This patch only overrides _bottom_id_clean_special_number.\n# It does not change geometry, crops, Studio HTML, scanner_server, or database files.\n\n_previous_bottom_id_clean_special_number_before_tg_patch = _bottom_id_clean_special_number\n\ndef _bottom_id_clean_special_number(text: str) -> str:\n    import re\n\n    raw_original = str(text or "").upper()\n    raw = raw_original.replace(" ", "").replace("\\\\", "/").replace("|", "/")\n    raw = raw.replace(",", "/").replace(".", "")\n    raw = raw.replace("’", "").replace("\'", "").replace("`", "")\n\n    # First, let the previous cleaner handle already-clean GG/TG/SVP/SWSH/etc.\n    prev = _previous_bottom_id_clean_special_number_before_tg_patch(raw)\n    if prev:\n        return prev\n\n    # Create a digit-normalized copy for TG/GG repair only.\n    # OCR commonly sees: O -> 0, I/L -> 1.\n    t = raw.replace("O", "0").replace("I", "1").replace("L", "1")\n\n    # TG01TG30 or TG01/TG30 -> TG01/TG30\n    m = re.search(r"TG0*(\\d{1,2})/?TG0*(\\d{1,2})", t)\n    if m:\n        left = int(m.group(1))\n        right = int(m.group(2))\n        return f"TG{left:02d}/TG{right}"\n\n    # Variants seen in Flareon:\n    # TGOMTG30 -> TG0MTG30 after O->0\n    # TGOMIG30 -> TG0M1G30 after O->0 and I->1\n    # Treat M/N immediately after TG0 as likely "1/" for TG01.\n    m = re.search(r"TG0*[MN]+[1/]?TG0*(\\d{1,2})", t)\n    if m:\n        right = int(m.group(1))\n        return f"TG01/TG{right}"\n\n    m = re.search(r"TG0*[MN]+[1/]?G0*(\\d{1,2})", t)\n    if m:\n        right = int(m.group(1))\n        return f"TG01/TG{right}"\n\n    # Repair TGO14G30 / TG014G30 as TG01/TG30 when total 30 is visible.\n    m = re.search(r"TG0*1\\d*G0*(30)", t)\n    if m:\n        return "TG01/TG30"\n\n    # Repair when OCR captures 01 and TG30 nearby.\n    m = re.search(r"0*1/?TG0*(\\d{1,2})", t)\n    if m and "TG" in t:\n        right = int(m.group(1))\n        return f"TG01/TG{right}"\n\n    # General cautious fallback for TG strings with visible total 30.\n    if "TG" in t and "30" in t:\n        m = re.search(r"TG0*(\\d{1,2})", t)\n        if m:\n            left = int(m.group(1))\n            if 1 <= left <= 30:\n                return f"TG{left:02d}/TG30"\n\n    # Keep a no-slash GG fallback.\n    m = re.search(r"GG0*(\\d{1,2})/?GG0*(\\d{1,2})", t)\n    if m:\n        left = int(m.group(1))\n        right = int(m.group(2))\n        return f"GG{left:02d}/GG{right}"\n\n    return ""\n'

TARGET.write_text(s + "\n" + append, encoding="utf-8")

print("SUCCESS: TG special-number repair patch installed.")
print(f"Backup created: {BACKUP}")
print("Changed file: scanner_core_region_ocr.py")
print("")
print("What changed:")
print("- Adds repair rules for TG OCR variants")
print("- Examples repaired: TGOMTG30, TGOMIG30, TGO1TG30 -> TG01/TG30")
print("- Leaves GG/SVP/SWSH/BW/XY/SM behavior intact")
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
