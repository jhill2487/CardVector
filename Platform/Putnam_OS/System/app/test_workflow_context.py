import json
import tempfile
import unittest
from pathlib import Path

from workflow_context import (
    active_listings_summary,
    discover_workflow_jobs,
    group_processing_jobs,
    jobs_from_queue_rows,
    update_workflow_context,
)


class WorkflowContextTests(unittest.TestCase):
    def test_capture_folder_association_and_handoff_stages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Capture"
            folder = root / "07.16.26"
            folder.mkdir(parents=True)
            (folder / "capture_session.json").write_text(
                json.dumps(
                    {
                        "capture_session_id": "session-1",
                        "folder": str(folder),
                        "capture_type": "NEW_CAPTURE",
                        "photos_captured": 40,
                        "etb_location": "ETB-005-C",
                        "finished_at": "2026-07-16T10:00:00",
                    }
                ),
                encoding="utf-8",
            )

            jobs = discover_workflow_jobs(root)
            self.assertEqual(jobs[0]["capture_folder"], str(folder))
            self.assertEqual(jobs[0]["stage"], "Ready for CardUploader")

            update_workflow_context(folder, capture_session_id="session-1", carduploader_handoff_status="opened")
            jobs = discover_workflow_jobs(root)
            self.assertEqual(jobs[0]["stage"], "Awaiting CSV Import")

            update_workflow_context(
                folder,
                capture_session_id="session-1",
                carduploader_handoff_status="uploaded",
                carduploader_uploaded_at="2026-07-16T11:00:00",
                current_workflow_state="Uploaded to CardUploader",
                supabase_originals_cleanup_eligible=True,
                supabase_originals_cleanup_reason="carduploader_handoff_confirmed",
            )
            jobs = discover_workflow_jobs(root)
            self.assertEqual(jobs[0]["stage"], "Uploaded to CardUploader")
            self.assertEqual(jobs[0]["state"], "Complete")
            self.assertEqual(jobs[0]["action"], "Open Capture Folder")
            self.assertTrue(jobs[0]["supabase_originals_cleanup_eligible"])
            self.assertEqual(jobs[0]["supabase_originals_cleanup_reason"], "carduploader_handoff_confirmed")

            source = Path(temp) / "carduploader.csv"
            source.write_text("Card Name,Price\nPikachu,1.00\n", encoding="utf-8")
            update_workflow_context(folder, imported_csv_path=str(source), row_count=1, current_workflow_state="Pricing Review")
            jobs = discover_workflow_jobs(root)
            self.assertEqual(jobs[0]["stage"], "Pricing Review")
            self.assertEqual(group_processing_jobs(jobs)["Pricing Review"][0]["row_count"], 1)

    def test_failed_queue_row_retains_capture_queue_action(self):
        jobs = jobs_from_queue_rows(
            [
                {
                    "capture_session_id": "failed-1",
                    "status": "FAILED",
                    "capture_type": "PHYSICAL_INVENTORY",
                    "etb_location": "ETB-002-G",
                    "image_count": 40,
                    "last_error": "Storage authorization missing.",
                }
            ]
        )
        self.assertEqual(jobs[0]["action"], "Retry Failed Capture")
        self.assertEqual(jobs[0]["etb_location"], "ETB-002-G")

    def test_active_listing_summary_is_source_labeled(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "ebay-active.csv"
            source.write_text("Item number,Title\n1,Card A\n2,Card B\n", encoding="utf-8")
            summary = active_listings_summary(source)
            self.assertEqual(summary["count"], 2)
            self.assertIn("Local eBay Active Listings CSV", summary["source"])


if __name__ == "__main__":
    unittest.main()
