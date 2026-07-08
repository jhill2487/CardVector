from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "project_locks" / "locked_manifest.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if not MANIFEST.exists():
        print("ERROR: No lock manifest found. Run install_project_locks.py first.")
        raise SystemExit(1)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ok = True
    print("Verifying locked files...\n")
    for entry in data.get("locked_files", []):
        rel = entry["path"]
        path = ROOT / rel
        expected = entry["sha256"]
        if not path.exists():
            ok = False
            print(f"MISSING: {rel}")
            continue
        actual = sha256(path)
        if actual == expected:
            print(f"OK:      {rel}")
        else:
            ok = False
            print(f"CHANGED: {rel}")
            print(f"        expected {expected}")
            print(f"        actual   {actual}")
    if ok:
        print("\nPASS: locked geometry/layout files are unchanged.")
    else:
        print("\nFAIL: one or more locked files changed. Restore from project_locks/locked_backups if this was accidental.")
        raise SystemExit(2)

if __name__ == "__main__":
    main()
