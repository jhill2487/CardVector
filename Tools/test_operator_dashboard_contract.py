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
        header = self.index_html[
            self.index_html.index('<header class="site-header"'):
            self.index_html.index("</header>")
        ]
        footer = self.index_html[
            self.index_html.index('<footer class="footer"'):
            self.index_html.index("</footer>")
        ]
        self.assertNotIn('href="/operator"', header)
        self.assertNotIn('href="/#mobile-capture"', header)
        self.assertIn('class="footer-admin"', footer)
        self.assertIn('href="/operator"', footer)
        self.assertIn('href="/#mobile-capture"', footer)

    def test_operator_routes_are_static_export_clients(self):
        for route in ('"operator"', '"registry"', '"mobile-capture"', '"batches"', '"batch-workflow"', '"listings"', '"listing-reconciliation"', '"repricing"', '"price-review"'):
            self.assertIn(route, self.exporter)
        self.assertIn('route === "operator"', self.app_js)
        self.assertIn('route === "registry"', self.app_js)
        self.assertIn('route === "batches"', self.app_js)
        self.assertIn('route === "listings"', self.app_js)
        self.assertIn('route === "repricing"', self.app_js)
        self.assertIn("renderOperatorDashboard", self.app_js)
        self.assertIn("renderOperatorRegistry", self.app_js)
        self.assertIn("renderOperatorBatchWorkflow", self.app_js)
        self.assertIn("renderOperatorListingReconciliation", self.app_js)
        self.assertIn("renderOperatorRepricingReview", self.app_js)

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
        self.assertIn("Batch References", self.app_js)
        self.assertIn("CardUploader batch-history links", self.app_js)
        self.assertIn("safeCardUploaderBatchHistoryUrl", self.app_js)
        self.assertIn("batchHasCardUploaderHistoryEvidence", self.app_js)
        self.assertIn("safeCardUploaderUrl", self.app_js)
        self.assertIn("shortBatchId", self.app_js)
        self.assertIn("CardUploader ID:", self.app_js)
        self.assertIn("Batches by ETB Slot", self.app_js)
        self.assertIn("Grouped from CardUploader history records only", self.app_js)
        self.assertIn("CardUploader Batch History", self.app_js)
        self.assertIn("ETB-001-A.2", self.app_js)
        self.assertIn('"cardvector_location_carduploader_batches_v"', self.app_js)

    def test_operator_dashboard_hides_retired_registry_and_listing_review_cards(self):
        dashboard_source = self.app_js[
            self.app_js.index("function renderOperatorDashboard"):
            self.app_js.index("function registryWarningHtml")
        ]
        self.assertNotIn('href="/operator/registry"', dashboard_source)
        self.assertNotIn("ETB / Location Registry", dashboard_source)
        self.assertNotIn('href="/operator/listings"', dashboard_source)
        self.assertNotIn("Existing Listing Review", dashboard_source)
        self.assertIn('href="/#mobile-capture"', dashboard_source)
        self.assertIn('href="/operator/batches"', dashboard_source)
        self.assertIn('href="/operator/repricing"', dashboard_source)

    def test_existing_listing_reconciliation_is_csv_snapshot_only(self):
        self.assertIn("Existing Listing Review", self.app_js)
        self.assertIn("parseEbayListingsCsv", self.app_js)
        self.assertIn("parseMarketplaceListingsCsv", self.app_js)
        self.assertIn("parseCardUploaderInventoryCsv", self.app_js)
        self.assertIn("cardvector_marketplace_listing_snapshots", self.app_js)
        self.assertIn("cardvector_inventory_listing_matches", self.app_js)
        self.assertIn("cardvector_marketplace_allocation_ledger_v", self.app_js)
        self.assertIn("cardvector_ebay_listing_reconciliation_v", self.app_js)
        self.assertIn(
            "This page does not update CardUploader inventory or revise, end, publish, sync, or otherwise change live marketplace listings.",
            self.app_js,
        )
        listing_source = self.app_js[
            self.app_js.index("const ebayListingColumns"):
            self.app_js.index("function renderOperatorRegistryView")
        ]
        self.assertNotIn("revise_listing", listing_source)
        self.assertNotIn("publish_listing", listing_source)
        self.assertNotIn("end_listing", listing_source)
        self.assertNotIn("sync_to_tcgplayer", listing_source)
        self.assertIn('"owner_user_id,marketplace,marketplace_listing_id"', listing_source)

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
            self.app_js.index("function renderOperatorDashboard")
        ]
        self.assertNotRegex(operator_source, r"\.(insert|upsert|update|delete)\(")
        self.assertNotIn("service_role", operator_source.lower())

    def test_operator_supabase_reads_are_egress_capped_and_cached(self):
        self.assertIn("const egressSafeMode = true", self.app_js)
        self.assertIn("egressSafeCacheMs = 5 * 60 * 1000", self.app_js)
        self.assertIn("registrySessions: 25", self.app_js)
        self.assertIn("listingSnapshots: 1200", self.app_js)
        self.assertIn("allocationLedger: 1200", self.app_js)
        self.assertIn("readEgressCache(\"operatorRegistry\", user)", self.app_js)
        self.assertIn("writeEgressCache(\"operatorRegistry\", user, data)", self.app_js)
        self.assertIn("Refresh from Supabase", self.app_js)
        self.assertIn("Egress saver: registry data is metadata-only", self.app_js)
        self.assertIn("captureMaxEdge: 1400", self.app_js)
        self.assertIn("captureJpegQuality: 0.82", self.app_js)

    def test_operator_layout_has_mobile_constraints(self):
        for selector in (
            ".operator-grid",
            ".registry-layout",
            ".registry-summary",
            ".registry-slot-grid",
            ".batch-reference-row",
            ".batch-location-grid",
            ".batch-pill",
            ".operator-main-panel",
            ".batch-technical-id",
            ".listing-file-drop",
            ".listing-reconciliation-row",
            ".repricing-row",
            ".repricing-command-bar",
        ):
            self.assertIn(selector, self.style_css)
        mobile_block = re.search(r"@media \(max-width: 720px\) \{(.*)\n\}", self.style_css, re.S)
        self.assertIsNotNone(mobile_block)
        self.assertIn(".operator-grid", mobile_block.group(1))
        self.assertIn("grid-template-columns: 1fr", mobile_block.group(1))


if __name__ == "__main__":
    unittest.main()
