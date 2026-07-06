from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(__file__).parent.resolve()

if len(sys.argv) < 2:
    print("Usage:")
    print("python cardvector_folder_inspector.py <folder>")
    sys.exit(1)

TARGET = ROOT / sys.argv[1]
REPORT = ROOT / f"FOLDER_INSPECTION_{TARGET.name}.txt"

IGNORE = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

EXTENSIONS = {}

largest = []


def ignored(path):
    return any(part in IGNORE for part in path.parts)


files = 0
folders = 0

lines = []
lines.append("=" * 100)
lines.append(f"FOLDER INSPECTION REPORT : {TARGET.name}")
lines.append("=" * 100)
lines.append(f"Generated: {datetime.now()}")
lines.append("")

if not TARGET.exists():
    lines.append("Folder not found.")
    REPORT.write_text("\n".join(lines))
    print(REPORT)
    sys.exit()

for p in TARGET.rglob("*"):

    if ignored(p):
        continue

    if p.is_dir():
        folders += 1
        continue

    files += 1

    ext = p.suffix.lower() or "[none]"
    EXTENSIONS[ext] = EXTENSIONS.get(ext, 0) + 1

    try:
        size = p.stat().st_size
    except Exception:
        size = 0

    largest.append((size, p))

largest.sort(reverse=True)

lines.append(f"Folder: {TARGET}")
lines.append(f"Subfolders: {folders}")
lines.append(f"Files: {files}")
lines.append("")

lines.append("FILE TYPES")
lines.append("-" * 80)

for ext, count in sorted(EXTENSIONS.items(), key=lambda x: (-x[1], x[0])):
    lines.append(f"{ext:12} {count}")

lines.append("")
lines.append("LARGEST FILES")
lines.append("-" * 80)

for size, path in largest[:25]:
    rel = path.relative_to(ROOT)
    lines.append(f"{size:>12,} bytes   {rel}")

lines.append("")
lines.append("TOP LEVEL CONTENTS")
lines.append("-" * 80)

for item in sorted(TARGET.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
    kind = "DIR " if item.is_dir() else "FILE"
    lines.append(f"{kind:5} {item.name}")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("Report created:")
print(REPORT)
print()