from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from Platform.putnam_paths import DATA_CONFIG_DIR, DATA_EXPORTS_DIR, PUTNAM_OS_DIR


DEFAULT_ETB_CAPACITY = 400
DEFAULT_ETB_LOCATION_CAPACITY = 40
ETB_LOCATION_CODES = tuple("ABCDEFGHIJ")
LOCATION_STATUSES = ["Empty", "Active", "Full", "Location Complete", "Needs Review", "Archived"]
ETB_RE = re.compile(r"^ETB-(\d{2,3})$")
ETB_LOCATION_RE = re.compile(r"^ETB-(\d{2,3})-([A-Z])$")
CARDVECTOR_WEB_BASE_URL = "https://cardvector.app"
ETB_OPERATIONAL_DATA_DIR = PUTNAM_OS_DIR / "System" / "data" / "inventory"
OLD_ETB_LOCATION_REGISTRY = DATA_CONFIG_DIR / "etb_location_registry.json"
ETB_LOCATION_REGISTRY = ETB_OPERATIONAL_DATA_DIR / "etb_location_registry.json"
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
        raise ValueError("ETB status must be Empty, Active, Full, Location Complete, Needs Review, or Archived.")
    return status


def normalize_location_code(value: str) -> str:
    code = str(value or "").strip().upper()
    if code not in ETB_LOCATION_CODES:
        raise ValueError("ETB location must be one of A-J.")
    return code


def etb_location_id(etb_code: str, location_code: str) -> str:
    return f"{normalize_etb_code(etb_code)}-{normalize_location_code(location_code)}"


def parse_etb_location_id(value: str) -> tuple[str, str, str]:
    code = str(value or "").strip().upper()
    match = ETB_LOCATION_RE.match(code)
    if not match:
        raise ValueError("ETB location must use ETB-###-Letter format, example ETB-001-A.")
    etb_code = f"ETB-{int(match.group(1)):03d}"
    location_code = normalize_location_code(match.group(2))
    return etb_code, location_code, etb_location_id(etb_code, location_code)


def etb_qr_payload(etb_code: str) -> str:
    return f"{CARDVECTOR_WEB_BASE_URL}/etb/{normalize_etb_code(etb_code)}"


def location_qr_payload(etb_code: str, location_code: str) -> str:
    return f"{CARDVECTOR_WEB_BASE_URL}/location/{normalize_etb_code(etb_code)}/{normalize_location_code(location_code)}"


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


def migrate_etb_location_registry() -> Path:
    if ETB_LOCATION_REGISTRY.exists():
        return ETB_LOCATION_REGISTRY
    if OLD_ETB_LOCATION_REGISTRY.exists():
        ETB_LOCATION_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        ETB_LOCATION_REGISTRY.write_bytes(OLD_ETB_LOCATION_REGISTRY.read_bytes())
    return ETB_LOCATION_REGISTRY


def load_etb_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or migrate_etb_location_registry()
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
    registry_path = path or migrate_etb_location_registry()
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
            "qr_payload": item.get("qr_payload") or location_qr_payload(etb_code, code),
            "capacity": capacity,
            "stored_count": assigned,
            "remaining_capacity": remaining,
            "status": normalize_status(status),
            "assigned_batch": item.get("assigned_batch", item.get("assigned_session", "")),
            "carduploader_batch_url": item.get("carduploader_batch_url", ""),
            "carduploader_batch_id": item.get("carduploader_batch_id", ""),
            "carduploader_batch_name": item.get("carduploader_batch_name", ""),
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
    item["qr_payload"] = item.get("qr_payload") or etb_qr_payload(code)
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


def supabase_etb_location_rows() -> tuple[list[dict[str, Any]], str]:
    """Return canonical Supabase registry rows in the legacy UI shape.

    The local JSON registry remains the compatibility cache/export path until
    the production Supabase migration and data import are approved. This helper
    is intentionally read-only and fail-closed so an unavailable canonical
    registry cannot erase or override local data.
    """
    try:
        from Platform.cardvector.integrations.supabase import (
            SupabaseRegistryClient,
            canonical_rows_to_legacy_etb_rows,
        )

        rows = canonical_rows_to_legacy_etb_rows(SupabaseRegistryClient().list_locations())
        return sorted(rows, key=location_sort_key), ""
    except Exception as exc:
        return [], str(exc)


