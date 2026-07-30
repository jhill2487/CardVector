from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from Platform.Putnam_OS.System.app.inventory_locations import (
    cloud_location_registry_snapshot,
    merge_cloud_location_registry,
    next_unprovisioned_location_code,
    parse_etb_location_id,
    record_completed_batch_location,
)
from Platform.Putnam_OS.System.tools import mobile_capture_queue as queue


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260716130000_mobile_location_registry.sql"
APP_JS = ROOT / "Docs" / "app.js"


class MobileLocationDatabaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.app_js = APP_JS.read_text(encoding="utf-8")

    def test_authenticated_operators_can_list_private_etbs_and_locations(self):
        self.assertIn('create policy "authorized operators read etbs"', self.sql)
        self.assertIn('create policy "authorized operators read locations"', self.sql)
        self.assertIn("grant select on table public.cardvector_etbs to authenticated", self.sql)
        self.assertIn("grant select on table public.cardvector_locations to authenticated", self.sql)
        self.assertIn("alter table public.cardvector_etbs enable row level security", self.sql)
        self.assertIn("alter table public.cardvector_locations enable row level security", self.sql)

    def test_location_creation_requires_authentication_and_authorization(self):
        self.assertIn("v_user_id uuid := auth.uid()", self.sql)
        self.assertIn("Authentication required.", self.sql)
        self.assertIn("Location-management authorization required.", self.sql)
        self.assertIn("cardvector_location_operators", self.sql)
        self.assertIn("can_manage_locations", self.sql)

    def test_anon_and_unrestricted_browser_writes_are_rejected(self):
        self.assertIn("revoke all on table public.cardvector_locations from anon", self.sql)
        self.assertIn("revoke insert, update, delete on table public.cardvector_locations from authenticated", self.sql)
        self.assertIn("revoke all on function public.cardvector_create_next_location(text, text) from anon", self.sql)
        self.assertNotIn("grant insert on table public.cardvector_locations to authenticated", self.sql)
        self.assertNotIn("SERVICE_ROLE", self.app_js)

    def test_canonical_format_capacity_status_and_uniqueness_contract(self):
        for contract in (
            "^ETB-[0-9]{3}$",
            "location_code ~ '^[A-J]$'",
            "location_id = etb_id || '-' || location_code",
            "default 400",
            "default 40",
            "unique (etb_id, location_code)",
        ):
            self.assertIn(contract, self.sql)

    def test_atomic_next_location_serializes_and_rechecks_expected_proposal(self):
        self.assertIn("for update", self.sql.lower())
        self.assertIn("with ordinality", self.sql.lower())
        self.assertIn("order by allowed.sequence_number", self.sql.lower())
        self.assertIn("v_expected <> v_next_code", self.sql)
        self.assertIn("Location availability changed", self.sql)
        self.assertIn("No available location remains", self.sql)

    def test_mobile_routes_do_not_auto_start_camera(self):
        etb_start = self.app_js.index('if (route === "etb"')
        location_start = self.app_js.index('if (route === "location"')
        no_qr_start = self.app_js.index('route === "mobile-capture"')
        camera_start = self.app_js.index('if (route === "capture" && parts[1] && parts[2])')
        etb_route = self.app_js[etb_start:location_start]
        no_qr_route = self.app_js[no_qr_start:camera_start]
        self.assertIn("initializeCaptureEntry", etb_route)
        self.assertNotIn("initializeCapture(etbId", etb_route)
        self.assertIn("initializeCaptureEntry();", no_qr_route)
        self.assertNotIn("initializeCapture(etbId", no_qr_route)
        self.assertIn('route === "mobile"', no_qr_route)

    def test_direct_location_route_retains_explicit_capture_type_choice(self):
        location_start = self.app_js.index('if (route === "location"')
        no_qr_start = self.app_js.index('route === "mobile-capture"')
        direct_route = self.app_js[location_start:no_qr_start]
        self.assertIn("captureChoiceHtml(etbId, location)", direct_route)
        self.assertNotIn("initializeCapture(etbId", direct_route)

    def test_etb_and_no_qr_flows_preserve_capture_type_and_canonical_location(self):
        for contract in (
            "state.captureType = normalizeCaptureType",
            "state.etbId = mobileCore.normalizeEtbId",
            "state.location = mobileCore.normalizeLocationCode",
            "mobileCore.canonicalLocationId",
            "captureRoute(state.etbId, state.location, state.captureType, state.captureLayout)",
            "Start Capture",
        ):
            self.assertIn(contract, self.app_js)

    def test_no_qr_mobile_entry_uses_streamlined_dropdown_form(self):
        for contract in (
            'id="mobile-capture-type"',
            'id="mobile-capture-etb"',
            'id="mobile-capture-location"',
            'id="mobile-capture-layout"',
            'id="mobile-capture-entry-form"',
            "renderMobileCaptureForm",
            "Choose ETB first",
        ):
            self.assertIn(contract, self.app_js)

    def test_mobile_capture_allows_operator_to_select_camera_device(self):
        for contract in (
            'id="camera-device-select"',
            "navigator.mediaDevices.enumerateDevices",
            'device.kind === "videoinput"',
            "deviceId: { exact: deviceId }",
            "saveSelectedCameraDeviceId",
            "Switching camera...",
        ):
            self.assertIn(contract, self.app_js)

    def test_mobile_creation_uses_restricted_rpc(self):
        self.assertIn('client.rpc("cardvector_create_next_location"', self.app_js)
        self.assertIn("p_expected_location_code", self.app_js)
        self.assertNotIn('.from("cardvector_locations").insert', self.app_js)


