Putnam Scanner Studio v0.2

Purpose:
- One browser page for image loading, border/region editing, label saving, and scanner testing.
- Built to replace the separate border trainer + incomplete workbench.

Install/Run:
1. Extract all files into:
   C:\Users\JaredHill\Personal\PutnamCollectibles

2. From Command Prompt:
   cd /d "C:\Users\JaredHill\Personal\PutnamCollectibles"
   python scanner_server.py

3. Open Chrome/Edge:
   http://127.0.0.1:8765

Workflow:
1. Drag a card image into the drop area, or choose a file.
2. Adjust green card border.
3. Adjust blue name, yellow number, magenta set-code regions.
4. Click Save Label JSON.
5. Click Run Scanner on This Card.

Notes:
- HTML should stay mostly stable.
- Future scanner logic changes should usually go in scanner_core_region_ocr.py or scanner_config.json.
- Images save into input_photos.
- Labels save into border_training_labels.
- Results save into the configured output folder.
