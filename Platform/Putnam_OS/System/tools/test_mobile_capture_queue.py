from __future__ import annotations

import unittest

from Platform.Putnam_OS.System.tools.mobile_capture_queue import (
    MobileCaptureError,
    parse_etb_location,
    session_location_id,
    storage_object_url,
    safe_path_part,
    update_session_status,
)


class MobileCaptureQueueTests(unittest.TestCase):
    def test_parse_etb_location_normalizes_location_id(self):
        self.assertEqual(parse_etb_location("etb-002-a"), ("ETB-002", "A", "ETB-002-A"))

    def test_safe_path_part_removes_path_separators(self):
        self.assertEqual(safe_path_part("ETB-002/A"), "ETB-002_A")

    def test_session_location_id_accepts_existing_frontend_field(self):
        self.assertEqual(session_location_id({"etb_location": "ETB-002-A"}), "ETB-002-A")

    def test_session_location_id_accepts_required_alias_field(self):
        self.assertEqual(session_location_id({"etb_location_id": "ETB-002-A"}), "ETB-002-A")

    def test_session_location_id_rejects_missing_location(self):
        with self.assertRaises(MobileCaptureError):
            session_location_id({})

    def test_update_status_rejects_processing_as_terminal_update(self):
        with self.assertRaises(MobileCaptureError):
            update_session_status("capture-1", "PROCESSING")

    def test_storage_object_url_encodes_path_segments(self):
        self.assertEqual(
            storage_object_url("https://example.supabase.co/", "mobile-capture-originals", "user 1/ETB-001-A/file 1.jpg"),
            "https://example.supabase.co/storage/v1/object/mobile-capture-originals/user%201/ETB-001-A/file%201.jpg",
        )


if __name__ == "__main__":
    unittest.main()
