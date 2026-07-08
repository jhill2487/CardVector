from pathlib import Path

ROOT = Path(__file__).parent.resolve()
APP = ROOT / "Platform" / "Putnam_OS" / "System" / "app"
REPORT = ROOT / "CARDVECTOR_CONFIG_REFERENCE_REPORT.txt"

SEARCH_TERMS = [
    "capture_settings.json",
    "capture_settings",
    "obs_host",
    "obs_scene",
    "obs_port",
    "thumbnail_preview",
    "Putnam_Platform",
    "content",
]

lines = []
lines.append("=" * 100)
lines.append("CARDVECTOR CONFIG REFERENCE REPORT")
lines.append("=" * 100)
lines.append("")

for py in sorted(APP.glob("*.py")):

    try:
        text = py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    matches = []

    lower = text.lower()

    for term in SEARCH_TERMS:
        if term.lower() in lower:
            matches.append(term)

    if matches:
        lines.append("-" * 100)
        lines.append(py.name)
        lines.append("Matches:")
        for m in sorted(set(matches)):
            lines.append(f"  - {m}")
        lines.append("")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("Created:")
print(REPORT)
print()