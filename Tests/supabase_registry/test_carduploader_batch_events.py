from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Platform.cardvector.integrations.supabase.registry import (
    CANONICAL_CARDUPLOADER_BATCH_EVENTS_TABLE,
    CanonicalCardUploaderBatchEvent,
    SupabaseRegistryClient,
    canonical_registry_uuid,
)
from Tools import backfill_carduploader_batch_events as backfill


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260730120000_carduploader_batch_events.sql"


class CardUploaderBatchEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8")

    def test_migration_declares_batch_event_table_with_rls(self):
        self.assertIn(
            f"create table if not exists public.{CANONICAL_CARDUPLOADER_BATCH_EVENTS_TABLE}",
            self.sql,
        )
        self.assertIn(
            f"alter table public.{CANONICAL_CARDUPLOADER_BATCH_EVENTS_TABLE} enable row level security",
            self.sql,
        )
        self.assertIn(
            f"revoke all on table public.{CANONICAL_CARDUPLOADER_BATCH_EVENTS_TABLE} from anon",
            self.sql,
        )
        self.assertIn("location_id uuid references public.cardvector_storage_locations", self.sql)
        self.assertIn("cardvector_carduploader_batch_events_batch_id_idx", self.sql)

    def test_batch_event_contract_serializes_expected_fields(self):
        event = CanonicalCardUploaderBatchEvent(
            id=canonical_registry_uuid("carduploader_batch_event", "batch-1"),
            carduploader_batch_id="batch-1",
            carduploader_batch_url="https://carduploader.com/dashboard/history/ungraded/batch-1",
            location_display_code="ETB-002-F",
            event_type="refill",
            card_count=47,
            total_value=98.56,
            metadata={"source": "test"},
        )
        row = event.to_row()
        self.assertEqual(row["carduploader_batch_id"], "batch-1")
        self.assertEqual(row["location_display_code"], "ETB-002-F")
        self.assertEqual(row["event_type"], "refill")
        self.assertNotIn("owner_user_id", row)
        restored = CanonicalCardUploaderBatchEvent.from_row(row)
        self.assertEqual(restored.total_value, 98.56)

    def test_client_upserts_batch_events_to_canonical_table(self):
        class RecordingClient(SupabaseRegistryClient):
            def __init__(self):
                super().__init__("https://example.supabase.co", "service-role-key")
                self.path = ""
                self.body = None

            def request_json(self, method, path, body=None, *, prefer=None):
                self.path = path
                self.body = body
                return []

        client = RecordingClient()
        client.upsert_carduploader_batch_events(
            [
                {
                    "id": "event-1",
                    "carduploader_batch_id": "batch-1",
                    "carduploader_batch_url": "https://carduploader.com/dashboard/history/ungraded/batch-1",
                }
            ]
        )
        self.assertIn(CANONICAL_CARDUPLOADER_BATCH_EVENTS_TABLE, client.path)
        self.assertEqual(client.body[0]["carduploader_batch_id"], "batch-1")

    def test_multiple_batches_for_same_slot_are_event_history_not_conflicts(self):
        rows = [
            _row("1", "2026-07-10", "ETB-002-F", count=40),
            _row("2", "2026-07-20", "ETB-002-F", count=47),
        ]
        plan = backfill.build_plan(rows, _registry("ETB-002", {"F": 12}))
        events = [item for item in plan["items"] if item["location_display_code"] == "ETB-002-F"]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_type"], "initial_fill")
        self.assertEqual(events[1]["event_type"], "refill")
        self.assertEqual(plan["counts"]["location_event"], 2)

    def test_broad_etb_label_requires_physical_conversion_review(self):
        rows = [
            backfill.CardUploaderBatchHistoryRow.from_mapping(
                {
                    "sequence": 1,
                    "batch_id": "batch-003",
                    "url": "https://carduploader.com/dashboard/history/ungraded/batch-003",
                    "label": "Ungraded - English Pokemon ETB-003 - Pokemon English",
                    "card_count": "7",
                    "date": "7/12/2026",
                }
            )
        ]
        plan = backfill.build_plan(rows, _registry("ETB-003", {}))
        self.assertEqual(plan["items"][0]["classification"], "needs_physical_conversion")
        self.assertEqual(plan["items"][0]["event_type"], "unassigned")
        self.assertEqual(plan["supabase_rows"], [])

    def test_local_apply_preserves_stored_count_and_adds_batch_history(self):
        registry = _registry("ETB-002", {"F": 12})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "etb_location_registry.json"
            path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
            plan = backfill.build_plan(
                [
                    _row("1", "2026-07-10", "ETB-002-F", count=40),
                    _row("2", "2026-07-20", "ETB-002-F", count=47),
                ],
                registry,
            )
            result = backfill.apply_to_local_registry(plan, path)
            updated = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(Path(result["backup_path"]).exists())
        slot = next(
            item
            for item in updated["locations"][0]["locations"]
            if item["location_code"] == "F"
        )
        self.assertEqual(slot["stored_count"], 12)
        self.assertEqual(slot["carduploader_batch_count"], 2)
        self.assertEqual(slot["carduploader_batch_id"], "batch-2")


def _row(batch_suffix: str, date: str, location: str, *, count: int) -> backfill.CardUploaderBatchHistoryRow:
    return backfill.CardUploaderBatchHistoryRow.from_mapping(
        {
            "sequence": int(batch_suffix),
            "batch_id": f"batch-{batch_suffix}",
            "url": f"https://carduploader.com/dashboard/history/ungraded/batch-{batch_suffix}",
            "label": f"Ungraded - English Pokemon {location} - Pokemon English",
            "etb_location": location,
            "card_count": str(count),
            "total_value": "1.00",
            "date": date,
        }
    )


def _registry(etb_id: str, slots: dict[str, int]) -> dict:
    children = []
    for code, count in slots.items():
        children.append(
            {
                "location_code": code,
                "location_id": f"{etb_id}-{code}",
                "capacity": 40,
                "stored_count": count,
                "remaining_capacity": max(0, 40 - count),
                "status": "Location Complete" if count else "Empty",
            }
        )
    return {
        "updated_at": "2026-07-30T12:00:00",
        "default_capacity": 400,
        "locations": [
            {
                "location_code": etb_id,
                "status": "Active",
                "total_capacity": 400,
                "locations": children,
            }
        ],
        "history": [],
    }


if __name__ == "__main__":
    unittest.main()
