@echo off
cd /d "%~dp0"

echo Starting Pokemon Watcher backend.
echo.
echo Backend:
echo   http://127.0.0.1:8790/api/search
echo.
echo Keep this window open while using the Whatnot overlay.
echo Close this window to stop overlay search, thumbnails, and prices.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
  python viewer_server.py
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  py viewer_server.py
  exit /b %errorlevel%
)

set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
  "%CODEX_PY%" viewer_server.py
  exit /b %errorlevel%
)

echo Python was not found.
pause
