Putnam Scanner Studio v0.4

What changed:
- Adds /api/scan endpoint.
- Browser can now run Upload Only or Run Scanner.
- Server attempts to call scanner_core_region_ocr.py if present.
- If the engine callable is not wired yet, it returns Needs Review instead of crashing.

Install:
1. Extract this zip into:
   C:\Users\JaredHill\Personal\PutnamCollectibles

2. Restart server:
   Ctrl+C
   python scanner_server.py

3. Open:
   http://127.0.0.1:8765

4. Press Ctrl+F5 in browser.

Expected:
- Drop/choose image works.
- Upload Only returns image_received.
- Run Scanner returns OCR/match if scanner_core_region_ocr.py exposes scan_image/run_scan/scan_one.
- If not, it will report engine_loaded_no_callable; that means the server/UI is wired and only the engine adapter needs one function added.
