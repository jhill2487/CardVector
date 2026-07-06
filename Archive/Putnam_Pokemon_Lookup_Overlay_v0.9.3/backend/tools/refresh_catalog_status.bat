@echo off
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
  python card_catalog.py
  pause
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  py card_catalog.py
  pause
  exit /b %errorlevel%
)

set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
  "%CODEX_PY%" card_catalog.py
  pause
  exit /b %errorlevel%
)

echo Python was not found.
pause
