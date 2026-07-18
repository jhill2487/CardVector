from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Platform.cardvector.application import CaptureApplication
from Platform.cardvector.application.runtime import EventPublisher, ExecutionContext
from Platform.cardvector.capture import (
    CaptureService,
    capture_pair_rows,
    load_auto_capture_settings,
    normalize_auto_capture_settings,
    save_auto_capture_settings,
)
from Platform.cardvector.integrations.carduploader import (
    CardUploaderRecognitionAdapter,
)


class FakeDesktopCapture:
    allow_placeholder = True
    obs_manager = object()

    def __init__(self):
        self.calls = []

    def start_session(self):
        self.calls.append(("start_session",))
        return {"folder": "capture-folder", "records": []}

    def capture(self, session, side):
        self.calls.append(("capture", session, side))
        return type(
            "Result",
            (),
            {"path": Path("000001_front.jpg"), "side": side},
        )()

    def capture_bytes(self, session, side, image_bytes, capture_mode="OBS WebSocket"):
        self.calls.append(("capture_bytes", session, side, image_bytes, capture_mode))
        return type(
            "Result",
            (),
            {"path": Path("000001_front.jpg"), "side": side},
        )()

    def next_capture_side(self, session):
        self.calls.append(("next_capture_side", session))
        return "front"

    def capture_next(self, session):
        self.calls.append(("capture_next", session))
        return self.capture(session, "front")

    def retake_last(self, session):
        self.calls.append(("retake_last", session))
        return Path("_retakes/000001_front.jpg")

    def finish_session(self, session):
        self.calls.append(("finish_session", session))

    def obs_status(self):
        self.calls.append(("obs_status",))
        return "OBS status: connected"

    def launch_obs(self):
        self.calls.append(("launch_obs",))
        return Path("obs64.exe")

    def capture_obs_jpeg(self):
        self.calls.append(("capture_obs_jpeg",))
        return b"jpeg"

    def _save_session(self, session):
        self.calls.append(("save_session", session))


class FakeMobileCapture:
    current_workstation = "TEST-PC"

    def __init__(self):
        self.calls = []

    def environment_ready(self):
        self.calls.append(("environment_ready",))
        return True, "Connected"

    def list_queue(self, include_diagnostics=True, limit=100):
        self.calls.append(("list_queue", include_diagnostics, limit))
        return [{"capture_session_id": "mobile-1"}]

    def sync_locations(self, strict=True):
        self.calls.append(("sync_locations", strict))
        return {"changed": False}

    def process(self, session_id):
        self.calls.append(("process", session_id))
        return {"capture_folder": "folder"}

    def process_next_pending(self):
        self.calls.append(("process_next_pending",))
        return {"capture_folder": "staged-folder"}

    def process_all_pending(self, limit=25):
        self.calls.append(("process_all_pending", limit))
        return []

    def complete(self, session_id):
        self.calls.append(("complete", session_id))
        return {"status": "CONVERTED"}

    def fail(self, session_id, message):
        self.calls.append(("fail", session_id, message))
        return {"status": "FAILED"}

    def retry_failed(self, session_id):
        self.calls.append(("retry_failed", session_id))
        return {"status": "PENDING_CONVERSION"}

    def local_folder(self, session_id):
        self.calls.append(("local_folder", session_id))
        return Path("local-folder")


