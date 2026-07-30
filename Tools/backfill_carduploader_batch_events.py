from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


def _bootstrap_repo_import_path() -> None:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents]:
        if (candidate / ".putnam_root").exists() or (
            (candidate / "AGENTS.md").exists() and (candidate / "Docs").exists()
        ):
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return


_bootstrap_repo_import_path()

from Platform.putnam_paths import ROOT
from Platform.Putnam_OS.System.app.inventory_locations import (
    carduploader_batch_events_from_location,
    ensure_etb_location_records,
    load_etb_registry,
    normalize_etb_code,
    normalize_etb_record,
    normalize_location_code,
    save_etb_registry,
)
from Platform.cardvector.integrations.supabase.registry import (
    CanonicalCardUploaderBatchEvent,
    canonical_registry_uuid,
)


DEFAULT_SCRAPE = (
    ROOT / "Data" / "Imports" / "CardUploader" / "carduploader_batch_history_links_20260730.json"
)
DEFAULT_REGISTRY = (
    ROOT / "Platform" / "Putnam_OS" / "System" / "data" / "inventory" / "etb_location_registry.json"
)
DEFAULT_REPORT_DIR = ROOT / "Data" / "Imports" / "CardUploader" / "reports"
ETB_SLOT_RE = re.compile(r"\b(ETB-\d{2,3}-[A-J])\b", re.IGNORECASE)
ETB_RE = re.compile(r"\b(ETB-\d{2,3})\b", re.IGNORECASE)


@dataclass(frozen=True)
class CardUploaderBatchHistoryRow:
    sequence: int
    batch_id: str
    url: str
    label: str = ""
    etb_location: str = ""
    card_count: int | None = None
    total_value: float | None = None
    date: str = ""
    source_url: str = ""
    scraped_at: str = ""

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "CardUploaderBatchHistoryRow":
        return cls(
            sequence=_int(row.get("sequence")),
            batch_id=str(row.get("batch_id") or "").strip(),
            url=str(row.get("url") or "").strip(),
            label=_clean_text(row.get("label") or ""),
            etb_location=str(row.get("etb_location") or "").strip().upper(),
            card_count=_optional_int(row.get("card_count")),
            total_value=_optional_float(row.get("total_value")),
            date=str(row.get("date") or "").strip(),
            source_url=str(row.get("source_url") or "").strip(),
            scraped_at=str(row.get("scraped_at") or "").strip(),
        )

    @property
    def batch_type(self) -> str:
        parts = self.url.rstrip("/").split("/")
        if len(parts) >= 2 and parts[-2]:
            return parts[-2]
        return "ungraded"

    @property
    def batch_date_iso(self) -> str:
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(self.date, fmt).date().isoformat()
            except ValueError:
                continue
        return ""

    @property
    def game(self) -> str:
        label = self.label.lower()
        if "one piece" in label:
            return "One Piece"
        if "magic" in label or "mtg" in label:
            return "Magic: The Gathering"
        if "pokemon" in label:
            return "Pokemon"
        return ""

    @property
    def language(self) -> str:
        label = self.label.lower()
        if "japanese" in label:
            return "Japanese"
        if "english" in label:
            return "English"
        return ""


@dataclass
class BatchEventPlanItem:
    batch_id: str
    url: str
    label: str
    location_display_code: str = ""
    etb_display_code: str = ""
    classification: str = "unassigned_no_location"
    event_type: str = "unknown"
    reason: str = ""
    registry_location_exists: bool = False
    already_linked: bool = False
    card_count: int | None = None
    total_value: float | None = None
    batch_date: str = ""
    source_url: str = ""
    scraped_at: str = ""
    sequence: int = 0
    canonical_event_id: str = ""
    canonical_location_id: str = ""
    supabase_row: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_batch_history(path: Path) -> list[CardUploaderBatchHistoryRow]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [CardUploaderBatchHistoryRow.from_mapping(row) for row in csv.DictReader(handle)]
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return [CardUploaderBatchHistoryRow.from_mapping(row) for row in data]


