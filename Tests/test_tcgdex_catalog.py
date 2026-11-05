"""Offline contract tests for the read-only TCGdex adapter."""
import io
import json
import unittest

from Platform.cardvector.integrations.tcgdex import TCGdexCatalog, normalize_card


class Response(io.BytesIO):
    pass


class CatalogTests(unittest.TestCase):
    def test_normalize_exact_card(self):
        card = normalize_card({"id": "swsh7-215", "name": "Umbreon VMAX",
                               "localId": "215", "set": {"id": "swsh7", "name": "Evolving Skies"}})
        self.assertEqual((card.provider, card.provider_id, card.local_id), ("tcgdex", "swsh7-215", "215"))
        self.assertIsNone(card.image_url)

    def test_lookup_and_search(self):
        urls = []
        def opener(request, timeout):
            urls.append(request.full_url)
            data = [{"id": "swsh7-215", "name": "Umbreon VMAX"}] if "?" in request.full_url else {"id": "swsh7-215", "name": "Umbreon VMAX"}
            return Response(json.dumps(data).encode())
        client = TCGdexCatalog(opener=opener)
        self.assertEqual(client.get_card("swsh7-215").provider_id, "swsh7-215")
        self.assertEqual(len(client.search_cards("Umbreon VMAX")), 1)
        self.assertIn("name=Umbreon+VMAX", urls[1])

    def test_invalid_ids(self):
        with self.assertRaises(ValueError):
            TCGdexCatalog().get_card("../cards")
        with self.assertRaises(ValueError):
            normalize_card({"name": "Missing id"})


if __name__ == "__main__":
    unittest.main()
