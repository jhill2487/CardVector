import importlib.util
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "Docs"
APP_PATH = DOCS / "app.js"
EXPORTER_PATH = ROOT / "Tools" / "export_cardvector_site.py"
EXPECTED_URLS = {
    "EBAY_STORE_URL": "https://www.ebay.com/str/jhilltcg?mkcid=1&mkrid=711-53200-19255-0&siteid=0&campid=5339178316&customid=&toolid=10001&mkevt=1",
    "TCGPLAYER_STORE_URL": "https://www.tcgplayer.com/sellers/Putnam-Collectibles/747c057d",
    "WHATNOT_REFERRAL_URL": "https://whatnot.com/invite/putnam_collectibles",
    "WHATNOT_SELLER_REFERRAL_URL": "https://whatnot.com/invite/seller/putnam_collectibles",
    "COLLECTION_INQUIRY_URL": "https://tally.so/r/ob1ABN",
}


def load_exporter():
    spec = importlib.util.spec_from_file_location("cardvector_site_exporter", EXPORTER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.anchors.append(dict(attrs))


class PublicStorefrontContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((DOCS / "site-config.json").read_text(encoding="utf-8"))
        cls.source_html = (DOCS / "index.html").read_text(encoding="utf-8-sig")
        cls.source_js = (DOCS / "app.js").read_text(encoding="utf-8-sig")
        cls.source_css = (DOCS / "style.css").read_text(encoding="utf-8-sig")
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp_dir.name) / "public-site"
        load_exporter().export_site(DOCS, cls.output, "storefront-test")
        cls.output_html = (cls.output / "index.html").read_text(encoding="utf-8")
        cls.output_404 = (cls.output / "404.html").read_text(encoding="utf-8")
        cls.output_js = (cls.output / "app.js").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_marketplace_configuration_is_complete(self):
        self.assertEqual(EXPECTED_URLS, self.config)
        self.assertNotIn("PASTE_", json.dumps(self.config))

    def test_navigation_labels_are_in_required_order(self):
        nav = re.search(r'<ul class="nav-links"[^>]*>(.*?)</ul>', self.source_html, re.S)
        self.assertIsNotNone(nav)
        labels = [
            "Shop eBay",
            "Shop TCGplayer",
            "Sell Your Collection",
            "Whatnot",
            "About",
            "Contact",
            "Mobile Capture",
        ]
        positions = [nav.group(1).index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('href="/#mobile-capture"', nav.group(1))

    def test_sell_and_bulk_routes_share_one_destination(self):
        self.assertIn('new Set(["sell", "bulk", "buylist"])', self.source_js)
        self.assertIn("renderSellCollectionPage", self.source_js)
        self.assertNotIn('new Set(["buylist", "bulk", "events", "about"])', self.source_js)
        for route_id in ('id="sell"', 'id="bulk"', 'id="buylist"'):
            self.assertIn(route_id, self.source_html)

    def test_whatnot_copy_is_clear_and_non_guaranteed(self):
        self.assertIn("Whatnot Referral Bonuses", self.source_html)
        self.assertIn("New to Whatnot?", self.source_html)
        self.assertIn("Interested in Selling?", self.source_html)
        self.assertIn("any available new-user promotional credit", self.source_html)
        self.assertIn("any available new-seller promotional bonus", self.source_html)
        self.assertIn("credit eligibility are determined by Whatnot and may change", self.source_html)
        self.assertNotRegex(self.source_html, r"\$\d+[^<]*Whatnot")

    def test_marketplace_affiliate_disclosure_is_present(self):
        disclosure = "Some marketplace links may be affiliate links."
        self.assertIn(disclosure, self.source_html)
        self.assertIn(disclosure, self.output_html)
        self.assertIn(disclosure, self.output_404)

    def test_export_resolves_configuration_and_keeps_links_safe(self):
        for text in (self.output_html, self.output_404, self.output_js):
            self.assertNotRegex(text, r"\{\{[A-Z0-9_]+\}\}")
        for url in EXPECTED_URLS.values():
            self.assertIn(url, self.output_html)

        parser = AnchorParser()
        parser.feed(self.output_html)
        external = [anchor for anchor in parser.anchors if anchor.get("href", "").startswith("https://")]
        self.assertTrue(external)
        for anchor in external:
            self.assertEqual("_blank", anchor.get("target"), anchor)
            rel = set(anchor.get("rel", "").split())
            self.assertTrue({"noopener", "noreferrer"}.issubset(rel), anchor)

    def test_mobile_navigation_contract_avoids_horizontal_scroller(self):
        self.assertIn("@media (max-width: 900px)", self.source_css)
        self.assertIn(".nav-menu[open] > .nav-links", self.source_css)
        self.assertNotIn("overflow-x: auto", self.source_css)
        self.assertIn("min-height: 44px", self.source_css)
        self.assertIn('"mobile-capture"', EXPORTER_PATH.read_text(encoding="utf-8"))
        self.assertIn('"mobile"', EXPORTER_PATH.read_text(encoding="utf-8"))
        self.assertIn("mobileHashRoutes", APP_PATH.read_text(encoding="utf-8"))

    def test_public_export_contains_no_private_credentials(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in self.output.rglob("*")
            if path.is_file()
        )
        prohibited = (
            "service_role",
            "SUPABASE_SERVICE_ROLE_KEY",
            "CARDVECTOR_SITE_DEPLOY_TOKEN",
            "C:\\Users\\user\\OneDrive\\PutnamCollectibles",
        )
        for value in prohibited:
            self.assertNotIn(value, combined)


if __name__ == "__main__":
    unittest.main()
