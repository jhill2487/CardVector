"""Read-only availability-probe safety and source classifier tests."""
import importlib.util
import io
import pathlib
import unittest
import urllib.error

path=pathlib.Path(__file__).resolve().parents[1]/"probe_pokewallet_images.py"
spec=importlib.util.spec_from_file_location("probe",path)
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

P1="pk_"+"a"*64
P2="pk_"+"b"*64

class TestImageProbe(unittest.TestCase):
    def test_exact_card_filter_never_selects_normal_printing(self):
        rows=[
            {"provider_id":P1,"card_name":"Meganium 001 Staff","image_status":"missing"},
            {"provider_id":P2,"card_name":"Riolu 010 Pokemon Center Exclusive","image_status":"pending"},
            {"provider_id":"pk_"+"c"*64,"card_name":"Meganium","image_status":"pending"},
            {"provider_id":"pk_"+"d"*64,"card_name":"Meganium 001 Staff","image_status":"matched"}
        ]
        found=probe.select_records(rows,"Meganium 001 Staff;Riolu 010 Pokemon Center Exclusive",2)
        self.assertEqual(len(found),2)
        self.assertEqual({r["provider_id"] for r in found},{P1,P2})

    def test_empty_name_and_invalid_limits_rejected(self):
        with self.assertRaises(ValueError):
            probe.select_records([],"",2)
        with self.assertRaises(ValueError):
            probe.select_records([],"Meganium",100)

    def test_signature_requires_real_image_binary(self):
        class Response:
            status=200
            def __init__(self,ctype,payload):
                self.headers={"Content-Type":ctype}
                self.data=payload
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return self.data[:n]
        def run(ctype,payload):
            return probe.probe_image(P1,"fake",lambda req,timeout:Response(ctype,payload))
        self.assertEqual(run("image/jpeg",b"\xff\xd8\xff"+b"0"*16),"available_unverified")
        self.assertEqual(run("image/webp",b"RIFF0000WEBP"+b"0"*16),"available_unverified")
        self.assertEqual(run("text/html",b"<html>hello"),"invalid_image_response")
        self.assertEqual(run("image/jpeg",b"<html>hello"),"invalid_image_response")

    def test_missing_and_rate_limit(self):
        def missing(req,timeout):
            raise urllib.error.HTTPError(req.full_url,404,"missing",{},None)
        def capped(req,timeout):
            raise urllib.error.HTTPError(req.full_url,429,"cap",{},None)
        self.assertEqual(probe.probe_image(P1,"fake",missing),"not_available")
        self.assertEqual(probe.probe_image(P1,"fake",capped),"rate_limited")
        with self.assertRaises(ValueError):
            probe.probe_image("not-a-id","fake")

if __name__=="__main__":
    unittest.main()
