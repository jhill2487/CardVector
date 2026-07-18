from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


PathResolver = Callable[[Any, Path | None], Path | None]
RecordResolver = Callable[[dict[str, Any], Path], tuple[Path | None, str, bool]]
FallbackLogger = Callable[[Path, list[str]], None]


def load_capture_session_file(folder: Path | str) -> dict[str, Any]:
    session_path = Path(folder) / "capture_session.json"
    if not session_path.exists():
        return {}
    try:
        data = json.loads(session_path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _default_path_resolver(value: Any, session_folder: Path | None = None) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    if session_folder is not None:
        return Path(session_folder) / path
    return path


def resolve_capture_record_image(
    record: dict[str, Any],
    session_folder: Path,
    *,
    path_resolver: PathResolver | None = None,
) -> tuple[Path | None, str, bool]:
    resolver = path_resolver or _default_path_resolver
    metadata_value = record.get("path") or ""
    filename = str(record.get("filename", "") or "").strip()
    metadata_path = resolver(metadata_value, session_folder)
    try:
        if metadata_path and metadata_path.exists():
            return metadata_path, "", False
    except OSError:
        pass
    if filename:
        filename_path = resolver(filename, session_folder)
        try:
            if filename_path and filename_path.exists():
                diagnostic = metadata_value if metadata_value else ""
                return filename_path, str(diagnostic), False
        except OSError:
            pass
    unresolved = metadata_value or filename
    return None, str(unresolved), True


def capture_pair_rows(
    folder: Path | str | None,
    limit: int = 24,
    *,
    session_loader: Callable[[Path], dict[str, Any]] = load_capture_session_file,
    record_resolver: RecordResolver | None = None,
    fallback_logger: FallbackLogger | None = None,
) -> list[dict[str, Any]]:
    session_folder = Path(folder) if folder else None
    if not session_folder or not session_folder.exists():
        return []
    pairs: dict[int, dict[str, Any]] = {}
    session_data = session_loader(session_folder)
    capture_layout = str(session_data.get("capture_layout") or "").strip().upper()
    if capture_layout not in {"FRONT_ONLY", "FRONT_BACK"}:
        is_legacy_mobile_front_only = (
            str(session_data.get("source") or "").upper() == "MOBILE_WEB"
            and "front_only" in str(session_data.get("capture_workflow") or "").lower()
        )
        capture_layout = "FRONT_ONLY" if is_legacy_mobile_front_only else "FRONT_BACK"
    session_records = session_data.get("records", [])
    if not isinstance(session_records, list):
        session_records = []
    fallback_paths: list[str] = []
    unresolved_paths: list[str] = []
    resolver = record_resolver or (
        lambda record, current_folder: resolve_capture_record_image(
            record,
            current_folder,
        )
    )
    for record in session_records:
        if not isinstance(record, dict):
            continue
        side = str(record.get("side", "")).lower()
        if side not in {"front", "back"}:
            continue
        try:
            number = int(record.get("card_number") or 0)
        except Exception:
            number = 0
        if number <= 0:
            match = re.match(
                r"^(\d{6})_(front|back)\.jpe?g$",
                str(record.get("filename", "")),
                re.IGNORECASE,
            )
            number = int(match.group(1)) if match else 0
        image, fallback, unresolved = resolver(record, session_folder)
        if fallback:
            fallback_paths.append(fallback)
        if unresolved:
            unresolved_paths.append(
                fallback
                or record.get("filename")
                or record.get("path")
                or "<blank>"
            )
        if number > 0 and image:
            item = pairs.setdefault(
                number,
                {
                    "pair_number": number,
                    "front": None,
                    "back": None,
                    "timestamp": "",
                },
            )
            item[side] = image
    needs_scan = not session_records or bool(unresolved_paths)
    if needs_scan:
        images: list[Path] = []
        for pattern in ("*.jpg", "*.jpeg"):
            images.extend(
                [path for path in session_folder.glob(pattern) if path.is_file()]
            )
        for image in images:
            match = re.match(
                r"^(\d{6})_(front|back)\.jpe?g$",
                image.name,
                re.IGNORECASE,
            )
            if not match:
                continue
            number = int(match.group(1))
            side = match.group(2).lower()
            item = pairs.setdefault(
                number,
                {
                    "pair_number": number,
                    "front": None,
                    "back": None,
                    "timestamp": "",
                },
            )
            current = item.get(side)
            try:
                current_exists = bool(current and current.exists())
            except OSError:
                current_exists = False
            if not current_exists:
                item[side] = image
    if fallback_logger is not None:
        fallback_logger(session_folder, fallback_paths)

    rows: list[dict[str, Any]] = []
    for number, item in pairs.items():
        paths = [
            path for path in [item.get("front"), item.get("back")] if path
        ]
        if not paths:
            continue
        mtimes = []
        for path in paths:
            try:
                mtimes.append(path.stat().st_mtime if path.exists() else 0)
            except OSError:
                mtimes.append(0)
        latest_mtime = max(mtimes) if mtimes else 0
        status = (
            "Complete"
            if item.get("front")
            and (capture_layout == "FRONT_ONLY" or item.get("back"))
            else "Waiting for Back"
            if item.get("front")
            else "Needs Front"
        )
        rows.append(
            {
                "pair_number": number,
                "front": item.get("front"),
                "back": item.get("back"),
                "session_folder": session_folder,
                "timestamp": datetime.fromtimestamp(latest_mtime).strftime("%H:%M:%S"),
                "latest_mtime": latest_mtime,
                "status": status,
                "capture_layout": capture_layout,
            }
        )
    sorted_rows = sorted(
        rows,
        key=lambda row: row["latest_mtime"],
        reverse=True,
    )[:limit]
    for index, row in enumerate(sorted_rows):
        row["latest"] = index == 0
    return sorted_rows


def capture_pair_status(session: dict[str, Any] | None) -> str:
    if not session:
        return "Ready"
    records = session.get("records") or []
    if not records:
        return "Ready"
    try:
        current_number = int(session.get("current_card_number") or 1)
    except Exception:
        current_number = 1
    current_sides = set()
    for record in records:
        try:
            record_number = int(record.get("card_number") or 0)
        except Exception:
            record_number = 0
        if record_number == current_number:
            current_sides.add(str(record.get("side", "")).lower())
    if "front" in current_sides and "back" not in current_sides:
        return "Waiting for Back"
    if "back" in current_sides:
        return "Ready for Next Card"
    return "Ready"


def capture_cards_completed(
    session: dict[str, Any] | None,
    *,
    path_resolver: Callable[[Any], Path | None] | None = None,
    rows_loader: Callable[[Path, int], list[dict[str, Any]]] | None = None,
) -> int:
    if not session:
        return 0
    raw_folder = session.get("folder", "")
    folder = (
        path_resolver(raw_folder)
        if path_resolver is not None
        else Path(raw_folder)
    )
    if folder is None:
        folder = Path(raw_folder)
    load_rows = rows_loader or (
        lambda current_folder, limit: capture_pair_rows(current_folder, limit)
    )
    return sum(
        1
        for row in load_rows(folder, 9999)
        if row["status"] == "Complete"
    )


__all__ = [
    "capture_cards_completed",
    "capture_pair_rows",
    "capture_pair_status",
    "load_capture_session_file",
    "resolve_capture_record_image",
]