def registry_slot_codes(registry: Mapping[str, Any]) -> set[str]:
    codes: set[str] = set()
    for etb in registry.get("locations", []) or []:
        try:
            normalized = normalize_etb_record(dict(etb), dict(registry))
        except (TypeError, ValueError):
            continue
        for slot in normalized.get("locations", []) or []:
            try:
                codes.add(f"{normalized['location_code']}-{normalize_location_code(slot.get('location_code', ''))}")
            except ValueError:
                continue
    return codes


def existing_batch_ids_by_location(registry: Mapping[str, Any]) -> dict[str, set[str]]:
    by_location: dict[str, set[str]] = {}
    for etb in registry.get("locations", []) or []:
        try:
            normalized = normalize_etb_record(dict(etb), dict(registry))
        except (TypeError, ValueError):
            continue
        for slot in normalized.get("locations", []) or []:
            location_id = str(slot.get("location_id") or "").upper()
            for event in carduploader_batch_events_from_location(slot):
                batch_id = str(event.get("carduploader_batch_id") or "").strip()
                if batch_id:
                    by_location.setdefault(location_id, set()).add(batch_id)
    return by_location


def infer_location(row: CardUploaderBatchHistoryRow) -> tuple[str, str]:
    explicit = str(row.etb_location or "").strip().upper()
    if explicit:
        try:
            etb, location = explicit.rsplit("-", 1)
            return f"{normalize_etb_code(etb)}-{normalize_location_code(location)}", ""
        except ValueError:
            pass
    match = ETB_SLOT_RE.search(row.label)
    if match:
        value = match.group(1).upper()
        etb, location = value.rsplit("-", 1)
        return f"{normalize_etb_code(etb)}-{normalize_location_code(location)}", ""
    broad = ETB_RE.search(row.label)
    if broad:
        return "", normalize_etb_code(broad.group(1))
    return "", ""


def build_plan(rows: Iterable[CardUploaderBatchHistoryRow], registry: Mapping[str, Any]) -> dict[str, Any]:
    slots = registry_slot_codes(registry)
    linked = existing_batch_ids_by_location(registry)
    rows_sorted = sorted(
        rows,
        key=lambda item: (
            item.batch_date_iso or "9999-12-31",
            item.sequence,
            item.batch_id,
        ),
    )
    seen_by_location: dict[str, int] = {}
    items: list[BatchEventPlanItem] = []
    for row in rows_sorted:
        location_id, broad_etb = infer_location(row)
        if location_id:
            location_exists = location_id in slots
            already_linked = row.batch_id in linked.get(location_id, set())
            if not location_exists:
                classification = "missing_registry_location"
                event_type = "unknown"
                reason = "The CardUploader label has an ETB slot, but that slot is not present in the local registry."
            else:
                prior_count = seen_by_location.get(location_id, 0)
                event_type = "refill" if prior_count or already_linked else "initial_fill"
                classification = "already_linked" if already_linked else "location_event"
                reason = (
                    "Already represented in the local registry."
                    if already_linked
                    else "Explicit CardUploader ETB slot can be recorded as a historical batch event."
                )
                seen_by_location[location_id] = prior_count + 1
            etb_display_code = location_id.rsplit("-", 1)[0]
        elif broad_etb:
            location_exists = False
            already_linked = False
            classification = "needs_physical_conversion"
            event_type = "unassigned"
            etb_display_code = broad_etb
            reason = (
                "The CardUploader label names an ETB but not an A-J slot; it needs physical conversion review."
            )
        else:
            location_exists = False
            already_linked = False
            classification = "unassigned_no_location"
            event_type = "unassigned"
            etb_display_code = ""
            reason = "No ETB location could be inferred safely from the CardUploader label."

        canonical_event = CanonicalCardUploaderBatchEvent(
            id=canonical_registry_uuid("carduploader_batch_event", row.batch_id),
            carduploader_batch_id=row.batch_id,
            carduploader_batch_url=row.url,
            location_id=canonical_registry_uuid("location", location_id) if location_id else "",
            location_display_code=location_id,
            etb_display_code=etb_display_code,
            carduploader_batch_name=(f"{location_id} CardUploader Batch" if location_id else ""),
            batch_label=row.label,
            batch_type=row.batch_type,
            game=row.game,
            language=row.language,
            event_type=event_type,
            card_count=row.card_count,
            total_value=row.total_value,
            batch_date=row.batch_date_iso,
            source="carduploader_history_scrape",
            scraped_at=row.scraped_at,
            metadata={
                "source_url": row.source_url,
                "sequence": row.sequence,
                "classification": classification,
                "note": "CardUploader batch events are provenance, not inventory counts.",
            },
        )
        items.append(
            BatchEventPlanItem(
                batch_id=row.batch_id,
                url=row.url,
                label=row.label,
                location_display_code=location_id,
                etb_display_code=etb_display_code,
                classification=classification,
                event_type=event_type,
                reason=reason,
                registry_location_exists=location_exists,
                already_linked=already_linked,
                card_count=row.card_count,
                total_value=row.total_value,
                batch_date=row.batch_date_iso,
                source_url=row.source_url,
                scraped_at=row.scraped_at,
                sequence=row.sequence,
                canonical_event_id=canonical_event.id,
                canonical_location_id=canonical_event.location_id,
                supabase_row=canonical_event.to_row(),
            )
        )
    counts: dict[str, int] = {}
    for item in items:
        counts[item.classification] = counts.get(item.classification, 0) + 1
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "registry_path": str(DEFAULT_REGISTRY),
        "batch_count": len(items),
        "counts": counts,
        "items": [item.to_dict() for item in items],
        "supabase_rows": [
            item.supabase_row
            for item in items
            if item.classification in {"location_event", "already_linked"}
        ],
        "notes": [
            "CardUploader batch events preserve historical batch webpage links.",
            "CardUploader card_count is not used to update stored_count.",
            "Broad ETB labels without A-J location remain review-only.",
        ],
    }


