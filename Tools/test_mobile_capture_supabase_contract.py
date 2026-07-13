from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260713153000_mobile_capture.sql"
PUBLIC_CONFIG = ROOT / "Docs" / "mobile-capture-config.js"


class MobileCaptureSupabaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.config = PUBLIC_CONFIG.read_text(encoding="utf-8")

    def test_migration_defines_required_tables(self):
        self.assertIn("create table if not exists public.mobile_capture_sessions", self.sql)
        self.assertIn("create table if not exists public.mobile_capture_images", self.sql)

    def test_migration_supports_required_session_fields_and_aliases(self):
        for field in (
            "capture_session_id",
            "etb_location",
            "etb_location_id",
            "source",
            "status",
            "operator_id",
            "source_device",
            "image_count",
            "conversion_status",
            "conversion_workstation",
            "schema_version",
        ):
            self.assertIn(field, self.sql)

    def test_migration_supports_required_statuses(self):
        for status in ("DRAFT", "UPLOADING", "PENDING_CONVERSION", "PROCESSING", "CONVERTED", "FAILED", "CANCELLED"):
            self.assertIn(status, self.sql)

    def test_migration_defines_private_bucket_and_storage_policies(self):
        self.assertIn("mobile-capture-originals", self.sql)
        self.assertIn("public = false", self.sql)
        self.assertIn("operators upload mobile originals", self.sql)
        self.assertIn("operators read mobile originals", self.sql)

    def test_migration_enables_rls_and_operator_policies(self):
        self.assertIn("enable row level security", self.sql)
        self.assertIn("operators insert own mobile capture sessions", self.sql)
        self.assertIn("operators update own draft mobile capture sessions", self.sql)

    def test_public_config_has_no_private_secret_names(self):
        forbidden = (
            "SERVICE_ROLE",
            "CARDVECTOR_SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_SERVICE_ROLE_KEY",
            "DATABASE_PASSWORD",
            "GITHUB_TOKEN",
        )
        for token in forbidden:
            self.assertNotIn(token, self.config)


if __name__ == "__main__":
    unittest.main()
