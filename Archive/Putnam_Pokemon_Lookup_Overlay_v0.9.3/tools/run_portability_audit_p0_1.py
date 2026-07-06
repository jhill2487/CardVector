from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv

ROOT = Path.cwd()
TOOLS = ROOT / "tools"
ARCHIVE = ROOT / "archive_old_versions"
REPORTS = ROOT / "reports"

TOOLS.mkdir(exist_ok=True)
ARCHIVE.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

AUDIT_PATTERNS = [
    "C:\\Users\\",
    "C:/Users/",
    "JaredHill",
    "C:\\Users\\JaredHill",
    "C:/Users/JaredHill",
    "C:\\Users\\user",
    "C:/Users/user",
    "OneDrive\\PutnamCollectibles",
    "OneDrive/PutnamCollectibles",
    "Documents\\Codex",
    "Documents/Codex",
    "Desktop\\Scanner Interface Dev",
    "Desktop/Scanner Interface Dev",
]

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "archive_old_versions",
    "reports",
}

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".css",
    ".html",
    ".json",
    ".bat",
    ".ps1",
    ".cmd",
    ".txt",
    ".md",
    ".csv",
    ".sql",
    ".yaml",
    ".yml",
}

rows = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue

    rel_parts = set(path.relative_to(ROOT).parts)
    if rel_parts & SKIP_DIRS:
        continue

    if path.suffix.lower() not in TEXT_EXTENSIONS:
        continue

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        rows.append({
            "file": str(path.relative_to(ROOT)),
            "line": "",
            "pattern": "READ_ERROR",
            "text": str(exc),
        })
        continue

    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern in AUDIT_PATTERNS:
            if pattern.lower() in line.lower():
                rows.append({
                    "file": str(path.relative_to(ROOT)),
                    "line": line_no,
                    "pattern": pattern,
                    "text": line.strip()[:500],
                })

csv_path = REPORTS / f"portability_audit_p0_1_{stamp}.csv"
txt_path = REPORTS / f"portability_audit_p0_1_{stamp}.txt"

with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["file", "line", "pattern", "text"])
    writer.writeheader()
    writer.writerows(rows)

with txt_path.open("w", encoding="utf-8") as handle:
    handle.write("Putnam Project Portability Audit P0.1\n")
    handle.write(f"Project root: {ROOT}\n")
    handle.write(f"Timestamp: {stamp}\n")
    handle.write(f"Findings: {len(rows)}\n\n")

    current_file = None
    for row in rows:
        if row["file"] != current_file:
            current_file = row["file"]
            handle.write(f"\n=== {current_file} ===\n")
        handle.write(f"Line {row['line']} | {row['pattern']} | {row['text']}\n")

print("Portability audit complete.")
print("Findings:", len(rows))
print("CSV:", csv_path)
print("TXT:", txt_path)

if rows:
    print("\nTop findings:")
    for row in rows[:20]:
        print(f"{row['file']}:{row['line']} | {row['pattern']} | {row['text'][:120]}")
else:
    print("No hardcoded user/path portability issues found.")