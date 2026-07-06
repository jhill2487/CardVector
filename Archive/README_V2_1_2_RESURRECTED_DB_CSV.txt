Putnam Collectibles Scanner - V2.1.2 Resurrected + DB/CSV Improvements

This rebuild preserves the V2.1.2 behavior that mattered most:
- raw/default Tesseract OCR runs first, before preprocessing
- combined OCR text is used for matching
- database-name rescue matching remains active
- images still move to processed_photos or review_photos
- optional OCR debug text files are saved with --save-ocr-text

New lookup options:
1) SQLite database:
   python card_intake_app_v2_1_2_resurrected.py --sqlite database\putnam_pokemon_cloud_ready.sqlite --input input_photos --save-ocr-text

2) CSV lookup file:
   python card_intake_app_v2_1_2_resurrected.py --lookup database\putnam_pokemon_cards_cloud_ready.csv --input input_photos --save-ocr-text

3) Folder of CSV files, such as TradingCardDex CSV exports:
   python card_intake_app_v2_1_2_resurrected.py --lookup "C:\path\to\Pokemon-Card-CSV" --input input_photos --save-ocr-text

4) Legacy Excel lookup/workbook:
   python card_intake_app_v2_1_2_resurrected.py --workbook Putnam_Master_Inventory_Card_Intake_Workflow.xlsx --input input_photos --save-ocr-text

Recommended first test, plain text only, no workbook writes, no image moves:
   python card_intake_app_v2_1_2_resurrected.py --sqlite database\putnam_pokemon_cloud_ready.sqlite --input input_photos --save-ocr-text --scan-only --no-move

If Tesseract is installed in the default Windows location, the script points pytesseract to:
   C:\Program Files\Tesseract-OCR\tesseract.exe

Expected folders:
- input_photos: put test images here
- processed_photos: matched images move here unless --no-move is used
- review_photos: unmatched images move here unless --no-move is used
- ocr_debug: saved OCR text files when --save-ocr-text is used

What improved:
- accepts Excel, CSV, CSV folders, and SQLite
- maps common column names from Putnam, TradingCardDex, and TCGCSV-style sources
- normalizes card numbers like 073/086 -> 73/86
- recognizes simple set-code hints like CRI, PRE, PAL, SVI, OBF, MEG
