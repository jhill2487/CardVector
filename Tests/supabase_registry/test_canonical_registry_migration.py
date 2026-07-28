from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Platform.cardvector.integrations.supabase.registry import (
    CanonicalLocation,
    SupabaseRegistryClient,
    canonical_rows_to_legacy_etb_rows,
    legacy_status_to_canonical,
)
from Tools import migrate_legacy_registry_to_supabase as migration


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260725090000_canonical_capture_location_registry.sql"
APP_JS = ROOT / "Docs" / "app.js"


class CanonicalSupabaseRegistryMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.app_js = APP_JS.read_text(encoding="utf-8")

    def test_canonical_tables_are_declared_with_rls(self):
        for table in (
            "cardvector_storage_locations",
            "cardvector_capture_sessions",
            "cardvector_capture_images",
            "cardvector_inventory_relationships",
        ):
            self.assertIn(f"create table if not exists public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
            self.assertIn(f"revoke all on table public.{table} from anon", self.sql)

    def test_location_model_supports_hierarchy_and_container_types(self):
        self.assertIn("parent_location_id uuid references public.cardvector_storage_locations", self.sql)
        for value in ("'room'", "'shelf'", "'cabinet'", "'drawer'", "'etb'", "'box'", "'binder'", "'bin'", "'slot'", "'custom'"):
            self.assertIn(value, self.sql)

    def test_capture_images_link_storage_metadata_to_sessions(self):
        self.assertIn("capture_session_id uuid not null references public.cardvector_capture_sessions", self.sql)
        self.assertIn("storage_bucket text not null default 'mobile-capture-originals'", self.sql)
        self.assertIn("storage_object_path text not null", self.sql)
        self.assertIn("cardvector_capture_images_session_sequence_idx", self.sql)
        self.assertIn("cardvector_capture_images_storage_path_idx", self.sql)

    def test_next_etb_slot_rpc_is_authenticated_and_atomic(self):
        self.assertIn("cardvector_create_next_etb_slot", self.sql)
        self.assertIn("v_user_id uuid := auth.uid()", self.sql)
        self.assertIn("Location-management authorization required.", self.sql)
        self.assertIn("for update", self.sql.lower())
        self.assertIn("with ordinality", self.sql.lower())

    def test_legacy_status_mapping(self):
        self.assertEqual(legacy_status_to_canonical("Location Complete"), "location_complete")
        self.assertEqual(legacy_status_to_canonical("Mobile Capture Staged"), "staged")
        self.assertEqual(legacy_status_to_canonical("Available"), "active")

    def test_legacy_registry_dry_run_maps_etb_and_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(
                json.dumps(
                    {
                        "updated_at": "2026-07-25T09:00:00",
                        "locations": [
                            {
                                "location_code": "ETB-002",
                                "status": "Active",
                                "locations": [
                                    {
                                        "location_code": "A",
                                        "location_id": "ETB-002-A",
                                        "status": "Location Complete",
                                        "capacity": 40,
                                        "stored_count": 40,
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            args = migration.parse_args(["--registry", str(path)])
            report = migration.build_report(args)
        self.assertEqual(report["records_discovered"]["locations"], 2)
        rows = report["prepared_rows"]["locations"]
        self.assertEqual(rows[0]["location_type"], "etb")
        self.assertEqual(rows[1]["location_type"], "slot")
        self.assertEqual(rows[1]["status"], "location_complete")
        self.assertFalse(report["invalid_records"])

    def test_canonical_rows_project_to_legacy_ui_shape(self):
        etb = CanonicalLocation(
            id="etb-uuid",
            name="ETB-002",
            display_code="ETB-002",
            location_type="etb",
            status="active",
            capacity=400,
        )
        slot = CanonicalLocation(
            id="slot-uuid",
            name="ETB-002-A",
            parent_location_id="etb-uuid",
            display_code="ETB-002-A",
            legacy_location_code="A",
            location_type="slot",
            status="location_complete",
            capacity=40,
            stored_count=40,
        )
        rows = canonical_rows_to_legacy_etb_rows([slot, etb])
        self.assertEqual(rows[0]["location_code"], "ETB-002")
        self.assertEqual(rows[0]["locations"][0]["location_code"], "A")
        self.assertEqual(rows[0]["locations"][0]["status"], "Location Complete")

    def test_mobile_app_writes_canonical_registry_with_legacy_fallback(self):
        for contract in (
            '.from("cardvector_storage_locations")',
            '.from("cardvector_capture_sessions")',
            '.from("cardvector_capture_images")',
            "cardvector_create_next_etb_slot",
            "cardvector_create_next_location",
            "requireCanonicalRegistry",
            "tolerateLegacyCompatibilityWrite",
        ):
            self.assertIn(contract, self.app_js)

    def test_mobile_upload_creates_canonical_session_before_legacy_compatibility_write(self):
        submit_start = self.app_js.index("async function submitCapture")
        session_create = self.app_js.index(
            'upsertCanonicalCaptureSession(client, session, orderedImages, user, "uploading")',
            submit_start,
        )
        legacy_create = self.app_js.index('.from("mobile_capture_sessions").upsert', submit_start)
        self.assertLess(session_create, legacy_create)

    def test_apply_mode_blocks_unresolved_conflicts(self):
        rows = [
            {"id": "same-id", "status": "staged"},
            {"id": "same-id", "status": "completed"},
        ]
        unique, duplicates, conflicts, excluded = migration.deduplicate_rows(rows, "id")
        self.assertEqual(len(unique), 1)
        self.assertFalse(duplicates)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(len(excluded), 1)
        self.assertTrue(conflicts[0]["blocking"])

    def test_same_filename_in_different_sessions_is_not_deduplicated(self):
        rows = [
            {
                "id": "img-1",
                "_migration_entity_type": "capture_image",
                "capture_session_id": "session-a",
                "sequence_number": 1,
                "storage_bucket": "mobile-capture-originals",
                "storage_object_path": "user/session-a/0001-card.jpg",
                "original_filename": "card.jpg",
            },
            {
                "id": "img-2",
                "_migration_entity_type": "capture_image",
                "capture_session_id": "session-b",
                "sequence_number": 1,
                "storage_bucket": "mobile-capture-originals",
                "storage_object_path": "user/session-b/0001-card.jpg",
                "original_filename": "card.jpg",
            },
        ]
        rows, conflicts, excluded = migration.enforce_capture_image_identity_rules(rows)
        self.assertEqual(len(rows), 2)
        self.assertFalse(conflicts)
        self.assertFalse(excluded)

    def test_same_storage_path_cannot_create_two_canonical_images(self):
        rows = [
            {
                "id": "img-1",
                "_migration_entity_type": "capture_image",
                "capture_session_id": "session-a",
                "sequence_number": 1,
                "storage_bucket": "mobile-capture-originals",
                "storage_object_path": "user/session-a/0001-card.jpg",
            },
            {
                "id": "img-2",
                "_migration_entity_type": "capture_image",
                "capture_session_id": "session-a",
                "sequence_number": 2,
                "storage_bucket": "mobile-capture-originals",
                "storage_object_path": "user/session-a/0001-card.jpg",
            },
        ]
        rows, conflicts, excluded = migration.enforce_capture_image_identity_rules(rows)
        self.assertEqual(len(rows), 1)
        self.assertEqual(conflicts[0]["classification"], "Duplicate storage object path")
        self.assertEqual(len(excluded), 1)

    def test_same_checksum_in_same_session_is_detected(self):
        rows = [
            {
                "id": "img-1",
                "_migration_entity_type": "capture_image",
                "capture_session_id": "session-a",
                "sequence_number": 1,
                "storage_bucket": "mobile-capture-originals",
                "storage_object_path": "user/session-a/0001-card.jpg",
                "checksum": "abc",
            },
            {
                "id": "img-2",
                "_migration_entity_type": "capture_image",
                "capture_session_id": "session-a",
                "sequence_number": 2,
                "storage_bucket": "mobile-capture-originals",
                "storage_object_path": "user/session-a/0002-card.jpg",
                "checksum": "abc",
            },
        ]
        rows, conflicts, excluded = migration.enforce_capture_image_identity_rules(rows)
        self.assertEqual(len(rows), 1)
        self.assertEqual(conflicts[0]["classification"], "Duplicate image checksum")
        self.assertEqual(len(excluded), 1)

    def test_newer_existing_record_is_not_overwritten_without_resolution(self):
        rows = [
            {
                "id": "session-1",
                "_migration_entity_type": "capture_session",
                "legacy_session_id": "legacy-1",
                "status": "staged",
                "updated_at": "2026-07-25T12:00:00",
            },
            {
                "id": "session-1",
                "_migration_entity_type": "capture_session",
                "legacy_session_id": "legacy-1",
                "status": "draft",
                "updated_at": "2026-07-24T12:00:00",
            },
        ]
        unique, _duplicates, conflicts, _excluded = migration.deduplicate_rows(rows, "id")
        migration.assign_conflict_numbers(conflicts)
        migration.apply_reviewed_resolutions({"capture_session": unique}, conflicts, {"resolutions": []})
        self.assertEqual(unique[0]["status"], "staged")
        self.assertTrue(conflicts[0]["blocking"])

    def test_approved_exact_duplicate_skip_is_idempotent(self):
        rows = [
            {"id": "same", "_migration_entity_type": "capture_session", "legacy_session_id": "same"},
            {"id": "same", "_migration_entity_type": "capture_session", "legacy_session_id": "same"},
        ]
        unique, duplicates, conflicts, excluded = migration.deduplicate_rows(rows, "id")
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(duplicates), 1)
        self.assertFalse(conflicts)
        self.assertEqual(len(excluded), 1)

    def test_reviewed_skip_exact_duplicate_resolves_blocking_conflict(self):
        rows = [
            {"id": "same", "_migration_entity_type": "capture_session", "legacy_session_id": "same", "status": "staged"},
            {"id": "same", "_migration_entity_type": "capture_session", "legacy_session_id": "same", "status": "draft"},
        ]
        unique, _duplicates, conflicts, _excluded = migration.deduplicate_rows(rows, "id")
        migration.assign_conflict_numbers(conflicts)
        plan = {
            "resolutions": [
                {
                    "conflict_id": conflicts[0]["conflict_id"],
                    "action": "skip_exact_duplicate",
                    "approved": True,
                }
            ]
        }
        migration.apply_reviewed_resolutions({"capture_session": unique}, conflicts, plan)
        self.assertTrue(conflicts[0]["resolved"])
        self.assertFalse(conflicts[0]["blocking"])
        self.assertEqual(conflicts[0]["resolution_action"], "skip_exact_duplicate")

    def test_dry_run_counts_balance(self):
        discovered = {"locations": 1, "capture_sessions": 2, "capture_images": 3}
        prepared = {"locations": 1, "capture_sessions": 1, "capture_images": 2}
        conflicts = [
            {
                "entity_type": "capture_session",
                "resolved": True,
                "resolution_action": "skip_exact_duplicate",
                "blocking": False,
            },
            {
                "entity_type": "capture_image",
                "resolved": True,
                "resolution_action": "skip_exact_duplicate",
                "blocking": False,
            },
        ]
        balance = migration.balance_counts(discovered, prepared, [], conflicts, [])
        self.assertTrue(balance["balanced"])
        self.assertEqual(balance["entities"]["capture_sessions"]["skipped_exact_duplicates"], 1)
        self.assertEqual(balance["entities"]["capture_images"]["skipped_exact_duplicates"], 1)
        self.assertEqual(balance["entities"]["capture_sessions"]["unresolved_conflicts"], 0)

    def test_unresolved_conflict_does_not_balance_as_duplicate_skip(self):
        discovered = {"locations": 0, "capture_sessions": 2, "capture_images": 0}
        prepared = {"locations": 0, "capture_sessions": 1, "capture_images": 0}
        conflicts = [{"entity_type": "capture_session", "blocking": True}]
        balance = migration.balance_counts(discovered, prepared, [], conflicts, [])
        self.assertTrue(balance["balanced"])
        self.assertEqual(balance["entities"]["capture_sessions"]["skipped_exact_duplicates"], 0)
        self.assertEqual(balance["entities"]["capture_sessions"]["unresolved_conflicts"], 1)

    def test_resolution_file_parser_rejects_unknown_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "resolution.json"
            path.write_text(json.dumps({"resolutions": [{"action": "wing_it"}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                migration.load_resolution_file(path)

    def test_bulk_upsert_payloads_use_matching_object_keys(self):
        class RecordingClient(SupabaseRegistryClient):
            def __init__(self):
                super().__init__("https://example.supabase.co", "service-role-key")
                self.body = None

            def request_json(self, method, path, body=None, *, prefer=None):
                self.body = body
                return []

        client = RecordingClient()
        client.upsert_locations(
            [
                {
                    "id": "slot-a",
                    "name": "ETB-001-A",
                    "parent_location_id": "etb-001",
                    "legacy_location_code": "A",
                },
                {
                    "id": "etb-001",
                    "name": "ETB-001",
                    "parent_location_id": "",
                },
            ]
        )
        self.assertIsNotNone(client.body)
        key_sets = {tuple(sorted(row.keys())) for row in client.body}
        self.assertEqual(len(key_sets), 1)
        self.assertIsNone(client.body[1]["parent_location_id"])
        self.assertIsNone(client.body[1]["legacy_location_code"])


if __name__ == "__main__":
    unittest.main()
