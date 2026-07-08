from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
ARCHIVE = ROOT / "archive_old_versions"
DOCS = ROOT / "docs"
ARCHIVE.mkdir(exist_ok=True)
DOCS.mkdir(exist_ok=True)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

files = {
    "start_lookup_backend.bat": r'''@echo off
cd /d "%~dp0backend"
echo Starting Putnam Pokemon Lookup backend...
echo URL: http://127.0.0.1:8790/viewer.html
echo.
"%USERPROFILE%\AppData\Local\Python\pythoncore-3.14-64\python.exe" viewer_server.py
pause
''',

    "restart_lookup_backend.bat": r'''@echo off
cd /d "%~dp0"

echo Stopping existing Putnam backend on port 8790...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8790" ^| findstr "LISTENING"') do (
    echo Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Starting Putnam Pokemon Lookup backend...
cd /d "%~dp0backend"
echo URL: http://127.0.0.1:8790/viewer.html
echo.
"%USERPROFILE%\AppData\Local\Python\pythoncore-3.14-64\python.exe" viewer_server.py
pause
''',

    "open_lookup_viewer.bat": r'''@echo off
start "" "http://127.0.0.1:8790/viewer.html"
''',

    "open_chrome_extensions.bat": r'''@echo off
start "" "chrome://extensions"
''',

    "run_portability_audit.bat": r'''@echo off
cd /d "%~dp0"
"%USERPROFILE%\AppData\Local\Python\pythoncore-3.14-64\python.exe" ".\tools\run_portability_audit_p0_1.py"
pause
''',

    "fix_data_sources_portability.bat": r'''@echo off
cd /d "%~dp0"
"%USERPROFILE%\AppData\Local\Python\pythoncore-3.14-64\python.exe" ".\tools\fix_data_sources_portability_p0_2.py"
pause
''',
}

for name, content in files.items():
    path = ROOT / name
    if path.exists():
        (ARCHIVE / f"{path.stem}_before_p0_4_{stamp}{path.suffix}").write_text(path.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    path.write_text(content, encoding="utf-8")

readme = DOCS / "launcher_scripts.md"
readme.write_text("""# Project Launcher Scripts

Patch P0.4 added one-click launcher scripts to the project root.

## Scripts

### start_lookup_backend.bat
Starts the Putnam Pokemon Lookup backend on port 8790.

### restart_lookup_backend.bat
Stops any process listening on port 8790, then starts the backend again.

### open_lookup_viewer.bat
Opens the local backend viewer in the browser.

### open_chrome_extensions.bat
Opens Chrome Extensions so the unpacked extension can be reloaded.

### run_portability_audit.bat
Runs the portability audit.

### fix_data_sources_portability.bat
Rewrites backend/data_sources.json for the current PC username/path.

## Normal workflow

1. Double-click restart_lookup_backend.bat
2. Open chrome://extensions and reload the extension
3. Use the Putnam Pokemon Lookup Overlay
""", encoding="utf-8")

print("Patch P0.4 installed.")
print("Created project launcher scripts in:", ROOT)
print("Docs:", readme)