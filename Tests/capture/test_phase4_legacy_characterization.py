from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "Platform" / "Putnam_OS" / "System" / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

capture_studio = importlib.import_module("capture_studio")
putnam_os = importlib.import_module("putnam_os")


def jpeg_bytes(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (360, 520), color).save(buffer, format="JPEG")
    return buffer.getvalue()


class Phase4LegacyCaptureCharacterizationTests(unittest.TestCase):
    def test_desktop_session_and_pair_output_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = capture_studio.CaptureStudioService(
                capture_root=Path(tmp),
                allow_placeholder=True,
            )
            session = service.start_session()
            service.capture_bytes(session, "front", jpeg_bytes("red"), "OBS Auto Capture")
            service.capture_bytes(session, "back", jpeg_bytes("blue"), "OBS Auto Capture")
            rows = putnam_os.capture_pair_rows(session["folder"])

            persisted = json.loads(
                (Path(session["folder"]) / "capture_session.json").read_text(encoding="utf-8")
            )

        self.assertEqual(
            sorted(persisted),
            [
                "capture_mode",
                "current_card_number",
                "finished_at",
                "folder",
                "photos_captured",
                "records",
                "started_at",
            ],
        )
        self.assertEqual(
            [record["filename"] for record in persisted["records"]],
            ["000001_front.jpg", "000001_back.jpg"],
        )
        self.assertEqual(persisted["current_card_number"], 2)
        self.assertEqual(persisted["photos_captured"], 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pair_number"], 1)
        self.assertEqual(rows[0]["status"], "Complete")
        self.assertEqual(rows[0]["capture_layout"], "FRONT_BACK")
        self.assertTrue(rows[0]["latest"])

    def test_pair_status_vocabulary_is_stable(self):
        self.assertEqual(putnam_os.capture_pair_status(None), "Ready")
        self.assertEqual(
            putnam_os.capture_pair_status(
                {
                    "current_card_number": 1,
                    "records": [{"card_number": 1, "side": "front"}],
                }
            ),
            "Waiting for Back",
        )
        self.assertEqual(
            putnam_os.capture_pair_status(
                {
                    "current_card_number": 1,
                    "records": [
                        {"card_number": 1, "side": "front"},
                        {"card_number": 1, "side": "back"},
                    ],
                }
            ),
            "Ready for Next Card",
        )

    def test_auto_capture_math_and_normalization_are_stable(self):
        red = jpeg_bytes("red")
        blue = jpeg_bytes("blue")
        red_signature = putnam_os.capture_frame_signature(red)
        blue_signature = putnam_os.capture_frame_signature(blue)

        self.assertEqual(putnam_os.signature_difference(red_signature, red_signature), 0)
        self.assertGreater(putnam_os.signature_difference(red_signature, blue_signature), 0.05)
        self.assertEqual(
            putnam_os.normalize_auto_capture_settings(
                {
                    "auto_capture_enabled": True,
                    "stability_delay_seconds": "99",
                    "duplicate_lockout_seconds": "0",
                    "frame_poll_interval_ms": "20",
                    "sensitivity": "unknown",
                }
            ),
            {
                "auto_capture_enabled": True,
                "stability_delay_seconds": 5.0,
                "duplicate_lockout_seconds": 0.5,
                "frame_poll_interval_ms": 100,
                "sensitivity": "Medium",
            },
        )
        self.assertEqual(
            putnam_os.auto_capture_thresholds({"sensitivity": "High"}),
            {"present": 0.07, "empty": 0.035, "stable": 0.012, "changed": 0.045},
        )

    def test_production_recognition_is_an_external_handoff(self):
        source = (APP_DIR / "putnam_os.py").read_text(encoding="utf-8")
        queue_source = (
            ROOT / "Platform" / "Putnam_OS" / "System" / "tools" / "mobile_capture_queue.py"
        ).read_text(encoding="utf-8")

        self.assertIn("CardUploader owns card recognition", source)
        self.assertIn("CardUploader remains the recognition system", queue_source)
        self.assertNotIn("Archive.Scanner_Development", source)
        self.assertNotIn("pytesseract", source)

    def test_putnam_os_runtime_resolves_canonical_capture_application(self):
        runtime = putnam_os.build_application_runtime()
        capture_application = runtime.services.resolve("capture")

        self.assertEqual(type(capture_application).__name__, "CaptureApplication")
        self.assertEqual(type(capture_application._capture).__name__, "CaptureService")
        self.assertEqual(
            type(capture_application._recognition).__name__,
            "CardUploaderRecognitionAdapter",
        )


if __name__ == "__main__":
    unittest.main()
