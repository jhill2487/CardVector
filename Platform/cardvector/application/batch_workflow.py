from __future__ import annotations

from typing import Any, Iterable, Protocol

from Platform.cardvector.batch_workflow import BatchWorkflowQuery

from .runtime import ExecutionContext


class BatchWorkflowOperations(Protocol):
    def create_batch(self, batch_id: str, *, location_label: str = "") -> Any: ...

    def ensure_batch(self, batch_id: str, *, location_label: str = "") -> Any: ...

    def get_batch(self, batch_id: str) -> Any: ...

    def list_batches(self, query: BatchWorkflowQuery | None = None) -> list[Any]: ...

    def mark_capture_started(self, batch_id: str) -> Any: ...

    def mark_capture_complete(self, batch_id: str) -> Any: ...

    def mark_carduploader_upload_started(self, batch_id: str) -> Any: ...

    def mark_carduploader_upload_complete(self, batch_id: str) -> Any: ...

    def set_marketplace_selection(
        self,
        batch_id: str,
        *,
        ebay_selected: bool,
        tcgplayer_selected: bool,
        other_marketplaces: Iterable[str] = (),
    ) -> Any: ...

    def mark_csv_exported(
        self,
        batch_id: str,
        *,
        csv_reference: str = "",
    ) -> Any: ...

    def start_price_review(self, batch_id: str) -> Any: ...

    def complete_price_review(
        self,
        batch_id: str,
        *,
        output_reference: str = "",
    ) -> Any: ...

    def fail_price_review(self, batch_id: str, message: str) -> Any: ...

    def add_batch_note(self, batch_id: str, note: str) -> Any: ...


class BatchWorkflowApplication:
    """Coordinates batch milestones without observing CardUploader card data."""

    def __init__(self, service: BatchWorkflowOperations) -> None:
        self._service = service

    def create_batch(
        self,
        batch_id: str,
        *,
        location_label: str = "",
        context: ExecutionContext | None = None,
    ) -> Any:
        self._check_cancellation(context)
        result = self._service.create_batch(
            batch_id,
            location_label=location_label,
        )
        self._publish(context, "batch_workflow.created", result)
        return result

    def ensure_batch(self, batch_id: str, *, location_label: str = "") -> Any:
        return self._service.ensure_batch(batch_id, location_label=location_label)

    def get_batch(self, batch_id: str) -> Any:
        return self._service.get_batch(batch_id)

    def list_batches(self, query: BatchWorkflowQuery | None = None) -> list[Any]:
        return self._service.list_batches(query)

    def mark_capture_started(self, batch_id: str, context: ExecutionContext | None = None) -> Any:
        return self._change(
            "batch_workflow.capture_started",
            self._service.mark_capture_started,
            batch_id,
            context=context,
        )

    def mark_capture_complete(self, batch_id: str, context: ExecutionContext | None = None) -> Any:
        return self._change(
            "batch_workflow.capture_complete",
            self._service.mark_capture_complete,
            batch_id,
            context=context,
        )

    def mark_carduploader_upload_started(
        self,
        batch_id: str,
        context: ExecutionContext | None = None,
    ) -> Any:
        return self._change(
            "batch_workflow.carduploader_upload_started",
            self._service.mark_carduploader_upload_started,
            batch_id,
            context=context,
        )

    def mark_carduploader_upload_complete(
        self,
        batch_id: str,
        context: ExecutionContext | None = None,
    ) -> Any:
        return self._change(
            "batch_workflow.carduploader_upload_complete",
            self._service.mark_carduploader_upload_complete,
            batch_id,
            context=context,
        )

    def set_marketplace_selection(
        self,
        batch_id: str,
        *,
        ebay_selected: bool,
        tcgplayer_selected: bool,
        other_marketplaces: Iterable[str] = (),
        context: ExecutionContext | None = None,
    ) -> Any:
        self._check_cancellation(context)
        result = self._service.set_marketplace_selection(
            batch_id,
            ebay_selected=ebay_selected,
            tcgplayer_selected=tcgplayer_selected,
            other_marketplaces=other_marketplaces,
        )
        self._publish(context, "batch_workflow.marketplaces_confirmed", result)
        return result

    def mark_csv_exported(
        self,
        batch_id: str,
        *,
        csv_reference: str = "",
        context: ExecutionContext | None = None,
    ) -> Any:
        self._check_cancellation(context)
        result = self._service.mark_csv_exported(
            batch_id,
            csv_reference=csv_reference,
        )
        self._publish(context, "batch_workflow.csv_received", result)
        return result

    def start_price_review(
        self,
        batch_id: str,
        context: ExecutionContext | None = None,
    ) -> Any:
        return self._change(
            "batch_workflow.price_review_started",
            self._service.start_price_review,
            batch_id,
            context=context,
        )

    def complete_price_review(
        self,
        batch_id: str,
        *,
        output_reference: str = "",
        context: ExecutionContext | None = None,
    ) -> Any:
        self._check_cancellation(context)
        result = self._service.complete_price_review(
            batch_id,
            output_reference=output_reference,
        )
        self._publish(context, "batch_workflow.price_review_complete", result)
        return result

    def fail_price_review(
        self,
        batch_id: str,
        message: str,
        context: ExecutionContext | None = None,
    ) -> Any:
        self._check_cancellation(context)
        result = self._service.fail_price_review(batch_id, message)
        self._publish(context, "batch_workflow.price_review_failed", result)
        return result

    def add_batch_note(self, batch_id: str, note: str) -> Any:
        return self._service.add_batch_note(batch_id, note)

    def _change(
        self,
        event_name: str,
        operation: Any,
        batch_id: str,
        *,
        context: ExecutionContext | None,
    ) -> Any:
        self._check_cancellation(context)
        result = operation(batch_id)
        self._publish(context, event_name, result)
        return result

    @staticmethod
    def _publish(
        context: ExecutionContext | None,
        event_name: str,
        result: Any,
    ) -> None:
        if context is None:
            return
        batch = getattr(result, "batch", result)
        context.publish(
            event_name,
            batch_id=str(getattr(batch, "batch_id", "")),
            overall_status=str(
                getattr(getattr(batch, "overall_status", ""), "value", "")
            ),
        )

    @staticmethod
    def _check_cancellation(context: ExecutionContext | None) -> None:
        if context is not None:
            context.cancellation.raise_if_cancelled()


__all__ = ["BatchWorkflowApplication", "BatchWorkflowOperations"]
