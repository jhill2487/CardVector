from __future__ import annotations
import json, stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "project_locks" / "locked_manifest.json"


def set_writable(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
    except Exception as exc:
        print(f"WARNING: Could not unlock {path}: {exc}")


def main() -> None:
    if not MANIFEST.exists():
        print("ERROR: No lock manifest found.")
        raise SystemExit(1)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for entry in data.get("locked_files", []):
        path = ROOT / entry["path"]
        if path.exists():
            set_writable(path)
            print(f"UNLOCKED: {entry['path']}")
    print("Done. Only use this before deliberate geometry/layout edits.")

if __name__ == "__main__":
    main()
