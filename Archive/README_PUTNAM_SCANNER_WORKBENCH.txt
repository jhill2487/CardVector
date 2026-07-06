Putnam Scanner Workbench v0.1

Goal:
Stop downloading a new Python script for every scanner iteration. Run one local server and test scanner settings/results from a browser.

Install once:
  python -m pip install pillow opencv-python numpy pytesseract

Copy these files into:
  C:\Users\JaredHill\Personal\PutnamCollectibles

Files:
  scanner_server.py
  scanner_workbench.html
  scanner_config.json
  scanner_core_region_ocr.py

Run:
  cd /d "C:\Users\JaredHill\Personal\PutnamCollectibles"
  python scanner_server.py

Open if it does not open automatically:
  http://127.0.0.1:8765

Default config expects:
  border_training_labels\IMG_7505.json
  border_training_labels\*.json
  input_photos\*.JPG
  database\putnam_pokemon_cloud_ready.sqlite

Use:
  - Run Selected Card for one test label
  - Run All Labels for bulk testing
  - Results table shows Auto Match or Needs Review

Patch workflow going forward:
  - For thresholds/paths, edit scanner_config.json or use the browser fields.
  - For scanner algorithm changes, replace scanner_core_region_ocr.py only.
