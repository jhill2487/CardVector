from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


def _bootstrap_repo_import_path() -> None:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents]:
        if (
            (candidate / ".putnam_root").exists()
            or ((candidate / "AGENTS.md").exists() and (candidate / "Docs" / "AGENTS.md").exists())
        ):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return


_bootstrap_repo_import_path()

from Platform.putnam_paths import PUTNAM_OS_DIR, ROOT
from Platform.Putnam_OS.System.app.inventory_locations import (
    DEFAULT_ETB_LOCATION_CAPACITY,
    cloud_location_registry_snapshot,
    merge_cloud_location_registry,
    normalize_etb_code,
    normalize_location_code,
)
from Platform.cardvector.integrations.supabase import SupabaseRegistryClient
from Platform.cardvector.integrations.supabase import canonical_registry_uuid, legacy_status_to_canonical


MOBILE_CAPTURE_ROOT = ROOT / "MobileCapture"
MOBILE_PENDING_DIR = MOBILE_CAPTURE_ROOT / "Pending"
MOBILE_PROCESSING_DIR = MOBILE_CAPTURE_ROOT / "Processing"
MOBILE_CONVERTED_DIR = MOBILE_CAPTURE_ROOT / "Converted"
MOBILE_FAILED_DIR = MOBILE_CAPTURE_ROOT / "Failed"
INVENTORY_CONVERSION_DIR = PUTNAM_OS_DIR / "System" / "data" / "inventory_conversion"
INVENTORY_CONVERSION_SESSIONS_DIR = INVENTORY_CONVERSION_DIR / "sessions"
CURRENT_INVENTORY_CONVERSION = INVENTORY_CONVERSION_DIR / "current_inventory_conversion.json"
CAPTURE_ROOT = ROOT / "Capture"
INVENTORY_CONVERSION_CAPTURE_ROOT = CAPTURE_ROOT / "Physical_Inventory_Conversion"


class MobileCaptureError(RuntimeError):
    pass


PRIMARY_QUEUE_STATUSES = ("PENDING_CONVERSION", "PROCESSING", "FAILED", "CONVERTED", "CANCELLED")
DIAGNOSTIC_QUEUE_STATUSES = ("DRAFT", "UPLOADING")
QUEUE_STATUS_LABELS = {
    "PENDING_CONVERSION": "Pending",
    "PROCESSING": "Processing",
    "CONVERTED": "Converted",
    "FAILED": "Failed",
    "CANCELLED": "Cancelled",
    "DRAFT": "Draft",
    "UPLOADING": "Uploading",
}


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_etb_location(value: str) -> tuple[str, str, str]:
    raw = str(value or "").strip().upper()
    parts = raw.rsplit("-", 1)
    if len(parts) != 2:
        raise MobileCaptureError(f"Invalid ETB location: {value}")
    etb = normalize_etb_code(parts[0])
    location = normalize_location_code(parts[1])
    return etb, location, f"{etb}-{location}"


def session_location_id(session: dict[str, Any]) -> str:
    location_id = str(session.get("etb_location") or session.get("etb_location_id") or "").strip()
    if not location_id:
        raise MobileCaptureError("Mobile capture session is missing etb_location/etb_location_id.")
    return parse_etb_location(location_id)[2]


