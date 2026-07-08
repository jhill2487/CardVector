Putnam Scanner V2.2.0 Region OCR

Purpose
-------
This version replaces full-card OCR with region OCR:
- card border from Border Trainer JSON
- perspective warp to upright card
- reusable template regions from one good labeled card
- OCR only name / number / set code
- database match against putnam_pokemon_cloud_ready.sqlite

This prevents attack names from becoming the card name.

Install
-------
python -m pip install pandas opencv-python numpy pytesseract pillow

Recommended first test
----------------------
python putnam_scanner_v2_2_0_region_ocr.py --template-label border_training_labels\IMG_7505.json --target-labels border_training_labels --images input_photos --sqlite database\putnam_pokemon_cloud_ready.sqlite --output region_ocr_v2_2_0_test --skip-template-source --save-ocr-text

Outputs
-------
region_ocr_v2_2_0_test\putnam_region_ocr_results.csv
region_ocr_v2_2_0_test\warped_cards
region_ocr_v2_2_0_test\region_crops
region_ocr_v2_2_0_test\overlays
region_ocr_v2_2_0_test\ocr_debug

Confidence rules
----------------
Number + Set Code + Name = auto_match
Unique Number + Set Code but weak/missing name = candidate_review
Name only = review

Current limitation
------------------
This version still needs Border Trainer JSON labels for each target image's card border.
The next step is to replace target card labels with automatic border detection once enough border examples are collected.
