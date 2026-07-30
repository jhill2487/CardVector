from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from Platform.putnam_paths import ROOT, WORK_SESSIONS_DIR
from Platform.cardvector.integrations.supabase.registry import (
    SupabaseRegistryClient,
    SupabaseRegistryError,
    canonical_registry_uuid,
    legacy_status_to_canonical,
)


LEGACY_REGISTRY = (
    ROOT / "Platform" / "Putnam_OS" / "System" / "data" / "inventory" / "etb_location_registry.json"
)
LEGACY_REGISTRY_OLD = ROOT / "Data" / "Config" / "etb_location_registry.json"
LEGACY_BATCH_REGISTRY = ROOT / "Platform" / "Putnam_OS" / "System" / "config" / "location_registry.json"
CONVERSION_SESSIONS = (
    ROOT / "Platform" / "Putnam_OS" / "System" / "data" / "inventory_conversion" / "sessions"
)

APPROVED_SUPABASE_PROJECT_REF = "iqdpfgpkagjxzedfxrvn"
RESOLUTION_ACTIONS = {
    "skip_exact_duplicate",
    "skip_incoming",
    "keep_existing",
    "merge_provenance",
    "update_from_incoming",
    "keep_both",
    "manual_block",
}


def canonical_uuid(kind: str, legacy_id: str) -> str:
    return canonical_registry_uuid(kind, legacy_id)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_files(paths: Iterable[Path], backup_dir: Path) -> list[dict[str, Any]]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups = []
    for path in paths:
        if not path.exists():
            continue
        target = backup_dir / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        backups.append(
            {
                "source": str(path),
                "backup": str(target),
                "sha256": file_sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return backups


def normalize_location_code(etb_code: str, location_code: str) -> str:
    location = str(location_code or "").strip().upper()
    if location.startswith(str(etb_code).upper() + "-"):
        return location.split("-")[-1]
    return location


def build_location_rows(registry: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for etb in registry.get("locations", []) or []:
        etb_code = str(etb.get("etb_id") or etb.get("location_code") or "").strip().upper()
        if not etb_code:
            invalid.append({"type": "etb", "record": etb, "error": "missing etb code"})
            continue
        etb_id = canonical_uuid("location", etb_code)
        rows.append(
            {
                "_migration_entity_type": "location",
                "_migration_source_file": str(LEGACY_REGISTRY),
                "_migration_record_id": etb_code,
                "_migration_display": etb_code,
                "id": etb_id,
                "name": etb_code,
                "location_type": "etb",
                "status": legacy_status_to_canonical(str(etb.get("status") or "")),
                "source": "legacy_json_migration",
                "legacy_id": etb_code,
                "legacy_etb_id": etb_code,
                "display_code": etb_code,
                "capacity": int(etb.get("total_capacity") or etb.get("estimated_capacity") or 400),
                "stored_count": int(etb.get("stored_count") or etb.get("estimated_assigned_count") or 0),
                "metadata": {
                    "active_location": etb.get("active_location") or "",
                    "current_active_location": etb.get("current_active_location") or "",
                },
                "migration_metadata": {
                    "source_file": str(LEGACY_REGISTRY),
                    "source_updated_at": registry.get("updated_at") or "",
                },
                "created_at": etb.get("created_at") or None,
                "updated_at": etb.get("updated_at") or None,
            }
        )
        for child in etb.get("locations", []) or []:
            code = normalize_location_code(etb_code, str(child.get("location_code") or ""))
            if code not in tuple("ABCDEFGHIJ"):
                invalid.append(
                    {
                        "type": "slot",
                        "record": child,
                        "error": f"invalid location code {code!r}",
                    }
                )
                continue
            display_code = str(child.get("location_id") or f"{etb_code}-{code}").strip().upper()
            rows.append(
                {
                    "_migration_entity_type": "location",
                    "_migration_source_file": str(LEGACY_REGISTRY),
                    "_migration_record_id": display_code,
                    "_migration_display": display_code,
                    "id": canonical_uuid("location", display_code),
                    "parent_location_id": etb_id,
                    "name": display_code,
                    "location_type": "slot",
                    "status": legacy_status_to_canonical(str(child.get("status") or "")),
                    "source": "legacy_json_migration",
                    "legacy_id": display_code,
                    "legacy_etb_id": etb_code,
                    "legacy_location_code": code,
                    "display_code": display_code,
                    "capacity": int(child.get("capacity") or 40),
                    "stored_count": int(child.get("stored_count") or 0),
                    "metadata": {
                        "assigned_batch": child.get("assigned_batch") or "",
                        "carduploader_batch_url": child.get("carduploader_batch_url") or "",
                        "carduploader_batch_id": child.get("carduploader_batch_id") or "",
                        "carduploader_batch_name": child.get("carduploader_batch_name") or "",
                    },
                    "migration_metadata": {
                        "source_file": str(LEGACY_REGISTRY),
                        "source_updated_at": registry.get("updated_at") or "",
                    },
                    "created_at": child.get("created_at") or None,
                    "updated_at": child.get("updated_at") or None,
                }
            )
    return rows, invalid


def session_status(value: str) -> str:
    normalized = str(value or "").strip().lower()
    mapping = {
        "mobile capture staged": "staged",
        "location complete": "completed",
        "ready for capture": "draft",
        "waiting for capture": "draft",
        "processing": "processing",
        "failed": "failed",
        "cancelled": "cancelled",
    }
    return mapping.get(normalized, "draft")


def build_session_and_image_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    sessions: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    if not CONVERSION_SESSIONS.exists():
        return sessions, images, invalid
    for path in sorted(CONVERSION_SESSIONS.glob("*.json")):
        try:
            item = read_json(path)
        except Exception as exc:
            invalid.append({"type": "conversion_session", "path": str(path), "error": str(exc)})
            continue
        legacy_session_id = str(item.get("mobile_capture_session_id") or item.get("session_id") or path.stem)
        location_id = str(item.get("location_id") or "").strip().upper()
        location_uuid = canonical_uuid("location", location_id) if location_id else ""
        session_uuid = canonical_uuid("capture_session", legacy_session_id)
        session_row = {
            "_migration_entity_type": "capture_session",
            "_migration_source_file": str(path),
            "_migration_record_id": legacy_session_id,
            "_migration_session_id": legacy_session_id,
            "_migration_display": legacy_session_id,
            "id": session_uuid,
            "source_application": item.get("source") or "CardVector OS",
            "originating_device": {"source": item.get("source") or "legacy_conversion_session"},
            "location_id": location_uuid or None,
            "status": session_status(str(item.get("status") or "")),
            "photo_count": int(item.get("photos_captured") or item.get("cards_captured") or 0),
            "processed_count": 0,
            "recognized_count": 0,
            "failed_count": 0,
            "legacy_session_id": legacy_session_id,
            "legacy_capture_type": str(item.get("session_type") or ""),
            "legacy_etb_location_id": location_id,
            "migration_metadata": {
                "source_file": str(path),
                "legacy_status": item.get("status") or "",
                "capture_folder": item.get("capture_folder") or "",
                "capture_session_file": item.get("capture_session_file") or "",
            },
            "created_at": item.get("created_at") or None,
            "updated_at": item.get("updated_at") or None,
            "completed_at": item.get("updated_at") if session_status(str(item.get("status") or "")) == "completed" else None,
        }
        sessions.append(session_row)
        capture_file_value = str(item.get("capture_session_file") or "").strip()
        capture_file = Path(capture_file_value) if capture_file_value else None
        if capture_file and capture_file.is_file():
            try:
                capture = read_json(capture_file)
            except Exception as exc:
                invalid.append({"type": "capture_session_file", "path": str(capture_file), "error": str(exc)})
                continue
            for index, record in enumerate(capture.get("records", []) or [], start=1):
                legacy_image_id = str(record.get("mobile_image_id") or f"{legacy_session_id}:{index}")
                storage_path = str(record.get("mobile_storage_path") or record.get("path") or "")
                images.append(
                    {
                        "_migration_entity_type": "capture_image",
                        "_migration_source_file": str(capture_file),
                        "_migration_record_id": legacy_image_id,
                        "_migration_session_id": legacy_session_id,
                        "_migration_filename": str(record.get("filename") or ""),
                        "_migration_storage_path": storage_path,
                        "id": canonical_uuid("capture_image", legacy_image_id),
                        "capture_session_id": session_uuid,
                        "storage_bucket": record.get("mobile_storage_bucket") or "mobile-capture-originals",
                        "storage_object_path": storage_path,
                        "original_filename": record.get("filename") or "",
                        "sequence_number": index,
                        "upload_status": "uploaded",
                        "processing_status": "staged" if session_row["status"] == "staged" else "processed",
                        "legacy_image_id": legacy_image_id,
                        "migration_metadata": {
                            "source_capture_session_file": str(capture_file),
                            "local_path": record.get("path") or "",
                            "side": record.get("side") or "",
                            "card_number": record.get("card_number") or "",
                        },
                        "created_at": record.get("captured_at") or capture.get("started_at") or None,
                    }
                )
    return sessions, images, invalid


def detect_duplicates(rows: list[Mapping[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    duplicates = []
    for row in rows:
        value = str(row.get(key) or "")
        if not value:
            continue
        seen[value] = seen.get(value, 0) + 1
        if seen[value] == 2:
            duplicates.append({"key": key, "value": value})
    return duplicates


def row_entity_type(row: Mapping[str, Any]) -> str:
    if row.get("_migration_entity_type"):
        return str(row.get("_migration_entity_type"))
    if row.get("legacy_image_id"):
        return "capture_image"
    if row.get("legacy_session_id"):
        return "capture_session"
    return "location"


def row_source_file(row: Mapping[str, Any]) -> str:
    metadata = dict(row.get("migration_metadata") or {})
    return str(
        row.get("_migration_source_file")
        or metadata.get("source_file")
        or metadata.get("source_capture_session_file")
        or ""
    )


def row_record_id(row: Mapping[str, Any]) -> str:
    return str(
        row.get("_migration_record_id")
        or row.get("legacy_image_id")
        or row.get("legacy_session_id")
        or row.get("legacy_id")
        or row.get("id")
        or ""
    )


def row_session_id(row: Mapping[str, Any]) -> str:
    return str(row.get("_migration_session_id") or row.get("legacy_session_id") or "")


def row_filename(row: Mapping[str, Any]) -> str:
    return str(row.get("_migration_filename") or row.get("original_filename") or "")


def row_storage_path(row: Mapping[str, Any]) -> str:
    return str(row.get("_migration_storage_path") or row.get("storage_object_path") or "")


def comparable_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_migration_")}


def flattened_values(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, Mapping):
        items: dict[str, Any] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.update(flattened_values(child, child_prefix))
        return items
    return {prefix: value}


def conflicting_fields(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> list[dict[str, Any]]:
    left = flattened_values(comparable_row(existing))
    right = flattened_values(comparable_row(incoming))
    fields = []
    for field in sorted(set(left) | set(right)):
        if left.get(field) != right.get(field):
            fields.append(
                {
                    "field": field,
                    "existing": left.get(field),
                    "incoming": right.get(field),
                }
            )
    return fields


def conflict_category(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> str:
    entity = row_entity_type(existing)
    if entity == "capture_image":
        if row_storage_path(existing) and row_storage_path(existing) == row_storage_path(incoming):
            return "Duplicate storage object path"
        if existing.get("checksum") and existing.get("checksum") == incoming.get("checksum") and existing.get("capture_session_id") == incoming.get("capture_session_id"):
            return "Duplicate image checksum"
        if row_record_id(existing) == row_record_id(incoming):
            return "Duplicate legacy identifier"
        return "Multiple legacy records map to one canonical record"
    if entity == "capture_session":
        if row_session_id(existing) and row_session_id(existing) == row_session_id(incoming):
            return "Duplicate capture session"
        if existing.get("location_id") != incoming.get("location_id"):
            return "Conflicting location assignment"
        if existing.get("status") != incoming.get("status"):
            return "Conflicting status"
        return "Multiple legacy records map to one canonical record"
    if existing.get("parent_location_id") != incoming.get("parent_location_id"):
        return "Missing or inconsistent parent relationship"
    if existing.get("legacy_etb_id") != incoming.get("legacy_etb_id"):
        return "Conflicting ETB/container assignment"
    if existing.get("status") != incoming.get("status"):
        return "Conflicting status"
    return "Multiple legacy records map to one canonical record"


def conflict_resolution_guidance(category: str) -> tuple[str, bool, str]:
    if category in {"Duplicate storage object path", "Duplicate capture session"}:
        return (
            "merge_provenance",
            True,
            "High",
        )
    if category in {"Exact duplicate", "Duplicate legacy identifier", "Duplicate image checksum"}:
        return (
            "skip_incoming",
            True,
            "High",
        )
    if category in {"Conflicting timestamp", "Legacy record is newer", "Existing Supabase record is newer"}:
        return (
            "review_timestamp_then_update_or_keep_existing",
            False,
            "Medium",
        )
    return ("manual_review", False, "Low")


def build_conflict(
    entity_type: str,
    key: str,
    value: str,
    existing: Mapping[str, Any],
    incoming: Mapping[str, Any],
) -> dict[str, Any]:
    fields = conflicting_fields(existing, incoming)
    category = conflict_category(existing, incoming)
    recommendation, automated, confidence = conflict_resolution_guidance(category)
    if not fields:
        category = "Exact duplicate"
        recommendation, automated, confidence = conflict_resolution_guidance(category)
    return {
        "entity_type": entity_type,
        "key": key,
        "value": value,
        "legacy_source_file": row_source_file(incoming),
        "legacy_record_id": row_record_id(incoming),
        "canonical_id": str(incoming.get("id") or value),
        "capture_session_id": row_session_id(incoming),
        "image_filename": row_filename(incoming),
        "storage_path": row_storage_path(incoming),
        "existing_values": comparable_row(existing),
        "incoming_values": comparable_row(incoming),
        "conflicting_fields": fields,
        "relevant_timestamps": {
            "existing_created_at": existing.get("created_at"),
            "existing_updated_at": existing.get("updated_at"),
            "incoming_created_at": incoming.get("created_at"),
            "incoming_updated_at": incoming.get("updated_at"),
        },
        "source_application": str(incoming.get("source_application") or incoming.get("source") or ""),
        "classification": category,
        "recommended_resolution": recommendation,
        "safe_to_automate": automated,
        "confidence": confidence,
        "resolved": False,
        "blocking": True,
        "existing_source_file": row_source_file(existing),
        "existing_record_id": row_record_id(existing),
    }


def excluded_record_from_conflict(conflict: Mapping[str, Any]) -> dict[str, Any]:
    action = str(conflict.get("resolution_action") or conflict.get("recommended_resolution") or "")
    safe_to_skip = (
        bool(conflict.get("safe_to_automate"))
        or bool(conflict.get("resolved") and action == "skip_exact_duplicate")
    )
    return {
        "entity_type": conflict.get("entity_type"),
        "source_file": conflict.get("legacy_source_file"),
        "record_id": conflict.get("legacy_record_id"),
        "session_id": conflict.get("capture_session_id"),
        "filename": conflict.get("image_filename"),
        "storage_path": conflict.get("storage_path"),
        "reason_excluded": conflict.get("classification"),
        "conflict_category": conflict.get("classification"),
        "safe_to_skip": safe_to_skip,
        "recommended_resolution": action,
        "should_merge_or_import": (
            "approved duplicate skip"
            if action == "skip_exact_duplicate"
            else "merge provenance before apply"
            if action == "merge_provenance"
            else "skip incoming duplicate"
        ),
        "canonical_id": conflict.get("canonical_id"),
    }


def deduplicate_rows(
    rows: list[dict[str, Any]],
    key: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    unique: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        value = str(row.get(key) or "")
        if not value:
            unique[f"__missing__:{len(unique)}"] = row
            continue
        existing = unique.get(value)
        if existing is None:
            unique[value] = row
            continue
        entity_type = row_entity_type(row)
        if json.dumps(existing, sort_keys=True, default=str) == json.dumps(row, sort_keys=True, default=str):
            duplicate = build_conflict(entity_type, key, value, existing, row)
            duplicate["classification"] = "Exact duplicate"
            duplicate["recommended_resolution"] = "skip_incoming"
            duplicate["safe_to_automate"] = True
            duplicate["confidence"] = "High"
            duplicate["resolved"] = True
            duplicate["blocking"] = False
            duplicates.append(duplicate)
            excluded.append(excluded_record_from_conflict(duplicate))
        else:
            conflict = build_conflict(entity_type, key, value, existing, row)
            conflicts.append(conflict)
            excluded.append(excluded_record_from_conflict(conflict))
    return list(unique.values()), duplicates, conflicts, excluded


def deduplicate_rows_by_identity(
    rows: list[dict[str, Any]],
    identity_name: str,
    identity_value,
    category: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    unique: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        value = str(identity_value(row) or "")
        if not value:
            unique.append(row)
            continue
        existing = seen.get(value)
        if existing is None:
            seen[value] = row
            unique.append(row)
            continue
        conflict = build_conflict(row_entity_type(row), identity_name, value, existing, row)
        conflict["classification"] = category
        recommendation, automated, confidence = conflict_resolution_guidance(category)
        conflict["recommended_resolution"] = recommendation
        conflict["safe_to_automate"] = automated
        conflict["confidence"] = confidence
        conflicts.append(conflict)
        excluded.append(excluded_record_from_conflict(conflict))
    return unique, conflicts, excluded


def enforce_capture_image_identity_rules(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows, storage_conflicts, storage_excluded = deduplicate_rows_by_identity(
        rows,
        "storage_bucket+storage_object_path",
        lambda row: f"{row.get('storage_bucket') or ''}|{row.get('storage_object_path') or ''}"
        if row.get("storage_object_path")
        else "",
        "Duplicate storage object path",
    )
    rows, sequence_conflicts, sequence_excluded = deduplicate_rows_by_identity(
        rows,
        "capture_session_id+sequence_number",
        lambda row: f"{row.get('capture_session_id') or ''}|{row.get('sequence_number') or ''}"
        if row.get("capture_session_id") and row.get("sequence_number")
        else "",
        "Multiple legacy records map to one canonical record",
    )
    rows, checksum_conflicts, checksum_excluded = deduplicate_rows_by_identity(
        rows,
        "capture_session_id+checksum",
        lambda row: f"{row.get('capture_session_id') or ''}|{row.get('checksum') or ''}"
        if row.get("capture_session_id") and row.get("checksum")
        else "",
        "Duplicate image checksum",
    )
    return (
        rows,
        storage_conflicts + sequence_conflicts + checksum_conflicts,
        storage_excluded + sequence_excluded + checksum_excluded,
    )


def assign_conflict_numbers(conflicts: list[dict[str, Any]]) -> None:
    for index, conflict in enumerate(conflicts, start=1):
        conflict["conflict_number"] = index
        conflict["conflict_id"] = f"CV-REG-{index:04d}"


def load_resolution_file(path: Path | None) -> dict[str, Any]:
    if not path:
        return {"schema_version": "1.0", "resolutions": []}
    data = read_json(path)
    resolutions = data.get("resolutions")
    if not isinstance(resolutions, list):
        raise ValueError("Resolution file must contain a resolutions list.")
    for item in resolutions:
        action = str(item.get("action") or "")
        if action not in RESOLUTION_ACTIONS:
            raise ValueError(f"Unsupported resolution action: {action!r}")
    return data


def resolution_index(resolution_file: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    lookup: dict[str, Mapping[str, Any]] = {}
    for item in resolution_file.get("resolutions", []) or []:
        conflict_id = str(item.get("conflict_id") or "")
        if conflict_id:
            lookup[conflict_id] = item
    return lookup


def apply_reviewed_resolutions(
    rows_by_entity: dict[str, list[dict[str, Any]]],
    conflicts: list[dict[str, Any]],
    resolution_file: Mapping[str, Any],
) -> None:
    lookup = resolution_index(resolution_file)
    for conflict in conflicts:
        item = lookup.get(str(conflict.get("conflict_id") or ""))
        if not item:
            continue
        action = str(item.get("action") or "")
        approved = bool(item.get("approved"))
        if not approved or action == "manual_block":
            conflict["resolution_action"] = action or "unapproved"
            conflict["blocking"] = True
            conflict["resolved"] = False
            continue
        if action in {"skip_exact_duplicate", "skip_incoming", "keep_existing"}:
            conflict["resolution_action"] = action
            conflict["blocking"] = False
            conflict["resolved"] = True
            continue
        if action == "merge_provenance":
            merge_provenance(rows_by_entity, conflict)
            conflict["resolution_action"] = action
            conflict["blocking"] = False
            conflict["resolved"] = True
            continue
        if action == "update_from_incoming":
            update_from_incoming(rows_by_entity, conflict)
            conflict["resolution_action"] = action
            conflict["blocking"] = False
            conflict["resolved"] = True
            continue
        if action == "keep_both":
            if keep_both_with_override(rows_by_entity, conflict, item):
                conflict["resolution_action"] = action
                conflict["blocking"] = False
                conflict["resolved"] = True
            else:
                conflict["resolution_action"] = action
                conflict["blocking"] = True
                conflict["resolved"] = False


def merge_provenance(rows_by_entity: dict[str, list[dict[str, Any]]], conflict: Mapping[str, Any]) -> None:
    row = find_row_by_id(rows_by_entity.get(str(conflict.get("entity_type")) or "", []), str(conflict.get("canonical_id") or ""))
    if row is None:
        return
    metadata = dict(row.get("migration_metadata") or {})
    merged = list(metadata.get("merged_conflicts") or [])
    merged.append(
        {
            "conflict_id": conflict.get("conflict_id"),
            "source_file": conflict.get("legacy_source_file"),
            "record_id": conflict.get("legacy_record_id"),
            "storage_path": conflict.get("storage_path"),
        }
    )
    metadata["merged_conflicts"] = merged
    row["migration_metadata"] = metadata


def update_from_incoming(rows_by_entity: dict[str, list[dict[str, Any]]], conflict: Mapping[str, Any]) -> None:
    rows = rows_by_entity.get(str(conflict.get("entity_type")) or "", [])
    row = find_row_by_id(rows, str(conflict.get("canonical_id") or ""))
    if row is not None:
        row.clear()
        row.update(dict(conflict.get("incoming_values") or {}))


def keep_both_with_override(
    rows_by_entity: dict[str, list[dict[str, Any]]],
    conflict: Mapping[str, Any],
    item: Mapping[str, Any],
) -> bool:
    override = str(item.get("canonical_id_override") or "")
    if not override:
        return False
    incoming = dict(conflict.get("incoming_values") or {})
    incoming["id"] = override
    rows_by_entity.setdefault(str(conflict.get("entity_type") or ""), []).append(incoming)
    return True


def find_row_by_id(rows: list[dict[str, Any]], row_id: str) -> dict[str, Any] | None:
    for row in rows:
        if str(row.get("id") or "") == row_id:
            return row
    return None


def identity_rules() -> dict[str, Any]:
    return {
        "locations": [
            "Canonical id is deterministic from location display code during legacy migration.",
            "ETB display_code must be unique per owner.",
            "Slot display_code must be unique per owner and parent-child hierarchy must point to the ETB row.",
        ],
        "capture_sessions": [
            "Canonical id is deterministic from legacy capture session id during legacy migration.",
            "owner_user_id plus legacy_session_id is unique in Supabase.",
        ],
        "capture_images": [
            "Storage bucket plus storage object path is the strongest canonical uniqueness signal.",
            "Capture session id plus sequence number is a required ordering uniqueness signal.",
            "Checksum within the same session is duplicate-content evidence when available.",
            "Filename alone is never a uniqueness rule.",
        ],
    }


def balance_counts(
    discovered: Mapping[str, int],
    prepared: Mapping[str, int],
    duplicates: list[Mapping[str, Any]],
    conflicts: list[Mapping[str, Any]],
    invalid: list[Mapping[str, Any]],
) -> dict[str, Any]:
    entities = {
        "locations": "location",
        "capture_sessions": "capture_session",
        "capture_images": "capture_image",
    }
    rows = {}
    balanced = True
    for record_key, entity_type in entities.items():
        duplicate_count = sum(1 for item in duplicates if item.get("entity_type") == entity_type)
        approved_duplicate_count = sum(
            1
            for item in conflicts
            if item.get("entity_type") == entity_type
            and item.get("resolved")
            and item.get("resolution_action") == "skip_exact_duplicate"
        )
        conflict_count = sum(
            1
            for item in conflicts
            if item.get("entity_type") == entity_type and item.get("blocking")
        )
        invalid_count = sum(1 for item in invalid if item.get("type") == entity_type)
        skipped_duplicate_count = duplicate_count + approved_duplicate_count
        total = int(prepared.get(record_key, 0)) + skipped_duplicate_count + conflict_count + invalid_count
        expected = int(discovered.get(record_key, 0))
        row = {
            "discovered": expected,
            "prepared": int(prepared.get(record_key, 0)),
            "skipped_exact_duplicates": skipped_duplicate_count,
            "unresolved_conflicts": conflict_count,
            "invalid": invalid_count,
            "intentionally_excluded": 0,
            "balanced_total": total,
            "balanced": expected == total,
        }
        rows[record_key] = row
        balanced = balanced and row["balanced"]
    return {"balanced": balanced, "entities": rows}


def clean_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []
    for row in rows:
        cleaned.append(
            {
                key: value
                for key, value in row.items()
                if value is not None and value != "" and not key.startswith("_migration_")
            }
        )
    return cleaned


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    resolution_file = load_resolution_file(args.resolution_file)
    registry = read_json(args.registry)
    location_rows, invalid_locations = build_location_rows(registry)
    session_rows, image_rows, invalid_sessions = build_session_and_image_rows()
    discovered = {
        "locations": len(location_rows),
        "capture_sessions": len(session_rows),
        "capture_images": len(image_rows),
    }
    location_rows, duplicate_locations, conflicting_locations, excluded_locations = deduplicate_rows(location_rows, "id")
    session_rows, duplicate_sessions, conflicting_sessions, excluded_sessions = deduplicate_rows(session_rows, "id")
    image_rows, duplicate_images, conflicting_images, excluded_images = deduplicate_rows(image_rows, "id")
    image_rows, identity_image_conflicts, identity_image_excluded = enforce_capture_image_identity_rules(image_rows)
    duplicates = duplicate_locations + duplicate_sessions + duplicate_images
    conflicts = conflicting_locations + conflicting_sessions + conflicting_images + identity_image_conflicts
    assign_conflict_numbers(conflicts)
    rows_by_entity = {
        "location": location_rows,
        "capture_session": session_rows,
        "capture_image": image_rows,
    }
    apply_reviewed_resolutions(rows_by_entity, conflicts, resolution_file)
    location_rows = rows_by_entity["location"]
    session_rows = rows_by_entity["capture_session"]
    image_rows = rows_by_entity["capture_image"]
    excluded_records = excluded_locations + [excluded_record_from_conflict(conflict) for conflict in conflicts]
    invalid_records = invalid_locations + invalid_sessions
    prepared = {
        "locations": len(location_rows),
        "capture_sessions": len(session_rows),
        "capture_images": len(image_rows),
    }
    balance = balance_counts(discovered, prepared, duplicates, conflicts, invalid_records)
    blocking_conflicts = [conflict for conflict in conflicts if conflict.get("blocking")]
    approved_duplicate_skips = {
        "locations": sum(
            1
            for conflict in conflicts
            if conflict.get("entity_type") == "location"
            and conflict.get("resolved")
            and conflict.get("resolution_action") == "skip_exact_duplicate"
        ),
        "capture_sessions": sum(
            1
            for conflict in conflicts
            if conflict.get("entity_type") == "capture_session"
            and conflict.get("resolved")
            and conflict.get("resolution_action") == "skip_exact_duplicate"
        ),
        "capture_images": sum(
            1
            for conflict in conflicts
            if conflict.get("entity_type") == "capture_image"
            and conflict.get("resolved")
            and conflict.get("resolution_action") == "skip_exact_duplicate"
        ),
    }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "apply" if args.apply else "dry-run",
        "registry": str(args.registry),
        "supabase_project_url": "configured" if args.apply else "not used in dry-run",
        "approved_supabase_project_ref": APPROVED_SUPABASE_PROJECT_REF,
        "resolution_file": str(args.resolution_file) if args.resolution_file else "",
        "identity_rules": identity_rules(),
        "records_discovered": discovered,
        "records_prepared": prepared,
        "records_inserted_or_updated": {
            "locations": 0,
            "capture_sessions": 0,
            "capture_images": 0,
        },
        "records_skipped": {
            "locations": len(duplicate_locations),
            "capture_sessions": len(duplicate_sessions),
            "capture_images": len(duplicate_images),
        },
        "records_excluded": {
            "locations": sum(1 for row in excluded_records if row.get("entity_type") == "location"),
            "capture_sessions": sum(1 for row in excluded_records if row.get("entity_type") == "capture_session"),
            "capture_images": sum(1 for row in excluded_records if row.get("entity_type") == "capture_image"),
        },
        "approved_duplicate_skips": approved_duplicate_skips,
        "duplicate_records": duplicates,
        "conflicting_records": conflicts,
        "excluded_records": excluded_records,
        "excluded_sessions": [
            row for row in excluded_records if row.get("entity_type") == "capture_session"
        ],
        "excluded_images": [
            row for row in excluded_records if row.get("entity_type") == "capture_image"
        ],
        "invalid_records": invalid_records,
        "blocking_conflicts": blocking_conflicts,
        "balance": balance,
        "failed_records": [],
        "legacy_ids_mapped": {
            "locations": [
                {"legacy_id": row.get("legacy_id"), "canonical_id": row.get("id")}
                for row in location_rows
            ],
            "capture_sessions": [
                {
                    "legacy_id": row.get("legacy_session_id"),
                    "canonical_id": row.get("id"),
                }
                for row in session_rows
            ],
        },
        "unresolved_relationships": [
            row
            for row in session_rows
            if row.get("location_id")
            and row.get("location_id") not in {location.get("id") for location in location_rows}
        ],
        "prepared_rows": {
            "locations": clean_rows(location_rows),
            "capture_sessions": clean_rows(session_rows),
            "capture_images": clean_rows(image_rows),
        },
    }


def write_reports(report: Mapping[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "legacy_registry_migration_report.json"
    md_path = output_dir / "legacy_registry_migration_summary.md"
    conflict_json_path = output_dir / "legacy_registry_conflict_report.json"
    conflict_csv_path = output_dir / "legacy_registry_conflict_report.csv"
    conflict_md_path = output_dir / "legacy_registry_conflict_report.md"
    excluded_sessions_csv_path = output_dir / "excluded_capture_sessions.csv"
    excluded_images_csv_path = output_dir / "excluded_capture_images.csv"
    resolution_plan_path = output_dir / "proposed_resolution_plan.json"
    balanced_summary_path = output_dir / "balanced_dry_run_summary.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    conflict_json_path.write_text(json.dumps(report.get("conflicting_records", []), indent=2) + "\n", encoding="utf-8")
    write_conflict_csv(report.get("conflicting_records", []), conflict_csv_path)
    write_excluded_csv(report.get("excluded_sessions", []), excluded_sessions_csv_path)
    write_excluded_csv(report.get("excluded_images", []), excluded_images_csv_path)
    write_conflict_markdown(report, conflict_md_path)
    write_resolution_plan(report, resolution_plan_path)
    balanced_summary_path.write_text(json.dumps(report.get("balance", {}), indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Legacy Registry Migration Summary",
        "",
        f"Generated: {report['generated_at']}",
        f"Mode: {report['mode']}",
        f"Registry: `{report['registry']}`",
        "",
        "## Records",
        "",
    ]
    for key, value in report["records_discovered"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Prepared Rows", ""])
    for key, value in report["records_prepared"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Quality",
            "",
            f"- duplicates: {len(report['duplicate_records'])}",
            f"- reviewed conflict records: {len(report['conflicting_records'])}",
            f"- blocking conflicts: {len(report.get('blocking_conflicts', []))}",
            f"- approved duplicate skips: {sum((report.get('approved_duplicate_skips') or {}).values())}",
            f"- invalid: {len(report['invalid_records'])}",
            f"- unresolved relationships: {len(report['unresolved_relationships'])}",
            f"- counts balanced: {report.get('balance', {}).get('balanced')}",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def write_conflict_csv(conflicts: Any, path: Path) -> None:
    fieldnames = [
        "conflict_number",
        "conflict_id",
        "entity_type",
        "classification",
        "legacy_source_file",
        "legacy_record_id",
        "canonical_id",
        "capture_session_id",
        "image_filename",
        "storage_path",
        "conflicting_fields",
        "existing_updated_at",
        "incoming_updated_at",
        "source_application",
        "recommended_resolution",
        "safe_to_automate",
        "confidence",
        "resolved",
        "blocking",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for conflict in conflicts or []:
            writer.writerow(
                {
                    "conflict_number": conflict.get("conflict_number"),
                    "conflict_id": conflict.get("conflict_id"),
                    "entity_type": conflict.get("entity_type"),
                    "classification": conflict.get("classification"),
                    "legacy_source_file": conflict.get("legacy_source_file"),
                    "legacy_record_id": conflict.get("legacy_record_id"),
                    "canonical_id": conflict.get("canonical_id"),
                    "capture_session_id": conflict.get("capture_session_id"),
                    "image_filename": conflict.get("image_filename"),
                    "storage_path": conflict.get("storage_path"),
                    "conflicting_fields": "; ".join(
                        str(item.get("field")) for item in conflict.get("conflicting_fields", [])
                    ),
                    "existing_updated_at": conflict.get("relevant_timestamps", {}).get("existing_updated_at"),
                    "incoming_updated_at": conflict.get("relevant_timestamps", {}).get("incoming_updated_at"),
                    "source_application": conflict.get("source_application"),
                    "recommended_resolution": conflict.get("recommended_resolution"),
                    "safe_to_automate": conflict.get("safe_to_automate"),
                    "confidence": conflict.get("confidence"),
                    "resolved": conflict.get("resolved"),
                    "blocking": conflict.get("blocking"),
                }
            )


def write_excluded_csv(rows: Any, path: Path) -> None:
    fieldnames = [
        "entity_type",
        "source_file",
        "record_id",
        "session_id",
        "filename",
        "storage_path",
        "reason_excluded",
        "conflict_category",
        "safe_to_skip",
        "recommended_resolution",
        "should_merge_or_import",
        "canonical_id",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows or []:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_conflict_markdown(report: Mapping[str, Any], path: Path) -> None:
    conflicts = list(report.get("conflicting_records", []) or [])
    counts: dict[str, int] = {}
    for conflict in conflicts:
        category = str(conflict.get("classification") or "Other")
        counts[category] = counts.get(category, 0) + 1
    lines = [
        "# Legacy Registry Conflict Report",
        "",
        f"Generated: {report.get('generated_at')}",
        f"Mode: {report.get('mode')}",
        f"Total conflicts: {len(conflicts)}",
        f"Blocking conflicts: {len(report.get('blocking_conflicts', []))}",
        "",
        "## Category Counts",
        "",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"- {category}: {count}")
    lines.extend(["", "## Conflicts", ""])
    for conflict in conflicts:
        fields = ", ".join(item.get("field", "") for item in conflict.get("conflicting_fields", []))
        lines.extend(
            [
                f"### {conflict.get('conflict_id')} - {conflict.get('classification')}",
                "",
                f"- Conflict number: {conflict.get('conflict_number')}",
                f"- Entity type: {conflict.get('entity_type')}",
                f"- Legacy source file: `{conflict.get('legacy_source_file')}`",
                f"- Legacy record ID: `{conflict.get('legacy_record_id')}`",
                f"- Canonical ID: `{conflict.get('canonical_id')}`",
                f"- Capture session ID: `{conflict.get('capture_session_id')}`",
                f"- Image filename/storage path: `{conflict.get('image_filename') or conflict.get('storage_path')}`",
                f"- Conflicting fields: {fields}",
                f"- Existing updated_at: `{conflict.get('relevant_timestamps', {}).get('existing_updated_at')}`",
                f"- Incoming updated_at: `{conflict.get('relevant_timestamps', {}).get('incoming_updated_at')}`",
                f"- Source application: `{conflict.get('source_application')}`",
                f"- Recommended resolution: `{conflict.get('recommended_resolution')}`",
                f"- Safe to automate: `{conflict.get('safe_to_automate')}`",
                f"- Confidence: `{conflict.get('confidence')}`",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_resolution_plan(report: Mapping[str, Any], path: Path) -> None:
    plan = {
        "schema_version": "1.0",
        "approved_project_ref": APPROVED_SUPABASE_PROJECT_REF,
        "generated_at": report.get("generated_at"),
        "instructions": (
            "Review every proposed resolution. Set approved to true only after "
            "operator review. Apply mode refuses unresolved or unapproved conflicts."
        ),
        "resolutions": [
            {
                "conflict_id": conflict.get("conflict_id"),
                "entity_type": conflict.get("entity_type"),
                "canonical_id": conflict.get("canonical_id"),
                "classification": conflict.get("classification"),
                "action": conflict.get("recommended_resolution")
                if conflict.get("recommended_resolution") in RESOLUTION_ACTIONS
                else "manual_block",
                "approved": False,
                "confidence": conflict.get("confidence"),
                "notes": "",
            }
            for conflict in report.get("conflicting_records", []) or []
        ],
    }
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")


def apply_report(report: dict[str, Any]) -> dict[str, Any]:
    client = SupabaseRegistryClient()
    inserted = report["records_inserted_or_updated"]
    try:
        locations = client.upsert_locations(report["prepared_rows"]["locations"])
        inserted["locations"] = len(locations)
        sessions = client.upsert_capture_sessions(report["prepared_rows"]["capture_sessions"])
        inserted["capture_sessions"] = len(sessions)
        images = client.upsert_capture_images(report["prepared_rows"]["capture_images"])
        inserted["capture_images"] = len(images)
    except SupabaseRegistryError as exc:
        report["failed_records"].append({"type": "supabase_apply", "error": str(exc)})
        raise
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or apply migration from legacy ETB/location JSON to canonical Supabase registry."
    )
    parser.add_argument("--registry", type=Path, default=LEGACY_REGISTRY)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--backup-dir", type=Path, default=None)
    parser.add_argument("--resolution-file", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-backup", action="store_true")
    parser.add_argument("--confirm-schema-migration", action="store_true")
    parser.add_argument("--approved-project-ref", default=APPROVED_SUPABASE_PROJECT_REF)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.report_dir or args.output_dir or (
        WORK_SESSIONS_DIR / "supabase_registry_migration" / timestamp
    )
    backup_dir = args.backup_dir or (output_dir / "backups")
    legacy_paths = [args.registry, LEGACY_REGISTRY_OLD, LEGACY_BATCH_REGISTRY]

    if args.apply and not args.confirm_backup:
        print("Apply mode requires --confirm-backup after reviewing the backup path.", file=sys.stderr)
        return 2
    if args.apply and not args.confirm_schema_migration:
        print("Apply mode requires --confirm-schema-migration after Supabase schema deployment is verified.", file=sys.stderr)
        return 2

    backups = backup_files(legacy_paths, backup_dir)
    report = build_report(args)
    report["backup"] = {"path": str(backup_dir), "files": backups}

    if args.apply:
        validation_error = apply_validation_error(args, report)
        if validation_error:
            json_path, md_path = write_reports(report, output_dir)
            print(f"Apply blocked: {validation_error}", file=sys.stderr)
            print(f"Backup: {backup_dir}", file=sys.stderr)
            print(f"JSON report: {json_path}", file=sys.stderr)
            print(f"Summary: {md_path}", file=sys.stderr)
            return 3
        report = apply_report(report)

    json_path, md_path = write_reports(report, output_dir)
    print(f"Mode: {report['mode']}")
    print(f"Backup: {backup_dir}")
    print(f"JSON report: {json_path}")
    print(f"Summary: {md_path}")
    print(f"Locations discovered: {report['records_discovered']['locations']}")
    print(f"Capture sessions discovered: {report['records_discovered']['capture_sessions']}")
    print(f"Capture images discovered: {report['records_discovered']['capture_images']}")
    print(f"Invalid records: {len(report['invalid_records'])}")
    print(f"Duplicates: {len(report['duplicate_records'])}")
    print(f"Reviewed conflict records: {len(report['conflicting_records'])}")
    print(f"Blocking conflicts: {len(report.get('blocking_conflicts', []))}")
    print(f"Approved duplicate skips: {sum((report.get('approved_duplicate_skips') or {}).values())}")
    print(f"Unresolved relationships: {len(report['unresolved_relationships'])}")
    return 0 if not report["failed_records"] else 1


def apply_validation_error(args: argparse.Namespace, report: Mapping[str, Any]) -> str:
    if not args.resolution_file:
        return "a reviewed --resolution-file is required."
    if report["invalid_records"]:
        return "invalid legacy records remain."
    if report.get("blocking_conflicts"):
        return "unresolved blocking conflicts remain."
    if not report.get("balance", {}).get("balanced"):
        return "migration totals do not reconcile."
    backup = report.get("backup", {})
    files = list(backup.get("files") or [])
    if not files:
        return "required legacy backups are missing."
    for item in files:
        backup_path = Path(str(item.get("backup") or ""))
        if not backup_path.exists():
            return f"backup file is missing: {backup_path}"
    url = os.environ.get("CARDVECTOR_SUPABASE_URL") or os.environ.get("SUPABASE_URL") or ""
    project_ref = project_ref_from_url(str(url or ""))
    expected = str(args.approved_project_ref or APPROVED_SUPABASE_PROJECT_REF)
    if project_ref != expected:
        return f"configured Supabase project {project_ref or '<unknown>'} does not match approved project {expected}."
    return ""


def project_ref_from_url(url: str) -> str:
    text = str(url or "").strip().lower()
    if "://" in text:
        text = text.split("://", 1)[1]
    host = text.split("/", 1)[0]
    if host.endswith(".supabase.co"):
        return host.split(".", 1)[0]
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
