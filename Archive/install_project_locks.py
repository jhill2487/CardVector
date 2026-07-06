from __future__ import annotations
import hashlib, json, os, shutil, stat
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCK_DIR = ROOT / "project_locks"
BACKUP_DIR = LOCK_DIR / "locked_backups"
MANIFEST = LOCK_DIR / "locked_manifest.json"

LOCKED_FILES = [
    "known_good/template_region_warp_matcher_v0_7.py",
    "known_good/IMG_7505.json",
    "known_good/IMG_7507.json",
    "scanner_studio.html",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def set_read_only(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        path.chmod(mode & ~stat.S_IWRITE)
    except Exception as exc:
        print(f"WARNING: Could not set read-only for {path}: {exc}")


def main() -> None:
    LOCK_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    entries = []

    missing = []
    for rel in LOCKED_FILES:
        path = ROOT / rel
        if not path.exists():
            missing.append(rel)
    if missing:
        print("ERROR: These files are missing and cannot be locked:")
        for rel in missing:
            print(f"  - {rel}")
        raise SystemExit(1)

    for rel in LOCKED_FILES:
        path = ROOT / rel
        backup_name = rel.replace("/", "__").replace("\\", "__")
        backup_path = BACKUP_DIR / f"{timestamp}__{backup_name}"
        shutil.copy2(path, backup_path)
        digest = sha256(path)
        entries.append({
            "path": rel,
            "sha256": digest,
            "backup": str(backup_path.relative_to(ROOT)),
            "locked_at": timestamp,
        })
        set_read_only(path)
        print(f"LOCKED: {rel}")

    manifest = {
        "lock_name": "Putnam Scanner geometry + Studio layout lock",
        "created_at": timestamp,
        "purpose": "Protect known-good v0.7 geometry and current Studio HTML layout from accidental patch drift.",
        "locked_files": entries,
        "rules": [
            "Do not modify known_good/template_region_warp_matcher_v0_7.py unless deliberately creating a new geometry baseline.",
            "Do not replace scanner_studio.html in OCR/server patches unless the user explicitly asks for UI/layout changes.",
            "Run verify_project_locks.py after applying any patch.",
            "Use unlock_locked_files.py only for deliberate geometry/layout changes, then relock_project_files.py after verification.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written: {MANIFEST}")
    print("Done. Geometry and Studio layout are now protected.")

if __name__ == "__main__":
    main()
