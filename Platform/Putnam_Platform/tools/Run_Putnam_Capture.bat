@echo off
setlocal

if defined USERENVIRONMENT (
  set "PUTNAM_ROOT=%USERENVIRONMENT%"
) else (
  set "PUTNAM_ROOT=%USERPROFILE%\OneDrive\PutnamCollectibles"
)

set "CAPTURE_APP=%PUTNAM_ROOT%\Platform\Putnam_Platform\capture\Putnam_Capture.py"

if not exist "%CAPTURE_APP%" (
  echo Putnam Capture was not found:
  echo %CAPTURE_APP%
  exit /b 1
)

set "OBS_PASSWORD="
set /p "OBS_PASSWORD=OBS WebSocket password: "

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py "%CAPTURE_APP%" --password "%OBS_PASSWORD%" %*
) else (
  python "%CAPTURE_APP%" --password "%OBS_PASSWORD%" %*
)

set "EXITCODE=%ERRORLEVEL%"

echo.
echo Putnam Capture exited with code %EXITCODE%.
pause
exit /b %EXITCODE%