class CanonicalCaptureTests(unittest.TestCase):
    def build_application(self):
        desktop = FakeDesktopCapture()
        mobile = FakeMobileCapture()
        factory_calls = []

        def factory(**kwargs):
            factory_calls.append(kwargs)
            return FakeDesktopCapture()

        service = CaptureService(
            desktop=desktop,
            mobile=mobile,
            desktop_factory=factory,
        )
        recognition = CardUploaderRecognitionAdapter(
            url_loader=lambda: "https://carduploader.example/history"
        )
        return (
            CaptureApplication(service, recognition),
            desktop,
            mobile,
            factory_calls,
        )

    def test_application_delegates_desktop_capture_without_shape_changes(self):
        application, desktop, _mobile, _factory = self.build_application()
        events = []
        publisher = EventPublisher()
        publisher.subscribe("capture.session_started", events.append)
        publisher.subscribe("capture.image_captured", events.append)
        context = ExecutionContext.create(events=publisher)

        session = application.start_session(context)
        result = application.capture(session, "front", context)
        application.finish_session(session, context)

        self.assertEqual(session, {"folder": "capture-folder", "records": []})
        self.assertEqual(result.path, Path("000001_front.jpg"))
        self.assertEqual(
            [call[0] for call in desktop.calls],
            ["start_session", "capture", "finish_session"],
        )
        self.assertEqual(
            [event.name for event in events],
            ["capture.session_started", "capture.image_captured"],
        )

    def test_application_delegates_mobile_queue_and_preserves_result(self):
        application, _desktop, mobile, _factory = self.build_application()

        self.assertEqual(
            application.list_queue(include_diagnostics=False, limit=5),
            [{"capture_session_id": "mobile-1"}],
        )
        self.assertEqual(
            application.process_next_pending(),
            {"capture_folder": "staged-folder"},
        )
        self.assertEqual(application.complete("mobile-1"), {"status": "CONVERTED"})
        self.assertEqual(application.retry_failed("mobile-1"), {"status": "PENDING_CONVERSION"})
        self.assertEqual(
            [call[0] for call in mobile.calls],
            ["list_queue", "process_next_pending", "complete", "retry_failed"],
        )

    def test_desktop_factory_preserves_obs_and_placeholder_dependencies(self):
        application, desktop, _mobile, factory_calls = self.build_application()

        child = application.create_desktop_service(Path("conversion-root"))

        self.assertIsInstance(child, FakeDesktopCapture)
        self.assertEqual(len(factory_calls), 1)
        self.assertEqual(factory_calls[0]["capture_root"], Path("conversion-root"))
        self.assertIs(factory_calls[0]["obs_manager"], desktop.obs_manager)
        self.assertTrue(factory_calls[0]["allow_placeholder"])

    def test_carduploader_handoff_has_no_recognition_or_browser_side_effect(self):
        application, _desktop, _mobile, _factory = self.build_application()

        handoff = application.prepare_recognition_handoff(
            capture_folder=Path("Capture/07.18.26"),
            capture_session_id="session-1",
            metadata={"capture_type": "NEW_CAPTURE", "etb_location": "ETB-001-A"},
        )

        self.assertEqual(handoff.provider, "CardUploader")
        self.assertEqual(handoff.status, "Ready for CardUploader")
        self.assertEqual(handoff.capture_folder, str(Path("Capture/07.18.26")))
        self.assertEqual(handoff.capture_session_id, "session-1")
        self.assertEqual(
            handoff.provider_url,
            "https://carduploader.example/history",
        )
        self.assertEqual(handoff.metadata["capture_type"], "NEW_CAPTURE")

    def test_pairing_preserves_front_only_and_front_back_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            front = root / "000001_front.jpg"
            back = root / "000001_back.jpg"
            front.write_bytes(b"front")
            back.write_bytes(b"back")
            (root / "capture_session.json").write_text(
                json.dumps(
                    {
                        "capture_layout": "FRONT_BACK",
                        "records": [
                            {
                                "filename": front.name,
                                "path": str(front),
                                "side": "front",
                                "card_number": 1,
                            },
                            {
                                "filename": back.name,
                                "path": str(back),
                                "side": "back",
                                "card_number": 1,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            rows = capture_pair_rows(root)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "Complete")
        self.assertEqual(rows[0]["capture_layout"], "FRONT_BACK")
        self.assertEqual(rows[0]["front"], front)
        self.assertEqual(rows[0]["back"], back)

    def test_auto_capture_settings_round_trip_uses_exact_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auto_capture_settings.json"
            expected = normalize_auto_capture_settings(
                {
                    "auto_capture_enabled": True,
                    "stability_delay_seconds": 1.25,
                    "duplicate_lockout_seconds": 2.5,
                    "frame_poll_interval_ms": 250,
                    "sensitivity": "High",
                }
            )
            saved = save_auto_capture_settings(path, expected)
            loaded = load_auto_capture_settings(path)

        self.assertEqual(saved, expected)
        self.assertEqual(loaded, expected)

    def test_canonical_capture_and_recognition_sources_have_no_ui_or_ocr_imports(self):
        source_paths = [
            Path("Platform/cardvector/capture/auto_capture.py"),
            Path("Platform/cardvector/capture/pairing.py"),
            Path("Platform/cardvector/capture/service.py"),
            Path("Platform/cardvector/application/capture.py"),
            Path("Platform/cardvector/integrations/carduploader/recognition.py"),
        ]
        source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

        self.assertNotIn("tkinter", source.lower())
        self.assertNotIn("pytesseract", source.lower())
        self.assertNotIn("Archive.Scanner_Development", source)
        self.assertNotIn("webbrowser", source)


if __name__ == "__main__":
    unittest.main()
