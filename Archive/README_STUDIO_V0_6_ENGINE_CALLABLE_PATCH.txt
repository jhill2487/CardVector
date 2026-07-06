Putnam Scanner Studio v0.6 - Engine Callable Patch

Replace scanner_core_region_ocr.py in your PutnamCollectibles folder with this version.

What it fixes:
- Adds scan_image(image_path, config, output_dir)
- Adds run_scan(...) and scan_one(...) aliases
- Keeps strict behavior: Auto Match or Needs Review, never weak labels
- Uses saved border labels when available
- Falls back to conservative auto-border detection only when possible

Important:
If an uploaded image has no saved border label and auto-border is not confident,
the engine will return Needs Review instead of guessing.
