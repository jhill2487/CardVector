from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from Platform.Putnam_OS.System.app import workflow_context


class Phase6LegacyWorkflowCharacterizationTests(unittest.TestCase):
    def test_existing_dashboard_stage_sequence_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Capture"
            folder = root / "07.19.26"
            folder.mkdir(parents=True)
            (folder / "capture_session.json").write_text(
                json.dumps(
                    {
                        "capture_session_id": "session-1",
                        "capture_type": "PHYSICAL_INVENTORY",
                        "etb_location": "ETB-002-G",
                        "photos_captured": 40,
                        "finished_at": "2026-07-19T12:00:00",
                    }
                ),
                encoding="utf-8",
            )

            job = workflow_context.discover_workflow_jobs(root)[0]
            self.assertEqual(
                (job["state"], job["stage"], job["action"]),
                ("Ready", "Ready for CardUploader", "Open CardUploader"),
            )

            workflow_context.update_workflow_context(
                folder,
                carduploader_handoff_status="opened",
            )
            job = workflow_context.discover_workflow_jobs(root)[0]
            self.assertEqual(
                (job["state"], job["stage"], job["action"]),
                ("Ready", "Awaiting CSV Import", "Import CardUploader CSV"),
            )

            csv_path = Path(temp) / "carduploader.csv"
            csv_path.write_text("Card Name\nFixture\n", encoding="utf-8")
            workflow_context.update_workflow_context(
                folder,
                imported_csv_path=str(csv_path),
                row_count=1,
            )
            job = workflow_context.discover_workflow_jobs(root)[0]
            self.assertEqual(
                (job["state"], job["stage"], job["action"]),
                ("Needs Attention", "Pricing Review", "Review Pricing"),
            )

            pricing = Path(temp) / "pricing"
            pricing.mkdir()
            workflow_context.update_workflow_context(
                folder,
                pricing_job_path=str(pricing),
            )
            job = workflow_context.discover_workflow_jobs(root)[0]
            self.assertEqual(
                (job["state"], job["stage"], job["action"]),
                ("Ready", "Ready for eBay Upload", "Open Export Folder"),
            )


if __name__ == "__main__":
    unittest.main()
