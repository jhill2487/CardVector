from __future__ import annotations

import unittest

from Platform.Putnam_OS.System.tools.mobile_capture_queue import parse_etb_location, safe_path_part


class MobileCaptureQueueTests(unittest.TestCase):
    def test_parse_etb_location_normalizes_location_id(self):
        self.assertEqual(parse_etb_location("etb-002-a"), ("ETB-002", "A", "ETB-002-A"))

    def test_safe_path_part_removes_path_separators(self):
        self.assertEqual(safe_path_part("ETB-002/A"), "ETB-002_A")


if __name__ == "__main__":
    unittest.main()
