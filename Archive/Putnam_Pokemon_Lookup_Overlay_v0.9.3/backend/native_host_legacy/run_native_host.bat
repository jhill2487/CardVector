@echo off
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  python native_host.py
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  py native_host.py
  exit /b %errorlevel%
)

set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
  "%CODEX_PY%" native_host.py
  exit /b %errorlevel%
)

exit /b 1
