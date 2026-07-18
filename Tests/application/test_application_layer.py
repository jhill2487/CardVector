from __future__ import annotations

import ast
import json
from pathlib import Path
import tempfile
import unittest

from Platform.cardvector.application import (
    ApplicationCancelled,
    ApplicationRuntime,
    Command,
    WorkflowApplication,
    WorkflowDelegates,
)
from Platform.Putnam_OS.System.app import workflow_context as legacy_workflow_context


ROOT = Path(__file__).resolve().parents[2]
APPLICATION_ROOT = ROOT / "Platform" / "cardvector" / "application"
PUTNAM_OS_SOURCE = (
    ROOT / "Platform" / "Putnam_OS" / "System" / "app" / "putnam_os.py"
).read_text(encoding="utf-8")


def legacy_delegates() -> WorkflowDelegates:
    return WorkflowDelegates(
        discover_workflow_jobs=legacy_workflow_context.discover_workflow_jobs,
        jobs_from_queue_rows=legacy_workflow_context.jobs_from_queue_rows,
        merge_job_lists=legacy_workflow_context.merge_job_lists,
        recent_completed_jobs=legacy_workflow_context.recent_completed_jobs,
        group_processing_jobs=legacy_workflow_context.group_processing_jobs,
        active_listings_summary=legacy_workflow_context.active_listings_summary,
        business_alerts=legacy_workflow_context.business_alerts,
        update_workflow_context=legacy_workflow_context.update_workflow_context,
    )


class ApplicationRuntimeTests(unittest.TestCase):
    def test_service_registration_command_dispatch_progress_events_and_cancellation(self):
        runtime = ApplicationRuntime()
        service = object()
        runtime.services.register("sample", service)
        self.assertIs(runtime.services.resolve("sample"), service)
        self.assertTrue(runtime.services.contains("sample"))

        progress = []
        events = []
        runtime.progress.subscribe(progress.append)
        runtime.events.subscribe("job.complete", events.append)

        def handler(command, context):
            context.report("Running", current=1, total=1)
            context.publish("job.complete", job_id=command.payload["job_id"])
            return command.payload["job_id"]

        runtime.commands.register("run.job", handler)
        context = runtime.create_execution_context(
            execution_id="session-1",
            metadata={"operator": "test"},
        )
        result = runtime.commands.dispatch(
            Command("run.job", {"job_id": "job-1"}),
            context,
        )

        self.assertEqual(result, "job-1")
        self.assertEqual(context.execution_id, "session-1")
        self.assertEqual(context.metadata["operator"], "test")
        self.assertEqual(progress[0].execution_id, "session-1")
        self.assertEqual(events[0].payload["job_id"], "job-1")

        context.cancellation.cancel("operator canceled")
        with self.assertRaisesRegex(ApplicationCancelled, "operator canceled"):
            runtime.commands.dispatch(Command("run.job"), context)

    def test_duplicate_registration_requires_explicit_replacement(self):
        runtime = ApplicationRuntime()
        runtime.services.register("sample", "first")
        with self.assertRaises(KeyError):
            runtime.services.register("sample", "second")
        runtime.services.register("sample", "second", replace=True)
        self.assertEqual(runtime.services.resolve("sample", str), "second")


