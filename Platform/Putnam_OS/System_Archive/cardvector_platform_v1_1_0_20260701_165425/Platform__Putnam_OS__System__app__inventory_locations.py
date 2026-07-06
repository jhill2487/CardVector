from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from Platform.putnam_paths import DATA_CONFIG_DIR, DATA_EXPORTS_DIR


DEFAULT_ETB_CAPACITY = 100
LOCATION_STATUSES = ["Active", "Full", "Available", "Empty"]
ETB_RE = re.compile(r"^ETB-(\d{3})$")
ETB_LOCATION_REGISTRY = DATA_CONFIG_DIR / "etb_location_registry.json"
ETB_LABEL_ROOT = DATA_EXPORTS_DIR / "Inventory_Location_Labels"


def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_etb_code(value: str) -> str:
    code = str(value or "").strip().upper()
    match = ETB_RE.match(code)
    if not match:
        raise ValueError("ETB location must use ETB-### format, example ETB-001.")
    return f"ETB-{int(match.group(1)):03d}"


def normalize_status(value: str) -> str:
    status = str(value or "").strip().title()
    if status not in LOCATION_STATUSES:
        raise ValueError("ETB status must be Active, Full, Available, or Empty.")
    return status


def _default_registry() -> dict[str, Any]:
    now = timestamp()
    return {
        "version": 1,
        "updated_at": now,
        "default_capacity": DEFAULT_ETB_CAPACITY,
        "locations": [],
        "history": [],
    }


def load_etb_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or ETB_LOCATION_REGISTRY
    if not registry_path.exists():
        return _default_registry()
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    except Exception:
        data = _default_registry()
    data.setdefault("version", 1)
    data.setdefault("default_capacity", DEFAULT_ETB_CAPACITY)
    data.setdefault("locations", [])
    data.setdefault("history", [])
    return data


def save_etb_registry(registry: dict[str, Any], path: Path | None = None) -> Path:
    registry_path = path or ETB_LOCATION_REGISTRY
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = timestamp()
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry_path


def location_sort_key(location: dict[str, Any]) -> int:
    try:
        return int(str(location.get("location_code", "ETB-999")).split("-")[1])
    except Exception:
        return 999999


def etb_location_rows(path: Path | None = None) -> list[dict[str, Any]]:
    registry = load_etb_registry(path)
    rows = []
    for location in registry.get("locations", []):
        capacity = int(location.get("estimated_capacity") or registry.get("default_capacity") or DEFAULT_ETB_CAPACITY)
        assigned = location.get("estimated_assigned_count")
        assigned_count = int(assigned) if str(assigned or "").strip() else 0
        rows.append({
            "location_code": normalize_etb_code(location.get("location_code", "")),
            "status": normalize_status(location.get("status", "Available")),
            "estimated_capacity": capacity,
            "estimated_assigned_count": assigned_count,
            "estimated_remaining_capacity": max(0, capacity - assigned_count),
            "created_at": location.get("created_at", ""),
            "updated_at": location.get("updated_at", ""),
        })
    return sorted(rows, key=location_sort_key)


def next_etb_code(path: Path | None = None) -> str:
    rows = etb_location_rows(path)
    if not rows:
        return "ETB-001"
    next_number = max(location_sort_key(row) for row in rows) + 1
    return f"ETB-{next_number:03d}"


def create_etb_location(path: Path | None = None, capacity: int = DEFAULT_ETB_CAPACITY) -> dict[str, Any]:
    registry = load_etb_registry(path)
    code = next_etb_code(path)
    now = timestamp()
    location = {
        "location_code": code,
        "status": "Available",
        "estimated_capacity": int(capacity or DEFAULT_ETB_CAPACITY),
        "estimated_assigned_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    registry.setdefault("locations", []).append(location)
    registry.setdefault("history", []).append({
        "timestamp": now,
        "location_code": code,
        "action": "created",
        "status": "Available",
    })
    save_etb_registry(registry, path)
    return location


def update_etb_status(code: str, status: str, path: Path | None = None) -> dict[str, Any]:
    normalized_code = normalize_etb_code(code)
    normalized_status = normalize_status(status)
    registry = load_etb_registry(path)
    for location in registry.get("locations", []):
        if normalize_etb_code(location.get("location_code", "")) == normalized_code:
            location["status"] = normalized_status
            location["updated_at"] = timestamp()
            registry.setdefault("history", []).append({
                "timestamp": location["updated_at"],
                "location_code": normalized_code,
                "action": "status_updated",
                "status": normalized_status,
            })
            save_etb_registry(registry, path)
            return location
    raise ValueError(f"ETB location not found: {normalized_code}")


def _label_html(code: str) -> str:
    escaped_code = html.escape(code)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escaped_code} Label</title>
  <style>
    @page {{ size: 4in 2in; margin: 0.15in; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      color: #111;
    }}
    .label {{
      border: 2px solid #111;
      width: 95%;
      height: 85%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 64px;
      font-weight: 800;
      letter-spacing: 1px;
    }}
  </style>
</head>
<body>
  <div class="label">{escaped_code}</div>
</body>
</html>
"""


def generate_etb_label_files(rows: list[dict[str, Any]] | None = None, output_dir: Path | None = None) -> dict[str, Any]:
    label_dir = output_dir or ETB_LABEL_ROOT
    label_dir.mkdir(parents=True, exist_ok=True)
    label_rows = rows if rows is not None else etb_location_rows()
    html_files = []
    for row in label_rows:
        code = normalize_etb_code(row.get("location_code", ""))
        label_path = label_dir / f"{code}.html"
        label_path.write_text(_label_html(code), encoding="utf-8")
        html_files.append(label_path)
    index_lines = [
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>ETB Labels</title></head><body>",
        "<h1>Putnam Collectibles ETB Labels</h1>",
    ]
    for label_path in html_files:
        code = html.escape(label_path.stem)
        index_lines.append(f'<p><a href="{html.escape(label_path.name)}">{code}</a></p>')
    index_lines.append("</body></html>")
    index_path = label_dir / "index.html"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    return {
        "label_dir": label_dir,
        "index_file": index_path,
        "html_files": html_files,
    }
