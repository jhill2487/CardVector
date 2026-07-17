from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260713153000_mobile_capture.sql"
GRANTS_MIGRATION = ROOT / "supabase" / "migrations" / "20260713170000_mobile_capture_authenticated_grants.sql"
CAPTURE_TYPE_MIGRATION = ROOT / "supabase" / "migrations" / "20260716090000_mobile_capture_type.sql"
PUBLIC_CONFIG = ROOT / "Docs" / "mobile-capture-config.js"
APP_JS = ROOT / "Docs" / "app.js"


class MobileCaptureSupabaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.grants_sql = GRANTS_MIGRATION.read_text(encoding="utf-8")
        cls.capture_type_sql = CAPTURE_TYPE_MIGRATION.read_text(encoding="utf-8")
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

    def test_capture_type_migration_defines_two_workflows_and_backcompat(self):
        self.assertIn("add column if not exists capture_type", self.capture_type_sql)
        self.assertIn("default 'PHYSICAL_INVENTORY'", self.capture_type_sql)
        self.assertIn("'NEW_CAPTURE'", self.capture_type_sql)
        self.assertIn("'PHYSICAL_INVENTORY'", self.capture_type_sql)
        self.assertIn("mobile_capture_sessions_capture_type_chk", self.capture_type_sql)

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

    def test_authenticated_table_grants_support_rls_policies(self):
        self.assertIn("grant usage on schema public to authenticated", self.grants_sql)
        self.assertIn("grant select, insert, update", self.grants_sql)
        self.assertIn("on table public.mobile_capture_sessions", self.grants_sql)
        self.assertIn("on table public.mobile_capture_images", self.grants_sql)
        self.assertNotIn(" to anon", self.grants_sql)
        self.assertNotIn("grant delete", self.grants_sql)

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
            "source_device: sourceDevice",
            "capture_type: normalizeCaptureType(session.capture_type)",
            'status: "UPLOADING"',
            'source: "MOBILE_WEB"',
            'conversion_status: "UPLOADING"',
        ):
            self.assertIn(field, self.app_js)

    def test_frontend_stores_capture_layout_in_existing_private_device_metadata(self):
        for field in (
            "captureLayoutConfig",
            "FRONT_ONLY",
            "FRONT_BACK",
            "capture_layout: normalizedLayout",
            "capture_layout: captureLayout",
            "source_device: sourceDevice",
            "Choose Photo Mode",
            "captureLayoutIsComplete",
        ):
            self.assertIn(field, self.app_js)

    def test_frontend_capture_layout_applies_to_both_capture_types(self):
        self.assertIn("Object.entries(captureLayoutConfig)", self.app_js)
        self.assertIn("captureRoute(etbId, location, captureType, layout)", self.app_js)
        self.assertIn("initializeCapture(etbId, location, captureType, captureLayout)", self.app_js)
        self.assertIn("capturePositionForOrder", self.app_js)
        self.assertIn("Card ${position.cardNumber} ${position.side", self.app_js)

    def test_frontend_records_image_order_and_upload_status(self):
        self.assertIn("image_order: index + 1", self.app_js)
        self.assertIn('upload_status: "UPLOADED"', self.app_js)

    def test_frontend_reports_sanitized_supabase_errors(self):
        self.assertIn("supabaseErrorDetails", self.app_js)
        self.assertIn("storageErrorDetails", self.app_js)
        self.assertIn("sanitizeErrorMessage", self.app_js)
        self.assertIn("Create capture session", self.app_js)
        self.assertIn("Upload original image", self.app_js)
        self.assertIn("Record uploaded image", self.app_js)
        self.assertIn("Submit capture session", self.app_js)

    def test_frontend_shows_signed_in_operator_indicator(self):
        self.assertIn("capture-operator", self.app_js)
        self.assertIn("authStateLabel", self.app_js)

    def test_frontend_storage_upload_uses_user_bearer_token(self):
        self.assertIn("uploadOriginalImage", self.app_js)
        self.assertIn("Authorization: `Bearer ${session.access_token}`", self.app_js)
        self.assertIn("apikey: cfg.supabaseAnonKey", self.app_js)
        self.assertIn("authTokenStateLabel", self.app_js)
        self.assertIn("user bearer token missing", self.app_js)

    def test_frontend_storage_path_and_file_validation(self):
        self.assertIn("storageObjectUrl", self.app_js)
        self.assertIn("validateUploadImage", self.app_js)
        self.assertIn("image.file instanceof Blob", self.app_js)
        self.assertIn('startsWith("image/")', self.app_js)
        self.assertIn("startsWith(`${user.id}/`)", self.app_js)

    def test_frontend_uses_explicit_capture_type_and_camera_screen(self):
        self.assertIn("captureTypeConfig", self.app_js)
        self.assertIn("New Inventory Capture", self.app_js)
        self.assertIn("Physical Inventory Conversion", self.app_js)
        self.assertIn("navigator.mediaDevices.getUserMedia", self.app_js)
        self.assertIn("captureStillFromVideo", self.app_js)
        self.assertIn("Finish Session", self.app_js)
        self.assertIn("Choose from Photo Library", self.app_js)

    def test_live_camera_capture_matches_centered_cover_preview(self):
        for contract in (
            "calculateCoverCrop",
            "video.videoWidth",
            "video.videoHeight",
            "video.getBoundingClientRect()",
            "crop.sourceX",
            "crop.sourceY",
            "crop.sourceWidth",
            "crop.sourceHeight",
            '"image/jpeg", 0.9',
            '"LIVE_CAMERA"',
            '"PHOTO_LIBRARY"',
        ):
            self.assertIn(contract, self.app_js)

        self.assertNotIn("context.drawImage(video, 0, 0, canvas.width, canvas.height)", self.app_js)


if __name__ == "__main__":
    unittest.main()
