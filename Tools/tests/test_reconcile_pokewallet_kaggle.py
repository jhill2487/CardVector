import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location("reconcile", Path(__file__).resolve().parents[1] / "reconcile_pokewallet_kaggle.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ReconciliationTests(unittest.TestCase):
    def test_zero_padding_and_promo_names(self):
        card = mod.read_cards([{"id":"pk_x", "card_info":{"name":"Pikachu Libre","set_name":"XY Trainer Kit Pikachu Libre","card_number":"014"}}])
        image = mod.parse_image({"RelativePath":r"Pokemon TCG\Pokemon TCG\xy-trainer-kit-pikachu-libre\en_US-TK9A-014-pikachu_libre.jpg"})
        matched, review, missing = mod.reconcile(card, [image], {"XY Trainer Kit Pikachu Libre":["xy-trainer-kit-pikachu-libre"]})
        self.assertEqual((len(matched),len(review),len(missing)), (1,0,0))

    def test_conflicting_names_are_never_accepted(self):
        cards = mod.read_cards([{"card_info":{"name":"Raichu","set_name":"Base Set","card_number":"58"}}])
        image = mod.parse_image({"RelativePath":"Pokemon TCG/Pokemon TCG/base-set/pikachu-base-set-bs-58.jpg"})
        matched, review, missing = mod.reconcile(cards, [image], {"Base Set":["base-set"]})
        self.assertEqual((len(matched),len(review),len(missing)), (0,1,0))

    def test_multiple_finishes_require_review(self):
        cards = mod.read_cards([{"card_info":{"name":"Bulbasaur","set_name":"151","card_number":"001"}}])
        images = [mod.parse_image({"RelativePath":f"Pokemon TCG/Pokemon TCG/151/sv3-5_en_001_{finish}.jpg"}) for finish in ("std","rev")]
        matched, review, missing = mod.reconcile(cards, images, {})
        self.assertEqual((len(matched),len(review),len(missing)), (0,1,0))

    def test_no_set_guessing(self):
        cards = mod.read_cards([{"card_info":{"name":"Pikachu","set_name":"Mega Evolution Promo","card_number":"93"}}])
        images = [mod.parse_image({"RelativePath":"Pokemon TCG/Pokemon TCG/mcdonalds-collection-2024/en_US-MCD24-093-pikachu.jpg"})]
        matched, review, missing = mod.reconcile(cards, images, {})
        self.assertEqual((len(matched),len(review),len(missing)), (0,0,1))

if __name__ == "__main__":
    unittest.main()
