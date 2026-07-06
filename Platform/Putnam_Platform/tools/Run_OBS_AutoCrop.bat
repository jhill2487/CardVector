@echo off
setlocal

if defined USERENVIRONMENT (
  set "PUTNAM_ROOT=%USERENVIRONMENT%"
) else (
  set "PUTNAM_ROOT=%USERPROFILE%\OneDrive\PutnamCollectibles"
)

set "AUTOCROP_APP=%PUTNAM_ROOT%\Putnam_Platform\capture\obs_capture_autocrop.py"

if not exist "%AUTOCROP_APP%" (
  echo OBS Capture Auto Crop pipeline was not found:
  echo %AUTOCROP_APP%
  exit /b 1
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py "%AUTOCROP_APP%" %*
) else (
  python "%AUTOCROP_APP%" %*
)

set "EXITCODE=%ERRORLEVEL%"

echo.
echo OBS Capture Auto Crop exited with code %EXITCODE%.
pause
exit /b %EXITCODE%
