from pathlib import Path
import re

ROOT = Path(__file__).parent.resolve()
REPORT = ROOT / "CARDVECTOR_PRODUCTION_PATH_REPORT.txt"

IMPORT_RE = re.compile(
    r'^\s*(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\. ,]+))',
    re.MULTILINE,
)

visited = set()


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def find_launcher():
    launchers = list(ROOT.rglob("Run CardVector OS Production.vbs"))
    if not launchers:
        return None
    return launchers[0]


def find_python_from_vbs(vbs):
    text = read_text(vbs)

    py = re.findall(r'([A-Za-z0-9_\\/\- ]+\.py)', text, re.IGNORECASE)
    if py:
        return py[0]

    return None


def resolve_python(relative_path):
    target = ROOT / relative_path

    if target.exists():
        return target.resolve()

    matches = list(ROOT.rglob(Path(relative_path).name))
    if matches:
        return matches[0]

    return None


def imports_from_file(path):
    text = read_text(path)

    imports = []

    for match in IMPORT_RE.finditer(text):

        if match.group(1):
            imports.append(match.group(1).split(".")[0])

        if match.group(2):
            for part in match.group(2).split(","):
                imports.append(part.strip().split(".")[0])

    return sorted(set(imports))


def locate_module(module):

    matches = []

    for p in ROOT.rglob(f"{module}.py"):
        matches.append(p)

    return matches


def walk(path, depth=0, lines=None):

    if lines is None:
        lines = []

    if path in visited:
        return

    visited.add(path)

    indent = "    " * depth

    lines.append(f"{indent}{path.relative_to(ROOT)}")

    for module in imports_from_file(path):

        files = locate_module(module)

        if not files:
            continue

        walk(files[0], depth + 1, lines)

    return lines


def main():

    launcher = find_launcher()

    report = []

    report.append("=" * 80)
    report.append("CARDVECTOR PRODUCTION PATH REPORT")
    report.append("=" * 80)
    report.append("")

    if not launcher:
        report.append("Launcher not found.")
        REPORT.write_text("\n".join(report))
        return

    report.append(f"Launcher:")
    report.append(f"    {launcher.relative_to(ROOT)}")
    report.append("")

    py = find_python_from_vbs(launcher)

    if not py:
        report.append("No Python script referenced inside launcher.")
        REPORT.write_text("\n".join(report))
        return

    report.append(f"Launcher references:")
    report.append(f"    {py}")
    report.append("")

    entry = resolve_python(py)

    if not entry:
        report.append("Unable to locate entry point.")
        REPORT.write_text("\n".join(report))
        return

    report.append("Production Import Tree")
    report.append("-" * 80)

    tree = walk(entry)

    if tree:
        report.extend(tree)

    REPORT.write_text("\n".join(report), encoding="utf-8")

    print()
    print("Production Path Report created:")
    print(REPORT)
    print()


if __name__ == "__main__":
    main()