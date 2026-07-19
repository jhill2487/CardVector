from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class WorkflowStepStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_REQUIRED = "not_required"
    NEEDS_REVIEW = "needs_review"


class OverallBatchStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class BatchWorkflow:
    """Batch-level operational state without CardUploader-owned card data."""

    batch_id: str
    location_label: str = ""
    capture_status: WorkflowStepStatus = WorkflowStepStatus.NOT_STARTED
    capture_completed_at: str = ""
    carduploader_upload_status: WorkflowStepStatus = WorkflowStepStatus.NOT_STARTED
    carduploader_upload_completed_at: str = ""
    marketplace_selection_status: WorkflowStepStatus = WorkflowStepStatus.NOT_STARTED
    marketplace_selection_confirmed_at: str = ""
    ebay_selected: bool = False
    tcgplayer_selected: bool = False
    other_marketplaces: tuple[str, ...] = ()
    carduploader_csv_export_status: WorkflowStepStatus = WorkflowStepStatus.NOT_STARTED
    carduploader_csv_exported_at: str = ""
    csv_export_reference: str = ""
    price_review_status: WorkflowStepStatus = WorkflowStepStatus.NOT_STARTED
    price_review_started_at: str = ""
    price_review_completed_at: str = ""
    price_review_output_reference: str = ""
    notes: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""
    error_status: str = ""
    error_message: str = ""

    @property
    def overall_status(self) -> OverallBatchStatus:
        statuses = (
            self.capture_status,
            self.carduploader_upload_status,
            self.marketplace_selection_status,
            self.carduploader_csv_export_status,
            self.price_review_status,
        )
        if WorkflowStepStatus.FAILED in statuses:
            return OverallBatchStatus.FAILED
        if WorkflowStepStatus.BLOCKED in statuses:
            return OverallBatchStatus.BLOCKED
        if WorkflowStepStatus.NEEDS_REVIEW in statuses:
            return OverallBatchStatus.NEEDS_REVIEW
        terminal = {WorkflowStepStatus.COMPLETE, WorkflowStepStatus.NOT_REQUIRED}
        if all(status in terminal for status in statuses):
            return OverallBatchStatus.COMPLETE
        if any(status != WorkflowStepStatus.NOT_STARTED for status in statuses):
            return OverallBatchStatus.IN_PROGRESS
        return OverallBatchStatus.NOT_STARTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "batch_id": self.batch_id,
            "location_label": self.location_label,
            "capture_status": self.capture_status.value,
            "capture_completed_at": self.capture_completed_at,
            "carduploader_upload_status": self.carduploader_upload_status.value,
            "carduploader_upload_completed_at": self.carduploader_upload_completed_at,
            "marketplace_selection_status": self.marketplace_selection_status.value,
            "marketplace_selection_confirmed_at": self.marketplace_selection_confirmed_at,
            "ebay_selected": self.ebay_selected,
            "tcgplayer_selected": self.tcgplayer_selected,
            "other_marketplaces": list(self.other_marketplaces),
            "carduploader_csv_export_status": self.carduploader_csv_export_status.value,
            "carduploader_csv_exported_at": self.carduploader_csv_exported_at,
            "csv_export_reference": self.csv_export_reference,
            "price_review_status": self.price_review_status.value,
            "price_review_started_at": self.price_review_started_at,
            "price_review_completed_at": self.price_review_completed_at,
            "price_review_output_reference": self.price_review_output_reference,
            "notes": list(self.notes),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_status": self.error_status,
            "error_message": self.error_message,
            "overall_status": self.overall_status.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BatchWorkflow":
        return cls(
            batch_id=str(value.get("batch_id") or "").strip(),
            location_label=str(value.get("location_label") or "").strip(),
            capture_status=WorkflowStepStatus(
                value.get("capture_status") or WorkflowStepStatus.NOT_STARTED.value
            ),
            capture_completed_at=str(value.get("capture_completed_at") or ""),
            carduploader_upload_status=WorkflowStepStatus(
                value.get("carduploader_upload_status")
                or WorkflowStepStatus.NOT_STARTED.value
            ),
            carduploader_upload_completed_at=str(
                value.get("carduploader_upload_completed_at") or ""
            ),
            marketplace_selection_status=WorkflowStepStatus(
                value.get("marketplace_selection_status")
                or WorkflowStepStatus.NOT_STARTED.value
            ),
            marketplace_selection_confirmed_at=str(
                value.get("marketplace_selection_confirmed_at") or ""
            ),
            ebay_selected=bool(value.get("ebay_selected", False)),
            tcgplayer_selected=bool(value.get("tcgplayer_selected", False)),
            other_marketplaces=tuple(
                str(item).strip()
                for item in value.get("other_marketplaces") or ()
                if str(item).strip()
            ),
            carduploader_csv_export_status=WorkflowStepStatus(
                value.get("carduploader_csv_export_status")
                or WorkflowStepStatus.NOT_STARTED.value
            ),
            carduploader_csv_exported_at=str(
                value.get("carduploader_csv_exported_at") or ""
            ),
            csv_export_reference=str(value.get("csv_export_reference") or ""),
            price_review_status=WorkflowStepStatus(
                value.get("price_review_status")
                or WorkflowStepStatus.NOT_STARTED.value
            ),
            price_review_started_at=str(value.get("price_review_started_at") or ""),
            price_review_completed_at=str(
                value.get("price_review_completed_at") or ""
            ),
            price_review_output_reference=str(
                value.get("price_review_output_reference") or ""
            ),
            notes=tuple(
                str(item).strip()
                for item in value.get("notes") or ()
                if str(item).strip()
            ),
            created_at=str(value.get("created_at") or ""),
            updated_at=str(value.get("updated_at") or ""),
            error_status=str(value.get("error_status") or ""),
            error_message=str(value.get("error_message") or ""),
        )


@dataclass(frozen=True)
class BatchWorkflowQuery:
    overall_status: OverallBatchStatus | None = None
    capture_status: WorkflowStepStatus | None = None
    price_review_status: WorkflowStepStatus | None = None
    marketplace_selection_status: WorkflowStepStatus | None = None


@dataclass(frozen=True)
class BatchWorkflowResult:
    batch: BatchWorkflow
    changed_fields: tuple[str, ...] = field(default_factory=tuple)


__all__ = [
    "BatchWorkflow",
    "BatchWorkflowQuery",
    "BatchWorkflowResult",
    "OverallBatchStatus",
    "WorkflowStepStatus",
]
