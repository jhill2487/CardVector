Putnam Scanner Lock Patch

Purpose:
Protect the known-good geometry and current Studio layout from accidental patch drift.

Locked files:
- known_good/template_region_warp_matcher_v0_7.py
- known_good/IMG_7505.json
- known_good/IMG_7507.json
- scanner_studio.html

Normal workflow:
1. Run once:
   python install_project_locks.py

2. After any future patch:
   python verify_project_locks.py

3. If verification fails and you did NOT intend to change geometry/layout:
   restore the file from project_locks\locked_backups

4. Only if intentionally changing geometry/layout:
   python unlock_locked_files.py
   make/test the deliberate change
   python relock_project_files.py

Patch discipline going forward:
- OCR patches should overwrite only scanner_core_region_ocr.py.
- Server patches should overwrite only scanner_server.py, unless UI changes are explicitly requested.
- HTML/layout patches should not be bundled with OCR patches.
- Geometry patches should never touch known_good unless we are creating a new verified baseline.
