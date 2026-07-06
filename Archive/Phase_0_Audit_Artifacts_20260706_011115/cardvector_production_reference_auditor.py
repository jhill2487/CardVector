from pathlib import Path
from datetime import datetime
import ast
import re

WORKSPACE = Path(__file__).parent.resolve()
APP = WORKSPACE / "Platform" / "Putnam_OS" / "System" / "app"
LAUNCHER = WORKSPACE / "Platform" / "Putnam_OS" / "Run CardVector OS Production.vbs"
REPORT = WORKSPACE / "CARDVECTOR_PRODUCTION_REFERENCE_REPORT.txt"


def safe_read(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def rel(path):
    try:
        return str(path.relative_to(WORKSPACE))
    except Exception:
        return str(path)


def parse_imports(path):
    imports = set()
    text = safe_read(path)

    try:
        tree = ast.parse(text)
    except Exception:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    return imports


def launcher_entry():
    text = safe_read(LAUNCHER)
    matches = re.findall(r"([A-Za-z0-9_\\/\- ]+\.py)", text, re.IGNORECASE)

    for match in matches:
        candidate = WORKSPACE / match.strip().lstrip("\\/")
        if candidate.exists():
            return candidate.resolve()

    return None


def classify_file(path, entry, imported_by):
    name = path.name.lower()

    if entry and path.resolve() == entry.resolve():
        return "🟢 Production Entry Point"

    if imported_by:
        return "🟢 Imported by Production"

    if name.startswith("test_"):
        return "🟢 Test Utility"

    if "backup" in name or "bak" in name:
        return "📦 Backup"

    if name.startswith("run_") or name.endswith("_cli.py"):
        return "🟡 Standalone Tool"

    return "❓ Unreferenced"


def main():
    lines = []

    lines.append("=" * 100)
    lines.append("CARDVECTOR PRODUCTION REFERENCE REPORT")
    lines.append("=" * 100)
    lines.append(f"Generated: {datetime.now()}")
    lines.append("")

    if not APP.exists():
        lines.append("ERROR: Production app folder not found.")
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print(REPORT)
        return

    py_files = sorted(APP.glob("*.py"))
    module_to_file = {p.stem: p for p in py_files}

    entry = launcher_entry()

    lines.append("Production App Root:")
    lines.append(f"  {rel(APP)}")
    lines.append("")

    lines.append("Launcher:")
    lines.append(f"  {rel(LAUNCHER)}")
    lines.append("")

    lines.append("Resolved Entry Point:")
    lines.append(f"  {rel(entry) if entry else 'NOT FOUND'}")
    lines.append("")

    imported_by = {p: [] for p in py_files}

    for file in py_files:
        imports = parse_imports(file)
        for module in imports:
            target = module_to_file.get(module)
            if target:
                imported_by[target].append(file)

    lines.append("FILE CLASSIFICATION")
    lines.append("-" * 100)

    for file in py_files:
        refs = imported_by[file]
        status = classify_file(file, entry, refs)

        lines.append("")
        lines.append(file.name)
        lines.append(f"Status: {status}")
        lines.append(f"Path: {rel(file)}")
        lines.append(f"Modified: {datetime.fromtimestamp(file.stat().st_mtime)}")
        lines.append(f"Size: {file.stat().st_size:,} bytes")

        if refs:
            lines.append("Referenced by:")
            for ref in refs:
                lines.append(f"  - {ref.name}")
        else:
            lines.append("Referenced by: none detected")

    lines.append("")
    lines.append("SUMMARY")
    lines.append("-" * 100)

    counts = {}
    for file in py_files:
        status = classify_file(file, entry, imported_by[file])
        counts[status] = counts.get(status, 0) + 1

    for status, count in counts.items():
        lines.append(f"{status}: {count}")

    lines.append("")
    lines.append("NOTE")
    lines.append("-" * 100)
    lines.append("This report detects direct static imports inside System/app.")
    lines.append("Dynamic imports or subprocess calls may require manual review.")
    lines.append("Do not delete files based only on this report. Archive first.")

    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("Production Reference Report created:")
    print(REPORT)
    print()


if __name__ == "__main__":
    main()