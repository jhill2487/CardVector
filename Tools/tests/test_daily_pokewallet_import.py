import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("daily",Path(__file__).resolve().parents[1]/"run_daily_pokewallet_import.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def card(n):
    return {"id":"pk_"+str(n),"card_info":{"name":"Pikachu","card_number":str(n),"product_type":"card"}}

class DailyTests(unittest.TestCase):
    def test_exactly_750_and_continue_next_day_without_skips(self):
        state=mod.make_state()
        source=[card(n) for n in range(1,801)]
        writes=[]
        def fetch(path):
            if path=="/sets":
                return {"data":[{"set_id":"30","name":"Recent","release_date":"12th November, 2026"}]}
            page=int(path.split("page=")[1].split("&")[0])
            start=(page-1)*mod.PAGE_SIZE
            return {"set":{"set_id":"30","total_cards":800},
                    "cards":source[start:start+mod.PAGE_SIZE]}
        def write(checkpoint,rows):
            writes.extend(r["provider_id"] for r in rows)
        first=mod.step(state,fetch,write,[],cap=750,max_requests=40)
        self.assertEqual(first["today"],750)
        self.assertEqual((state["next_set"],state["next_page"],state["next_offset"]),(0,8,50))
        self.assertFalse(state["finished"])
        second=mod.step(state,fetch,write,[],cap=750,max_requests=40)
        self.assertEqual(second["today"],50)
        self.assertTrue(state["finished"])
        self.assertEqual(len(set(writes)),800)
        self.assertEqual(len(writes),800)
        self.assertEqual(state["cards_imported"],800)
        third=mod.step(state,fetch,write,[],cap=750,max_requests=40)
        self.assertEqual(third["today"],0)

    def test_sealed_products_do_not_count_against_750(self):
        state=mod.make_state()
        rows=[{"id":"pack","card_info":{"product_type":"sealed"}}]+[card(n) for n in range(1,10)]
        def fetch(path):
            if path=="/sets":return {"data":[{"set_id":"1","name":"Promo","release_date":"28th March, 2025"}]}
            return {"set":{"set_id":"1","total_cards":len(rows)},"cards":rows}
        imported=[]
        result=mod.step(state,fetch,lambda s,rs:imported.extend(rs),[],cap=750,max_requests=10)
        self.assertEqual(result["today"],9)
        self.assertTrue(result["finished"])
        self.assertEqual(len(imported),9)

    def test_human_dates_newest_first(self):
        sets=mod.normalize_sets({"data":[
            {"set_id":"1","name":"Old","release_date":"28th March, 2025"},
            {"set_id":"2","name":"New","release_date":"2nd November, 2026"},
            {"set_id":"3","name":"Ancient","release_date":"4th May, 2011"}]})
        self.assertEqual([s["set_id"] for s in sets],["2","1","3"])

    def test_request_budget_resumes(self):
        state=mod.make_state()
        calls=[]
        def fetch(path):
            calls.append(path)
            if path=="/sets":return {"data":[{"set_id":"1","name":"Set"}]}
            page=int(path.split("page=")[1].split("&")[0])
            return {"set":{"set_id":"1","total_cards":400},"cards":[card(page*100+n) for n in range(100)]}
        first=mod.step(state,fetch,lambda s,rs:None,[],cap=750,max_requests=2)
        self.assertEqual(first["today"],100)
        self.assertEqual(state["next_page"],2)
        second=mod.step(state,fetch,lambda s,rs:None,[],cap=750,max_requests=5)
        self.assertEqual(second["today"],300)
        self.assertTrue(state["finished"])
        self.assertEqual(state["cards_imported"],400)

if __name__=="__main__":
    unittest.main()
