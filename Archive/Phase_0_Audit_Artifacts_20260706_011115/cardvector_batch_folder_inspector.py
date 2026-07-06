from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(__file__).parent.resolve()

IGNORE = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

REPORT = ROOT / "CARDVECTOR_BATCH_FOLDER_REPORT.txt"


def ignored(path):
    return any(part in IGNORE for part in path.parts)


def inspect(folder: Path):
    files = 0
    dirs = 0

    ext_counts = {}
    py_files = 0

    newest = None

    for p in folder.rglob("*"):

        if ignored(p):
            continue

        if p.is_dir():
            dirs += 1
            continue

        files += 1

        ext = p.suffix.lower() or "[none]"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

        if ext == ".py":
            py_files += 1

        try:
            m = datetime.fromtimestamp(p.stat().st_mtime)
            if newest is None or m > newest:
                newest = m
        except Exception:
            pass

    return {
        "files": files,
        "dirs": dirs,
        "python": py_files,
        "extensions": ext_counts,
        "newest": newest,
    }


def classify(folder_name, stats):

    name = folder_name.lower()

    if stats["python"] > 0:
        return "❓ Review (contains Python)"

    if "archive" in name:
        return "🟢 Archive"

    if stats["files"] < 10:
        return "🟡 Small Folder"

    return "❓ Review"


lines = []

lines.append("=" * 100)
lines.append("CARDVECTOR BATCH FOLDER REPORT")
lines.append("=" * 100)
lines.append(f"Generated: {datetime.now()}")
lines.append("")

folders = sys.argv[1:]

if not folders:
    print("Usage:")
    print("python cardvector_batch_folder_inspector.py Folder1 Folder2 Folder3")
    raise SystemExit()

summary = {}

for name in folders:

    folder = ROOT / name

    lines.append("=" * 100)
    lines.append(name)

    if not folder.exists():
        lines.append("NOT FOUND")
        lines.append("")
        continue

    stats = inspect(folder)

    status = classify(name, stats)

    summary[status] = summary.get(status, 0) + 1

    lines.append(f"Classification : {status}")
    lines.append(f"Folders        : {stats['dirs']}")
    lines.append(f"Files          : {stats['files']}")
    lines.append(f"Python Files   : {stats['python']}")

    if stats["newest"]:
        lines.append(f"Newest File    : {stats['newest']}")

    lines.append("Extensions:")

    for ext, count in sorted(stats["extensions"].items(), key=lambda x: (-x[1], x[0]))[:10]:
        lines.append(f"   {ext:10} {count}")

    lines.append("")

lines.append("=" * 100)
lines.append("SUMMARY")
lines.append("=" * 100)

for k, v in summary.items():
    lines.append(f"{k}: {v}")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("Batch report created:")
print(REPORT)
print()