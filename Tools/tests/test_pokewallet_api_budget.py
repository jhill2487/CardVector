import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pokewallet_api_budget as budget


class BudgetTests(unittest.TestCase):
    def test_first_day_allocates_900_for_images(self):
        with patch.object(budget, "current", return_value=None):
            self.assertEqual(budget.choose_image_cap({}, 1753), 900)

    def test_after_900_image_day_next_day_allocates_1000_when_ready(self):
        previous = dict(image_requests=900, metadata_requests=60, image_cap=900)
        with patch.object(budget, "current", side_effect=[previous,None]):
            self.assertEqual(budget.choose_image_cap({}, 1753), 1000)

    def test_after_900_image_day_but_only_small_image_queue_metadata_replenishes(self):
        previous = dict(image_requests=900, metadata_requests=60, image_cap=900)
        with patch.object(budget, "current", side_effect=[previous,None]):
            self.assertEqual(budget.choose_image_cap({}, 200), 900)

    def test_current_day_cap_never_changes_mid_day(self):
        with patch.object(budget, "current", side_effect=[None,dict(image_cap=1000)]):
            self.assertEqual(budget.choose_image_cap({}, 0), 1000)

    def test_metadata_waits_for_image_target(self):
        with patch.object(budget,"current",return_value=dict(
                image_requests=899,metadata_requests=0,image_cap=900)):
            self.assertEqual(budget.metadata_allowance({}),0)

    def test_metadata_uses_remaining_100_request_allowance(self):
        with patch.object(budget,"current",return_value=dict(
                image_requests=900,metadata_requests=5,image_cap=900)):
            self.assertEqual(budget.metadata_allowance({}),95)

    def test_1000_image_day_prevents_metadata_calls(self):
        with patch.object(budget,"current",return_value=dict(
                image_requests=1000,metadata_requests=0,image_cap=1000)):
            self.assertEqual(budget.metadata_allowance({}),0)


if __name__=="__main__":
    unittest.main()
