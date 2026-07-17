import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import putnam_os


class MobileCaptureThumbnailPairTests(unittest.TestCase):
    @staticmethod
    def write_session(folder: Path, capture_layout: str, records: list[dict]) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        for record in records:
            (folder / record["filename"]).write_bytes(b"jpeg")
        (folder / "capture_session.json").write_text(
            json.dumps(
                {
                    "folder": str(folder),
                    "source": "MOBILE_WEB",
                    "capture_layout": capture_layout,
                    "records": records,
                }
            ),
            encoding="utf-8",
        )

    def test_front_back_mobile_records_render_as_one_complete_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Capture" / "07.17.26"
            self.write_session(
                folder,
                "FRONT_BACK",
                [
                    {"filename": "000001_front.jpg", "side": "front", "card_number": 1},
                    {"filename": "000001_back.jpg", "side": "back", "card_number": 1},
                ],
            )
            rows = putnam_os.capture_pair_rows(folder)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "Complete")
        self.assertEqual(rows[0]["capture_layout"], "FRONT_BACK")
        self.assertEqual(rows[0]["front"].name, "000001_front.jpg")
        self.assertEqual(rows[0]["back"].name, "000001_back.jpg")

    def test_front_only_mobile_record_is_complete_without_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Capture" / "07.17.26"
            self.write_session(
                folder,
                "FRONT_ONLY",
                [{"filename": "000001_front.jpg", "side": "front", "card_number": 1}],
            )
            rows = putnam_os.capture_pair_rows(folder)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "Complete")
        self.assertEqual(rows[0]["capture_layout"], "FRONT_ONLY")
        self.assertIsNone(rows[0]["back"])

    def test_latest_capture_session_finds_nested_physical_inventory_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture_root = Path(tmp) / "Capture"
            nested = capture_root / "Physical_Inventory_Conversion" / "07.17.26"
            self.write_session(
                nested,
                "FRONT_ONLY",
                [{"filename": "000001_front.jpg", "side": "front", "card_number": 1}],
            )
            with mock.patch.object(putnam_os, "CAPTURE_ROOT", capture_root):
                latest = putnam_os.latest_capture_session()
        self.assertEqual(latest, nested)


if __name__ == "__main__":
    unittest.main()
