from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from Platform.putnam_paths import DATA_CONFIG_DIR, DATA_EXPORTS_DIR


DEFAULT_ETB_CAPACITY = 400
DEFAULT_ETB_LOCATION_CAPACITY = 40
ETB_LOCATION_CODES = tuple("ABCDEFGHIJ")
LOCATION_STATUSES = ["Empty", "Active", "Full", "Location Complete", "Needs Review", "Archived"]
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
    if status == "Available":
        status = "Empty"
    if status not in LOCATION_STATUSES:
        raise ValueError("ETB status must be Empty, Active, Full, Needs Review, or Archived.")
    return status


def normalize_location_code(value: str) -> str:
    code = str(value or "").strip().upper()
    if code not in ETB_LOCATION_CODES:
        raise ValueError("ETB location must be one of A-J.")
    return code


def etb_location_id(etb_code: str, location_code: str) -> str:
    return f"{normalize_etb_code(etb_code)}-{normalize_location_code(location_code)}"


def active_location_from_record(location: dict[str, Any]) -> str:
    return normalize_location_code(
        location.get("current_active_location")
        or location.get("active_location")
        or location.get("active_location_code")
        or "A"
    )


def _default_registry() -> dict[str, Any]:
    now = timestamp()
    return {
        "version": 2,
        "updated_at": now,
        "default_etb_capacity": DEFAULT_ETB_CAPACITY,
        "default_location_capacity": DEFAULT_ETB_LOCATION_CAPACITY,
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
    data.setdefault("version", 2)
    data.setdefault("default_etb_capacity", data.get("default_capacity", DEFAULT_ETB_CAPACITY) or DEFAULT_ETB_CAPACITY)
    data["default_etb_capacity"] = int(data.get("default_etb_capacity") or DEFAULT_ETB_CAPACITY)
    if data["default_etb_capacity"] == 100:
        data["default_etb_capacity"] = DEFAULT_ETB_CAPACITY
    data.setdefault("default_location_capacity", DEFAULT_ETB_LOCATION_CAPACITY)
    data["default_location_capacity"] = int(data.get("default_location_capacity") or DEFAULT_ETB_LOCATION_CAPACITY)
    data["default_capacity"] = data["default_etb_capacity"]
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


def ensure_etb_location_records(location: dict[str, Any], registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = registry or {}
    etb_code = normalize_etb_code(location.get("location_code", ""))
    default_capacity = int(registry.get("default_location_capacity") or DEFAULT_ETB_LOCATION_CAPACITY)
    existing = {}
    for item in location.get("locations") or []:
        try:
            code = normalize_location_code(item.get("location_code", ""))
        except Exception:
            continue
        existing[code] = item
    records = []
    now = timestamp()
    for code in ETB_LOCATION_CODES:
        item = dict(existing.get(code) or {})
        assigned = int(item.get("stored_count", item.get("estimated_assigned_count", 0)) or 0)
        capacity = int(item.get("capacity", item.get("estimated_capacity", default_capacity)) or default_capacity)
        remaining = max(0, capacity - assigned)
        status = item.get("status") or ("Full" if remaining == 0 and capacity > 0 else "Active" if assigned else "Empty")
        records.append({
            "location_code": code,
            "location_id": etb_location_id(etb_code, code),
            "qr_payload": f"cardvector://location/{etb_code}/{code}",
            "capacity": capacity,
            "stored_count": assigned,
            "remaining_capacity": remaining,
            "status": normalize_status(status),
            "assigned_batch": item.get("assigned_batch", item.get("assigned_session", "")),
            "created_at": item.get("created_at") or location.get("created_at") or now,
            "updated_at": item.get("updated_at") or location.get("updated_at") or now,
        })
    location["locations"] = records
    return records


def etb_status_from_counts(stored_count: int, remaining: int, locations: list[dict[str, Any]]) -> str:
    if any(item.get("status") == "Archived" for item in locations):
        return "Archived"
    if any(item.get("status") == "Needs Review" for item in locations):
        return "Needs Review"
    if remaining <= 0:
        return "Full"
    if stored_count <= 0:
        return "Empty"
    return "Active"


def next_available_location_code(locations: list[dict[str, Any]], preferred: str = "") -> str:
    preferred_code = ""
    if preferred:
        try:
            preferred_code = normalize_location_code(preferred)
        except Exception:
            preferred_code = ""
    for location in locations:
        code = normalize_location_code(location.get("location_code", ""))
        remaining = int(location.get("remaining_capacity", 0) or 0)
        status = normalize_status(location.get("status") or "Empty")
        if preferred_code and code != preferred_code:
            continue
        if remaining > 0 and status not in {"Full", "Archived"}:
            return code
    for location in locations:
        code = normalize_location_code(location.get("location_code", ""))
        remaining = int(location.get("remaining_capacity", 0) or 0)
        status = normalize_status(location.get("status") or "Empty")
        if remaining > 0 and status not in {"Full", "Archived"}:
            return code
    return ETB_LOCATION_CODES[-1]


def normalize_etb_record(location: dict[str, Any], registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or {}
    code = normalize_etb_code(location.get("location_code", ""))
    item = dict(location)
    item["location_code"] = code
    item["etb_id"] = code
    item["qr_payload"] = f"cardvector://etb/{code}"
    item["total_capacity"] = int(item.get("total_capacity", item.get("estimated_capacity", registry.get("default_etb_capacity", DEFAULT_ETB_CAPACITY))) or DEFAULT_ETB_CAPACITY)
    if item["total_capacity"] == 100:
        item["total_capacity"] = DEFAULT_ETB_CAPACITY
    locations = ensure_etb_location_records(item, registry)
    try:
        active_location = active_location_from_record(item)
    except Exception:
        active_location = ""
    active_location = next_available_location_code(locations, active_location)
    stored_count = sum(int(loc.get("stored_count") or 0) for loc in locations)
    remaining = max(0, item["total_capacity"] - stored_count)
    item["stored_count"] = stored_count
    item["remaining_space"] = remaining
    item["active_location"] = active_location
    item["current_active_location"] = active_location
    current_status = normalize_status(item.get("status") or etb_status_from_counts(stored_count, remaining, locations))
    item["status"] = "Needs Review" if current_status == "Needs Review" else etb_status_from_counts(stored_count, remaining, locations)
    item["estimated_capacity"] = item["total_capacity"]
    item["estimated_assigned_count"] = stored_count
    item["estimated_remaining_capacity"] = remaining
    return item


def etb_location_rows(path: Path | None = None) -> list[dict[str, Any]]:
    registry = load_etb_registry(path)
    rows = []
    for location in registry.get("locations", []):
        row = normalize_etb_record(location, registry)
        row["location_summary"] = ", ".join(
            f"{loc['location_code']} {loc['stored_count']}/{loc['capacity']}"
            for loc in row.get("locations", [])
        )
        rows.append(row)
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
        "etb_id": code,
        "status": "Empty",
        "total_capacity": int(capacity or DEFAULT_ETB_CAPACITY),
        "stored_count": 0,
        "remaining_space": int(capacity or DEFAULT_ETB_CAPACITY),
        "active_location": "A",
        "current_active_location": "A",
        "qr_payload": f"cardvector://etb/{code}",
        "created_at": now,
        "updated_at": now,
    }
    ensure_etb_location_records(location, registry)
    location["estimated_capacity"] = location["total_capacity"]
    location["estimated_assigned_count"] = 0
    location["estimated_remaining_capacity"] = location["remaining_space"]
    registry.setdefault("locations", []).append(location)
    registry.setdefault("history", []).append({
        "timestamp": now,
        "location_code": code,
        "action": "created",
        "status": "Empty",
        "locations_created": list(ETB_LOCATION_CODES),
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


def current_active_location(code: str, path: Path | None = None) -> dict[str, Any]:
    normalized_code = normalize_etb_code(code)
    for location in etb_location_rows(path):
        if location["location_code"] != normalized_code:
            continue
        active_code = active_location_from_record(location)
        for child in location.get("locations", []):
            if normalize_location_code(child.get("location_code", "")) == active_code:
                return child
    raise ValueError(f"ETB location not found: {normalized_code}")


def set_current_active_location(code: str, location_code: str, path: Path | None = None) -> dict[str, Any]:
    normalized_code = normalize_etb_code(code)
    normalized_location = normalize_location_code(location_code)
    registry = load_etb_registry(path)
    now = timestamp()
    for location in registry.get("locations", []):
        if normalize_etb_code(location.get("location_code", "")) == normalized_code:
            ensure_etb_location_records(location, registry)
            location["active_location"] = normalized_location
            location["current_active_location"] = normalized_location
            location["updated_at"] = now
            registry.setdefault("history", []).append({
                "timestamp": now,
                "location_code": normalized_code,
                "location": normalized_location,
                "action": "active_location_updated",
            })
            save_etb_registry(registry, path)
            return normalize_etb_record(location, registry)
    raise ValueError(f"ETB location not found: {normalized_code}")


def mark_location_complete(code: str, location_code: str, path: Path | None = None, captured_count: int | None = None) -> dict[str, Any]:
    normalized_code = normalize_etb_code(code)
    normalized_location = normalize_location_code(location_code)
    registry = load_etb_registry(path)
    now = timestamp()
    for location in registry.get("locations", []):
        if normalize_etb_code(location.get("location_code", "")) != normalized_code:
            continue
        children = ensure_etb_location_records(location, registry)
        for child in children:
            if normalize_location_code(child.get("location_code", "")) == normalized_location:
                capacity = int(child.get("capacity") or DEFAULT_ETB_LOCATION_CAPACITY)
                stored_count = capacity if captured_count is None else max(0, min(capacity, int(captured_count or 0)))
                child["stored_count"] = stored_count
                child["remaining_capacity"] = max(0, capacity - stored_count)
                child["status"] = "Location Complete" if stored_count >= capacity else "Needs Review"
                child["updated_at"] = now
        location["locations"] = children
        location["active_location"] = next_available_location_code(children)
        location["current_active_location"] = location["active_location"]
        location["updated_at"] = now
        registry.setdefault("history", []).append({
            "timestamp": now,
            "location_code": normalized_code,
            "location": normalized_location,
            "action": "location_complete",
            "captured_count": captured_count,
        })
        save_etb_registry(registry, path)
        return normalize_etb_record(location, registry)
    raise ValueError(f"ETB location not found: {normalized_code}")


def assign_batch_to_location(code: str, location_code: str, batch_id: str, path: Path | None = None) -> dict[str, Any]:
    normalized_code = normalize_etb_code(code)
    normalized_location = normalize_location_code(location_code)
    batch = str(batch_id or "").strip()
    registry = load_etb_registry(path)
    now = timestamp()
    for location in registry.get("locations", []):
        if normalize_etb_code(location.get("location_code", "")) != normalized_code:
            continue
        children = ensure_etb_location_records(location, registry)
        for child in children:
            if normalize_location_code(child.get("location_code", "")) == normalized_location:
                child["assigned_batch"] = batch
                child["updated_at"] = now
        location["locations"] = children
        location["updated_at"] = now
        registry.setdefault("history", []).append({
            "timestamp": now,
            "location_code": normalized_code,
            "location": normalized_location,
            "action": "batch_assigned",
            "batch": batch,
        })
        save_etb_registry(registry, path)
        return normalize_etb_record(location, registry)
    raise ValueError(f"ETB location not found: {normalized_code}")


def resolve_cardvector_qr_payload(payload: str, path: Path | None = None) -> dict[str, Any]:
    value = str(payload or "").strip()
    etb_match = re.fullmatch(r"cardvector://etb/(ETB-\d{3})", value, re.IGNORECASE)
    location_match = re.fullmatch(r"cardvector://location/(ETB-\d{3})/([A-J])", value, re.IGNORECASE)
    if not etb_match and not location_match:
        raise ValueError("Unsupported CardVector QR payload.")

    etb_code = normalize_etb_code((etb_match or location_match).group(1))
    rows = etb_location_rows(path)
    etb = next((row for row in rows if row["location_code"] == etb_code), None)
    if not etb:
        raise ValueError(f"ETB not found: {etb_code}")

    if etb_match:
        locations = etb.get("locations", [])
        summary = [
            f"{item.get('location_code')}: {int(item.get('stored_count') or 0)}/{int(item.get('capacity') or DEFAULT_ETB_LOCATION_CAPACITY)} {item.get('status', '')}".strip()
            for item in locations
        ]
        return {
            "type": "etb",
            "payload": value,
            "title": etb_code,
            "etb_id": etb_code,
            "status": etb.get("status", ""),
            "stored": int(etb.get("stored_count", 0) or 0),
            "capacity": int(etb.get("total_capacity", DEFAULT_ETB_CAPACITY) or DEFAULT_ETB_CAPACITY),
            "active_location": etb.get("current_active_location") or etb.get("active_location") or "",
            "locations_summary": summary,
            "last_updated": etb.get("updated_at", ""),
        }

    location_code = normalize_location_code(location_match.group(2))
    location = next(
        (item for item in etb.get("locations", []) if normalize_location_code(item.get("location_code", "")) == location_code),
        None,
    )
    if not location:
        raise ValueError(f"Location not found: {etb_code}-{location_code}")
    return {
        "type": "location",
        "payload": value,
        "title": f"{etb_code} Location {location_code}",
        "etb_id": etb_code,
        "location": location_code,
        "stored": int(location.get("stored_count", 0) or 0),
        "capacity": int(location.get("capacity", DEFAULT_ETB_LOCATION_CAPACITY) or DEFAULT_ETB_LOCATION_CAPACITY),
        "status": location.get("status", ""),
        "assigned_batch": location.get("assigned_batch") or location.get("assigned_session") or "",
        "last_updated": location.get("updated_at", ""),
    }


def qr_resolution_text(resolved: dict[str, Any]) -> str:
    if resolved.get("type") == "etb":
        lines = [
            f"ETB ID: {resolved.get('etb_id', '')}",
            f"Status: {resolved.get('status', '')}",
            f"Stored: {resolved.get('stored', 0)}/{resolved.get('capacity', DEFAULT_ETB_CAPACITY)}",
            f"Active Location: {resolved.get('active_location', '') or '(none)'}",
            f"Last Updated: {resolved.get('last_updated', '') or '(none)'}",
            "",
            "Locations A-J:",
        ]
        lines.extend(f"- {item}" for item in resolved.get("locations_summary", []))
        return "\n".join(lines)
    return "\n".join([
        f"ETB ID: {resolved.get('etb_id', '')}",
        f"Location: {resolved.get('location', '')}",
        f"Occupancy: {resolved.get('stored', 0)}/{resolved.get('capacity', DEFAULT_ETB_LOCATION_CAPACITY)}",
        f"Status: {resolved.get('status', '')}",
        f"Assigned Batch: {resolved.get('assigned_batch', '') or '(none)'}",
        f"Last Updated: {resolved.get('last_updated', '') or '(none)'}",
    ])


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
