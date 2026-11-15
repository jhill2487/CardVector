import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from import_delta_reign_images import image_type,path_for

class DeltaReignImageTests(unittest.TestCase):
    def test_png_validation(self):
        data=bytearray(b"\x89PNG\r\n\x1a\n"+b"\x00"*16)
        data[16:20]=(600).to_bytes(4,"big")
        data[20:24]=(800).to_bytes(4,"big")
        self.assertEqual(image_type(bytes(data)+b"\x00"*300),("png","image/png"))
    def test_jpeg_validation(self):
        self.assertEqual(image_type(b"\xff\xd8\xff"+b"\x00"*300+b"\xff\xd9"),("jpg","image/jpeg"))
    def test_no_fake_html(self):
        with self.assertRaises(ValueError):
            image_type(b"<html>"+b"x"*300)
    def test_canonical_path(self):
        card={"provider_id":"pk_"+"a"*64,"card_number":"001/103"}
        self.assertEqual(path_for(card,"png"),
                         "pokewallet/delta-reign/001-103_"+"a"*16+".png")
    def test_reject_path_injection(self):
        with self.assertRaises(ValueError):
            path_for({"provider_id":"pk_"+"a"*64,"card_number":"../bad"},"png")

if __name__=="__main__":
    unittest.main()
