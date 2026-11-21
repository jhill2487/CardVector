import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_hourly_pokewallet_images as hourly


def card(num, set_id, status="missing", path=None):
    pid = "pk_" + f"{num:040x}"
    return dict(set_id=set_id,set_name="SV: Shrouded Fable",
                provider_id=pid,card_name="Card " + str(num),
                card_number=str(num),image_status=status,image_path=path)


class HourlyImageTests(unittest.TestCase):
    def test_name_to_slug_is_generic(self):
        self.assertEqual(hourly.slug_for("SV: Shrouded Fable"), "shrouded-fable")
        self.assertEqual(hourly.slug_for("SV07: Stellar Crown"), "stellar-crown")
        self.assertEqual(hourly.slug_for("Trading Card Game Classic"), "trading-card-game-classic")

    def test_promo_and_alphanumeric_card_numbers_have_safe_unique_r2_keys(self):
        importer=hourly.importer
        pid="pk_"+"a"*64
        old_slug=importer.SET_SLUG
        try:
            importer.SET_SLUG="scarlet-violet-promo-cards"
            for raw,slug in [
                ("SVP 175","svp-175"),("SVP 176","svp-176"),
                ("SVP 200","svp-200"),("SVP193","svp193"),
                ("TG01/TG30","tg01-tg30"),("15/102","15-102"),
            ]:
                path=importer.path_for({"provider_id":pid,"card_number":raw},"jpg")
                self.assertIn("/"+slug+"_",path)
                self.assertTrue(path.endswith(".jpg"))
            for raw in ("../secret","foo?bar","a\\\\b","SVP:175","", "S"*41):
                with self.assertRaises(ValueError):
                    importer.path_for({"provider_id":pid,"card_number":raw},"jpg")
        finally:
            importer.SET_SLUG=old_slug

    def test_uses_only_complete_english_metadata_and_preserves_approvals(self):
        cards = [card(1,"23529"),card(2,"23529"),card(3,"23529","matched","Pokemon TCG/other/3.jpg"),
                 card(4,"44444"), card(5,"88888")]
        languages = [
            dict(set_id="23529",language="eng",expected_card_count=3),
            dict(set_id="44444",language="eng",expected_card_count=2), # incomplete
            dict(set_id="88888",language="jap",expected_card_count=1),
        ]
        reviews = [dict(provider_id=cards[2]["provider_id"], review_status="approved",
                        candidate_path="Pokemon TCG/other/3.jpg")]
        def fake_records(table,fields,headers,order="set_id"):
            return {"cv_admin_set_languages":languages,
                    "cv_admin_pokewallet_catalog":cards,
                    "cv_admin_image_reviews":reviews,
                    "cv_admin_image_import_priority":[]}[table]
        with patch.object(hourly,"records",side_effect=fake_records):
            sets=hourly.eligible_sets({})
        self.assertEqual(len(sets),1)
        self.assertEqual(sets[0]["set_id"],"23529")
        self.assertEqual(sets[0]["missing"],2)

    def test_hourly_runner_stops_at_provider_quota(self):
        secrets={name:"dummy" for name in
                 ("SUPABASE_SERVICE_ROLE_KEY","POKEWALLET_API_KEY",
                  "R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET")}
        selected=[dict(set_id="23529",slug="shrouded-fable",count=107,
                       missing=107,partially_staged=0),
                  dict(set_id="23381",slug="temporal-forces",count=218,
                       missing=218,partially_staged=0)]
        result={"attempted":50,"remaining_unstaged":57,"counts":{"uploaded":50},
                "quota_remaining_day":700,"quota_remaining_hour":0}
        with patch.dict(os.environ,secrets),\
             patch.object(hourly,"eligible_sets",return_value=selected),\
             patch.object(hourly.importer,"db_headers",return_value={}),\
             patch.object(hourly.importer,"r2_client",return_value=MagicMock()),\
             patch.object(hourly.quota,"choose_image_cap",return_value=900),\
             patch.object(hourly.quota,"current",return_value=None),\
             patch.object(hourly.quota,"reserve",return_value={"allowed":True}),\
             patch.object(hourly.importer,"run",return_value=result) as do_run,\
             patch.object(hourly.approval,"approve_set") as do_approve:
            hourly.run()
        self.assertEqual(do_run.call_count,1)
        do_approve.assert_not_called()

    def test_complete_set_is_approved_and_advances(self):
        secrets={name:"dummy" for name in
                 ("SUPABASE_SERVICE_ROLE_KEY","POKEWALLET_API_KEY",
                  "R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET")}
        selected=[dict(set_id="23529",slug="shrouded-fable",count=2,
                       missing=2,partially_staged=0),
                  dict(set_id="23381",slug="temporal-forces",count=1,
                       missing=1,partially_staged=0)]
        results=[
            {"attempted":2,"remaining_unstaged":0,"counts":{"uploaded":2},
             "quota_remaining_day":99,"quota_remaining_hour":98},
            {"attempted":1,"remaining_unstaged":0,"counts":{"uploaded":1},
             "quota_remaining_day":98,"quota_remaining_hour":97},
        ]
        with patch.dict(os.environ,secrets),\
             patch.object(hourly,"eligible_sets",return_value=selected),\
             patch.object(hourly.importer,"db_headers",return_value={}),\
             patch.object(hourly.importer,"r2_client",return_value=MagicMock()),\
             patch.object(hourly.quota,"choose_image_cap",return_value=900),\
             patch.object(hourly.quota,"current",return_value=None),\
             patch.object(hourly.quota,"reserve",return_value={"allowed":True}),\
             patch.object(hourly.importer,"run",side_effect=results) as do_run,\
             patch.object(hourly.approval,"approve_set",return_value=(2,"approved")) as do_approve:
            hourly.run()
        self.assertEqual(do_run.call_count,2)
        self.assertEqual(do_approve.call_count,2)


if __name__ == "__main__":
    unittest.main()
