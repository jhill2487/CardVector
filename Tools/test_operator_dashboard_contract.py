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
        for route in ('"operator"', '"registry"', '"mobile-capture"'):
            self.assertIn(route, self.exporter)
        self.assertIn('route === "operator"', self.app_js)
        self.assertIn('route === "registry"', self.app_js)
        self.assertIn("renderOperatorDashboard", self.app_js)
        self.assertIn("renderOperatorRegistry", self.app_js)

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
        ):
            self.assertIn(selector, self.style_css)
        mobile_block = re.search(r"@media \(max-width: 720px\) \{(.*)\n\}", self.style_css, re.S)
        self.assertIsNotNone(mobile_block)
        self.assertIn(".operator-grid", mobile_block.group(1))
        self.assertIn("grid-template-columns: 1fr", mobile_block.group(1))


if __name__ == "__main__":
    unittest.main()
