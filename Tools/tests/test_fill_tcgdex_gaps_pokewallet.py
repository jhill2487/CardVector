import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fill_tcgdex_gaps_pokewallet as gap

def tcg(ident,name="Pikachu",set_name="Trainer Kit"):
 return {"id":ident,"set_name":set_name,"name":name,
         "number":ident.split("-")[-1]}
def provider(ident="pk_"+"a"*64,name="Pikachu",number="014",set_name="Trainer Kit"):
 return {"provider_id":ident,"set_id":"123","set_name":set_name,
         "card_name":name,"card_number":number,"image_status":"pending","image_path":None}

class Matching(unittest.TestCase):
 def test_exact_unique(self):
  pairs,skips=gap.eligible([tcg("kit-014")],[provider()],set())
  self.assertEqual(len(pairs),1)
 def test_duplicate_printings_not_assumed(self):
  candidates=[provider(),provider("pk_"+"b"*64)]
  pairs,skips=gap.eligible([tcg("kit-014")],candidates,set())
  self.assertFalse(pairs)
  self.assertEqual(skips["missing_or_ambiguous_identity"],1)
 def test_wrong_name_is_not_used(self):
  pairs,skips=gap.eligible([tcg("kit-014")],[provider(name="Raichu")],set())
  self.assertFalse(pairs)
 def test_stamp_is_never_silently_substituted(self):
  pairs,skips=gap.eligible([tcg("kit-014",name="Pikachu Staff")],
                          [provider(name="Pikachu Staff")],set())
  self.assertFalse(pairs)
 def test_wrong_set_is_not_used(self):
  pairs,skips=gap.eligible([tcg("kit-014")],
                          [provider(set_name="Base Set")],set())
  self.assertFalse(pairs)
 def test_known_missing_provider_result_not_refetched(self):
  pairs,skips=gap.eligible([tcg("kit-014")],[provider()],{"kit-014"})
  self.assertFalse(pairs)
  self.assertEqual(skips["cached"],1)
 def test_distinct_tcgdex_same_number_is_ambiguous(self):
  a=tcg("kit-014")
  b={**a,"id":"kit-014a"}
  pairs,skips=gap.eligible([a,b],[provider()],set())
  self.assertEqual(len(pairs),1) # numbered 014a is distinct identity
if __name__=="__main__":
 unittest.main()
