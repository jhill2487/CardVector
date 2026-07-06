@echo off
cd /d "%~dp0"

echo Starting Pokemon Watcher search server on http://127.0.0.1:8790/viewer.html
echo Keep this window open while using this debug viewer.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
  start "" http://127.0.0.1:8790/viewer.html
  python viewer_server.py
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  start "" http://127.0.0.1:8790/viewer.html
  py viewer_server.py
  exit /b %errorlevel%
)

set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
  start "" http://127.0.0.1:8790/viewer.html
  "%CODEX_PY%" viewer_server.py
  exit /b %errorlevel%
)

echo Python was not found.
pause
