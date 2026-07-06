from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.resolve()
REPORT = ROOT / "CARDVECTOR_ROOT_CLEANUP_REPORT.txt"

IGNORE = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

KEEP_ROOT = {
    "Platform",
    "Data",
    "Docs",
    "Tools",
    "Business",
    "Shared",
    "Archive",
}

REVIEW_HINTS = [
    "Putnam_",
    "Capture",
    "Scanner",
    "Temp",
    "Test",
    "Backup",
    "Old",
]

def folder_stats(folder):
    files = 0
    dirs = 0

    try:
        for p in folder.rglob("*"):
            if any(part in IGNORE for part in p.parts):
                continue

            if p.is_file():
                files += 1
            elif p.is_dir():
                dirs += 1
    except Exception:
        pass

    return files, dirs


def classify(name):

    if name in KEEP_ROOT:
        return "🟢 Keep"

    lower = name.lower()

    if lower.startswith("putnam_"):
        return "🟡 Review"

    if "capture" in lower:
        return "🟡 Review"

    if "scanner" in lower:
        return "🟡 Review"

    if "backup" in lower:
        return "📦 Archive"

    if "old" in lower:
        return "📦 Archive"

    if "temp" in lower:
        return "📦 Archive"

    return "❓ Review"


lines = []

lines.append("=" * 90)
lines.append("CARDVECTOR ROOT CLEANUP REPORT")
lines.append("=" * 90)
lines.append(f"Generated: {datetime.now()}")
lines.append("")

items = sorted(ROOT.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

summary = {}

for item in items:

    if item.name in IGNORE:
        continue

    status = classify(item.name)

    summary[status] = summary.get(status, 0) + 1

    lines.append("-" * 90)
    lines.append(item.name)
    lines.append(f"Classification: {status}")

    if item.is_dir():

        files, dirs = folder_stats(item)

        lines.append("Type: Folder")
        lines.append(f"Subfolders: {dirs}")
        lines.append(f"Files: {files}")

    else:

        lines.append("Type: File")
        lines.append(f"Size: {item.stat().st_size:,} bytes")

lines.append("")
lines.append("=" * 90)
lines.append("SUMMARY")
lines.append("=" * 90)

for k, v in summary.items():
    lines.append(f"{k}: {v}")

lines.append("")
lines.append("NEXT STEP")
lines.append("=" * 90)
lines.append("Nothing should be moved yet.")
lines.append("Use this report to decide the future workspace layout.")
lines.append("Move items only after approval.")
lines.append("Delete nothing.")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("Root Cleanup Report created:")
print(REPORT)
print()