from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from Platform.cardvector.application import (
    ApplicationCancelled,
    ApplicationRuntime,
    BatchWorkflowApplication,
)
from Platform.cardvector.batch_workflow import (
    BatchWorkflow,
    BatchWorkflowPersistenceError,
    BatchWorkflowQuery,
    BatchWorkflowService,
    DuplicateBatchError,
    InvalidBatchIdError,
    InvalidStatusTransitionError,
    JsonBatchWorkflowRepository,
    OverallBatchStatus,
    WorkflowStepStatus,
)


ROOT = Path(__file__).resolve().parents[2]
PUTNAM_OS_SOURCE = (
    ROOT / "Platform" / "Putnam_OS" / "System" / "app" / "putnam_os.py"
).read_text(encoding="utf-8")


class FixedClock:
    def __init__(self) -> None:
        self.counter = 0

    def __call__(self) -> str:
        self.counter += 1
        return f"2026-07-19T12:00:{self.counter:02d}+00:00"


class BatchWorkflowModelTests(unittest.TestCase):
    def test_serialization_is_batch_level_only(self):
        batch = BatchWorkflow(
            batch_id="ETB-002-G",
            location_label="ETB-002-G",
            ebay_selected=True,
            other_marketplaces=("Whatnot",),
            notes=("Operator confirmed upload.",),
        )
        payload = batch.to_dict()

        forbidden = {
            "card_name",
            "set",
            "card_number",
            "card_quantity",
            "cards_captured",
            "row_count",
            "image_count",
            "quantity",
            "sku",
            "card_location",
            "condition",
            "card_images",
            "listing_id",
        }
        self.assertTrue(forbidden.isdisjoint(payload))
        self.assertEqual(BatchWorkflow.from_dict(payload), batch)

        payload["card_name"] = "Must not cross the boundary"
        self.assertNotIn("card_name", BatchWorkflow.from_dict(payload).to_dict())

    def test_overall_status_is_derived_from_step_statuses(self):
        self.assertEqual(
            BatchWorkflow(batch_id="BATCH-1").overall_status,
            OverallBatchStatus.NOT_STARTED,
        )
        self.assertEqual(
            BatchWorkflow(
                batch_id="BATCH-1",
                capture_status=WorkflowStepStatus.COMPLETE,
            ).overall_status,
            OverallBatchStatus.IN_PROGRESS,
        )
        self.assertEqual(
            BatchWorkflow(
                batch_id="BATCH-1",
                price_review_status=WorkflowStepStatus.FAILED,
            ).overall_status,
            OverallBatchStatus.FAILED,
        )


class BatchWorkflowServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "batches"
        self.clock = FixedClock()
        self.repository = JsonBatchWorkflowRepository(self.root)
        self.service = BatchWorkflowService(self.repository, clock=self.clock)

    def test_complete_batch_pipeline_preserves_confirmations_and_references(self):
        self.service.create_batch("ETB-002-G", location_label="ETB-002-G")
        self.service.mark_capture_complete("ETB-002-G")
        self.service.mark_carduploader_upload_started("ETB-002-G")
        self.service.mark_carduploader_upload_complete("ETB-002-G")
        self.service.set_marketplace_selection(
            "ETB-002-G",
            ebay_selected=True,
            tcgplayer_selected=True,
            other_marketplaces=("Whatnot", "Whatnot"),
        )
        self.service.mark_csv_exported(
            "ETB-002-G",
            csv_reference="fixtures/carduploader.csv",
        )
        self.service.start_price_review("ETB-002-G")
        result = self.service.complete_price_review(
            "ETB-002-G",
            output_reference="fixtures/pricing-output",
        )

        batch = result.batch
        self.assertEqual(batch.overall_status, OverallBatchStatus.COMPLETE)
        self.assertTrue(batch.ebay_selected)
        self.assertTrue(batch.tcgplayer_selected)
        self.assertEqual(batch.other_marketplaces, ("Whatnot",))
        self.assertEqual(batch.csv_export_reference, "fixtures/carduploader.csv")
        self.assertEqual(
            batch.price_review_output_reference,
            "fixtures/pricing-output",
        )
        self.assertTrue(batch.capture_completed_at)
        self.assertTrue(batch.price_review_completed_at)

    def test_no_marketplace_selected_is_an_explicit_batch_confirmation(self):
        self.service.create_batch("BATCH-EMPTY")
        result = self.service.set_marketplace_selection(
            "BATCH-EMPTY",
            ebay_selected=False,
            tcgplayer_selected=False,
        )
        self.assertEqual(
            result.batch.marketplace_selection_status,
            WorkflowStepStatus.COMPLETE,
        )
        self.assertFalse(result.batch.ebay_selected)
        self.assertFalse(result.batch.tcgplayer_selected)

    def test_failure_retry_and_invalid_transition(self):
        self.service.create_batch("BATCH-RETRY")
        self.service.start_price_review("BATCH-RETRY")
        failed = self.service.fail_price_review("BATCH-RETRY", "fixture failure")
        self.assertEqual(
            failed.batch.price_review_status,
            WorkflowStepStatus.FAILED,
        )
        self.assertEqual(failed.batch.error_status, "price_review_failed")

        retried = self.service.start_price_review("BATCH-RETRY")
        self.assertEqual(
            retried.batch.price_review_status,
            WorkflowStepStatus.IN_PROGRESS,
        )
        self.assertEqual(retried.batch.error_message, "")
        self.service.complete_price_review("BATCH-RETRY")
        with self.assertRaises(InvalidStatusTransitionError):
            self.service.fail_price_review("BATCH-RETRY", "too late")

    def test_duplicate_missing_and_unsafe_batch_ids_are_rejected(self):
        self.service.create_batch("ETB-001-A")
        with self.assertRaises(DuplicateBatchError):
            self.service.create_batch("ETB-001-A")
        with self.assertRaises(InvalidBatchIdError):
            self.service.create_batch("")
        with self.assertRaises(InvalidBatchIdError):
            self.service.create_batch("../outside")

    def test_notes_timestamps_filtering_and_idempotent_completion(self):
        self.service.create_batch("BATCH-1")
        first = self.service.mark_capture_complete("BATCH-1").batch
        second = self.service.mark_capture_complete("BATCH-1").batch
        self.assertEqual(first.capture_completed_at, second.capture_completed_at)
        noted = self.service.add_batch_note("BATCH-1", "Ready for upload").batch
        self.assertEqual(noted.notes, ("Ready for upload",))

        self.service.create_batch("BATCH-2")
        matches = self.service.list_batches(
            BatchWorkflowQuery(capture_status=WorkflowStepStatus.COMPLETE)
        )
        self.assertEqual([batch.batch_id for batch in matches], ["BATCH-1"])

    def test_json_repository_is_atomic_and_reports_persistence_failures(self):
        self.service.create_batch("BATCH-ATOMIC")
        record = self.root / "BATCH-ATOMIC.json"
        payload = json.loads(record.read_text(encoding="utf-8"))
        self.assertEqual(payload["batch_id"], "BATCH-ATOMIC")
        self.assertFalse((self.root / "BATCH-ATOMIC.json.tmp").exists())

        invalid_root = Path(self.temp.name) / "not-a-directory"
        invalid_root.write_text("occupied", encoding="utf-8")
        failing = BatchWorkflowService(
            JsonBatchWorkflowRepository(invalid_root),
            clock=self.clock,
        )
        with self.assertRaises(BatchWorkflowPersistenceError):
            failing.create_batch("BATCH-FAIL")


class BatchWorkflowApplicationTests(unittest.TestCase):
    def test_application_facade_publishes_batch_events(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = ApplicationRuntime()
            service = BatchWorkflowService(
                JsonBatchWorkflowRepository(Path(temp)),
                clock=FixedClock(),
            )
            application = BatchWorkflowApplication(service)
            events = []
            runtime.events.subscribe(
                "batch_workflow.capture_complete",
                events.append,
            )
            context = runtime.create_execution_context(execution_id="test")

            application.create_batch("ETB-005-B", context=context)
            result = application.mark_capture_complete(
                "ETB-005-B",
                context=context,
            )

            self.assertEqual(
                result.batch.capture_status,
                WorkflowStepStatus.COMPLETE,
            )
            self.assertEqual(events[0].payload["batch_id"], "ETB-005-B")

            context.cancellation.cancel("operator canceled")
            with self.assertRaises(ApplicationCancelled):
                application.mark_carduploader_upload_started(
                    "ETB-005-B",
                    context=context,
                )
            self.assertEqual(
                application.get_batch("ETB-005-B").carduploader_upload_status,
                WorkflowStepStatus.NOT_STARTED,
            )

    def test_putnam_os_delegates_existing_milestones(self):
        self.assertIn(
            'runtime.services.register(\n        "batch_workflow"',
            PUTNAM_OS_SOURCE,
        )
        for operation in (
            "mark_capture_complete",
            "mark_carduploader_upload_started",
            "mark_carduploader_upload_complete",
            "mark_csv_exported",
            "start_price_review",
            "complete_price_review",
            "fail_price_review",
        ):
            self.assertIn(f'"{operation}"', PUTNAM_OS_SOURCE)
        self.assertNotIn("card_name=", PUTNAM_OS_SOURCE)
        self.assertNotIn("card_sku=", PUTNAM_OS_SOURCE)


if __name__ == "__main__":
    unittest.main()
