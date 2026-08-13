from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "Docs" / "app.js"
INDEX_HTML = ROOT / "Docs" / "index.html"
NOT_FOUND_HTML = ROOT / "Docs" / "404.html"
EXPORTER = ROOT / "Tools" / "export_cardvector_site.py"


class MobileCaptureRetirementContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_js = APP_JS.read_text(encoding="utf-8-sig")
        cls.index_html = INDEX_HTML.read_text(encoding="utf-8-sig")
        cls.not_found_html = NOT_FOUND_HTML.read_text(encoding="utf-8-sig")
        cls.exporter = EXPORTER.read_text(encoding="utf-8-sig")

    def test_public_site_no_longer_publishes_mobile_capture_config(self):
        self.assertFalse((ROOT / "Docs" / "mobile-capture-config.js").exists())
        self.assertNotIn("mobile-capture-config.js", self.index_html)
        self.assertNotIn("mobile-capture-config.js", self.not_found_html)
        self.assertNotIn("mobile-capture-config.js", self.exporter)

    def test_public_navigation_no_longer_links_to_mobile_capture(self):
        self.assertNotIn('href="/#mobile-capture"', self.index_html)
        self.assertNotIn('href="/#mobile-capture"', self.not_found_html)

    def test_old_mobile_capture_routes_render_retired_workflow(self):
        route_source = self.app_js[
            self.app_js.index("function renderRetiredMobileCapturePage"):
            self.app_js.index('if (route === "lot"')
        ]
        self.assertIn("CardVector mobile capture has moved to CardUploader", route_source)
        self.assertIn("CardVector no longer stages new mobile capture sessions", route_source)
        self.assertIn('route === "mobile-capture"', route_source)
        self.assertIn('route === "mobile"', route_source)
        self.assertIn('route === "capture"', route_source)
        self.assertNotIn("initializeCapture(", route_source)
        self.assertNotIn("initializeCaptureEntry", route_source)

    def test_operator_dashboard_points_to_carduploader_not_mobile_capture(self):
        dashboard_source = self.app_js[
            self.app_js.index("function renderOperatorDashboard"):
            self.app_js.index("function registryWarningHtml")
        ]
        self.assertIn("CardUploader batch references", dashboard_source)
        self.assertIn("https://carduploader.com/dashboard/history", self.app_js)
        self.assertNotIn("Mobile Capture", dashboard_source)
        self.assertNotIn("/#mobile-capture", dashboard_source)


if __name__ == "__main__":
    unittest.main()
