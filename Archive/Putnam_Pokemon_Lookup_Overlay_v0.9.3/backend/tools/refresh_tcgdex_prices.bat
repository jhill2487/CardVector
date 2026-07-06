@echo off
cd /d "%~dp0"

if "%~1"=="" (
  echo Drag a TCGdex link CSV onto this file, or run:
  echo refresh_tcgdex_prices.bat path\to\tcgdex_links.csv
  pause
  exit /b 1
)

where python >nul 2>nul
if %errorlevel%==0 (
  python tcgdex_prices.py "%~1"
  pause
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  py tcgdex_prices.py "%~1"
  pause
  exit /b %errorlevel%
)

set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
  "%CODEX_PY%" tcgdex_prices.py "%~1"
  pause
  exit /b %errorlevel%
)

echo Python was not found.
pause