def today_folder_name(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%m.%d.%y")


def session_capture_type(session: dict[str, Any]) -> str:
    """Return the normalized capture workflow.

    Existing mobile sessions predate capture-type selection, so they safely
    default to Physical Inventory Conversion.
    """
    device = session.get("source_device") or session.get("device") or {}
    raw = (
        session.get("capture_type")
        or (device.get("capture_type") if isinstance(device, dict) else "")
        or "PHYSICAL_INVENTORY"
    )
    normalized = str(raw or "").strip().upper().replace("-", "_").replace(" ", "_")
    if normalized in {"NEW", "NEW_CAPTURE", "NEW_INVENTORY"}:
        return "NEW_CAPTURE"
    return "PHYSICAL_INVENTORY"


def session_capture_layout(session: dict[str, Any]) -> str:
    """Return how mobile images map to cards and sides.

    The mobile site stores this in the existing private device metadata so the
    upload schema and RLS contract remain unchanged. Legacy sessions safely
    retain the historical front-only behavior.
    """
    device = session.get("source_device") or session.get("device") or {}
    raw = (
        session.get("capture_layout")
        or (device.get("capture_layout") if isinstance(device, dict) else "")
        or "FRONT_ONLY"
    )
    normalized = re.sub(r"[-+\s]+", "_", str(raw or "").strip().upper())
    if normalized in {"FRONT_BACK", "FRONT_AND_BACK", "BOTH", "PAIRED"}:
        return "FRONT_BACK"
    return "FRONT_ONLY"


def capture_record_position(sequence_number: int, capture_layout: str) -> tuple[int, str]:
    sequence = max(1, int(sequence_number))
    if session_capture_layout({"capture_layout": capture_layout}) == "FRONT_BACK":
        return ((sequence - 1) // 2) + 1, "front" if sequence % 2 else "back"
    return sequence, "front"


def next_capture_folder(capture_type: str = "PHYSICAL_INVENTORY") -> Path:
    """Create the next canonical dated capture folder.

    New captures land directly under Capture. Legacy physical-inventory
    sessions land under Capture/Physical_Inventory_Conversion. The first
    session of a day uses MM.DD.YY; later sessions use .1, .2, and so on.
    """
    root = CAPTURE_ROOT if capture_type == "NEW_CAPTURE" else INVENTORY_CONVERSION_CAPTURE_ROOT
    root.mkdir(parents=True, exist_ok=True)
    base = today_folder_name()
    candidate = root / base
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = root / f"{base}.{suffix}"
    candidate.mkdir(parents=False)
    return candidate


def safe_path_part(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in str(value or "").strip())
    return safe or "unassigned"


def workstation_name() -> str:
    return os.environ.get("COMPUTERNAME") or socket.gethostname() or "unknown-workstation"


def sanitize_error_message(value: Any, limit: int = 700) -> str:
    text = str(value or "").strip()
    text = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", text, flags=re.IGNORECASE)
    text = re.sub(r"eyJ[A-Za-z0-9._-]+", "[redacted-token]", text)
    text = re.sub(r"https://[a-z0-9-]+\.supabase\.co", "[supabase-url]", text, flags=re.IGNORECASE)
    text = re.sub(r"service[_ -]?role[^,\s)\"']*", "service-role-[redacted]", text, flags=re.IGNORECASE)
    return text[:limit]


def supabase_config() -> tuple[str, str]:
    url = os.environ.get("CARDVECTOR_SUPABASE_URL") or os.environ.get("SUPABASE_URL") or ""
    key = (
        os.environ.get("CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    )
    url = url.rstrip("/")
    key = key.strip()
    if not url or not key:
        raise MobileCaptureError(
            "Set CARDVECTOR_SUPABASE_URL and CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY before using the mobile capture queue."
        )
    return url, key


def request_json(method: str, path: str, body: Any | None = None, prefer: str | None = None) -> Any:
    base_url, key = supabase_config()
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MobileCaptureError(f"Supabase request failed: {exc.code} {sanitize_error_message(detail)}") from exc
    if not payload:
        return None
    return json.loads(payload)


def canonical_location_rows_from_snapshot(
    snapshot: dict[str, list[dict[str, Any]]],
    existing_rows: list[Any],
) -> tuple[list[dict[str, Any]], str]:
    existing_by_display = {
        str(getattr(item, "display_code", "") or "").upper(): item
        for item in existing_rows or []
        if str(getattr(item, "display_code", "") or "").strip()
    }
    existing_owner = next(
        (
            str(getattr(item, "owner_user_id", "") or "")
            for item in existing_rows or []
            if str(getattr(item, "owner_user_id", "") or "")
        ),
        "",
    )
    existing_stored_by_display = {
        str(getattr(item, "display_code", "") or "").upper(): max(
            0,
            int(getattr(item, "stored_count", 0) or 0),
        )
        for item in existing_rows or []
        if str(getattr(item, "display_code", "") or "").strip()
    }
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    parent_ids: dict[str, str] = {}
    for etb in snapshot.get("etbs", []) or []:
        etb_id = normalize_etb_code(etb.get("etb_id", ""))
        existing = existing_by_display.get(etb_id)
        owner_id = str(getattr(existing, "owner_user_id", "") or existing_owner)
        if existing is None and not owner_id:
            warnings.append(f"Skipped {etb_id}: owner_user_id unavailable for new canonical location.")
            continue
        row_id = str(getattr(existing, "id", "") or canonical_registry_uuid("location", etb_id))
        parent_ids[etb_id] = row_id
        row = {
            "id": row_id,
            "name": etb_id,
            "location_type": "etb",
            "status": legacy_status_to_canonical(etb.get("status", "")),
            "source": "CardVector OS",
            "legacy_id": etb_id,
            "legacy_etb_id": etb_id,
            "display_code": etb_id,
            "capacity": int(etb.get("capacity") or 400),
            "stored_count": 0,
            "sync_state": "synced",
            "metadata": {
                "active_location": etb.get("active_location_code") or "",
                "current_active_location": etb.get("active_location_code") or "",
                "source_updated_at": etb.get("source_updated_at") or "",
            },
        }
        if owner_id:
            row["owner_user_id"] = owner_id
        rows.append(row)

    stored_by_etb: dict[str, int] = {}
    for location in snapshot.get("locations", []) or []:
        etb_id = normalize_etb_code(location.get("etb_id", ""))
        location_code = normalize_location_code(location.get("location_code", ""))
        display_code = f"{etb_id}-{location_code}"
        existing = existing_by_display.get(display_code)
        owner_id = str(getattr(existing, "owner_user_id", "") or existing_owner)
        if existing is None and not owner_id:
            warnings.append(f"Skipped {display_code}: owner_user_id unavailable for new canonical location.")
            continue
        incoming_stored_count = max(0, int(location.get("stored_count") or 0))
        existing_stored_count = existing_stored_by_display.get(display_code, 0)
        if incoming_stored_count <= 0 < existing_stored_count:
            stored_count = existing_stored_count
            warnings.append(
                f"Preserved {display_code}: existing canonical stored_count "
                f"{existing_stored_count} is stronger than an empty desktop projection."
            )
        else:
            stored_count = incoming_stored_count
        stored_by_etb[etb_id] = stored_by_etb.get(etb_id, 0) + stored_count
        row = {
            "id": str(getattr(existing, "id", "") or canonical_registry_uuid("location", display_code)),
            "parent_location_id": parent_ids.get(etb_id) or canonical_registry_uuid("location", etb_id),
            "name": display_code,
            "location_type": "slot",
            "status": legacy_status_to_canonical(location.get("status", "")),
            "source": "CardVector OS",
            "legacy_id": display_code,
            "legacy_etb_id": etb_id,
            "legacy_location_code": location_code,
            "display_code": display_code,
            "capacity": int(location.get("capacity") or DEFAULT_ETB_LOCATION_CAPACITY),
            "stored_count": stored_count,
            "sync_state": "synced",
            "metadata": {
                "assigned_batch": location.get("assigned_batch") or "",
                "source_updated_at": location.get("source_updated_at") or "",
                "inventory_count_source": (
                    "existing_canonical"
                    if incoming_stored_count <= 0 < existing_stored_count
                    else "desktop_projection"
                ),
            },
        }
        if owner_id:
            row["owner_user_id"] = owner_id
        rows.append(row)

    for display_code, existing_stored_count in existing_stored_by_display.items():
        if existing_stored_count <= 0:
            continue
        try:
            etb_id = normalize_etb_code(display_code.rsplit("-", 1)[0])
            normalize_location_code(display_code.rsplit("-", 1)[1])
        except (IndexError, ValueError):
            continue
        if not any(row.get("display_code") == display_code for row in rows):
            stored_by_etb[etb_id] = stored_by_etb.get(etb_id, 0) + existing_stored_count

    for row in rows:
        if row.get("location_type") != "etb":
            continue
        stored_count = stored_by_etb.get(str(row.get("display_code") or ""), 0)
        row["stored_count"] = stored_count
        capacity = int(row.get("capacity") or 400)
        if stored_count <= 0:
            row["status"] = "empty"
        elif stored_count >= capacity:
            row["status"] = "full"
        else:
            row["status"] = "active"
    return rows, "; ".join(warnings)


def download_storage_object(bucket: str, storage_path: str, destination: Path) -> None:
    base_url, key = supabase_config()
    url = storage_object_url(base_url, bucket, storage_path)
    request = urllib.request.Request(
        url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
        },
        method="GET",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            destination.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MobileCaptureError(f"Storage download failed: {exc.code} {sanitize_error_message(detail)}") from exc


def list_sessions(statuses: tuple[str, ...] | list[str] | None = None, limit: int = 100) -> list[dict[str, Any]]:
    status_values = tuple(statuses or PRIMARY_QUEUE_STATUSES)
    query = urllib.parse.urlencode({
        "status": f"in.({','.join(status_values)})",
        "order": "updated_at.desc",
        "limit": str(limit),
        "select": "*",
    })
    return request_json("GET", f"/rest/v1/mobile_capture_sessions?{query}") or []


def list_pending_sessions(limit: int = 25) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({
        "status": "eq.PENDING_CONVERSION",
        "order": "submitted_at.asc",
        "limit": str(limit),
        "select": "*",
    })
    return request_json("GET", f"/rest/v1/mobile_capture_sessions?{query}") or []


def sync_cloud_location_registry() -> dict[str, Any]:
    """Synchronize cloud identity with the desktop offline registry projection."""
    snapshot = cloud_location_registry_snapshot()
    canonical_published = 0
    canonical_warning = ""
    try:
        canonical_client = SupabaseRegistryClient()
        existing = canonical_client.list_locations()
        canonical_rows, canonical_warning = canonical_location_rows_from_snapshot(snapshot, existing)
        if canonical_rows:
            canonical_client.upsert_locations(canonical_rows)
            canonical_published = len(canonical_rows)
    except Exception as exc:
        canonical_warning = sanitize_error_message(exc)
    if snapshot["etbs"]:
        request_json(
            "POST",
            "/rest/v1/cardvector_etbs?on_conflict=etb_id",
            snapshot["etbs"],
            prefer="resolution=merge-duplicates,return=minimal",
        )
    if snapshot["locations"]:
        request_json(
            "POST",
            "/rest/v1/cardvector_locations?on_conflict=location_id",
            snapshot["locations"],
            prefer="resolution=merge-duplicates,return=minimal",
        )
    cloud_etbs = request_json(
        "GET",
        "/rest/v1/cardvector_etbs?select=*&order=etb_id.asc",
    ) or []
    cloud_locations = request_json(
        "GET",
        "/rest/v1/cardvector_locations?select=*&order=etb_id.asc,location_code.asc",
    ) or []
    result = merge_cloud_location_registry(cloud_etbs, cloud_locations)
    result["etbs_published"] = len(snapshot["etbs"])
    result["locations_published"] = len(snapshot["locations"])
    result["canonical_locations_published"] = canonical_published
    result["canonical_sync_warning"] = canonical_warning
    return result


def load_session_images(session_id: str) -> list[dict[str, Any]]:
    query = (
        f"capture_session_id=eq.{urllib.parse.quote(session_id, safe='')}"
        "&removed_at=is.null"
        "&order=sequence_number.asc"
        "&select=*"
    )
    return request_json("GET", f"/rest/v1/mobile_capture_images?{query}") or []


def load_session(session_id: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode({
        "capture_session_id": f"eq.{session_id}",
        "limit": "1",
        "select": "*",
    })
    rows = request_json("GET", f"/rest/v1/mobile_capture_sessions?{query}") or []
    return rows[0] if rows else None


def claim_session(session_id: str) -> dict[str, Any]:
    now = iso_now()
    body = {
        "status": "PROCESSING",
        "conversion_status": "PROCESSING",
        "conversion_workstation": workstation_name(),
        "updated_at": now,
    }
    query = (
        f"capture_session_id=eq.{urllib.parse.quote(session_id, safe='')}"
        "&status=eq.PENDING_CONVERSION"
    )
    rows = request_json(
        "PATCH",
        f"/rest/v1/mobile_capture_sessions?{query}",
        body,
        prefer="return=representation",
    ) or []
    if not rows:
        raise MobileCaptureError(f"Session is not pending or was already claimed: {session_id}")
    return rows[0]


def retry_failed_session(session_id: str) -> dict[str, Any]:
    existing = load_session(session_id) or {}
    previous = sanitize_error_message(existing.get("error_message", ""))
    note = f"Retry requested by {workstation_name()} at {iso_now()}."
    if previous:
        note = f"{note} Previous error: {previous}"
    body = {
        "status": "PENDING_CONVERSION",
        "conversion_status": "PENDING_CONVERSION",
        "conversion_workstation": workstation_name(),
        "error_message": sanitize_error_message(note),
        "updated_at": iso_now(),
    }
    rows = request_json(
        "PATCH",
        f"/rest/v1/mobile_capture_sessions?capture_session_id=eq.{urllib.parse.quote(session_id, safe='')}&status=eq.FAILED",
        body,
        prefer="return=representation",
    ) or []
    if not rows:
        raise MobileCaptureError(f"Session is not failed or cannot be retried safely: {session_id}")
    return rows[0]


def update_session_status(session_id: str, status: str, message: str = "") -> dict[str, Any]:
    status = status.upper()
    if status not in {"CONVERTED", "FAILED", "CANCELLED"}:
        raise MobileCaptureError("Status must be CONVERTED, FAILED, or CANCELLED.")
    body = {
        "status": status,
        "conversion_status": status,
        "conversion_workstation": workstation_name(),
        "updated_at": iso_now(),
    }
    if message:
        body["error_message"] = sanitize_error_message(message)
    rows = request_json(
        "PATCH",
        f"/rest/v1/mobile_capture_sessions?capture_session_id=eq.{urllib.parse.quote(session_id, safe='')}",
        body,
        prefer="return=representation",
    ) or []
    if not rows:
        raise MobileCaptureError(f"Session not found: {session_id}")
    return rows[0]


def update_canonical_capture_status(
    session_id: str,
    status: str,
    *,
    processed_count: int | None = None,
    failed_count: int | None = None,
) -> dict[str, Any]:
    """Best-effort bridge to the canonical Supabase capture session record."""
    try:
        rows = SupabaseRegistryClient().update_capture_status_by_legacy_id(
            session_id,
            status,
            processed_count=processed_count,
            failed_count=failed_count,
        )
        return {"updated": bool(rows), "warning": ""}
    except Exception as exc:
        return {"updated": False, "warning": sanitize_error_message(exc)}


def storage_object_url(base_url: str, bucket: str, storage_path: str) -> str:
    encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in storage_path.split("/"))
    return f"{base_url.rstrip('/')}/storage/v1/object/{urllib.parse.quote(bucket, safe='')}/{encoded_path}"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def stage_session(session: dict[str, Any], images: list[dict[str, Any]]) -> dict[str, Any]:
    if not images:
        raise MobileCaptureError("Pending mobile capture session has no images.")
    etb, location, location_id = parse_etb_location(session_location_id(session))
    session_id = str(session["capture_session_id"])
    processing_dir = MOBILE_PROCESSING_DIR / safe_path_part(session_id)
    originals_dir = processing_dir / "originals"
    capture_type = session_capture_type(session)
    capture_layout = session_capture_layout(session)
    capture_folder = next_capture_folder(capture_type)
    records = []

    ordered_images = sorted(
        images,
        key=lambda image: int(image.get("sequence_number") or image.get("image_order") or 0),
    )
    for index, image in enumerate(ordered_images, start=1):
        bucket = str(image.get("storage_bucket") or "mobile-capture-originals")
        storage_path = str(image.get("storage_path") or "")
        if not storage_path:
            raise MobileCaptureError(f"Image record has no storage_path: {image}")
        suffix = Path(storage_path).suffix or ".jpg"
        original_path = originals_dir / f"{index:06d}{suffix}"
        download_storage_object(bucket, storage_path, original_path)
        card_number, side = capture_record_position(index, capture_layout)
        staged_path = capture_folder / f"{card_number:06d}_{side}{suffix}"
        staged_path.write_bytes(original_path.read_bytes())
        records.append({
            "filename": staged_path.name,
            "path": str(staged_path),
            "side": side,
            "card_number": card_number,
            "captured_at": image.get("created_at") or iso_now(),
            "capture_mode": "Mobile Web",
            "mobile_image_id": image.get("image_id", ""),
            "mobile_storage_bucket": bucket,
            "mobile_storage_path": storage_path,
        })

    card_count = len({record["card_number"] for record in records})
    capture_session = {
        "started_at": session.get("created_at") or iso_now(),
        "finished_at": iso_now(),
        "folder": str(capture_folder),
        "capture_mode": "Mobile Web",
        "capture_layout": capture_layout,
        "current_card_number": card_count + 1,
        "cards_captured": card_count,
        "photos_captured": len(records),
        "records": records,
        "source": "MOBILE_WEB",
        "capture_session_id": session_id,
        "etb": etb,
        "location": location,
        "location_id": location_id,
        "capture_type": capture_type,
        "capture_workflow": (
            "new_inventory_capture"
            if capture_type == "NEW_CAPTURE"
            else "physical_inventory_conversion"
        ),
    }
    write_json(capture_folder / "capture_session.json", capture_session)

    session_path: Path | None = None
    if capture_type == "PHYSICAL_INVENTORY":
        conversion_session_id = f"conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conversion_session = {
            "session_id": conversion_session_id,
            "session_type": "physical_inventory_conversion",
            "created_at": session.get("created_at") or iso_now(),
            "updated_at": iso_now(),
            "etb": etb,
            "location": location,
            "location_id": location_id,
            "operator": session.get("operator", ""),
            "status": "Mobile Capture Staged",
            "expected_capacity": DEFAULT_ETB_LOCATION_CAPACITY,
            "cards_captured": card_count,
            "photos_captured": len(records),
            "capture_layout": capture_layout,
            "capture_folder": str(capture_folder),
            "capture_session_file": str(capture_folder / "capture_session.json"),
            "mobile_capture_session_id": session_id,
            "source": "MOBILE_WEB",
            "workflow_state": "Pending Physical Inventory Conversion",
            "notes": "Mobile originals staged for existing Physical Inventory Conversion. CardUploader remains the recognition system.",
        }
        session_path = INVENTORY_CONVERSION_SESSIONS_DIR / f"{conversion_session_id}.json"
        write_json(session_path, conversion_session)
        write_json(CURRENT_INVENTORY_CONVERSION, conversion_session)

    manifest = {
        "mobile_capture_session": session,
        "mobile_capture_images": images,
        "processing_dir": str(processing_dir),
        "originals_dir": str(originals_dir),
        "capture_folder": str(capture_folder),
        "capture_session_file": str(capture_folder / "capture_session.json"),
        "inventory_conversion_session_file": str(session_path) if session_path else "",
        "capture_type": capture_type,
        "capture_layout": capture_layout,
        "staged_at": iso_now(),
        "workstation": workstation_name(),
    }
    write_json(processing_dir / "mobile_capture_manifest.json", manifest)
    return manifest


def status_label(status: str) -> str:
    return QUEUE_STATUS_LABELS.get(str(status or "").upper(), str(status or "Unknown"))


def local_session_folder(session_id: str) -> Path | None:
    safe_id = safe_path_part(session_id)
    candidates = [
        MOBILE_PROCESSING_DIR / safe_id,
        MOBILE_CONVERTED_DIR / safe_id,
        MOBILE_FAILED_DIR / safe_id,
        MOBILE_PENDING_DIR / safe_id,
    ]
    for candidate in candidates:
        if candidate.exists():
            manifest_path = candidate / "mobile_capture_manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    capture_folder = manifest.get("capture_folder")
                    if capture_folder and Path(capture_folder).exists():
                        return Path(capture_folder)
                except Exception:
                    pass
            return candidate
    return None


def session_row_model(session: dict[str, Any], current_workstation: str | None = None) -> dict[str, Any]:
    status = str(session.get("status") or "").upper()
    session_id = str(session.get("capture_session_id") or "")
    claimed_by = str(session.get("conversion_workstation") or "")
    current = current_workstation or workstation_name()
    locked_by_other = status == "PROCESSING" and bool(claimed_by) and claimed_by != current
    location_id = str(session.get("etb_location") or session.get("etb_location_id") or "")
    return {
        "status": status,
        "status_label": status_label(status),
        "etb_location": location_id,
        "capture_session_id": session_id,
        "image_count": int(session.get("image_count") or 0),
        "submitted_at": str(session.get("submitted_at") or session.get("updated_at") or session.get("created_at") or ""),
        "source": str(session.get("source") or ""),
        "capture_type": session_capture_type(session),
        "conversion_workstation": claimed_by,
        "last_error": sanitize_error_message(session.get("error_message", "")),
        "locked_by_other": locked_by_other,
        "local_folder": str(local_session_folder(session_id) or ""),
        "raw": session,
    }


def filter_session_rows(
    rows: list[dict[str, Any]],
    status_filter: str = "ACTIVE",
    search: str = "",
) -> list[dict[str, Any]]:
    status_filter = str(status_filter or "ACTIVE").upper()
    search = str(search or "").strip().upper()
    if status_filter == "ACTIVE":
        allowed = {"PENDING_CONVERSION", "PROCESSING", "FAILED"}
    elif status_filter == "PRIMARY":
        allowed = set(PRIMARY_QUEUE_STATUSES)
    elif status_filter == "ALL":
        allowed = set(PRIMARY_QUEUE_STATUSES + DIAGNOSTIC_QUEUE_STATUSES)
    else:
        allowed = {status_filter}
    filtered = [row for row in rows if row.get("status") in allowed]
    if search:
        filtered = [
            row for row in filtered
            if search in str(row.get("etb_location", "")).upper()
            or search in str(row.get("capture_session_id", "")).upper()
        ]
    return filtered


def queue_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "pending": sum(1 for row in rows if row.get("status") == "PENDING_CONVERSION"),
        "processing": sum(1 for row in rows if row.get("status") == "PROCESSING"),
        "failed": sum(1 for row in rows if row.get("status") == "FAILED"),
    }


class MobileCaptureQueueService:
    def __init__(self, current_workstation: str | None = None):
        self.current_workstation = current_workstation or workstation_name()
        self.last_location_sync_warning = ""
        self.last_location_sync_result: dict[str, Any] = {}

    def environment_ready(self) -> tuple[bool, str]:
        try:
            supabase_config()
            return True, "Connected"
        except MobileCaptureError as exc:
            return False, str(exc)

    def list_queue(self, include_diagnostics: bool = True, limit: int = 100) -> list[dict[str, Any]]:
        self.sync_locations(strict=False)
        statuses = PRIMARY_QUEUE_STATUSES + (DIAGNOSTIC_QUEUE_STATUSES if include_diagnostics else ())
        return [session_row_model(row, self.current_workstation) for row in list_sessions(statuses, limit=limit)]

    def sync_locations(self, strict: bool = True) -> dict[str, Any]:
        try:
            result = sync_cloud_location_registry()
            self.last_location_sync_result = result
            self.last_location_sync_warning = ""
            return result
        except Exception as exc:
            message = sanitize_error_message(exc)
            self.last_location_sync_warning = message
            if strict:
                raise MobileCaptureError(message) from exc
            return {"changed": False, "warning": message}

    def process(self, session_id: str) -> dict[str, Any]:
        self.sync_locations(strict=False)
        session = claim_session(session_id)
        images = load_session_images(session_id)
        try:
            manifest = stage_session(session, images)
        except Exception as exc:
            update_session_status(session_id, "FAILED", sanitize_error_message(exc))
            update_canonical_capture_status(session_id, "failed", failed_count=1)
            raise
        manifest["canonical_registry_sync"] = update_canonical_capture_status(
            session_id,
            "staged",
            processed_count=len(images),
        )
        return manifest

    def process_next_pending(self) -> dict[str, Any] | None:
        """Atomically claim and stage the oldest pending session, if any."""
        pending = list_pending_sessions(limit=1)
        if not pending:
            return None
        session_id = str(pending[0].get("capture_session_id") or "")
        if not session_id:
            return None
        try:
            return self.process(session_id)
        except MobileCaptureError as exc:
            # Another workstation may claim the row between the list and PATCH.
            if "already claimed" in str(exc).lower() or "not pending" in str(exc).lower():
                return None
            raise

    def process_all_pending(self, limit: int = 25) -> list[dict[str, Any]]:
        manifests = []
        for _index in range(max(0, int(limit))):
            manifest = self.process_next_pending()
            if not manifest:
                break
            manifests.append(manifest)
        return manifests

    def complete(self, session_id: str) -> dict[str, Any]:
        row = update_session_status(session_id, "CONVERTED")
        converted_dir = MOBILE_CONVERTED_DIR / safe_path_part(session_id)
        converted_dir.mkdir(parents=True, exist_ok=True)
        write_json(converted_dir / "mobile_capture_status.json", row)
        return row

    def fail(self, session_id: str, message: str) -> dict[str, Any]:
        row = update_session_status(session_id, "FAILED", sanitize_error_message(message))
        failed_dir = MOBILE_FAILED_DIR / safe_path_part(session_id)
        failed_dir.mkdir(parents=True, exist_ok=True)
        write_json(failed_dir / "mobile_capture_status.json", row)
        return row

    def retry_failed(self, session_id: str) -> dict[str, Any]:
        return retry_failed_session(session_id)

    def local_folder(self, session_id: str) -> Path | None:
        return local_session_folder(session_id)


def cmd_list(args: argparse.Namespace) -> int:
    rows = list_pending_sessions(args.limit)
    if not rows:
        print("No pending mobile capture sessions.")
        return 0
    for row in rows:
        print(
            "\t".join([
                str(row.get("capture_session_id", "")),
                str(row.get("etb_location") or row.get("etb_location_id") or ""),
                str(row.get("submitted_at", "")),
                str(row.get("image_count", 0)),
                str(row.get("status", "")),
            ])
        )
    return 0


def cmd_process(args: argparse.Namespace) -> int:
    session = claim_session(args.session_id)
    images = load_session_images(args.session_id)
    try:
        manifest = stage_session(session, images)
    except Exception as exc:
        update_session_status(args.session_id, "FAILED", str(exc))
        raise
    print(json.dumps({
        "status": "PROCESSING",
        "capture_session_id": args.session_id,
        "capture_folder": manifest["capture_folder"],
        "inventory_conversion_session_file": manifest["inventory_conversion_session_file"],
        "originals_dir": manifest["originals_dir"],
    }, indent=2))
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    row = update_session_status(args.session_id, "CONVERTED")
    converted_dir = MOBILE_CONVERTED_DIR / safe_path_part(args.session_id)
    converted_dir.mkdir(parents=True, exist_ok=True)
    write_json(converted_dir / "mobile_capture_status.json", row)
    print(f"Marked converted: {args.session_id}")
    return 0


def cmd_fail(args: argparse.Namespace) -> int:
    row = update_session_status(args.session_id, "FAILED", args.message)
    failed_dir = MOBILE_FAILED_DIR / safe_path_part(args.session_id)
    failed_dir.mkdir(parents=True, exist_ok=True)
    write_json(failed_dir / "mobile_capture_status.json", row)
    print(f"Marked failed: {args.session_id}")
    return 0


def cmd_retry_failed(args: argparse.Namespace) -> int:
    row = retry_failed_session(args.session_id)
    print(f"Retry queued: {row.get('capture_session_id', args.session_id)}")
    return 0


def cmd_sync_locations(_args: argparse.Namespace) -> int:
    result = sync_cloud_location_registry()
    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CardVector Mobile Capture queue processor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List pending mobile capture sessions")
    list_parser.add_argument("--limit", type=int, default=25)
    list_parser.set_defaults(func=cmd_list)

    process_parser = subparsers.add_parser("process", help="Claim and stage a pending mobile capture session")
    process_parser.add_argument("session_id")
    process_parser.set_defaults(func=cmd_process)

    complete_parser = subparsers.add_parser("complete", help="Mark a staged mobile capture session converted")
    complete_parser.add_argument("session_id")
    complete_parser.set_defaults(func=cmd_complete)

    fail_parser = subparsers.add_parser("fail", help="Mark a mobile capture session failed")
    fail_parser.add_argument("session_id")
    fail_parser.add_argument("--message", default="")
    fail_parser.set_defaults(func=cmd_fail)

    retry_parser = subparsers.add_parser("retry-failed", help="Return a failed mobile capture session to pending")
    retry_parser.add_argument("session_id")
    retry_parser.set_defaults(func=cmd_retry_failed)

    sync_parser = subparsers.add_parser("sync-locations", help="Synchronize the desktop ETB registry with Supabase")
    sync_parser.set_defaults(func=cmd_sync_locations)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except MobileCaptureError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