class WorkflowApplicationTests(unittest.TestCase):
    def test_snapshot_coordinates_delegates_and_preserves_cache_contract(self):
        calls = []
        now = [100.0]

        def discover(*args, **kwargs):
            calls.append(("discover", args, kwargs))
            return [{"job_id": "local", "updated_timestamp": "1"}]

        def queue(rows):
            source_rows = list(rows)
            calls.append(("queue", source_rows))
            return (
                [{"job_id": "queue", "updated_timestamp": "2"}]
                if source_rows
                else []
            )

        def merge(*groups, **kwargs):
            calls.append(("merge", kwargs))
            return [dict(item) for group in groups for item in group]

        def completed(root, **kwargs):
            calls.append(("completed", root, kwargs))
            return [{"job_id": "complete", "updated_timestamp": "0"}]

        delegates = WorkflowDelegates(
            discover_workflow_jobs=discover,
            jobs_from_queue_rows=queue,
            merge_job_lists=merge,
            recent_completed_jobs=completed,
            group_processing_jobs=lambda jobs: {"Ready": list(jobs)},
            active_listings_summary=lambda path: {"path": str(path)},
            business_alerts=lambda jobs, listings, **kwargs: [
                {"severity": "Ready", "text": str(len(list(jobs))), "action": ""}
            ],
            update_workflow_context=lambda folder, **updates: {
                "capture_folder": str(folder),
                **updates,
            },
        )
        application = WorkflowApplication(
            delegates,
            cache_seconds=8,
            clock=lambda: now[0],
        )

        first = application.snapshot(
            capture_root="Capture",
            mobile_processing_root="Processing",
            mobile_failed_root="Failed",
            queue_rows=[{"capture_session_id": "queue"}],
            active_job={"job_id": "active", "updated_timestamp": "3"},
            completed_root="Completed",
            include_completed=True,
        )
        second = application.snapshot(
            capture_root="Capture",
            mobile_processing_root="Processing",
            mobile_failed_root="Failed",
            queue_rows=[],
            active_job=None,
            completed_root="Completed",
        )

        self.assertEqual(
            [item["job_id"] for item in first],
            ["local", "queue", "active", "complete"],
        )
        self.assertEqual([item["job_id"] for item in second], ["local"])
        self.assertEqual(
            len([call for call in calls if call[0] == "discover"]),
            1,
        )

        now[0] = 101.0
        application.invalidate()
        application.snapshot(
            capture_root="Capture",
            mobile_processing_root="Processing",
            mobile_failed_root="Failed",
            queue_rows=[],
            active_job=None,
            completed_root="Completed",
        )
        self.assertEqual(
            len([call for call in calls if call[0] == "discover"]),
            2,
        )

    def test_facade_delegates_context_queries_without_reimplementing_them(self):
        application = WorkflowApplication(legacy_delegates())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Capture"
            folder = root / "07.18.26"
            folder.mkdir(parents=True)
            (folder / "capture_session.json").write_text(
                json.dumps(
                    {
                        "capture_session_id": "session-1",
                        "capture_type": "NEW_CAPTURE",
                        "photos_captured": 2,
                        "finished_at": "2026-07-18T10:00:00",
                    }
                ),
                encoding="utf-8",
            )

            expected = legacy_workflow_context.merge_job_lists(
                legacy_workflow_context.discover_workflow_jobs(
                    root,
                    Path(temp) / "processing",
                    Path(temp) / "failed",
                    limit=60,
                ),
                [],
                [],
                limit=65,
            )
            actual = application.snapshot(
                capture_root=root,
                mobile_processing_root=Path(temp) / "processing",
                mobile_failed_root=Path(temp) / "failed",
                queue_rows=[],
                active_job=None,
                completed_root=Path(temp) / "completed",
            )

            self.assertEqual(actual, expected)
            updated = application.update_context(
                folder,
                current_workflow_state="Awaiting CSV Import",
            )
            self.assertEqual(
                updated["current_workflow_state"],
                "Awaiting CSV Import",
            )
            self.assertEqual(
                application.group_processing_jobs(actual),
                legacy_workflow_context.group_processing_jobs(actual),
            )

    def test_putnam_os_routes_workflow_calls_through_application_service(self):
        self.assertIn("def build_application_runtime():", PUTNAM_OS_SOURCE)
        self.assertIn("self.workflow_application.snapshot(", PUTNAM_OS_SOURCE)
        self.assertIn("self.workflow_application.update_context(", PUTNAM_OS_SOURCE)
        self.assertIn("self.workflow_application.invalidate()", PUTNAM_OS_SOURCE)
        self.assertNotIn("from workflow_context import (", PUTNAM_OS_SOURCE)
        self.assertNotIn("self.workflow_local_jobs =", PUTNAM_OS_SOURCE)


class ApplicationDependencyTests(unittest.TestCase):
    def test_application_layer_has_no_ui_or_subsystem_dependencies(self):
        forbidden_roots = {
            "tkinter",
            "Platform.Putnam_OS",
            "Platform.Marketplace_Intelligence",
            "cardvector.presentation",
            "cardvector.capture",
            "cardvector.inventory",
            "cardvector.shipping",
            "cardvector.listings",
        }
        violations = []
        for path in APPLICATION_ROOT.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [item.name for item in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    if any(
                        name == forbidden or name.startswith(forbidden + ".")
                        for forbidden in forbidden_roots
                    ):
                        violations.append(f"{path.name}: {name}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
