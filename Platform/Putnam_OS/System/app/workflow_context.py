from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


WORKFLOW_CONTEXT_NAME = "cardvector_workflow.json"
PUBLIC_STATES = ("Ready", "In Progress", "Needs Attention", "Complete", "Failed")
PROCESSING_STAGES = (
    "Ready for CardUploader",
    "Awaiting CSV Import",
    "Uploaded to CardUploader",
    "Pricing Review",
    "Ready for eBay Upload",
    "Completed Recently",
)
CARDUPLOADER_UPLOADED_STATUSES = {
    "uploaded",
    "uploaded_to_carduploader",
    "carduploader_uploaded",
}


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _path_value(value: Any) -> str:
    return str(value or "").strip()


def _existing_path(value: Any) -> Path | None:
    raw = _path_value(value)
    if not raw:
        return None
    path = Path(raw)
    return path if path.exists() else None


def _parse_timestamp(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def workflow_context_path(capture_folder: str | Path) -> Path:
    return Path(capture_folder) / WORKFLOW_CONTEXT_NAME


def load_workflow_context(capture_folder: str | Path) -> dict[str, Any]:
    return _read_json(workflow_context_path(capture_folder))


def update_workflow_context(capture_folder: str | Path, **updates: Any) -> dict[str, Any]:
    """Persist only operator handoff state beside an existing capture session."""
    folder = Path(capture_folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = workflow_context_path(folder)
    current = _read_json(path)
    current.update({key: value for key, value in updates.items() if value is not None})
    current["capture_folder"] = str(folder)
    current["updated_timestamp"] = iso_now()
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    return current


def _stage_for_context(context: dict[str, Any], failed: bool = False) -> tuple[str, str, str]:
    if failed or context.get("last_error"):
        return "Failed", "Failed", "Retry Failed Capture"
    explicit = str(context.get("current_workflow_state") or "").strip()
    handoff_status = str(context.get("carduploader_handoff_status") or "").lower()
    if explicit in PROCESSING_STAGES:
        stage = explicit
    elif _existing_path(context.get("export_csv_path")) or _existing_path(context.get("pricing_job_path")):
        stage = "Ready for eBay Upload"
    elif _existing_path(context.get("imported_csv_path")):
        stage = "Pricing Review"
    elif handoff_status in CARDUPLOADER_UPLOADED_STATUSES:
        stage = "Uploaded to CardUploader"
    elif handoff_status in {"opened", "awaiting_csv", "complete"}:
        stage = "Awaiting CSV Import"
    else:
        stage = "Ready for CardUploader"

    mapping = {
        "Ready for CardUploader": ("Ready", "Open CardUploader"),
        "Awaiting CSV Import": ("Ready", "Import CardUploader CSV"),
        "Uploaded to CardUploader": ("Complete", "Open Capture Folder"),
        "Pricing Review": ("Needs Attention", "Review Pricing"),
        "Ready for eBay Upload": ("Ready", "Open Export Folder"),
        "Completed Recently": ("Complete", "Open Export Folder"),
    }
    public_state, action = mapping.get(stage, ("Ready", "Continue Processing"))
    return public_state, stage, action


def _capture_job(
    session: dict[str, Any],
    capture_folder: Path,
    context: dict[str, Any],
    *,
    source: str,
    failed: bool = False,
    last_error: str = "",
) -> dict[str, Any]:
    capture_type = str(
        context.get("capture_type")
        or session.get("capture_type")
        or (session.get("source_device") or {}).get("capture_type")
        or (session.get("device") or {}).get("capture_type")
        or "NEW_CAPTURE"
    ).strip().upper()
    capture_session_id = str(
        context.get("capture_session_id")
        or session.get("capture_session_id")
        or session.get("mobile_capture_session_id")
        or capture_folder.name
    )
    etb_location = str(
        context.get("etb_location")
        or session.get("etb_location")
        or session.get("etb_location_id")
        or session.get("batch_location")
        or ""
    )
    image_count = int(
        session.get("image_count")
        or session.get("photos_captured")
        or len(session.get("records") or [])
        or 0
    )
    public_state, stage, action = _stage_for_context(
        {**context, "last_error": last_error or context.get("last_error", "")},
        failed=failed,
    )
    updated = str(
        context.get("updated_timestamp")
        or session.get("updated_at")
        or session.get("finished_at")
        or session.get("submitted_at")
        or session.get("created_at")
        or session.get("started_at")
        or datetime.fromtimestamp(capture_folder.stat().st_mtime).isoformat(timespec="seconds")
    )
    return {
        "job_id": capture_session_id,
        "capture_session_id": capture_session_id,
        "capture_folder": str(capture_folder),
        "session_folder": capture_folder.name,
        "capture_type": capture_type,
        "etb_location": etb_location,
        "image_count": image_count,
        "row_count": int(context.get("row_count") or 0),
        "state": public_state,
        "stage": stage,
        "action": action,
        "source": source,
        "carduploader_handoff_status": str(context.get("carduploader_handoff_status") or ""),
        "carduploader_uploaded_at": str(context.get("carduploader_uploaded_at") or ""),
        "supabase_originals_cleanup_eligible": bool(context.get("supabase_originals_cleanup_eligible", False)),
        "supabase_originals_cleanup_reason": str(context.get("supabase_originals_cleanup_reason") or ""),
        "imported_csv_path": _path_value(context.get("imported_csv_path")),
        "pricing_job_path": _path_value(context.get("pricing_job_path")),
        "export_csv_path": _path_value(context.get("export_csv_path")),
        "last_error": str(last_error or context.get("last_error") or "").strip(),
        "updated_timestamp": updated,
    }


def _manifest_job(path: Path, failed: bool = False) -> dict[str, Any] | None:
    manifest = _read_json(path)
    if not manifest:
        return None
    session = manifest.get("mobile_capture_session") or manifest
    if not isinstance(session, dict):
        return None
    folder = _existing_path(manifest.get("capture_folder"))
    if folder is None:
        local = _existing_path(manifest.get("processing_dir"))
        if local is None:
            if not failed:
                return None
            local = path.parent
        folder = local
    context = load_workflow_context(folder)
    return _capture_job(
        session,
        folder,
        context,
        source="Mobile Capture",
        failed=failed,
        last_error=str(session.get("error_message") or manifest.get("last_error") or ""),
    )


def discover_workflow_jobs(
    capture_root: str | Path,
    mobile_processing_root: str | Path | None = None,
    mobile_failed_root: str | Path | None = None,
    *,
    limit: int = 60,
) -> list[dict[str, Any]]:
    """Build a bounded local job index from canonical session files."""
    jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_folders: set[str] = set()

    manifest_specs = (
        (Path(mobile_failed_root), True) if mobile_failed_root else None,
        (Path(mobile_processing_root), False) if mobile_processing_root else None,
    )
    for spec in manifest_specs:
        if not spec:
            continue
        root, failed = spec
        if not root.exists():
            continue
        names = ("mobile_capture_manifest.json", "mobile_capture_status.json") if failed else ("mobile_capture_manifest.json",)
        manifests = sorted(
            (item for name in names for item in root.rglob(name)),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests[:limit]:
            job = _manifest_job(path, failed=failed)
            if not job or job["job_id"] in seen_ids:
                continue
            jobs.append(job)
            seen_ids.add(job["job_id"])
            seen_folders.add(str(Path(job["capture_folder"]).resolve()).lower())

    capture_root = Path(capture_root)
    if capture_root.exists():
        sessions = sorted(capture_root.rglob("capture_session.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        for path in sessions[: limit * 2]:
            folder_key = str(path.parent.resolve()).lower()
            if folder_key in seen_folders:
                continue
            session = _read_json(path)
            if not session:
                continue
            context = load_workflow_context(path.parent)
            job = _capture_job(session, path.parent, context, source="Desktop Capture")
            if job["job_id"] in seen_ids:
                continue
            jobs.append(job)
            seen_ids.add(job["job_id"])
            seen_folders.add(folder_key)

    jobs.sort(key=lambda item: item.get("updated_timestamp", ""), reverse=True)
    return jobs[:limit]


def jobs_from_queue_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        status = str(row.get("status") or "").upper()
        if status not in {"PENDING_CONVERSION", "PROCESSING", "FAILED"}:
            continue
        if status == "FAILED":
            state, stage, action = "Failed", "Failed", "Retry Failed Capture"
        elif status == "PROCESSING":
            state, stage, action = "In Progress", "Downloading", "Open Capture Queue"
        else:
            state, stage, action = "Ready", "Waiting to Download", "Open Capture Queue"
        result.append(
            {
                "job_id": str(row.get("capture_session_id") or ""),
                "capture_session_id": str(row.get("capture_session_id") or ""),
                "capture_folder": str(row.get("local_folder") or ""),
                "session_folder": Path(str(row.get("local_folder") or "")).name,
                "capture_type": str(row.get("capture_type") or "NEW_CAPTURE"),
                "etb_location": str(row.get("etb_location") or ""),
                "image_count": int(row.get("image_count") or 0),
                "row_count": 0,
                "state": state,
                "stage": stage,
                "action": action,
                "source": "Mobile Queue",
                "last_error": str(row.get("last_error") or ""),
                "updated_timestamp": str(row.get("submitted_at") or ""),
                "locked_by_other": bool(row.get("locked_by_other")),
            }
        )
    return result


def merge_job_lists(*groups: Iterable[dict[str, Any]], limit: int = 60) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for group in groups:
        for job in group:
            key = str(job.get("job_id") or job.get("capture_folder") or "")
            if not key:
                continue
            current = merged.get(key)
            if current is None or str(job.get("updated_timestamp") or "") >= str(current.get("updated_timestamp") or ""):
                merged[key] = dict(job)
    return sorted(merged.values(), key=lambda item: item.get("updated_timestamp", ""), reverse=True)[:limit]


def group_processing_jobs(jobs: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped = {stage: [] for stage in PROCESSING_STAGES}
    for job in jobs:
        stage = str(job.get("stage") or "")
        if stage in grouped:
            grouped[stage].append(job)
    return grouped


def active_listings_summary(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {"count": 0, "source": "No verified active-listings CSV found", "path": "", "refreshed_at": "", "age_days": None}
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            count = sum(1 for _row in csv.DictReader(handle))
        modified = datetime.fromtimestamp(source.stat().st_mtime)
    except OSError:
        return {"count": 0, "source": "Active-listings source unavailable", "path": str(source), "refreshed_at": "", "age_days": None}
    age_days = max(0, (datetime.now() - modified).days)
    return {
        "count": count,
        "source": f"Local eBay Active Listings CSV: {source.name}",
        "path": str(source),
        "refreshed_at": modified.isoformat(timespec="minutes"),
        "age_days": age_days,
    }


def recent_completed_jobs(completed_root: str | Path, limit: int = 5) -> list[dict[str, Any]]:
    root = Path(completed_root)
    if not root.exists():
        return []
    result = []
    folders = sorted((path for path in root.iterdir() if path.is_dir()), key=lambda item: item.stat().st_mtime, reverse=True)
    for folder in folders:
        export = folder / "ebay_upload_ready.csv"
        if not export.exists():
            continue
        result.append(
            {
                "job_id": folder.name,
                "capture_session_id": "",
                "capture_folder": "",
                "session_folder": folder.name,
                "capture_type": "",
                "etb_location": "",
                "image_count": 0,
                "row_count": 0,
                "state": "Complete",
                "stage": "Completed Recently",
                "action": "Open Export Folder",
                "source": "Pricing",
                "pricing_job_path": str(folder),
                "export_csv_path": str(export),
                "last_error": "",
                "updated_timestamp": datetime.fromtimestamp(folder.stat().st_mtime).isoformat(timespec="seconds"),
            }
        )
        if len(result) >= limit:
            break
    return result
