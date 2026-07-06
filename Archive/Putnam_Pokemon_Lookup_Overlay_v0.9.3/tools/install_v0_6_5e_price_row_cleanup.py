from pathlib import Path
import shutil
import datetime

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "extension" / "overlay.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = ROOT / "archive_old_versions" / f"overlay_before_v0_6_5e_{stamp}.js"
backup.parent.mkdir(exist_ok=True)

shutil.copy2(TARGET, backup)

text = TARGET.read_text(encoding="utf-8")

text = text.replace(
    'if (!finish || finish === "normal") return "Normal";',
    'if (!finish || finish === "normal") return "NORMAL";'
)

text = text.replace(
    'if (finish.includes("reverse")) return "Reverse";',
    'if (finish.includes("reverse")) return "REVERSE";'
)

text = text.replace(
    'if (finish.includes("holo")) return "Holo";',
    'if (finish.includes("holo")) return "HOLO";'
)

text = text.replace(
    'return "Shadowless";',
    'return "SHADOWLESS";'
)

text = text.replace(
    'return "Unlimited";',
    'return "UNLIMITED";'
)

text = text.replace(
    'return "1st Edition";',
    'return "1ST EDITION";'
)

text = text.replace(
    'row.append(renderCompactConditionCell(variant, "MP", url));',
    '// MP hidden in compact mode'
)

text = text.replace(
    'row.append(renderCompactConditionCell(variant, "LP", url));',
    'row.append(renderCompactConditionCell(variant, "LP", url));\n      row.append(el("span",{className:"ppo-compact-separator",text:"|"}));'
)

TARGET.write_text(text, encoding="utf-8")

print("Installed v0.6.5E Price Row Cleanup")
print("Patched:", TARGET)
print("Backup :", backup)