def apply_to_local_registry(plan: Mapping[str, Any], registry_path: Path) -> dict[str, Any]:
    registry = load_etb_registry(registry_path)
    now = datetime.now().isoformat(timespec="seconds")
    backup_path = registry_path.with_name(
        f"{registry_path.stem}.before_carduploader_batch_backfill_{datetime.now().strftime('%Y%m%d_%H%M%S')}{registry_path.suffix}"
    )
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(registry_path, backup_path)

    updates = 0
    skipped = 0
    items_by_location: dict[str, list[dict[str, Any]]] = {}
    for item in plan.get("items", []) or []:
        if item.get("classification") not in {"location_event", "already_linked"}:
            skipped += 1
            continue
        location_id = str(item.get("location_display_code") or "").upper()
        items_by_location.setdefault(location_id, []).append(dict(item))

    for etb in registry.get("locations", []) or []:
        normalized = normalize_etb_record(etb, registry)
        children = ensure_etb_location_records(etb, registry)
        for child in children:
            location_id = str(child.get("location_id") or "").upper()
            additions = items_by_location.get(location_id, [])
            if not additions:
                continue
            existing_events = carduploader_batch_events_from_location(child)
            existing_ids = {
                str(event.get("carduploader_batch_id") or "").strip()
                for event in existing_events
            }
            for addition in additions:
                if addition["batch_id"] in existing_ids:
                    continue
                event = {
                    "carduploader_batch_id": addition["batch_id"],
                    "carduploader_batch_url": addition["url"],
                    "carduploader_batch_name": f"{location_id} CardUploader Batch",
                    "batch_label": addition["label"],
                    "batch_type": addition["supabase_row"].get("batch_type") or "ungraded",
                    "event_type": addition["event_type"],
                    "game": addition["supabase_row"].get("game") or "",
                    "language": addition["supabase_row"].get("language") or "",
                    "card_count": addition.get("card_count"),
                    "total_value": addition.get("total_value"),
                    "batch_date": addition.get("batch_date") or "",
                    "source": "carduploader_history_scrape",
                    "scraped_at": addition.get("scraped_at") or "",
                }
                existing_events.append(event)
                existing_ids.add(addition["batch_id"])
                updates += 1
            existing_events = sorted(
                existing_events,
                key=lambda event: (
                    str(event.get("batch_date") or ""),
                    str(event.get("scraped_at") or ""),
                    str(event.get("carduploader_batch_id") or ""),
                ),
            )
            latest = existing_events[-1]
            child["carduploader_batch_events"] = existing_events
            child["carduploader_batch_count"] = len(existing_events)
            child["carduploader_batch_history_updated_at"] = now
            child["carduploader_batch_id"] = latest.get("carduploader_batch_id") or ""
            child["carduploader_batch_url"] = latest.get("carduploader_batch_url") or ""
            child["carduploader_batch_name"] = latest.get("carduploader_batch_name") or ""
            child["updated_at"] = now
        etb["locations"] = children
    registry.setdefault("history", []).append(
        {
            "timestamp": now,
            "action": "carduploader_batch_event_backfill",
            "events_added": updates,
            "items_skipped": skipped,
            "backup_path": str(backup_path),
            "note": "CardUploader batch events are provenance only; stored_count was not updated.",
        }
    )
    save_etb_registry(registry, registry_path)
    return {"backup_path": str(backup_path), "events_added": updates, "items_skipped": skipped}