def shared_etb_location_rows(path: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read the shared registry when available, otherwise fall back to JSON."""
    cloud_rows, warning = supabase_etb_location_rows()
    if cloud_rows:
        return cloud_rows, {
            "source": "supabase",
            "warning": "",
            "fallback": False,
        }
    rows = etb_location_rows(path)
    return rows, {
        "source": "legacy_json_cache",
        "warning": warning,
        "fallback": True,
    }


def location_is_cloud_provisioned(location: dict[str, Any], active_location: str = "") -> bool:
    """Return whether a local A-J slot represents a real cloud-visible location."""
    try:
        code = normalize_location_code(location.get("location_code", ""))
    except ValueError:
        return False
    if bool(location.get("cloud_provisioned")):
        return True
    if active_location and code == normalize_location_code(active_location):
        return True
    if int(location.get("stored_count", location.get("estimated_assigned_count", 0)) or 0) > 0:
        return True
    try:
        if normalize_status(location.get("status") or "Empty") != "Empty":
            return True
    except ValueError:
        return True
    return any(
        str(location.get(field) or "").strip()
        for field in (
            "assigned_batch",
            "assigned_session",
            "carduploader_batch_id",
            "carduploader_batch_url",
            "carduploader_batch_name",
        )
    )


def next_unprovisioned_location_code(existing_codes: list[str] | tuple[str, ...] | set[str]) -> str:
    existing = set()
    for value in existing_codes or []:
        try:
            existing.add(normalize_location_code(value))
        except ValueError:
            continue
    return next((code for code in ETB_LOCATION_CODES if code not in existing), "")


def cloud_location_registry_snapshot(path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Build the validated desktop-to-cloud identity snapshot.

    Desktop A-J rows are capacity slots. Only explicitly provisioned or
    operationally used slots are cloud identities. All earlier letters are
    included to preserve canonical sequential allocation.
    """
    registry = load_etb_registry(path)
    etbs: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    etb_statuses = {"Empty", "Active", "Full", "Needs Review", "Archived"}

    for raw_etb in registry.get("locations", []):
        try:
            normalized = normalize_etb_record(raw_etb, registry)
        except (TypeError, ValueError):
            continue
        etb_id = normalized["location_code"]
        explicit_active = str(
            raw_etb.get("current_active_location") or raw_etb.get("active_location") or ""
        ).strip().upper()
        if explicit_active:
            try:
                explicit_active = normalize_location_code(explicit_active)
            except ValueError:
                explicit_active = ""
        status = str(normalized.get("status") or "Empty")
        if status not in etb_statuses:
            status = "Active" if int(normalized.get("stored_count") or 0) else "Empty"
        etbs.append({
            "etb_id": etb_id,
            "status": status,
            "capacity": int(normalized.get("total_capacity") or DEFAULT_ETB_CAPACITY),
            "active_location_code": explicit_active or None,
            "source_updated_at": str(raw_etb.get("updated_at") or registry.get("updated_at") or ""),
        })

        children = normalized.get("locations", [])
        signaled_codes = [
            normalize_location_code(child.get("location_code", ""))
            for child in children
            if location_is_cloud_provisioned(child, explicit_active)
        ]
        if not signaled_codes:
            continue
        highest_index = max(ETB_LOCATION_CODES.index(code) for code in signaled_codes)
        provisioned_codes = set(ETB_LOCATION_CODES[: highest_index + 1])
        for child in children:
            code = normalize_location_code(child.get("location_code", ""))
            if code not in provisioned_codes:
                continue
            capacity = int(child.get("capacity") or DEFAULT_ETB_LOCATION_CAPACITY)
            stored_count = max(0, int(child.get("stored_count") or 0))
            status = normalize_status(child.get("status") or "Empty")
            locations.append({
                "location_id": etb_location_id(etb_id, code),
                "etb_id": etb_id,
                "location_code": code,
                "status": status,
                "capacity": capacity,
                "stored_count": stored_count,
                "assigned_batch": str(child.get("assigned_batch") or ""),
                "source_updated_at": str(child.get("updated_at") or raw_etb.get("updated_at") or ""),
            })

    return {"etbs": etbs, "locations": locations}


def merge_cloud_location_registry(
    cloud_etbs: list[dict[str, Any]],
    cloud_locations: list[dict[str, Any]],
    path: Path | None = None,
) -> dict[str, Any]:
    """Merge cloud identity/provisioning into the offline desktop projection."""
    registry = load_etb_registry(path)
    local_etbs: dict[str, dict[str, Any]] = {}
    for item in registry.get("locations", []):
        try:
            local_etbs[normalize_etb_code(item.get("location_code", ""))] = item
        except ValueError:
            continue

    changed = False
    added_etbs: list[str] = []
    provisioned_locations: list[str] = []
    now = timestamp()
    for cloud_etb in cloud_etbs or []:
        try:
            etb_id = normalize_etb_code(cloud_etb.get("etb_id", ""))
        except ValueError:
            continue
        local = local_etbs.get(etb_id)
        if local is None:
            local = {
                "location_code": etb_id,
                "etb_id": etb_id,
                "status": "Empty",
                "total_capacity": int(cloud_etb.get("capacity") or DEFAULT_ETB_CAPACITY),
                "created_at": str(cloud_etb.get("created_at") or now),
                "updated_at": now,
                "locations": [],
            }
            registry.setdefault("locations", []).append(local)
            local_etbs[etb_id] = local
            added_etbs.append(etb_id)
            changed = True
        if not local.get("cloud_registered"):
            local["cloud_registered"] = True
            changed = True
        active_code = str(cloud_etb.get("active_location_code") or "").strip()
        if active_code and not (local.get("current_active_location") or local.get("active_location")):
            try:
                local["active_location"] = normalize_location_code(active_code)
                local["current_active_location"] = local["active_location"]
                changed = True
            except ValueError:
                pass
        ensure_etb_location_records(local, registry)

    for cloud_location in cloud_locations or []:
        try:
            etb_id = normalize_etb_code(cloud_location.get("etb_id", ""))
            code = normalize_location_code(cloud_location.get("location_code", ""))
            canonical_id = etb_location_id(etb_id, code)
        except ValueError:
            continue
        if str(cloud_location.get("location_id") or canonical_id) != canonical_id:
            continue
        local_etb = local_etbs.get(etb_id)
        if local_etb is None:
            continue
        children = ensure_etb_location_records(local_etb, registry)
        child = next(item for item in children if item["location_code"] == code)
        if not child.get("cloud_provisioned"):
            child["cloud_provisioned"] = True
            child["cloud_location_id"] = canonical_id
            provisioned_locations.append(canonical_id)
            changed = True
        if int(child.get("stored_count") or 0) == 0 and child.get("status") == "Empty":
            cloud_capacity = int(cloud_location.get("capacity") or DEFAULT_ETB_LOCATION_CAPACITY)
            if int(child.get("capacity") or DEFAULT_ETB_LOCATION_CAPACITY) != cloud_capacity:
                child["capacity"] = cloud_capacity
                child["remaining_capacity"] = cloud_capacity
                changed = True
            cloud_batch = str(cloud_location.get("assigned_batch") or "")
            if cloud_batch and not child.get("assigned_batch"):
                child["assigned_batch"] = cloud_batch
                changed = True
        local_etb["locations"] = children

    if changed:
        registry.setdefault("history", []).append({
            "timestamp": now,
            "action": "cloud_location_sync",
            "etbs_added": added_etbs,
            "locations_provisioned": provisioned_locations,
        })
        save_etb_registry(registry, path)
    return {
        "changed": changed,
        "etbs_received": len(cloud_etbs or []),
        "locations_received": len(cloud_locations or []),
        "etbs_added": added_etbs,
        "locations_provisioned": provisioned_locations,
    }


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
        "qr_payload": etb_qr_payload(code),
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


def ensure_etb_record(code: str, registry: dict[str, Any]) -> dict[str, Any]:
    normalized_code = normalize_etb_code(code)
    for location in registry.get("locations", []):
        try:
            if normalize_etb_code(location.get("location_code", "")) == normalized_code:
                return location
        except ValueError:
            continue
    now = timestamp()
    location = {
        "location_code": normalized_code,
        "etb_id": normalized_code,
        "qr_payload": etb_qr_payload(normalized_code),
        "status": "Empty",
        "total_capacity": DEFAULT_ETB_CAPACITY,
        "stored_count": 0,
        "remaining_space": DEFAULT_ETB_CAPACITY,
        "active_location": "A",
        "current_active_location": "A",
        "created_at": now,
        "updated_at": now,
        "locations": [],
    }
    ensure_etb_location_records(location, registry)
    registry.setdefault("locations", []).append(location)
    registry.setdefault("history", []).append({
        "timestamp": now,
        "location_code": normalized_code,
        "action": "created_from_batch_location",
        "status": "Empty",
    })
    return location


def record_completed_batch_location(
    batch_location: str,
    total_count: int | None,
    *,
    game: str = "",
    source: str = "",
    note: str = "",
    path: Path | None = None,
) -> dict[str, Any]:
    """Reflect a completed batch/User-SKU location in the shared ETB registry.

    The legacy seller tools use two-digit values such as ``ETB-07-A``. The
    shared registry and Supabase use ``ETB-007-A``. This bridge keeps the old
    callers working while ensuring the shared registry receives the canonical
    identity and the actual completed count.
    """
    etb_code, location_code, canonical_location_id = parse_etb_location_id(batch_location)
    try:
        count = max(0, int(total_count or 0))
    except (TypeError, ValueError):
        count = 0
    registry = load_etb_registry(path)
    now = timestamp()
    etb = ensure_etb_record(etb_code, registry)
    children = ensure_etb_location_records(etb, registry)
    for child in children:
        if normalize_location_code(child.get("location_code", "")) != location_code:
            continue
        capacity = int(child.get("capacity") or DEFAULT_ETB_LOCATION_CAPACITY)
        child["location_id"] = canonical_location_id
        child["stored_count"] = count
        child["remaining_capacity"] = max(0, capacity - count)
        child["status"] = "Location Complete" if count > 0 else "Needs Review"
        child["assigned_batch"] = canonical_location_id
        child.setdefault("metadata", {})
        child["updated_at"] = now
        break
    etb["locations"] = children
    etb["active_location"] = next_available_location_code(children, location_code)
    etb["current_active_location"] = etb["active_location"]
    etb["updated_at"] = now
    registry.setdefault("history", []).append({
        "timestamp": now,
        "location_code": etb_code,
        "location": location_code,
        "location_id": canonical_location_id,
        "action": "batch_location_completed",
        "status": "Location Complete" if count > 0 else "Needs Review",
        "captured_count": count,
        "game": str(game or ""),
        "source": str(source or ""),
        "note": str(note or ""),
    })
    save_etb_registry(registry, path)
    return normalize_etb_record(etb, registry)


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
                stored_count = capacity if captured_count is None else max(0, int(captured_count or 0))
                child["stored_count"] = stored_count
                child["remaining_capacity"] = max(0, capacity - stored_count)
                child["status"] = "Location Complete" if stored_count > 0 else "Needs Review"
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
    etb_match = re.fullmatch(r"(?:cardvector://|https://cardvector\.app/)etb/(ETB-\d{3})", value, re.IGNORECASE)
    location_match = re.fullmatch(r"(?:cardvector://|https://cardvector\.app/)location/(ETB-\d{3})/([A-J])", value, re.IGNORECASE)
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
        "carduploader_batch_url": location.get("carduploader_batch_url", ""),
        "carduploader_batch_id": location.get("carduploader_batch_id", ""),
        "carduploader_batch_name": location.get("carduploader_batch_name", ""),
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
        f"CardUploader Batch: {resolved.get('carduploader_batch_name', '') or resolved.get('carduploader_batch_id', '') or '(none)'}",
        f"CardUploader URL: {resolved.get('carduploader_batch_url', '') or '(none)'}",
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
