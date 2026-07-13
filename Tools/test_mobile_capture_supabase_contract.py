from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260713153000_mobile_capture.sql"
PUBLIC_CONFIG = ROOT / "Docs" / "mobile-capture-config.js"
APP_JS = ROOT / "Docs" / "app.js"


class MobileCaptureSupabaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.config = PUBLIC_CONFIG.read_text(encoding="utf-8")
        cls.app_js = APP_JS.read_text(encoding="utf-8")

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

    def test_frontend_stops_before_insert_when_unauthenticated(self):
        self.assertIn("Sign in required before upload.", self.app_js)
        self.assertIn("return;", self.app_js)

    def test_frontend_session_payload_is_rls_compatible(self):
        for field in (
            "buildSessionPayload",
            "etb_location_id: session.etb_location",
            "operator_id: user ? user.id : null",
            "user_id: user ? user.id : null",
            "source_device: session.device",
            'status: "UPLOADING"',
            'source: "MOBILE_WEB"',
            'conversion_status: "UPLOADING"',
        ):
            self.assertIn(field, self.app_js)

    def test_frontend_records_image_order_and_upload_status(self):
        self.assertIn("image_order: index + 1", self.app_js)
        self.assertIn('upload_status: "UPLOADED"', self.app_js)

    def test_frontend_reports_sanitized_supabase_errors(self):
        self.assertIn("supabaseErrorDetails", self.app_js)
        self.assertIn("sanitizeErrorMessage", self.app_js)
        self.assertIn("Create capture session", self.app_js)
        self.assertIn("Record uploaded image", self.app_js)
        self.assertIn("Submit capture session", self.app_js)

    def test_frontend_shows_signed_in_operator_indicator(self):
        self.assertIn("capture-operator", self.app_js)
        self.assertIn("authStateLabel", self.app_js)


if __name__ == "__main__":
    unittest.main()
