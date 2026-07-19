from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable, Iterable

from .exceptions import BatchWorkflowNotFoundError, DuplicateBatchError
from .models import (
    BatchWorkflow,
    BatchWorkflowQuery,
    BatchWorkflowResult,
    WorkflowStepStatus,
)
from .repository import BatchWorkflowRepository, validate_batch_id
from .status import validate_transition


Clock = Callable[[], str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BatchWorkflowService:
    """Owns batch-level workflow transitions, never card-level inventory."""

    def __init__(
        self,
        repository: BatchWorkflowRepository,
        *,
        clock: Clock = utc_now,
    ) -> None:
        self._repository = repository
        self._clock = clock

    def create_batch(
        self,
        batch_id: str,
        *,
        location_label: str = "",
    ) -> BatchWorkflow:
        now = self._clock()
        batch = BatchWorkflow(
            batch_id=validate_batch_id(batch_id),
            location_label=str(location_label or "").strip(),
            created_at=now,
            updated_at=now,
        )
        return self._repository.create(batch)

    def ensure_batch(
        self,
        batch_id: str,
        *,
        location_label: str = "",
    ) -> BatchWorkflow:
        try:
            return self.get_batch(batch_id)
        except BatchWorkflowNotFoundError:
            try:
                return self.create_batch(batch_id, location_label=location_label)
            except DuplicateBatchError:
                return self.get_batch(batch_id)

    def get_batch(self, batch_id: str) -> BatchWorkflow:
        return self._repository.get(validate_batch_id(batch_id))

    def list_batches(
        self,
        query: BatchWorkflowQuery | None = None,
    ) -> list[BatchWorkflow]:
        batches = self._repository.list()
        if query is None:
            return batches
        return [
            batch
            for batch in batches
            if (
                query.overall_status is None
                or batch.overall_status == query.overall_status
            )
            and (
                query.capture_status is None
                or batch.capture_status == query.capture_status
            )
            and (
                query.price_review_status is None
                or batch.price_review_status == query.price_review_status
            )
            and (
                query.marketplace_selection_status is None
                or batch.marketplace_selection_status
                == query.marketplace_selection_status
            )
        ]

    def mark_capture_started(self, batch_id: str) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "capture",
            "capture_status",
            WorkflowStepStatus.IN_PROGRESS,
        )

    def mark_capture_complete(self, batch_id: str) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "capture",
            "capture_status",
            WorkflowStepStatus.COMPLETE,
            capture_completed_at=self._clock(),
        )

    def mark_carduploader_upload_started(self, batch_id: str) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "carduploader_upload",
            "carduploader_upload_status",
            WorkflowStepStatus.IN_PROGRESS,
        )

    def mark_carduploader_upload_complete(
        self,
        batch_id: str,
    ) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "carduploader_upload",
            "carduploader_upload_status",
            WorkflowStepStatus.COMPLETE,
            carduploader_upload_completed_at=self._clock(),
        )

    def set_marketplace_selection(
        self,
        batch_id: str,
        *,
        ebay_selected: bool,
        tcgplayer_selected: bool,
        other_marketplaces: Iterable[str] = (),
    ) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "marketplace_selection",
            "marketplace_selection_status",
            WorkflowStepStatus.COMPLETE,
            marketplace_selection_confirmed_at=self._clock(),
            ebay_selected=bool(ebay_selected),
            tcgplayer_selected=bool(tcgplayer_selected),
            other_marketplaces=tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in other_marketplaces
                    if str(item).strip()
                )
            ),
            allow_same_updates=True,
        )

    def mark_marketplace_selection_needs_review(
        self,
        batch_id: str,
    ) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "marketplace_selection",
            "marketplace_selection_status",
            WorkflowStepStatus.NEEDS_REVIEW,
        )

    def mark_csv_exported(
        self,
        batch_id: str,
        *,
        csv_reference: str = "",
    ) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "carduploader_csv_export",
            "carduploader_csv_export_status",
            WorkflowStepStatus.COMPLETE,
            carduploader_csv_exported_at=self._clock(),
            csv_export_reference=str(csv_reference or ""),
        )

    def start_price_review(self, batch_id: str) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "price_review",
            "price_review_status",
            WorkflowStepStatus.IN_PROGRESS,
            price_review_started_at=self._clock(),
        )

    def complete_price_review(
        self,
        batch_id: str,
        *,
        output_reference: str = "",
    ) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "price_review",
            "price_review_status",
            WorkflowStepStatus.COMPLETE,
            price_review_completed_at=self._clock(),
            price_review_output_reference=str(output_reference or ""),
        )

    def fail_price_review(
        self,
        batch_id: str,
        message: str,
    ) -> BatchWorkflowResult:
        return self._transition(
            batch_id,
            "price_review",
            "price_review_status",
            WorkflowStepStatus.FAILED,
            error_status="price_review_failed",
            error_message=str(message or "").strip(),
            allow_same_updates=True,
        )

    def add_batch_note(self, batch_id: str, note: str) -> BatchWorkflowResult:
        batch = self.get_batch(batch_id)
        value = str(note or "").strip()
        if not value:
            return BatchWorkflowResult(batch=batch)
        updated = replace(
            batch,
            notes=(*batch.notes, value),
            updated_at=self._clock(),
        )
        return BatchWorkflowResult(
            batch=self._repository.save(updated),
            changed_fields=("notes", "updated_at"),
        )

    def _transition(
        self,
        batch_id: str,
        step: str,
        field: str,
        target: WorkflowStepStatus,
        allow_same_updates: bool = False,
        **updates: object,
    ) -> BatchWorkflowResult:
        batch = self.get_batch(batch_id)
        current = getattr(batch, field)
        validate_transition(step, current, target)
        if current == target and not allow_same_updates:
            return BatchWorkflowResult(batch=batch)
        changed = {field: target, "updated_at": self._clock(), **updates}
        if target == WorkflowStepStatus.IN_PROGRESS:
            changed.update({"error_status": "", "error_message": ""})
        updated = replace(batch, **changed)
        return BatchWorkflowResult(
            batch=self._repository.save(updated),
            changed_fields=tuple(changed),
        )


__all__ = ["BatchWorkflowService", "utc_now"]
