from pathlib import Path
from datetime import datetime
import os

ROOT = Path(__file__).parent.resolve()
REPORT = ROOT / "CARDVECTOR_PROJECT_AUDIT_REPORT.txt"

IGNORE_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env",
    "node_modules", "dist", "build", ".idea", ".vs",
    ".pytest_cache", ".mypy_cache"
}

TEXT_EXTENSIONS = {
    ".py", ".txt", ".md", ".json", ".toml", ".yaml", ".yml",
    ".ini", ".cfg", ".html", ".css", ".js", ".jsx", ".ts", ".tsx"
}

KEYWORDS = {
    "LABEL / QR": ["qrcode", "qr", "generate label", "label", "printer", "print"],
    "THUMBNAILS": ["thumbnail", "thumb", "preview", "rail", "image_uri", "photo"],
    "OBS / CAPTURE": ["obs", "websocket", "capture", "scene", "screenshot", "camera"],
    "DATABASE": ["sqlite", "database", "db_path", ".db"],
    "UI": ["button", "tab", "panel", "sidebar", "right rail", "render", "component"],
    "DEPENDENCIES": ["requirements", "pillow", "qrcode", "pyinstaller", "poetry"],
}

DEPENDENCY_FILES = [
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "environment.yml",
    "environment.yaml",
    "Pipfile",
    "poetry.lock",
]

ARCHIVE_HINTS = [
    "old", "backup", "bak", "copy", "prototype", "experiment",
    "test_", "_test", "debug", "tmp", "temp", "v1", "v2", "v3"
]


def ignored(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def file_size(path: Path) -> str:
    try:
        size = path.stat().st_size
    except Exception:
        return "unknown"

    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def collect_files():
    files = []
    for path in ROOT.rglob("*"):
        if ignored(path):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def main():
    files = collect_files()

    lines = []
    lines.append("=" * 90)
    lines.append("CARDVECTOR PROJECT AUDIT REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Root: {ROOT}")
    lines.append("=" * 90)
    lines.append("")

    lines.append("SUMMARY")
    lines.append("-" * 90)
    lines.append(f"Total files scanned: {len(files)}")
    lines.append("")

    lines.append("DEPENDENCY FILES FOUND")
    lines.append("-" * 90)
    found_dependency_files = []
    for dep in DEPENDENCY_FILES:
        matches = [f for f in files if f.name.lower() == dep.lower()]
        for match in matches:
            found_dependency_files.append(match)
            lines.append(f"- {rel(match)} ({file_size(match)})")
    if not found_dependency_files:
        lines.append("- None found")
    lines.append("")

    lines.append("LIKELY IMPORTANT FILES BY KEYWORD")
    lines.append("-" * 90)

    keyword_results = {group: [] for group in KEYWORDS}

    for path in files:
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        text = safe_read(path).lower()
        if not text:
            continue

        for group, terms in KEYWORDS.items():
            hits = [term for term in terms if term.lower() in text]
            if hits:
                keyword_results[group].append((path, hits))

    for group, matches in keyword_results.items():
        lines.append("")
        lines.append(f"[{group}]")
        if not matches:
            lines.append("  No matches found.")
            continue

        for path, hits in matches[:40]:
            lines.append(f"  - {rel(path)}")
            lines.append(f"    hits: {', '.join(hits)}")

        if len(matches) > 40:
            lines.append(f"  ... plus {len(matches) - 40} more")
    lines.append("")

    lines.append("POTENTIAL ARCHIVE CANDIDATES")
    lines.append("-" * 90)
    archive_candidates = []

    for path in files:
        lower = rel(path).lower()
        if any(hint in lower for hint in ARCHIVE_HINTS):
            archive_candidates.append(path)

    if archive_candidates:
        for path in archive_candidates[:100]:
            lines.append(f"- {rel(path)} ({file_size(path)})")
        if len(archive_candidates) > 100:
            lines.append(f"... plus {len(archive_candidates) - 100} more")
    else:
        lines.append("- None detected by filename hints")
    lines.append("")

    lines.append("TOP-LEVEL PROJECT STRUCTURE")
    lines.append("-" * 90)
    top_items = sorted(ROOT.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    for item in top_items:
        if item.name in IGNORE_DIRS:
            continue
        kind = "DIR " if item.is_dir() else "FILE"
        size = "" if item.is_dir() else f" ({file_size(item)})"
        lines.append(f"{kind}  {item.name}{size}")
    lines.append("")

    lines.append("NEXT REVIEW TARGETS")
    lines.append("-" * 90)
    lines.append("1. Dependency file containing qrcode / Pillow requirements")
    lines.append("2. Label generation file importing qrcode")
    lines.append("3. Thumbnail / preview / rail rendering file")
    lines.append("4. OBS websocket / capture connection file")
    lines.append("5. Archive candidates only after confirming they are unused")
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print("")
    print("CardVector project audit complete.")
    print(f"Report created here:")
    print(REPORT)
    print("")


if __name__ == "__main__":
    main()