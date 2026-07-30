import re
import unittest
from pathlib import Path


SOURCE_PATH = Path(__file__).with_name("putnam_os.py")
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")


def method_source(name, next_name):
    pattern = rf"^    def {re.escape(name)}\(.*?(?=^    def {re.escape(next_name)}\()"
    match = re.search(pattern, SOURCE, flags=re.MULTILINE | re.DOTALL)
    if not match:
        raise AssertionError(f"Could not find method block: {name}")
    return match.group(0)


class DesktopWorkflowUIContractTests(unittest.TestCase):
    def test_primary_navigation_is_simplified(self):
        shell = method_source("build_ui", "clear")
        self.assertIn('["Home", "Capture", "Processing", "Marketplace", "Orders"]', shell)
        self.assertIn('["Settings"]', shell)
        for old_primary in ('["Capture", "Capture Queue", "Import", "Pricing"]', '["Inventory", "Orders", "Shipping"]'):
            self.assertNotIn(old_primary, shell)

    def test_home_contains_only_actionable_section_titles(self):
        home = method_source("home_page", "capture_queue_page")
        for title in ("PENDING WORK", "ACTIVE LISTINGS"):
            self.assertIn(title, home)
        for removed in (
            "BUSINESS ALERTS",
            "TODAY'S MISSION",
            "CURRENT ACQUISITION",
            "WORKFLOW PROGRESS",
            "DECISION ENGINE",
            "RECENT ACTIVITY",
            "CONTENT SNAPSHOT",
            "VERIFIED INVENTORY REVIEW",
        ):
            self.assertNotIn(removed, home)
        self.assertNotIn("list_queue(", home)
        self.assertIn("refresh_workflow_jobs_background()", home)

    def test_processing_owns_import_pricing_and_idle_progress_is_hidden(self):
        processing = method_source("processing_page", "import_page")
        self.assertIn("CARDUPLOADER CSV", processing)
        self.assertIn("PRICING REVIEW", processing)
        self.assertIn("EBAY HANDOFF", processing)
        self.assertIn("self.pricing_progress_card.pack_forget()", processing)
        self.assertNotIn("ACQUISITION", processing)

    def test_capture_queue_remains_automatic(self):
        zero_touch = method_source("capture_queue_zero_touch_tick", "capture_queue_zero_touch_finished")
        self.assertIn("process_next_pending()", zero_touch)
        self.assertIn("threading.Thread", zero_touch)

    def test_handoff_urls_and_no_service_role_secret_in_ui(self):
        self.assertIn("https://carduploader.com/dashboard/history", SOURCE)
        self.assertIn("https://www.ebay.com/sh/ovw", SOURCE)
        settings = method_source("settings_page", "save_obs_settings_ui")
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", settings)
        self.assertNotIn("service_role", settings.lower())


if __name__ == "__main__":
    unittest.main()