class DesktopLocationSynchronizationTests(unittest.TestCase):
    def test_first_next_and_exhausted_location_rules(self):
        self.assertEqual(next_unprovisioned_location_code([]), "A")
        self.assertEqual(next_unprovisioned_location_code(["A", "B"]), "C")
        self.assertEqual(next_unprovisioned_location_code(list("ABCDEFGHIJ")), "")

    def test_snapshot_preserves_sequence_through_highest_operational_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps({
                "version": 2,
                "default_etb_capacity": 400,
                "default_location_capacity": 40,
                "locations": [{
                    "location_code": "ETB-002",
                    "status": "Active",
                    "locations": [
                        {"location_code": "B", "stored_count": 1, "capacity": 40, "status": "Active"},
                        {"location_code": "D", "stored_count": 40, "capacity": 40, "status": "Location Complete"},
                    ],
                }],
                "history": [],
            }), encoding="utf-8")
            snapshot = cloud_location_registry_snapshot(path)
        self.assertEqual([row["location_code"] for row in snapshot["locations"]], list("ABCD"))
        self.assertEqual(snapshot["locations"][-1]["location_id"], "ETB-002-D")

    def test_batch_location_bridge_uses_supabase_format_and_flexible_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            updated = record_completed_batch_location(
                "ETB-07-A",
                49,
                game="pokemon",
                source="test",
                path=path,
            )
            snapshot = cloud_location_registry_snapshot(path)

        self.assertEqual(parse_etb_location_id("ETB-07-A"), ("ETB-007", "A", "ETB-007-A"))
        self.assertEqual(updated["location_code"], "ETB-007")
        self.assertEqual(updated["stored_count"], 49)
        self.assertEqual(updated["locations"][0]["location_id"], "ETB-007-A")
        self.assertEqual(updated["locations"][0]["stored_count"], 49)
        self.assertEqual(updated["locations"][0]["status"], "Location Complete")
        self.assertEqual(snapshot["locations"][0]["location_id"], "ETB-007-A")
        self.assertEqual(snapshot["locations"][0]["stored_count"], 49)

    def test_mobile_created_location_merges_into_desktop_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps({
                "version": 2,
                "default_etb_capacity": 400,
                "default_location_capacity": 40,
                "locations": [],
                "history": [],
            }), encoding="utf-8")
            result = merge_cloud_location_registry(
                [{"etb_id": "ETB-009", "capacity": 400, "status": "Empty"}],
                [{
                    "location_id": "ETB-009-A",
                    "etb_id": "ETB-009",
                    "location_code": "A",
                    "capacity": 40,
                    "stored_count": 0,
                    "status": "Empty",
                }],
                path,
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
        child = saved["locations"][0]["locations"][0]
        self.assertTrue(result["changed"])
        self.assertEqual(child["location_id"], "ETB-009-A")
        self.assertTrue(child["cloud_provisioned"])

    def test_desktop_sync_uses_service_role_adapter_and_merges_cloud_rows(self):
        calls = []

        def fake_request(method, path, body=None, prefer=None):
            calls.append((method, path, body, prefer))
            if "cardvector_etbs?select" in path:
                return [{"etb_id": "ETB-001"}]
            if "cardvector_locations?select" in path:
                return [{"location_id": "ETB-001-A", "etb_id": "ETB-001", "location_code": "A"}]
            return None

        with (
            mock.patch.object(queue, "cloud_location_registry_snapshot", return_value={
                "etbs": [{"etb_id": "ETB-001"}],
                "locations": [{"location_id": "ETB-001-A"}],
            }),
            mock.patch.object(queue, "request_json", side_effect=fake_request),
            mock.patch.object(queue, "merge_cloud_location_registry", return_value={"changed": True}) as merge,
        ):
            result = queue.sync_cloud_location_registry()
        self.assertTrue(result["changed"])
        self.assertTrue(any("on_conflict=etb_id" in call[1] for call in calls))
        self.assertTrue(any("on_conflict=location_id" in call[1] for call in calls))
        merge.assert_called_once()

    def test_canonical_location_rows_inherit_owner_and_preserve_flexible_count(self):
        owner_id = "11111111-1111-1111-1111-111111111111"
        existing = [
            SimpleNamespace(
                id="etb-uuid",
                display_code="ETB-007",
                owner_user_id=owner_id,
            ),
            SimpleNamespace(
                id="slot-uuid",
                display_code="ETB-007-A",
                owner_user_id=owner_id,
            ),
        ]
        rows, warning = queue.canonical_location_rows_from_snapshot(
            {
                "etbs": [{"etb_id": "ETB-007", "status": "Active", "capacity": 400}],
                "locations": [{
                    "location_id": "ETB-007-A",
                    "etb_id": "ETB-007",
                    "location_code": "A",
                    "capacity": 40,
                    "stored_count": 49,
                    "status": "Location Complete",
                    "assigned_batch": "ETB-007-A",
                }],
            },
            existing,
        )
        slot = next(row for row in rows if row["display_code"] == "ETB-007-A")
        etb = next(row for row in rows if row["display_code"] == "ETB-007")
        self.assertEqual(warning, "")
        self.assertEqual(slot["id"], "slot-uuid")
        self.assertEqual(slot["owner_user_id"], owner_id)
        self.assertEqual(slot["stored_count"], 49)
        self.assertEqual(slot["status"], "location_complete")
        self.assertEqual(etb["stored_count"], 49)
        self.assertEqual(etb["status"], "active")

    def test_canonical_location_rows_update_existing_blank_owner_rows_only(self):
        existing = [
            SimpleNamespace(id="etb-uuid", display_code="ETB-007", owner_user_id=""),
            SimpleNamespace(id="slot-uuid", display_code="ETB-007-A", owner_user_id=""),
        ]
        rows, warning = queue.canonical_location_rows_from_snapshot(
            {
                "etbs": [
                    {"etb_id": "ETB-007", "status": "Active", "capacity": 400},
                    {"etb_id": "ETB-008", "status": "Active", "capacity": 400},
                ],
                "locations": [
                    {
                        "location_id": "ETB-007-A",
                        "etb_id": "ETB-007",
                        "location_code": "A",
                        "capacity": 40,
                        "stored_count": 49,
                        "status": "Location Complete",
                    },
                    {
                        "location_id": "ETB-008-A",
                        "etb_id": "ETB-008",
                        "location_code": "A",
                        "capacity": 40,
                        "stored_count": 2,
                        "status": "Location Complete",
                    },
                ],
            },
            existing,
        )

        self.assertEqual([row["display_code"] for row in rows], ["ETB-007", "ETB-007-A"])
        self.assertNotIn("owner_user_id", rows[0])
        self.assertEqual(rows[1]["stored_count"], 49)
        self.assertIn("Skipped ETB-008", warning)
        self.assertIn("Skipped ETB-008-A", warning)

    def test_canonical_location_rows_do_not_erase_existing_nonempty_slot(self):
        owner_id = "11111111-1111-1111-1111-111111111111"
        existing = [
            SimpleNamespace(
                id="etb-uuid",
                display_code="ETB-007",
                owner_user_id=owner_id,
                stored_count=49,
            ),
            SimpleNamespace(
                id="slot-uuid",
                display_code="ETB-007-A",
                owner_user_id=owner_id,
                stored_count=49,
            ),
        ]
        rows, warning = queue.canonical_location_rows_from_snapshot(
            {
                "etbs": [{"etb_id": "ETB-007", "status": "Empty", "capacity": 400}],
                "locations": [{
                    "location_id": "ETB-007-A",
                    "etb_id": "ETB-007",
                    "location_code": "A",
                    "capacity": 40,
                    "stored_count": 0,
                    "status": "Empty",
                }],
            },
            existing,
        )

        slot = next(row for row in rows if row["display_code"] == "ETB-007-A")
        etb = next(row for row in rows if row["display_code"] == "ETB-007")
        self.assertEqual(slot["stored_count"], 49)
        self.assertEqual(slot["metadata"]["inventory_count_source"], "existing_canonical")
        self.assertEqual(etb["stored_count"], 49)
        self.assertEqual(etb["status"], "active")
        self.assertIn("Preserved ETB-007-A", warning)

    def test_canonical_location_rows_roll_up_existing_slot_not_in_snapshot(self):
        owner_id = "11111111-1111-1111-1111-111111111111"
        existing = [
            SimpleNamespace(
                id="etb-uuid",
                display_code="ETB-007",
                owner_user_id=owner_id,
                stored_count=0,
            ),
            SimpleNamespace(
                id="slot-uuid",
                display_code="ETB-007-A",
                owner_user_id=owner_id,
                stored_count=49,
            ),
        ]
        rows, warning = queue.canonical_location_rows_from_snapshot(
            {
                "etbs": [{"etb_id": "ETB-007", "status": "Empty", "capacity": 400}],
                "locations": [],
            },
            existing,
        )

        self.assertEqual(warning, "")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["display_code"], "ETB-007")
        self.assertEqual(rows[0]["stored_count"], 49)
        self.assertEqual(rows[0]["status"], "active")

    def test_unapplied_location_migration_does_not_break_capture_queue_listing(self):
        service = queue.MobileCaptureQueueService(current_workstation="TEST-PC")
        with (
            mock.patch.object(queue, "sync_cloud_location_registry", side_effect=queue.MobileCaptureError("table missing")),
            mock.patch.object(queue, "list_sessions", return_value=[]),
        ):
            self.assertEqual(service.list_queue(), [])
        self.assertIn("table missing", service.last_location_sync_warning)


if __name__ == "__main__":
    unittest.main()
