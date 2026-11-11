import importlib.util
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
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
                return {"data":[{"set_id":"30","name":"Delta Reign","release_date":"12th November, 2026"}]}
            page=int(path.split("page=")[1].split("&")[0])
            start=(page-1)*mod.PAGE_SIZE
            return {"set":{"set_id":"30","total_cards":800},
                    "cards":source[start:start+mod.PAGE_SIZE]}
        def write(checkpoint,rows):
            writes.extend(r["provider_id"] for r in rows)
        first=mod.step(state,fetch,write,cap=750,max_requests=40,day="2026-11-11")
        self.assertEqual(first["today"],750)
        self.assertEqual((state["next_set"],state["next_page"],state["next_offset"]),(0,8,50))
        self.assertFalse(state["finished"])
        same_day=mod.step(state,fetch,write,cap=750,max_requests=40,day="2026-11-11")
        self.assertEqual(same_day["today"],0)
        second=mod.step(state,fetch,write,cap=750,max_requests=40,day="2026-11-12")
        self.assertEqual(second["today"],50)
        self.assertTrue(state["finished"])
        self.assertEqual(len(set(writes)),800)
        self.assertEqual(len(writes),800)
        self.assertEqual(state["cards_imported"],800)
        third=mod.step(state,fetch,write,cap=750,max_requests=40,day="2026-11-13")
        self.assertEqual(third["today"],0)

    def test_sealed_products_do_not_count_against_750(self):
        state=mod.make_state()
        rows=[{"id":"pack","card_info":{"product_type":"sealed"}}]+[card(n) for n in range(1,10)]
        def fetch(path):
            if path=="/sets":return {"data":[{"set_id":"1","name":"Chaos Rising","release_date":"28th March, 2025"}]}
            return {"set":{"set_id":"1","total_cards":len(rows)},"cards":rows}
        imported=[]
        result=mod.step(state,fetch,lambda s,rs:imported.extend(rs),cap=750,max_requests=10)
        self.assertEqual(result["today"],9)
        self.assertTrue(result["finished"])
        self.assertEqual(len(imported),9)

    def test_provider_records_have_variants_without_image_reconciliation(self):
        state=mod.make_state()
        example={"id":"pk_heracross","card_info":{"name":"Heracross",
                 "card_number":"001/103","variants":["Normal","Reverse Holofoil"]}}
        def fetch(path):
            if path=="/sets":
                return {"data":[{"set_id":"24831","name":"Delta Reign"}]}
            return {"set":{"set_id":"24831","total_cards":1},"cards":[example]}
        saved=[]
        mod.step(state,fetch,lambda checkpoint,rows:saved.extend(rows),day="2026-11-11")
        self.assertEqual(len(saved),1)
        self.assertEqual(saved[0]["provider_id"],"pk_heracross")
        self.assertEqual(saved[0]["variants"],["Normal","Reverse Holofoil"])
        self.assertEqual(saved[0]["image_status"],"pending")
        self.assertIsNone(saved[0]["image_path"])

    def test_human_dates_newest_first(self):
        sets=mod.normalize_sets({"data":[
            {"set_id":"1","name":"Old","release_date":"28th March, 2025"},
            {"set_id":"2","name":"New","release_date":"2nd November, 2026"},
            {"set_id":"3","name":"Ancient","release_date":"4th May, 2011"}]})
        self.assertEqual([s["set_id"] for s in sets],["2","1","3"])

    def test_provider_language_and_card_counts_override_name_guessing(self):
        rows=mod.normalize_sets({"data":[
            {"set_id":"99","name":"Unknown Promo Set","language":"eng",
             "card_count":200,"number_count":199,"sealed_count":3},
            {"set_id":"98","name":"Delta Reign","language":"jap",
             "card_count":25,"sealed_count":0}]})
        indexed={row["set_id"]:row for row in rows}
        self.assertEqual(indexed["99"]["language"],"eng")
        self.assertEqual(indexed["99"]["card_count"],200)
        self.assertEqual(indexed["99"]["number_count"],199)
        self.assertEqual(indexed["98"]["language"],"jap")
        self.assertEqual(indexed["98"]["card_count"],25)

    def test_existing_checkpoint_refresh_keeps_cursor_and_no_duplicate_pages(self):
        state=mod.make_state()
        state.update({"sets":[{"set_id":"2","name":"Delta Reign"},
                              {"set_id":"1","name":"Unknown Promo Set"}],
                      "next_set":1,"next_page":2,"next_offset":40,
                      "cards_imported":140})
        calls=[]
        rows=[card(n) for n in range(101,201)]
        def fetch(path):
            calls.append(path)
            if path=="/sets":
                # Incoming order differs; never reorder existing cursor's sets.
                return {"data":[
                    {"set_id":"1","name":"Unknown Promo Set","language":"eng",
                     "card_count":200,"sealed_count":0},
                    {"set_id":"2","name":"Delta Reign","language":"jap",
                     "card_count":25,"sealed_count":0}]}
            self.assertIn("/sets/1?page=2",path)
            return {"set":{"set_id":"1","total_cards":200,"language":"eng"},
                    "cards":rows}
        persisted=[]
        outcome=mod.step(state,fetch,lambda st,data:persisted.extend(data),
                         max_requests=5,cap=60,day="2026-11-12")
        self.assertEqual(calls[0],"/sets")
        self.assertEqual(outcome["today"],60)
        self.assertEqual((state["next_set"],state["next_page"],state["next_offset"]),
                         (2,1,0))
        self.assertEqual(state["cards_imported"],200)
        self.assertEqual(len(persisted),60)
        self.assertEqual(state["sets"][0]["set_id"],"2")
        self.assertEqual(state["sets"][1]["card_count"],200)
        self.assertTrue(state["directory_enriched"])

    def test_provider_language_rejects_wrong_set_page(self):
        state=mod.make_state()
        def fetch(path):
            if path=="/sets":
                return {"data":[{"set_id":"3","name":"Provider Set",
                                 "language":"eng","card_count":1}]}
            return {"set":{"set_id":"3","total_cards":1,"language":"jap"},
                    "cards":[card(1)]}
        with self.assertRaisesRegex(RuntimeError,"language mismatch"):
            mod.step(state,fetch,lambda st,rows:None)
        self.assertEqual((state["next_set"],state["next_page"],state["next_offset"]),
                         (0,1,0))
        self.assertEqual(state["cards_imported"],0)

    def test_request_budget_resumes(self):
        state=mod.make_state()
        calls=[]
        def fetch(path):
            calls.append(path)
            if path=="/sets":return {"data":[{"set_id":"1","name":"Delta Reign"}]}
            page=int(path.split("page=")[1].split("&")[0])
            return {"set":{"set_id":"1","total_cards":400},"cards":[card(page*100+n) for n in range(100)]}
        first=mod.step(state,fetch,lambda s,rs:None,cap=750,max_requests=2)
        self.assertEqual(first["today"],100)
        self.assertEqual(state["next_page"],2)
        second=mod.step(state,fetch,lambda s,rs:None,cap=750,max_requests=5)
        self.assertEqual(second["today"],300)
        self.assertTrue(state["finished"])
        self.assertEqual(state["cards_imported"],400)

if __name__=="__main__":
    unittest.main()
