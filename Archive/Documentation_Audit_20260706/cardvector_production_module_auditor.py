from pathlib import Path
from datetime import datetime
import ast

WORKSPACE = Path(__file__).parent.resolve()
APP = WORKSPACE / "Platform" / "Putnam_OS" / "System" / "app"
REPORT = WORKSPACE / "CARDVECTOR_PRODUCTION_MODULE_REPORT.txt"

KEYWORDS = {
    "Capture": ["capture", "camera", "photo", "thumbnail", "thumb"],
    "OBS": ["obs", "websocket", "scene"],
    "Labels": ["label", "qrcode", "qr", "printer"],
    "Inventory": ["inventory", "sku", "stock"],
    "Orders": ["order", "shipment", "fulfillment"],
    "Pricing": ["price", "pricing", "market", "tcgplayer", "ebay"],
    "Database": ["sqlite", "database", ".db"],
}

def safe_read(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def rel(path):
    return str(path.relative_to(WORKSPACE))

def analyze_python(path):
    result = {
        "imports": [],
        "classes": [],
        "functions": [],
        "keywords": set(),
    }

    text = safe_read(path)

    try:
        tree = ast.parse(text)
    except Exception:
        return result

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for n in node.names:
                result["imports"].append(n.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result["imports"].append(node.module)

        elif isinstance(node, ast.ClassDef):
            result["classes"].append(node.name)

        elif isinstance(node, ast.FunctionDef):
            result["functions"].append(node.name)

    lower = text.lower()

    for group, words in KEYWORDS.items():
        if any(w in lower for w in words):
            result["keywords"].add(group)

    result["imports"] = sorted(set(result["imports"]))
    result["keywords"] = sorted(result["keywords"])

    return result

def role_from_keywords(data):
    if "Capture" in data["keywords"]:
        return "Capture Module"
    if "OBS" in data["keywords"]:
        return "OBS Integration"
    if "Labels" in data["keywords"]:
        return "Label Center"
    if "Inventory" in data["keywords"]:
        return "Inventory"
    if "Orders" in data["keywords"]:
        return "Orders / Fulfillment"
    if "Pricing" in data["keywords"]:
        return "Pricing"
    if "Database" in data["keywords"]:
        return "Database"

    return "General"

def main():

    lines = []

    lines.append("="*100)
    lines.append("CARDVECTOR PRODUCTION MODULE REPORT")
    lines.append("="*100)
    lines.append(f"Generated: {datetime.now()}")
    lines.append("")

    if not APP.exists():
        lines.append("ERROR: Production app folder not found.")
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print(REPORT)
        return

    py_files = sorted(APP.glob("*.py"))

    lines.append(f"Production Root: {rel(APP)}")
    lines.append(f"Python Modules: {len(py_files)}")
    lines.append("")

    for file in py_files:

        info = analyze_python(file)

        lines.append("-"*100)
        lines.append(file.name)
        lines.append(f"Role: {role_from_keywords(info)}")
        lines.append(f"Modified: {datetime.fromtimestamp(file.stat().st_mtime)}")
        lines.append(f"Size: {file.stat().st_size:,} bytes")

        if info["keywords"]:
            lines.append("Keywords:")
            for k in info["keywords"]:
                lines.append(f"   - {k}")

        if info["imports"]:
            lines.append("Imports:")
            for i in info["imports"]:
                lines.append(f"   - {i}")

        if info["classes"]:
            lines.append(f"Classes ({len(info['classes'])}):")
            for c in info["classes"]:
                lines.append(f"   - {c}")

        if info["functions"]:
            lines.append(f"Functions ({len(info['functions'])}):")
            for f in info["functions"]:
                lines.append(f"   - {f}")

        lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("Production Module Report created:")
    print(REPORT)
    print()

if __name__ == "__main__":
    main()