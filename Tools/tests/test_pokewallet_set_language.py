import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pokewallet_set_language import set_language
from run_daily_pokewallet_import import make_state, step

class EnglishOnlyTests(unittest.TestCase):
 def test_language_classification(self):
  for name in ("Delta Reign","Chaos Rising","ME03: Perfect Order","SV10: Destined Rivals","SWSH12: Silver Tempest"):
   self.assertEqual(set_language({"name":name}),"eng",name)
  for name in ("30th Celebration - Japanese","SV10: The Glory of Team Rocket",
               "M4: Ninja Spinner","Abyss Eye","SV4a: Shiny Treasure ex"):
   self.assertEqual(set_language({"name":name}),"jpn",name)
  self.assertEqual(set_language({"name":"30th Celebration Premium Deck Set"}),"jpn")
  self.assertEqual(set_language({"name":"Unknown Promo Set"}),"und")
 def test_defer_japanese_without_requests_or_cards(self):
  state=make_state()
  state["sets"]=[{"set_id":"1","name":"SV10: The Glory of Team Rocket"},
                 {"set_id":"2","name":"ME03: Perfect Order"}]
  paths=[]
  persisted=[]
  def fetch(path):
   paths.append(path)
   if path=="/sets":
    return {"data":[{"set_id":"1","name":"SV10: The Glory of Team Rocket","language":"jap","card_count":1},
                    {"set_id":"2","name":"ME03: Perfect Order","language":"eng","card_count":1}]}
   return {"cards":[{"id":"test_card","card_info":{"name":"Pikachu","card_number":"1","product_type":"card"}}],
           "set":{"set_id":"2","total_cards":1,"language":"eng"}}
  def write(state,rows):
   persisted.extend(rows)
  result=step(state,fetch,write,day="2026-11-12")
  self.assertEqual(result["today"],1)
  self.assertEqual(len(paths),2)
  self.assertEqual(paths[0],"/sets")
  self.assertIn("/sets/2?",paths[1])
  self.assertEqual(len(persisted),1)
if __name__=="__main__":unittest.main()
