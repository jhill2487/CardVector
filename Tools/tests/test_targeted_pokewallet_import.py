import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_targeted_pokewallet_import as mod

class Store:
    headers={}
    def __init__(self): self.writes=[]; self.saved=None
    def upsert(self,table,rows):self.writes.extend(rows)
    def save(self,state):self.saved=state.copy()
    def publish(self,state):pass

def make_state():
    return {"version":2,"sets":[{"set_id":"23353","name":"SV: Paldean Fates",
                "card_count":245,"language":"eng"}],
            "next_set":31,"next_page":1,"next_offset":14,
            "daily_date":"2026-11-15","daily_imported":750,"cards_imported":3250}

def fetch(path):
    page=int(path.split("page=")[1].split("&")[0])
    start=(page-1)*100
    return {"set":{"set_id":"23353","language":"eng","total_cards":245},
            "cards":[{"id":f"pk_{n:04d}","card_info":{"name":"Card",
              "card_number":str(n),"variants":["Normal"]}}
             for n in range(start+1,min(246,start+101))]}

class Tests(unittest.TestCase):
    def test_import_245_once_and_preserve_regular_cursor(self):
        state=make_state();store=Store()
        with patch.object(mod,"api_json",return_value=[]), patch.object(mod.time,"sleep"):
            result=mod.run_targeted(state,store,fetch,now="2026-11-15")
        self.assertEqual(result["imported"],245)
        self.assertEqual(state["daily_imported"],995)
        self.assertEqual((state["next_set"],state["next_page"],state["next_offset"]),(31,1,14))
        self.assertEqual(len(store.writes),245)
        self.assertTrue(all(r["image_status"]=="pending" and r["image_path"] is None for r in store.writes))
    def test_sealed_products_are_fetched_but_not_counted_as_cards(self):
        state=make_state()
        state["sets"][0]["sealed_count"]=37
        store=Store()
        source=[
            {"id":f"pk_{n:04d}","card_info":{"name":"Card","card_number":str(n),"product_type":"card"}}
            for n in range(1,246)
        ]+[{"id":f"sealed_{n}","card_info":{"product_type":"sealed"}} for n in range(37)]
        def fetch_with_sealed(path):
            page=int(path.split("page=")[1].split("&")[0])
            return {"set":{"set_id":"23353","language":"eng","total_cards":282},
                "cards":source[(page-1)*100:page*100]}
        with patch.object(mod,"api_json",return_value=[]), patch.object(mod.time,"sleep"):
            result=mod.run_targeted(state,store,fetch_with_sealed,now="2026-11-15")
        self.assertEqual(result["imported"],245)
        self.assertEqual(len(store.writes),245)
        self.assertEqual(state["daily_imported"],995)
        self.assertEqual((state["next_set"],state["next_page"],state["next_offset"]),(31,1,14))

    def test_no_245_allowance_stops_without_fetching(self):
        state=make_state();state["daily_imported"]=800;store=Store()
        with self.assertRaisesRegex(RuntimeError,"allowance"):
            mod.run_targeted(state,store,lambda p: self.fail("should not fetch"),now="2026-11-15")
        self.assertFalse(store.writes)
    def test_existing_reviews_stop_before_any_import(self):
        state=make_state();store=Store()
        with patch.object(mod,"api_json",return_value=[{"provider_id":"old"}]):
            with self.assertRaisesRegex(RuntimeError,"overwrite"):
                mod.run_targeted(state,store,fetch,now="2026-11-15")
        self.assertFalse(store.writes)
    def test_incomplete_target_produces_no_writes(self):
        state=make_state();store=Store()
        def partial(path):
            v=fetch(path)
            if "page=3" in path:v["cards"]=v["cards"][:-1]
            return v
        with patch.object(mod,"api_json",return_value=[]),patch.object(mod.time,"sleep"):
            with self.assertRaises(RuntimeError):
                mod.run_targeted(state,store,partial,now="2026-11-15")
        self.assertFalse(store.writes)

if __name__=="__main__":unittest.main()
