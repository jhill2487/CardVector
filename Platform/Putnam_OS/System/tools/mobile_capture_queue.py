from __future__ import annotations

import argparse
import json
import os
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
    normalize_etb_code,
    normalize_location_code,
)


MOBILE_CAPTURE_ROOT = ROOT / "MobileCapture"
MOBILE_PENDING_DIR = MOBILE_CAPTURE_ROOT / "Pending"
MOBILE_PROCESSING_DIR = MOBILE_CAPTURE_ROOT / "Processing"
MOBILE_CONVERTED_DIR = MOBILE_CAPTURE_ROOT / "Converted"
MOBILE_FAILED_DIR = MOBILE_CAPTURE_ROOT / "Failed"
INVENTORY_CONVERSION_DIR = PUTNAM_OS_DIR / "System" / "data" / "inventory_conversion"
INVENTORY_CONVERSION_SESSIONS_DIR = INVENTORY_CONVERSION_DIR / "sessions"
CURRENT_INVENTORY_CONVERSION = INVENTORY_CONVERSION_DIR / "current_inventory_conversion.json"
INVENTORY_CONVERSION_CAPTURE_ROOT = ROOT / "Capture" / "Physical_Inventory_Conversion"


class MobileCaptureError(RuntimeError):
    pass


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


def next_capture_folder(location_id: str) -> Path:
    root = INVENTORY_CONVERSION_CAPTURE_ROOT / safe_path_part(location_id)
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
        raise MobileCaptureError(f"Supabase request failed: {exc.code} {detail}") from exc
    if not payload:
        return None
    return json.loads(payload)


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
        raise MobileCaptureError(f"Storage download failed: {exc.code} {detail}") from exc


def list_pending_sessions(limit: int = 25) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({
        "status": "eq.PENDING_CONVERSION",
        "order": "submitted_at.asc",
        "limit": str(limit),
        "select": "*",
    })
    return request_json("GET", f"/rest/v1/mobile_capture_sessions?{query}") or []


def load_session_images(session_id: str) -> list[dict[str, Any]]:
    query = (
        f"capture_session_id=eq.{urllib.parse.quote(session_id, safe='')}"
        "&removed_at=is.null"
        "&order=sequence_number.asc"
        "&select=*"
    )
    return request_json("GET", f"/rest/v1/mobile_capture_images?{query}") or []


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
        body["error_message"] = message
    rows = request_json(
        "PATCH",
        f"/rest/v1/mobile_capture_sessions?capture_session_id=eq.{urllib.parse.quote(session_id, safe='')}",
        body,
        prefer="return=representation",
    ) or []
    if not rows:
        raise MobileCaptureError(f"Session not found: {session_id}")
    return rows[0]


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
    capture_folder = next_capture_folder(location_id)
    records = []

    for index, image in enumerate(images, start=1):
        bucket = str(image.get("storage_bucket") or "mobile-capture-originals")
        storage_path = str(image.get("storage_path") or "")
        if not storage_path:
            raise MobileCaptureError(f"Image record has no storage_path: {image}")
        suffix = Path(storage_path).suffix or ".jpg"
        original_path = originals_dir / f"{index:06d}{suffix}"
        download_storage_object(bucket, storage_path, original_path)
        staged_path = capture_folder / f"{index:06d}_front{suffix}"
        staged_path.write_bytes(original_path.read_bytes())
        records.append({
            "filename": staged_path.name,
            "path": str(staged_path),
            "side": "front",
            "card_number": index,
            "captured_at": image.get("created_at") or iso_now(),
            "capture_mode": "Mobile Web",
            "mobile_image_id": image.get("image_id", ""),
            "mobile_storage_bucket": bucket,
            "mobile_storage_path": storage_path,
        })

    capture_session = {
        "started_at": session.get("created_at") or iso_now(),
        "finished_at": iso_now(),
        "folder": str(capture_folder),
        "capture_mode": "Mobile Web",
        "current_card_number": len(records) + 1,
        "photos_captured": len(records),
        "records": records,
        "source": "MOBILE_WEB",
        "capture_session_id": session_id,
        "etb": etb,
        "location": location,
        "location_id": location_id,
        "capture_workflow": "front_only_legacy_inventory_conversion",
    }
    write_json(capture_folder / "capture_session.json", capture_session)

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
        "cards_captured": len(records),
        "capture_folder": str(capture_folder),
        "capture_session_file": str(capture_folder / "capture_session.json"),
        "mobile_capture_session_id": session_id,
        "source": "MOBILE_WEB",
        "workflow_state": "Pending Physical Inventory Conversion",
        "notes": "Mobile originals staged for existing Physical Inventory Conversion. CardUploader recognition and Marketplace Intelligence remain downstream steps.",
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
        "inventory_conversion_session_file": str(session_path),
        "staged_at": iso_now(),
        "workstation": workstation_name(),
    }
    write_json(processing_dir / "mobile_capture_manifest.json", manifest)
    return manifest


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
