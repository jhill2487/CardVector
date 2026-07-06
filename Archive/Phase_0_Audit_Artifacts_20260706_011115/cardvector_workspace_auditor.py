from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).parent.resolve()
REPORT = ROOT / "CARDVECTOR_WORKSPACE_AUDIT_REPORT.txt"

IGNORE_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env",
    "node_modules", "dist", "build", ".idea", ".vs",
    ".pytest_cache", ".mypy_cache"
}

TEXT_EXTENSIONS = {
    ".py", ".txt", ".md", ".json", ".toml", ".yaml", ".yml",
    ".ini", ".cfg", ".html", ".css", ".js", ".jsx", ".ts", ".tsx",
    ".vbs", ".bat", ".ps1"
}

MODULE_KEYWORDS = {
    "Capture": ["capture", "camera", "photo", "image", "thumbnail", "thumb", "rail"],
    "OBS": ["obs", "websocket", "scene", "screenshot"],
    "Label Center": ["label", "qrcode", "qr", "printer", "print"],
    "Inventory": ["inventory", "sku", "stock", "quantity"],
    "Pricing": ["price", "pricing", "market", "tcgplayer", "ebay"],
    "Database": ["sqlite", "database", "db_path", ".db"],
    "UI": ["button", "tab", "panel", "sidebar", "render", "component"],
    "Config": ["config", "settings", "env", "path"],
}

DEPENDENCY_FILES = {
    "requirements.txt", "pyproject.toml", "setup.py",
    "environment.yml", "environment.yaml", "Pipfile", "poetry.lock"
}

ARCHIVE_HINTS = {
    "old", "backup", "bak", "copy", "prototype", "experiment",
    "debug", "tmp", "temp", "archive", "v1", "v2", "v3"
}


def ignored(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def size_label(path: Path) -> str:
    try:
        size = path.stat().st_size
    except Exception:
        return "unknown"

    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def modified_label(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "unknown"


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

    folder_counts = defaultdict(int)
    extension_counts = defaultdict(int)
    module_hits = defaultdict(list)
    dependency_files = []
    archive_candidates = []
    launchers = []

    for path in files:
        relative = rel(path)
        parts = Path(relative).parts
        top_folder = parts[0] if len(parts) > 1 else "[root]"

        folder_counts[top_folder] += 1
        extension_counts[path.suffix.lower() or "[no extension]"] += 1

        lower_name = relative.lower()

        if path.name in DEPENDENCY_FILES:
            dependency_files.append(path)

        if path.suffix.lower() in {".vbs", ".bat", ".ps1"} or "run " in path.name.lower():
            launchers.append(path)

        if any(hint in lower_name for hint in ARCHIVE_HINTS):
            archive_candidates.append(path)

        if path.suffix.lower() in TEXT_EXTENSIONS:
            text = safe_read(path).lower()
            haystack = lower_name + "\n" + text

            for module, keywords in MODULE_KEYWORDS.items():
                hits = [k for k in keywords if k in haystack]
                if hits:
                    module_hits[module].append((path, sorted(set(hits))))

    lines = []
    lines.append("=" * 100)
    lines.append("CARDVECTOR WORKSPACE AUDIT REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Workspace Root: {ROOT}")
    lines.append("=" * 100)
    lines.append("")

    lines.append("WORKSPACE SUMMARY")
    lines.append("-" * 100)
    lines.append(f"Total files scanned: {len(files)}")
    lines.append(f"Top-level folders found: {len([k for k in folder_counts if k != '[root]'])}")
    lines.append("")

    lines.append("TOP-LEVEL FOLDERS")
    lines.append("-" * 100)
    for folder, count in sorted(folder_counts.items(), key=lambda x: x[0].lower()):
        lines.append(f"- {folder}: {count} files")
    lines.append("")

    lines.append("FILE TYPES")
    lines.append("-" * 100)
    for ext, count in sorted(extension_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {ext}: {count}")
    lines.append("")

    lines.append("LAUNCHERS / RUN FILES")
    lines.append("-" * 100)
    if launchers:
        for path in launchers:
            lines.append(f"- {rel(path)} | modified {modified_label(path)} | {size_label(path)}")
    else:
        lines.append("- None found")
    lines.append("")

    lines.append("DEPENDENCY FILES")
    lines.append("-" * 100)
    if dependency_files:
        for path in dependency_files:
            lines.append(f"- {rel(path)} | modified {modified_label(path)} | {size_label(path)}")
    else:
        lines.append("- None found")
    lines.append("")

    lines.append("LIKELY MODULE FILES")
    lines.append("-" * 100)
    for module in MODULE_KEYWORDS:
        matches = module_hits[module]
        lines.append("")
        lines.append(f"[{module}]")
        if not matches:
            lines.append("  No matches found.")
            continue

        for path, hits in matches[:50]:
            lines.append(f"  - {rel(path)}")
            lines.append(f"    hits: {', '.join(hits)}")

        if len(matches) > 50:
            lines.append(f"  ... plus {len(matches) - 50} more")
    lines.append("")

    lines.append("POTENTIAL ARCHIVE CANDIDATES")
    lines.append("-" * 100)
    if archive_candidates:
        for path in archive_candidates[:150]:
            lines.append(f"- {rel(path)} | modified {modified_label(path)} | {size_label(path)}")
        if len(archive_candidates) > 150:
            lines.append(f"... plus {len(archive_candidates) - 150} more")
    else:
        lines.append("- None found")
    lines.append("")

    lines.append("NEXT REVIEW TARGETS")
    lines.append("-" * 100)
    lines.append("1. Confirm which launcher starts the active production app.")
    lines.append("2. Trace that launcher to the active Python entry point.")
    lines.append("3. Locate Label Center files using qrcode / label / printer hits.")
    lines.append("4. Locate Capture thumbnail rail files using thumbnail / thumb / rail hits.")
    lines.append("5. Locate OBS files using obs / websocket / scene hits.")
    lines.append("6. Do not archive anything until active production paths are confirmed.")
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print("")
    print("CardVector Workspace Audit complete.")
    print("Report created:")
    print(REPORT)
    print("")


if __name__ == "__main__":
    main()