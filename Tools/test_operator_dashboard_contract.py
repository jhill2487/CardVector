import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "Docs"


class OperatorDashboardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_html = (DOCS / "index.html").read_text(encoding="utf-8-sig")
        cls.app_js = (DOCS / "app.js").read_text(encoding="utf-8-sig")
        cls.style_css = (DOCS / "style.css").read_text(encoding="utf-8-sig")
        cls.exporter = (ROOT / "Tools" / "export_cardvector_site.py").read_text(encoding="utf-8-sig")

    def test_operator_navigation_is_present(self):
        self.assertIn('href="/operator"', self.index_html)
        self.assertIn("Open CardVector Operator Dashboard", self.index_html)
        self.assertIn('href="/#mobile-capture"', self.index_html)

    def test_operator_routes_are_static_export_clients(self):
        for route in ('"operator"', '"registry"', '"mobile-capture"', '"batches"', '"batch-workflow"'):
            self.assertIn(route, self.exporter)
        self.assertIn('route === "operator"', self.app_js)
        self.assertIn('route === "registry"', self.app_js)
        self.assertIn('route === "batches"', self.app_js)
        self.assertIn("renderOperatorDashboard", self.app_js)
        self.assertIn("renderOperatorRegistry", self.app_js)
        self.assertIn("renderOperatorBatchWorkflow", self.app_js)

    def test_operator_registry_reads_canonical_supabase_tables(self):
        expected_tables = (
            '"cardvector_storage_locations"',
            '"cardvector_capture_sessions"',
            '"cardvector_location_carduploader_batches_v"',
            '"cardvector_location_operators"',
        )
        for table in expected_tables:
            self.assertIn(table, self.app_js)
        self.assertIn("CardUploader batch-event view is pending migration", self.app_js)

    def test_batch_workflow_is_active_and_supabase_backed(self):
        self.assertIn('href="/operator/batches"', self.app_js)
        self.assertIn("CardUploader Batch References", self.app_js)
        self.assertIn("capture-session handoff state", self.app_js)
        self.assertIn("safeCardUploaderUrl", self.app_js)
        self.assertIn('"cardvector_location_carduploader_batches_v"', self.app_js)

    def test_schema_cache_missing_table_errors_are_optional(self):
        helper = self.app_js[
            self.app_js.index("function isMissingCanonicalRegistry"):
            self.app_js.index("function canonicalStatusFromLegacy")
        ]
        self.assertIn("could not find", helper)
        self.assertIn("schema cache", helper)

    def test_operator_registry_is_read_only(self):
        operator_source = self.app_js[
            self.app_js.index("async function loadOperatorRegistry"):
            self.app_js.index("async function createCloudNextLocation")
        ]
        self.assertNotRegex(operator_source, r"\.(insert|upsert|update|delete)\(")
        self.assertNotIn("service_role", operator_source.lower())

    def test_operator_layout_has_mobile_constraints(self):
        for selector in (
            ".operator-grid",
            ".registry-layout",
            ".registry-summary",
            ".registry-slot-grid",
            ".batch-reference-row",
            ".operator-main-panel",
        ):
            self.assertIn(selector, self.style_css)
        mobile_block = re.search(r"@media \(max-width: 720px\) \{(.*)\n\}", self.style_css, re.S)
        self.assertIsNotNone(mobile_block)
        self.assertIn(".operator-grid", mobile_block.group(1))
        self.assertIn("grid-template-columns: 1fr", mobile_block.group(1))


if __name__ == "__main__":
    unittest.main()
