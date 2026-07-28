from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping


CANONICAL_LOCATIONS_TABLE = "cardvector_storage_locations"
CANONICAL_CAPTURE_SESSIONS_TABLE = "cardvector_capture_sessions"
CANONICAL_CAPTURE_IMAGES_TABLE = "cardvector_capture_images"
CANONICAL_INVENTORY_RELATIONSHIPS_TABLE = "cardvector_inventory_relationships"


class SupabaseRegistryError(RuntimeError):
    """Raised when the canonical Supabase registry cannot be reached safely."""


def environment_config() -> tuple[str, str]:
    url = (
        os.environ.get("CARDVECTOR_SUPABASE_URL")
        or os.environ.get("SUPABASE_URL")
        or ""
    ).strip()
    key = (
        os.environ.get("CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    if not url or not key:
        raise SupabaseRegistryError(
            "Set CARDVECTOR_SUPABASE_URL and CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY "
            "before using the canonical registry service."
        )
    return url.rstrip("/"), key


def legacy_status_to_canonical(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    mapping = {
        "": "unknown",
        "available": "active",
        "active": "active",
        "empty": "empty",
        "full": "full",
        "location complete": "location_complete",
        "needs review": "needs_review",
        "mobile capture staged": "staged",
        "ready for capture": "active",
        "waiting for capture": "active",
        "archived": "archived",
    }
    return mapping.get(normalized, "unknown")


def canonical_status_to_legacy(value: str) -> str:
    mapping = {
        "empty": "Empty",
        "active": "Active",
        "full": "Full",
        "location_complete": "Location Complete",
        "needs_review": "Needs Review",
        "staged": "Mobile Capture Staged",
        "archived": "Archived",
        "unknown": "Needs Review",
    }
    return mapping.get(str(value or "").strip().lower(), "Needs Review")


@dataclass(frozen=True)
class CanonicalLocation:
    id: str
    name: str
    location_type: str
    status: str = "active"
    owner_user_id: str = ""
    organization_id: str = ""
    parent_location_id: str = ""
    description: str = ""
    source: str = "cardvector"
    legacy_id: str = ""
    legacy_etb_id: str = ""
    legacy_location_code: str = ""
    display_code: str = ""
    capacity: int | None = None
    stored_count: int = 0
    sync_state: str = "synced"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    migration_metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    archived_at: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "CanonicalLocation":
        return cls(
            id=str(row.get("id") or ""),
            owner_user_id=str(row.get("owner_user_id") or ""),
            organization_id=str(row.get("organization_id") or ""),
            parent_location_id=str(row.get("parent_location_id") or ""),
            name=str(row.get("name") or ""),
            description=str(row.get("description") or ""),
            location_type=str(row.get("location_type") or "custom"),
            status=str(row.get("status") or "unknown"),
            source=str(row.get("source") or ""),
            legacy_id=str(row.get("legacy_id") or ""),
            legacy_etb_id=str(row.get("legacy_etb_id") or ""),
            legacy_location_code=str(row.get("legacy_location_code") or ""),
            display_code=str(row.get("display_code") or ""),
            capacity=_optional_int(row.get("capacity")),
            stored_count=_int(row.get("stored_count")),
            sync_state=str(row.get("sync_state") or ""),
            metadata=dict(row.get("metadata") or {}),
            migration_metadata=dict(row.get("migration_metadata") or {}),
            created_at=str(row.get("created_at") or ""),
            updated_at=str(row.get("updated_at") or ""),
            archived_at=str(row.get("archived_at") or ""),
        )

    def to_row(self) -> dict[str, Any]:
        payload = asdict(self)
        return _remove_empty_strings(payload)


@dataclass(frozen=True)
class CanonicalCaptureSession:
    id: str
    status: str
    owner_user_id: str = ""
    organization_id: str = ""
    source_application: str = "CardVector.app"
    originating_device: Mapping[str, Any] = field(default_factory=dict)
    location_id: str = ""
    photo_count: int = 0
    processed_count: int = 0
    recognized_count: int = 0
    failed_count: int = 0
    sync_state: str = "synced"
    legacy_session_id: str = ""
    legacy_capture_type: str = ""
    legacy_etb_location_id: str = ""
    migration_metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    archived_at: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "CanonicalCaptureSession":
        return cls(
            id=str(row.get("id") or ""),
            owner_user_id=str(row.get("owner_user_id") or ""),
            organization_id=str(row.get("organization_id") or ""),
            source_application=str(row.get("source_application") or "CardVector.app"),
            originating_device=dict(row.get("originating_device") or {}),
            location_id=str(row.get("location_id") or ""),
            status=str(row.get("status") or "draft"),
            photo_count=_int(row.get("photo_count")),
            processed_count=_int(row.get("processed_count")),
            recognized_count=_int(row.get("recognized_count")),
            failed_count=_int(row.get("failed_count")),
            sync_state=str(row.get("sync_state") or ""),
            legacy_session_id=str(row.get("legacy_session_id") or ""),
            legacy_capture_type=str(row.get("legacy_capture_type") or ""),
            legacy_etb_location_id=str(row.get("legacy_etb_location_id") or ""),
            migration_metadata=dict(row.get("migration_metadata") or {}),
            created_at=str(row.get("created_at") or ""),
            updated_at=str(row.get("updated_at") or ""),
            completed_at=str(row.get("completed_at") or ""),
            archived_at=str(row.get("archived_at") or ""),
        )


@dataclass(frozen=True)
class CanonicalCaptureImage:
    id: str
    capture_session_id: str
    storage_object_path: str
    sequence_number: int
    owner_user_id: str = ""
    storage_bucket: str = "mobile-capture-originals"
    original_filename: str = ""
    upload_status: str = "uploaded"
    processing_status: str = "pending"
    checksum: str = ""
    byte_size: int | None = None
    width: int | None = None
    height: int | None = None
    legacy_image_id: str = ""
    migration_metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    archived_at: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "CanonicalCaptureImage":
        return cls(
            id=str(row.get("id") or ""),
            capture_session_id=str(row.get("capture_session_id") or ""),
            owner_user_id=str(row.get("owner_user_id") or ""),
            storage_bucket=str(row.get("storage_bucket") or "mobile-capture-originals"),
            storage_object_path=str(row.get("storage_object_path") or ""),
            original_filename=str(row.get("original_filename") or ""),
            sequence_number=_int(row.get("sequence_number")),
            upload_status=str(row.get("upload_status") or "uploaded"),
            processing_status=str(row.get("processing_status") or "pending"),
            checksum=str(row.get("checksum") or ""),
            byte_size=_optional_int(row.get("byte_size")),
            width=_optional_int(row.get("width")),
            height=_optional_int(row.get("height")),
            legacy_image_id=str(row.get("legacy_image_id") or ""),
            migration_metadata=dict(row.get("migration_metadata") or {}),
            created_at=str(row.get("created_at") or ""),
            updated_at=str(row.get("updated_at") or ""),
            archived_at=str(row.get("archived_at") or ""),
        )


class SupabaseRegistryClient:
    """REST adapter for canonical CardVector registry tables.

    The service role is used by trusted desktop tools only. Browser code uses
    RLS-protected public Supabase JS calls instead.
    """

    def __init__(
        self,
        supabase_url: str | None = None,
        service_role_key: str | None = None,
        *,
        retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if supabase_url is None or service_role_key is None:
            supabase_url, service_role_key = environment_config()
        self.supabase_url = str(supabase_url or "").rstrip("/")
        self.service_role_key = str(service_role_key or "")
        self.retries = max(0, int(retries))
        self._sleep = sleep
        if not self.supabase_url or not self.service_role_key:
            raise SupabaseRegistryError("Supabase URL and service-role key are required.")

    def list_locations(self) -> list[CanonicalLocation]:
        rows = self.request_json(
            "GET",
            f"/rest/v1/{CANONICAL_LOCATIONS_TABLE}"
            "?select=*&archived_at=is.null&order=display_code.asc",
        ) or []
        return [CanonicalLocation.from_row(row) for row in rows]

    def list_capture_sessions(self, limit: int = 100) -> list[CanonicalCaptureSession]:
        query = urllib.parse.urlencode(
            {
                "select": "*",
                "order": "updated_at.desc",
                "limit": str(int(limit)),
            }
        )
        rows = self.request_json(
            "GET",
            f"/rest/v1/{CANONICAL_CAPTURE_SESSIONS_TABLE}?{query}",
        ) or []
        return [CanonicalCaptureSession.from_row(row) for row in rows]

    def upsert_locations(self, rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        return self.request_json(
            "POST",
            f"/rest/v1/{CANONICAL_LOCATIONS_TABLE}?on_conflict=id",
            [_remove_empty_strings(dict(row)) for row in rows],
            prefer="resolution=merge-duplicates,return=representation",
        ) or []

    def upsert_capture_sessions(
        self,
        rows: list[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        return self.request_json(
            "POST",
            f"/rest/v1/{CANONICAL_CAPTURE_SESSIONS_TABLE}?on_conflict=id",
            [_remove_empty_strings(dict(row)) for row in rows],
            prefer="resolution=merge-duplicates,return=representation",
        ) or []

    def upsert_capture_images(
        self,
        rows: list[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        return self.request_json(
            "POST",
            f"/rest/v1/{CANONICAL_CAPTURE_IMAGES_TABLE}?on_conflict=id",
            [_remove_empty_strings(dict(row)) for row in rows],
            prefer="resolution=merge-duplicates,return=representation",
        ) or []

    def update_capture_status_by_legacy_id(
        self,
        legacy_session_id: str,
        status: str,
        *,
        processed_count: int | None = None,
        failed_count: int | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"status": status}
        if processed_count is not None:
            payload["processed_count"] = int(processed_count)
        if failed_count is not None:
            payload["failed_count"] = int(failed_count)
        query = urllib.parse.urlencode(
            {"legacy_session_id": f"eq.{legacy_session_id}", "select": "*"}
        )
        return self.request_json(
            "PATCH",
            f"/rest/v1/{CANONICAL_CAPTURE_SESSIONS_TABLE}?{query}",
            payload,
            prefer="return=representation",
        ) or []

    def request_json(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        *,
        prefer: str | None = None,
    ) -> Any:
        url = f"{self.supabase_url}{path}"
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            request = urllib.request.Request(
                url,
                data=payload,
                headers=headers,
                method=method.upper(),
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    data = response.read()
                if not data:
                    return None
                return json.loads(data.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise SupabaseRegistryError(
                    f"Supabase registry request failed: {exc.code} {_sanitize(detail)}"
                ) from exc
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt < self.retries:
                    self._sleep(0.25 * (attempt + 1))
                    continue
                break
        raise SupabaseRegistryError(
            f"Supabase registry request failed: {_sanitize(str(last_error))}"
        ) from last_error


def canonical_rows_to_legacy_etb_rows(
    locations: list[CanonicalLocation],
) -> list[dict[str, Any]]:
    by_parent: dict[str, list[CanonicalLocation]] = {}
    etbs: list[CanonicalLocation] = []
    for location in locations:
        if location.location_type == "etb":
            etbs.append(location)
        elif location.parent_location_id:
            by_parent.setdefault(location.parent_location_id, []).append(location)
    rows = []
    for etb in sorted(etbs, key=lambda item: item.display_code or item.name):
        children = []
        stored_total = 0
        for child in sorted(
            by_parent.get(etb.id, []),
            key=lambda item: item.legacy_location_code or item.display_code,
        ):
            stored = int(child.stored_count or 0)
            stored_total += stored
            capacity = child.capacity or 40
            children.append(
                {
                    "location_code": child.legacy_location_code
                    or (child.display_code or "").split("-")[-1],
                    "location_id": child.display_code or child.legacy_id,
                    "qr_payload": "",
                    "capacity": capacity,
                    "stored_count": stored,
                    "remaining_capacity": max(0, int(capacity) - stored),
                    "status": canonical_status_to_legacy(child.status),
                    "assigned_batch": str(child.metadata.get("assigned_batch", "")),
                    "carduploader_batch_url": str(
                        child.metadata.get("carduploader_batch_url", "")
                    ),
                    "carduploader_batch_id": str(
                        child.metadata.get("carduploader_batch_id", "")
                    ),
                    "carduploader_batch_name": str(
                        child.metadata.get("carduploader_batch_name", "")
                    ),
                    "cloud_location_uuid": child.id,
                    "sync_state": child.sync_state,
                    "created_at": child.created_at,
                    "updated_at": child.updated_at,
                }
            )
        capacity = etb.capacity or 400
        rows.append(
            {
                "location_code": etb.display_code or etb.legacy_id or etb.name,
                "etb_id": etb.display_code or etb.legacy_id or etb.name,
                "status": canonical_status_to_legacy(etb.status),
                "total_capacity": capacity,
                "stored_count": stored_total,
                "remaining_space": max(0, int(capacity) - stored_total),
                "estimated_capacity": capacity,
                "estimated_assigned_count": stored_total,
                "estimated_remaining_capacity": max(0, int(capacity) - stored_total),
                "active_location": str(etb.metadata.get("active_location", "")),
                "current_active_location": str(
                    etb.metadata.get("current_active_location", "")
                    or etb.metadata.get("active_location", "")
                ),
                "locations": children,
                "cloud_location_uuid": etb.id,
                "sync_state": etb.sync_state,
                "created_at": etb.created_at,
                "updated_at": etb.updated_at,
            }
        )
    return rows


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return _int(value)


def _remove_empty_strings(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value != ""}


def _sanitize(value: str) -> str:
    text = str(value or "")
    for token in ("Bearer ", "service_role", "apikey"):
        text = text.replace(token, "[redacted] ")
    return text[:500]


__all__ = [
    "CANONICAL_CAPTURE_IMAGES_TABLE",
    "CANONICAL_CAPTURE_SESSIONS_TABLE",
    "CANONICAL_INVENTORY_RELATIONSHIPS_TABLE",
    "CANONICAL_LOCATIONS_TABLE",
    "CanonicalCaptureImage",
    "CanonicalCaptureSession",
    "CanonicalLocation",
    "SupabaseRegistryClient",
    "SupabaseRegistryError",
    "canonical_rows_to_legacy_etb_rows",
    "environment_config",
    "legacy_status_to_canonical",
]
