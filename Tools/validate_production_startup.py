from __future__ import annotations

import compileall
import importlib
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path


def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents]:
        if (candidate / "AGENTS.md").exists() and (candidate / "Docs" / "AGENTS.md").exists():
            return candidate
    raise RuntimeError("Could not locate PutnamCollectibles root.")


ROOT = find_repo_root()
PUTNAM_OS = ROOT / "Platform" / "Putnam_OS"
SYSTEM = PUTNAM_OS / "System"
APP_DIR = SYSTEM / "app"
LOG_DIR = SYSTEM / "logs" / "Startup Logs"


def status_line(name: str, ok: bool, detail: str = "") -> str:
    label = "PASS" if ok else "FAIL"
    return f"{label} | {name}" + (f" | {detail}" if detail else "")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = LOG_DIR / f"startup_validation_{stamp}.txt"
    checks: list[tuple[str, bool, str]] = []

    compile_ok = compileall.compile_dir(str(PUTNAM_OS), quiet=1)
    checks.append(("Compile CardVector OS Python", bool(compile_ok), str(PUTNAM_OS)))

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))

    for module_name in ["Platform.putnam_paths", "capture_studio", "inventory_locations", "orders_fulfillment", "putnam_os"]:
        try:
            importlib.import_module(module_name)
            checks.append((f"Import {module_name}", True, ""))
        except Exception as exc:
            checks.append((f"Import {module_name}", False, f"{exc}\n{traceback.format_exc()}"))

    required_folders = [
        ROOT / "Data" / "Imports",
        ROOT / "Data" / "Exports",
        ROOT / "Data" / "Logs",
        PUTNAM_OS / "Incoming Files",
        PUTNAM_OS / "Completed Jobs",
        SYSTEM / "config",
        LOG_DIR,
    ]
    for folder in required_folders:
        checks.append((f"Required folder {folder}", folder.exists(), ""))

    ok = all(item[1] for item in checks)
    lines = [
        "CardVector OS v1.0.0 - CardVector Platform v1.0",
        f"Startup validation: {'PASS' if ok else 'FAIL'}",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Repository: {ROOT}",
        "",
    ]
    lines.extend(status_line(name, passed, detail) for name, passed, detail in checks)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    machine_report = LOG_DIR / "startup_validation_latest.json"
    machine_report.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "release": "CardVector Platform v1.0",
                "ok": ok,
                "report": str(report_path),
                "checks": [{"name": name, "ok": passed, "detail": detail} for name, passed, detail in checks],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"CardVector OS v1.0.0 - CardVector Platform v1.0")
    print(f"Startup validation: {'PASS' if ok else 'FAIL'}")
    print(f"Report: {report_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