def write_reports(plan: Mapping[str, Any], report_dir: Path) -> dict[str, str]:
    report_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": report_dir / "carduploader_batch_event_plan.json",
        "csv": report_dir / "carduploader_batch_event_plan.csv",
        "supabase_json": report_dir / "carduploader_batch_events_for_supabase.json",
        "markdown": report_dir / "carduploader_batch_event_plan.md",
    }
    paths["json"].write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    paths["supabase_json"].write_text(json.dumps(plan.get("supabase_rows", []), indent=2) + "\n", encoding="utf-8")
    with paths["csv"].open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "batch_id",
            "location_display_code",
            "etb_display_code",
            "classification",
            "event_type",
            "card_count",
            "total_value",
            "batch_date",
            "url",
            "reason",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in plan.get("items", []) or []:
            writer.writerow({field: item.get(field, "") for field in fieldnames})
    markdown = [
        "# CardUploader Batch Event Backfill Plan",
        "",
        f"Generated: {plan.get('generated_at', '')}",
        "",
        "## Counts",
        "",
    ]
    for key, value in sorted((plan.get("counts") or {}).items()):
        markdown.append(f"- {key}: {value}")
    markdown.extend(
        [
            "",
            "## Notes",
            "",
            "- CardUploader batch links are historical provenance events.",
            "- CardUploader card counts do not update ETB stored counts.",
            "- Broad ETB-only labels remain review-only until physical conversion is complete.",
        ]
    )
    paths["markdown"].write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return {key: str(value) for key, value in paths.items()}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan CardUploader batch-event backfill.")
    parser.add_argument("--scrape", type=Path, default=DEFAULT_SCRAPE)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--apply-local", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = read_batch_history(args.scrape)
    registry = load_etb_registry(args.registry)
    plan = build_plan(rows, registry)
    report_dir = args.report_dir or (
        DEFAULT_REPORT_DIR / f"carduploader_batch_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    report_paths = write_reports(plan, report_dir)
    result = {
        "mode": "apply-local" if args.apply_local and not args.dry_run else "dry-run",
        "reports": report_paths,
        "counts": plan.get("counts", {}),
        "batch_count": plan.get("batch_count", 0),
    }
    if args.apply_local and not args.dry_run:
        result["local_apply"] = apply_to_local_registry(plan, args.registry)
    print(json.dumps(result, indent=2))
    return 0


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    return text.replace("â€”", "-").replace("\u2014", "-")


def _int(value: Any) -> int:
    try:
        return int(float(str(value or "0").replace(",", "")))
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return _int(value)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
