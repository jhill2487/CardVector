from pathlib import Path
import re

ROOT = Path(__file__).parent.resolve()
REPORT = ROOT / "CARDVECTOR_PRODUCTION_PATH_REPORT_V2.txt"

LAUNCHER_NAME = "Run CardVector OS Production.vbs"

IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\. ,]+))",
    re.MULTILINE,
)

visited = set()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def find_launcher():
    matches = list(ROOT.rglob(LAUNCHER_NAME))
    return sorted(matches, key=lambda p: len(str(p)))[0] if matches else None


def extract_python_path_from_vbs(vbs: Path):
    text = read_text(vbs)

    matches = re.findall(r'["\']?([A-Za-z]:?[^"\']*?\.py)["\']?', text, re.IGNORECASE)

    cleaned = []
    for m in matches:
        m = m.strip()
        if ".py" in m.lower():
            cleaned.append(m)

    return cleaned


def resolve_entry_path(raw_path: str, launcher: Path):
    raw_path = raw_path.strip().strip('"').strip("'")

    candidates = []

    # Absolute Windows path
    p = Path(raw_path)
    if p.is_absolute():
        candidates.append(p)

    # Relative to workspace root
    candidates.append(ROOT / raw_path.lstrip("\\/"))

    # Relative to launcher folder
    candidates.append(launcher.parent / raw_path)

    # Relative to Putnam_OS folder
    candidates.append(ROOT / "Platform" / "Putnam_OS" / raw_path.lstrip("\\/"))

    for c in candidates:
        if c.exists():
            return c.resolve()

    return None


def parse_imports(path: Path):
    text = read_text(path)
    imports = []

    for match in IMPORT_RE.finditer(text):
        if match.group(1):
            imports.append(match.group(1))

        if match.group(2):
            for part in match.group(2).split(","):
                imports.append(part.strip())

    return sorted(set(i for i in imports if i))


def module_to_path(module_name: str, current_file: Path, production_root: Path):
    first = module_name.split(".")[0]
    parts = module_name.split(".")

    candidates = []

    # Same folder as current file
    candidates.append(current_file.parent / f"{first}.py")
    candidates.append(current_file.parent / first / "__init__.py")

    # Production root/app-relative
    candidates.append(production_root / f"{first}.py")
    candidates.append(production_root / first / "__init__.py")

    # Full dotted path under production root
    candidates.append(production_root.joinpath(*parts).with_suffix(".py"))
    candidates.append(production_root.joinpath(*parts) / "__init__.py")

    for c in candidates:
        if c.exists():
            return c.resolve()

    return None


def walk_imports(path: Path, production_root: Path, lines, depth=0):
    if path in visited:
        return

    visited.add(path)
    indent = "    " * depth

    tag = ""
    if "System_Archive" in path.parts or "Archive" in path.parts:
        tag = "  ⚠️ ARCHIVE PATH"

    lines.append(f"{indent}- {rel(path)}{tag}")

    for module in parse_imports(path):
        resolved = module_to_path(module, path, production_root)
        if resolved:
            walk_imports(resolved, production_root, lines, depth + 1)


def main():
    lines = []
    lines.append("=" * 90)
    lines.append("CARDVECTOR PRODUCTION PATH REPORT V2")
    lines.append("=" * 90)
    lines.append("")

    launcher = find_launcher()

    if not launcher:
        lines.append("ERROR: Production launcher not found.")
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("Report created:", REPORT)
        return

    lines.append("Launcher Found:")
    lines.append(f"  {rel(launcher)}")
    lines.append("")

    py_refs = extract_python_path_from_vbs(launcher)

    if not py_refs:
        lines.append("ERROR: No Python entry path found inside launcher.")
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("Report created:", REPORT)
        return

    lines.append("Python References Inside Launcher:")
    for ref in py_refs:
        lines.append(f"  - {ref}")
    lines.append("")

    entry = None
    for ref in py_refs:
        resolved = resolve_entry_path(ref, launcher)
        if resolved:
            entry = resolved
            break

    if not entry:
        lines.append("ERROR: Could not resolve launcher Python entry point.")
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print("Report created:", REPORT)
        return

    production_root = entry.parent

    lines.append("Resolved Production Entry Point:")
    lines.append(f"  {rel(entry)}")
    lines.append("")
    lines.append("Proposed Production Root To Freeze:")
    lines.append(f"  {rel(production_root)}")
    lines.append("")

    if "System_Archive" in entry.parts or "Archive" in entry.parts:
        lines.append("⚠️ WARNING: Entry point resolved inside an archive folder.")
        lines.append("Do not freeze this path until manually confirmed.")
        lines.append("")

    lines.append("Production Import Tree:")
    lines.append("-" * 90)
    walk_imports(entry, production_root, lines)

    lines.append("")
    lines.append("Result:")
    if any("ARCHIVE PATH" in line for line in lines):
        lines.append("  ⚠️ Archive paths appeared in the import tree. Review before freezing.")
    else:
        lines.append("  ✅ No archive paths detected in resolved production import tree.")

    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print("")
    print("Production Path Auditor v2 complete.")
    print("Report created:")
    print(REPORT)
    print("")


if __name__ == "__main__":
    main()