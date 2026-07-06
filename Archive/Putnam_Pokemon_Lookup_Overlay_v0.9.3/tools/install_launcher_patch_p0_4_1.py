from datetime import datetime
from pathlib import Path
import json

ROOT = Path.cwd()
BAT = ROOT / "restart_lookup_backend.bat"
MANIFEST = ROOT / "extension" / "manifest.json"
ARCHIVE = ROOT / "archive_old_versions"
ARCHIVE.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Backup files
if BAT.exists():
    (ARCHIVE / f"restart_lookup_backend_before_p0_4_1_{stamp}.bat").write_text(
        BAT.read_text(encoding="utf-8", errors="ignore"),
        encoding="utf-8"
    )

if MANIFEST.exists():
    manifest_text = MANIFEST.read_text(encoding="utf-8")
    (ARCHIVE / f"manifest_before_p0_4_1_{stamp}.json").write_text(
        manifest_text,
        encoding="utf-8"
    )
else:
    raise SystemExit(f"ERROR: Missing {MANIFEST}")

# Patch restart launcher
BAT.write_text(r'''@echo off
cd /d "%~dp0"

echo Stopping existing Putnam backend on port 8790...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8790" ^| findstr "LISTENING"') do (
    echo Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Opening Chrome Extensions page...
start "" "chrome://extensions"

echo.
echo Starting Putnam Pokemon Lookup backend...
cd /d "%~dp0backend"
echo URL: http://127.0.0.1:8790/viewer.html
echo.
echo After Chrome Extensions opens, click Reload on Putnam Pokemon Lookup Overlay.
echo.
"%USERPROFILE%\AppData\Local\Python\pythoncore-3.14-64\python.exe" viewer_server.py

pause
''', encoding="utf-8")

# Patch manifest for all-webpage availability
manifest = json.loads(manifest_text)

manifest["host_permissions"] = ["<all_urls>"]

for script in manifest.get("content_scripts", []):
    script["matches"] = ["<all_urls>"]

# Patch-level bump: 0.5.0 -> 0.5.1
manifest["version"] = "0.5.1"

MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("Patch P0.4.1 installed.")
print("restart_lookup_backend.bat now opens chrome://extensions.")
print("Extension now supports all webpages via <all_urls>.")
print("Manifest version updated to v0.5.1.")
print("Backups saved to:", ARCHIVE)