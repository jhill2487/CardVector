import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pokewallet_market_metadata import market_rows,market_row


def example(pid="pk_"+"a"*64,url="https://www.tcgplayer.com/product/556443"):
 return {
  "id":pid,
  "card_info":{"name":"Example","product_type":"card","rarity":"Double Rare"},
  "tcgplayer":{"url":url,"prices":[
   {"sub_type_name":"Holofoil","market_price":8.01,
    "updated_at":"2026-11-20T02:15:00Z"},
   {"sub_type_name":"Reverse Holofoil","market_price":9.21,
    "updated_at":"2026-11-19T02:15:00Z"}]}
 }

class MarketRowsTest(unittest.TestCase):
 def test_exact_printing_link_and_prices(self):
  row=market_row(example())
  self.assertEqual(row["tcgplayer_url"],"https://www.tcgplayer.com/product/556443")
  self.assertEqual(row["rarity"],"Double Rare")
  self.assertEqual([p["sub_type_name"] for p in row["tcgplayer_prices"]],
                   ["Holofoil","Reverse Holofoil"])
  self.assertEqual(row["tcgplayer_prices"][0]["market_price"],8.01)
 def test_never_invent_or_redirect_product_url(self):
  for url in ("https://other.example/product/556443",
              "https://tcgplayer.com.evil.net/product/556443",
              "javascript:alert(1)","https://www.tcgplayer.com/search?q=pokemon"):
   self.assertIsNone(market_row(example(url=url))["tcgplayer_url"])
 def test_no_inferred_price_from_missing_market_value(self):
  item=example()
  item["tcgplayer"]["prices"]=[{"sub_type_name":"Normal","low_price":1.2},
                                {"sub_type_name":"Normal","market_price":None}]
  self.assertEqual(market_row(item)["tcgplayer_prices"],[])
 def test_only_normalized_exact_ids_and_not_sealed(self):
  sample=example()
  self.assertEqual(len(market_rows([sample],[{"id":sample["id"]}])),1)
  self.assertEqual(market_rows([sample],[{"id":"other"}]),[])
  sample["card_info"]["product_type"]="sealed"
  self.assertIsNone(market_row(sample))
if __name__=="__main__":unittest.main()
