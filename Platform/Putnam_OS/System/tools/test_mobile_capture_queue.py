from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Platform.Putnam_OS.System.tools import mobile_capture_queue as queue
from Platform.Putnam_OS.System.tools.mobile_capture_queue import (
    MobileCaptureQueueService,
    MobileCaptureError,
    filter_session_rows,
    parse_etb_location,
    queue_summary,
    sanitize_error_message,
    session_row_model,
    session_location_id,
    session_capture_layout,
    session_capture_type,
    capture_record_position,
    storage_object_url,
    safe_path_part,
    stage_session,
    claim_session,
    update_session_status,
)


class MobileCaptureQueueTests(unittest.TestCase):
    @staticmethod
    def fake_download(_bucket, storage_path, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(storage_path, encoding="utf-8")

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

    def test_session_capture_type_defaults_blank_to_physical_inventory(self):
        self.assertEqual(session_capture_type({}), "PHYSICAL_INVENTORY")
        self.assertEqual(session_capture_type({"capture_type": ""}), "PHYSICAL_INVENTORY")
        self.assertEqual(session_capture_type({"device": {"capture_type": "new inventory"}}), "NEW_CAPTURE")

    def test_session_capture_layout_defaults_legacy_sessions_to_front_only(self):
        self.assertEqual(session_capture_layout({}), "FRONT_ONLY")
        self.assertEqual(session_capture_layout({"capture_layout": ""}), "FRONT_ONLY")
        self.assertEqual(
            session_capture_layout({"source_device": {"capture_layout": "front + back"}}),
            "FRONT_BACK",
        )

    def test_capture_record_position_maps_front_only_and_pairs(self):
        self.assertEqual(capture_record_position(1, "FRONT_ONLY"), (1, "front"))
        self.assertEqual(capture_record_position(2, "FRONT_ONLY"), (2, "front"))
        self.assertEqual(capture_record_position(1, "FRONT_BACK"), (1, "front"))
        self.assertEqual(capture_record_position(2, "FRONT_BACK"), (1, "back"))
        self.assertEqual(capture_record_position(3, "FRONT_BACK"), (2, "front"))
        self.assertEqual(capture_record_position(4, "FRONT_BACK"), (2, "back"))

    def test_storage_object_url_encodes_path_segments(self):
        self.assertEqual(
            storage_object_url("https://example.supabase.co/", "mobile-capture-originals", "user 1/ETB-001-A/file 1.jpg"),
            "https://example.supabase.co/storage/v1/object/mobile-capture-originals/user%201/ETB-001-A/file%201.jpg",
        )

    def test_sanitize_error_message_redacts_tokens_and_urls(self):
        text = sanitize_error_message("Bearer secret-token eyJabc https://abc.supabase.co service_role_key")
        self.assertIn("Bearer [redacted]", text)
        self.assertIn("[redacted-token]", text)
        self.assertIn("[supabase-url]", text)
        self.assertNotIn("secret-token", text)

    def test_missing_environment_variables_fail_closed(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            ok, message = MobileCaptureQueueService().environment_ready()
        self.assertFalse(ok)
        self.assertIn("CARDVECTOR_SUPABASE_URL", message)

    def test_queue_list_parsing_and_summary(self):
        rows = [
            {"capture_session_id": "s1", "status": "PENDING_CONVERSION", "etb_location": "ETB-001-A", "image_count": 2},
            {"capture_session_id": "s2", "status": "PROCESSING", "etb_location": "ETB-001-B", "conversion_workstation": "other"},
            {"capture_session_id": "s3", "status": "FAILED", "etb_location": "ETB-001-C", "error_message": "bad"},
        ]
        models = [session_row_model(row, current_workstation="this-pc") for row in rows]
        self.assertEqual(models[0]["status_label"], "Pending")
        self.assertTrue(models[1]["locked_by_other"])
        self.assertEqual(queue_summary(models), {"pending": 1, "processing": 1, "failed": 1})

    def test_status_filters_and_search(self):
        rows = [
            session_row_model({"capture_session_id": "pending-1", "status": "PENDING_CONVERSION", "etb_location": "ETB-001-A"}),
            session_row_model({"capture_session_id": "converted-1", "status": "CONVERTED", "etb_location": "ETB-002-A"}),
            session_row_model({"capture_session_id": "draft-1", "status": "DRAFT", "etb_location": "ETB-003-A"}),
        ]
        self.assertEqual([row["capture_session_id"] for row in filter_session_rows(rows, "ACTIVE")], ["pending-1"])
        self.assertEqual([row["capture_session_id"] for row in filter_session_rows(rows, "CONVERTED")], ["converted-1"])
        self.assertEqual([row["capture_session_id"] for row in filter_session_rows(rows, "ALL", "ETB-003")], ["draft-1"])

    def test_atomic_claim_conflict_rejects_non_pending_session(self):
        with mock.patch.object(queue, "request_json", return_value=[]):
            with self.assertRaises(MobileCaptureError):
                claim_session("session-1")

    def test_claim_uses_pending_conversion_guard(self):
        calls = []

        def fake_request(method, path, body=None, prefer=None):
            calls.append((method, path, body, prefer))
            return [{"capture_session_id": "session-1", "status": "PROCESSING"}]

        with mock.patch.object(queue, "request_json", side_effect=fake_request):
            claim_session("session-1")
        self.assertIn("status=eq.PENDING_CONVERSION", calls[0][1])
        self.assertEqual(calls[0][2]["status"], "PROCESSING")

    def test_stage_session_download_order_and_capture_session_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                mock.patch.object(queue, "MOBILE_PROCESSING_DIR", root / "MobileCapture" / "Processing"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_CAPTURE_ROOT", root / "Capture" / "Physical_Inventory_Conversion"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_SESSIONS_DIR", root / "inventory_conversion" / "sessions"),
                mock.patch.object(queue, "CURRENT_INVENTORY_CONVERSION", root / "inventory_conversion" / "current.json"),
                mock.patch.object(queue, "download_storage_object", side_effect=self.fake_download),
                mock.patch.object(queue, "workstation_name", return_value="TEST-PC"),
            ):
                manifest = stage_session(
                    {"capture_session_id": "session-1", "etb_location": "ETB-001-C", "created_at": "2026-07-13T12:00:00"},
                    [
                        {"image_id": "img-1", "storage_bucket": "mobile-capture-originals", "storage_path": "u/ETB-001-C/session-1/0001-a.jpg", "created_at": "t1"},
                        {"image_id": "img-2", "storage_bucket": "mobile-capture-originals", "storage_path": "u/ETB-001-C/session-1/0002-b.jpg", "created_at": "t2"},
                    ],
                )
            capture_file = Path(manifest["capture_session_file"])
            self.assertTrue(capture_file.exists())
            data = json.loads(capture_file.read_text(encoding="utf-8"))
            self.assertEqual(data["location_id"], "ETB-001-C")
            self.assertEqual(data["capture_session_id"], "session-1")
            self.assertEqual(data["capture_type"], "PHYSICAL_INVENTORY")
            self.assertEqual(data["capture_layout"], "FRONT_ONLY")
            self.assertEqual([record["mobile_image_id"] for record in data["records"]], ["img-1", "img-2"])
            self.assertEqual(
                [record["filename"] for record in data["records"]],
                ["000001_front.jpg", "000002_front.jpg"],
            )
            self.assertEqual(data["cards_captured"], 2)
            self.assertIn("Physical_Inventory_Conversion", str(capture_file))
            self.assertNotIn("ETB-001-C", capture_file.parent.name)

    def test_stage_session_reuses_cached_originals_without_redownload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = {"capture_session_id": "session-cache", "etb_location": "ETB-001-C", "created_at": "2026-07-13T12:00:00"}
            images = [
                {"image_id": "img-1", "storage_bucket": "mobile-capture-originals", "storage_path": "u/ETB-001-C/session-cache/0001-a.jpg", "created_at": "t1"},
                {"image_id": "img-2", "storage_bucket": "mobile-capture-originals", "storage_path": "u/ETB-001-C/session-cache/0002-b.jpg", "created_at": "t2"},
            ]
            with (
                mock.patch.object(queue, "MOBILE_PROCESSING_DIR", root / "MobileCapture" / "Processing"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_CAPTURE_ROOT", root / "Capture" / "Physical_Inventory_Conversion"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_SESSIONS_DIR", root / "inventory_conversion" / "sessions"),
                mock.patch.object(queue, "CURRENT_INVENTORY_CONVERSION", root / "inventory_conversion" / "current.json"),
                mock.patch.object(queue, "download_storage_object", side_effect=self.fake_download) as first_download,
                mock.patch.object(queue, "workstation_name", return_value="TEST-PC"),
            ):
                first_manifest = stage_session(session, images)
            self.assertEqual(first_download.call_count, 2)
            self.assertEqual(first_manifest["downloaded_originals"], 2)
            self.assertEqual(first_manifest["reused_originals"], 0)

            with (
                mock.patch.object(queue, "MOBILE_PROCESSING_DIR", root / "MobileCapture" / "Processing"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_CAPTURE_ROOT", root / "Capture" / "Physical_Inventory_Conversion"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_SESSIONS_DIR", root / "inventory_conversion" / "sessions"),
                mock.patch.object(queue, "CURRENT_INVENTORY_CONVERSION", root / "inventory_conversion" / "current.json"),
                mock.patch.object(queue, "download_storage_object", side_effect=AssertionError("unexpected redownload")) as second_download,
                mock.patch.object(queue, "workstation_name", return_value="TEST-PC"),
            ):
                second_manifest = stage_session(session, images)
            self.assertEqual(second_download.call_count, 0)
            self.assertEqual(second_manifest["downloaded_originals"], 0)
            self.assertEqual(second_manifest["reused_originals"], 2)
            download_manifest = json.loads(Path(second_manifest["download_manifest_file"]).read_text(encoding="utf-8"))
            self.assertEqual(len(download_manifest["downloads"]), 2)

    def test_stage_session_redownloads_when_cached_original_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = {"capture_session_id": "session-cache-missing", "etb_location": "ETB-001-C", "created_at": "2026-07-13T12:00:00"}
            images = [
                {"image_id": "img-1", "storage_bucket": "mobile-capture-originals", "storage_path": "u/ETB-001-C/session-cache-missing/0001-a.jpg", "created_at": "t1"},
            ]
            patches = [
                mock.patch.object(queue, "MOBILE_PROCESSING_DIR", root / "MobileCapture" / "Processing"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_CAPTURE_ROOT", root / "Capture" / "Physical_Inventory_Conversion"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_SESSIONS_DIR", root / "inventory_conversion" / "sessions"),
                mock.patch.object(queue, "CURRENT_INVENTORY_CONVERSION", root / "inventory_conversion" / "current.json"),
                mock.patch.object(queue, "workstation_name", return_value="TEST-PC"),
            ]
            with patches[0], patches[1], patches[2], patches[3], mock.patch.object(queue, "download_storage_object", side_effect=self.fake_download), patches[4]:
                first_manifest = stage_session(session, images)
            first_original = Path(first_manifest["originals_dir"]) / "000001.jpg"
            self.assertTrue(first_original.exists())
            first_original.unlink()

            with patches[0], patches[1], patches[2], patches[3], mock.patch.object(queue, "download_storage_object", side_effect=self.fake_download) as redownload, patches[4]:
                second_manifest = stage_session(session, images)
            self.assertEqual(redownload.call_count, 1)
            self.assertEqual(second_manifest["downloaded_originals"], 1)
            self.assertEqual(second_manifest["reused_originals"], 0)
            self.assertTrue(first_original.exists())

    def test_stage_session_routes_new_capture_to_root_capture_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                mock.patch.object(queue, "MOBILE_PROCESSING_DIR", root / "MobileCapture" / "Processing"),
                mock.patch.object(queue, "CAPTURE_ROOT", root / "Capture"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_CAPTURE_ROOT", root / "Capture" / "Physical_Inventory_Conversion"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_SESSIONS_DIR", root / "inventory_conversion" / "sessions"),
                mock.patch.object(queue, "CURRENT_INVENTORY_CONVERSION", root / "inventory_conversion" / "current.json"),
                mock.patch.object(queue, "download_storage_object", side_effect=self.fake_download),
                mock.patch.object(queue, "workstation_name", return_value="TEST-PC"),
            ):
                manifest = stage_session(
                    {
                        "capture_session_id": "session-new",
                        "etb_location": "ETB-001-A",
                        "capture_type": "NEW_CAPTURE",
                        "created_at": "2026-07-13T12:00:00",
                    },
                    [
                        {"image_id": "img-1", "storage_bucket": "mobile-capture-originals", "storage_path": "u/ETB-001-A/session-new/0001-a.jpg", "created_at": "t1"},
                    ],
                )
            capture_file = Path(manifest["capture_session_file"])
            data = json.loads(capture_file.read_text(encoding="utf-8"))
            self.assertEqual(capture_file.parent.parent, root / "Capture")
            self.assertEqual(data["capture_type"], "NEW_CAPTURE")
            self.assertEqual(data["capture_workflow"], "new_inventory_capture")
            self.assertEqual(manifest["inventory_conversion_session_file"], "")
            self.assertFalse((root / "inventory_conversion" / "current.json").exists())

    def test_stage_front_back_session_creates_matched_pair_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                mock.patch.object(queue, "MOBILE_PROCESSING_DIR", root / "MobileCapture" / "Processing"),
                mock.patch.object(queue, "CAPTURE_ROOT", root / "Capture"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_CAPTURE_ROOT", root / "Capture" / "Physical_Inventory_Conversion"),
                mock.patch.object(queue, "INVENTORY_CONVERSION_SESSIONS_DIR", root / "inventory_conversion" / "sessions"),
                mock.patch.object(queue, "CURRENT_INVENTORY_CONVERSION", root / "inventory_conversion" / "current.json"),
                mock.patch.object(queue, "download_storage_object", side_effect=self.fake_download),
                mock.patch.object(queue, "workstation_name", return_value="TEST-PC"),
            ):
                manifest = stage_session(
                    {
                        "capture_session_id": "session-pairs",
                        "etb_location": "ETB-002-G",
                        "capture_type": "PHYSICAL_INVENTORY",
                        "source_device": {"capture_layout": "FRONT_BACK"},
                        "created_at": "2026-07-17T12:00:00",
                    },
                    [
                        {"image_id": "img-2", "storage_path": "u/session/0002.jpg", "sequence_number": 2},
                        {"image_id": "img-1", "storage_path": "u/session/0001.jpg", "sequence_number": 1},
                        {"image_id": "img-4", "storage_path": "u/session/0004.jpg", "sequence_number": 4},
                        {"image_id": "img-3", "storage_path": "u/session/0003.jpg", "sequence_number": 3},
                    ],
                )
            capture_file = Path(manifest["capture_session_file"])
            data = json.loads(capture_file.read_text(encoding="utf-8"))
            self.assertEqual(data["capture_layout"], "FRONT_BACK")
            self.assertEqual(data["cards_captured"], 2)
            self.assertEqual(data["photos_captured"], 4)
            self.assertEqual(
                [(record["card_number"], record["side"], record["filename"]) for record in data["records"]],
                [
                    (1, "front", "000001_front.jpg"),
                    (1, "back", "000001_back.jpg"),
                    (2, "front", "000002_front.jpg"),
                    (2, "back", "000002_back.jpg"),
                ],
            )
            conversion = json.loads(Path(manifest["inventory_conversion_session_file"]).read_text(encoding="utf-8"))
            self.assertEqual(conversion["cards_captured"], 2)
            self.assertEqual(conversion["photos_captured"], 4)
            self.assertEqual(conversion["capture_layout"], "FRONT_BACK")

    def test_next_capture_folder_uses_dot_suffixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Capture" / "01.02.26").mkdir(parents=True)
            (root / "Capture" / "01.02.26.1").mkdir(parents=True)
            with (
                mock.patch.object(queue, "CAPTURE_ROOT", root / "Capture"),
                mock.patch.object(queue, "today_folder_name", return_value="01.02.26"),
            ):
                self.assertEqual(queue.next_capture_folder("NEW_CAPTURE").name, "01.02.26.2")

    def test_local_folder_helper_reads_manifest_capture_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processing = root / "Processing" / "session-1"
            capture_folder = root / "Capture" / "Physical_Inventory_Conversion" / "ETB-001-C" / "07.13.26"
            capture_folder.mkdir(parents=True)
            processing.mkdir(parents=True)
            (processing / "mobile_capture_manifest.json").write_text(json.dumps({"capture_folder": str(capture_folder)}), encoding="utf-8")
            with mock.patch.object(queue, "MOBILE_PROCESSING_DIR", root / "Processing"):
                self.assertEqual(queue.local_session_folder("session-1"), capture_folder)

    def test_service_process_uses_claim_load_stage_sequence(self):
        service = MobileCaptureQueueService(current_workstation="TEST-PC")
        with (
            mock.patch.object(queue, "sync_cloud_location_registry", return_value={"changed": False}),
            mock.patch.object(queue, "claim_session", return_value={"capture_session_id": "session-1"}),
            mock.patch.object(queue, "load_session_images", return_value=[{"image_id": "img-1"}]),
            mock.patch.object(queue, "stage_session", return_value={"capture_folder": "folder"}) as stage,
        ):
            self.assertEqual(service.process("session-1")["capture_folder"], "folder")
        stage.assert_called_once()

    def test_service_complete_fail_and_retry_use_controlled_actions(self):
        service = MobileCaptureQueueService(current_workstation="TEST-PC")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                mock.patch.object(queue, "MOBILE_CONVERTED_DIR", root / "Converted"),
                mock.patch.object(queue, "MOBILE_FAILED_DIR", root / "Failed"),
                mock.patch.object(queue, "update_session_status", return_value={"status": "CONVERTED"}) as update,
            ):
                service.complete("session-1")
            update.assert_called_with("session-1", "CONVERTED")
            with (
                mock.patch.object(queue, "MOBILE_FAILED_DIR", root / "Failed"),
                mock.patch.object(queue, "update_session_status", return_value={"status": "FAILED"}) as update,
            ):
                service.fail("session-1", "Bearer should-redact")
            self.assertNotIn("should-redact", update.call_args.args[2])
        with mock.patch.object(queue, "retry_failed_session", return_value={"status": "PENDING_CONVERSION"}) as retry:
            service.retry_failed("session-1")
        retry.assert_called_with("session-1")

    def test_retry_failed_requires_failed_status(self):
        with mock.patch.object(queue, "load_session", return_value={"error_message": "previous"}):
            with mock.patch.object(queue, "request_json", return_value=[]):
                with self.assertRaises(MobileCaptureError):
                    queue.retry_failed_session("session-1")

    def test_capture_queue_ui_uses_service_layer_and_cancels_auto_refresh(self):
        source = (queue.ROOT / "Platform" / "Putnam_OS" / "System" / "app" / "putnam_os.py").read_text(encoding="utf-8")
        self.assertIn("MobileCaptureQueueService", source)
        self.assertIn("capture_queue_cancel_auto_refresh", source)
        self.assertIn("self.after_cancel(after_id)", source)
        self.assertIn("self.after(30000, self.capture_queue_refresh_ui)", source)
        self.assertNotIn("request_json(", source)


if __name__ == "__main__":
    unittest.main()
