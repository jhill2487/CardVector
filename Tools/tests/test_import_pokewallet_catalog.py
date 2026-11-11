import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location("pw_importer", Path(__file__).resolve().parents[1] / "import_pokewallet_catalog.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ImporterTests(unittest.TestCase):
    def test_newest_dated_sets_first(self):
        sets = [
            {"name":"Promo 2024","release_date":"","source_position":0},
            {"name":"Recent Set","release_date":"2026-09-01","source_position":1},
            {"name":"Old Set","release_date":"2022-01-01","source_position":2},
            {"name":"New Set","release_date":"2026-11-01","source_position":3},
            {"name":"Undated A","release_date":"","source_position":4}
        ]
        ordered=mod.order_sets_newest_first(sets)
        self.assertEqual([x["name"] for x in ordered],["New Set","Recent Set","Old Set","Promo 2024","Undated A"])

    def test_resumes_checkpoint_without_reordering(self):
        state=mod.initial_state()
        payloads={
            "/sets":{"data":[
                {"set_id":1,"name":"Older","release_date":"2021-01-01"},
                {"set_id":2,"name":"Newest","release_date":"2026-09-01"}
            ]},
            "/sets/2?page=1&limit=200":{"set":{"set_id":2,"total_cards":1},"cards":[
                {"id":"id-2","card_info":{"name":"Pikachu","card_number":"1"}}
            ]},
            "/sets/1?page=1&limit=200":{"set":{"set_id":1,"total_cards":1},"cards":[
                {"id":"id-1","card_info":{"name":"Raichu","card_number":"1"}}
            ]}
        }
        calls=[]
        def api(path):
            calls.append(path)
            return payloads[path]
        mod.run_batch(state,api,lambda state:None,budget=2,interval=0)
        self.assertEqual(calls,["/sets","/sets/2?page=1&limit=200"])
        self.assertEqual(state["next_set"],1)
        mod.run_batch(state,api,lambda state:None,budget=1,interval=0)
        self.assertEqual(calls[-1],"/sets/1?page=1&limit=200")
        self.assertTrue(state["finished"])

if __name__=="__main__":
    unittest.main()
