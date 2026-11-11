import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("publisher",Path(__file__).resolve().parents[1]/"publish_import_progress.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
class PublisherTests(unittest.TestCase):
 def test_checkpoint_and_reconciliation_fields(self):
  state={"sets":[{"name":"one"},{"name":"two"}],"next_set":1,"cards":[{},{}],"finished":False}
  record=mod.make_record(state)
  self.assertEqual(record["sets_total"],2)
  self.assertEqual(record["sets_complete"],1)
  self.assertEqual(record["status"],"importing")
  self.assertIsNone(record["images_matched"])
  report=mod.make_record(state,{"matched":1,"needs_review":2,"missing":3})
  self.assertEqual((report["images_matched"],report["images_review"],report["images_missing"]),(1,2,3))
 def test_cannot_claim_more_sets_than_exist(self):
  with self.assertRaises(ValueError):
   mod.make_record({"sets":[{}],"next_set":2})
if __name__=="__main__": unittest.main()
