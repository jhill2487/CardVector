import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_import_with_diagnostics as diag

class FakeStore:
    def __init__(self):self.rows=[]
    def upsert(self,table,rows):
        assert table=="cv_admin_import_run_diagnostics"
        self.rows.extend(rows)

class Tests(unittest.TestCase):
    def test_start_failure_and_success_are_recorded(self):
        store=FakeStore()
        diag.report(store,"123","targeted_paldean_fates","started")
        diag.report(store,"123","targeted_paldean_fates","failed",
                    error_class="RuntimeError",error_message="Provider total mismatch")
        diag.report(store,"124","daily","completed")
        self.assertEqual([r["status"] for r in store.rows],["started","failed","completed"])
        self.assertEqual(store.rows[1]["error_class"],"RuntimeError")
        self.assertIn("finished_at",store.rows[1])
        self.assertNotIn("finished_at",store.rows[0])
    def test_message_does_not_persist_secret_token(self):
        store=FakeStore()
        diag.report(store,"123","daily","failed",error_message="Bearer abc123")
        self.assertNotIn("abc123",store.rows[0]["error_message"])
    def test_no_unexpected_credentials_or_provider_queries_in_reporting(self):
        store=FakeStore()
        diag.report(store,"123","manual_topup","completed",imported_count=0)
        self.assertEqual(store.rows[0]["run_kind"],"manual_topup")

if __name__=="__main__":unittest.main()
