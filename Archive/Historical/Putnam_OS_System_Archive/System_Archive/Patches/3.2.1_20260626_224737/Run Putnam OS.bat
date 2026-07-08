@echo off
setlocal

if "%USERENVIRONMENT%"=="" (
    if exist "%USERPROFILE%\OneDrive\PutnamCollectibles\Putnam_OS" (
        set "USERENVIRONMENT=%USERPROFILE%\OneDrive\PutnamCollectibles"
    ) else if exist "%USERPROFILE%\Documents\PutnamCollectibles\Putnam_OS" (
        set "USERENVIRONMENT=%USERPROFILE%\Documents\PutnamCollectibles"
    ) else (
        echo ERROR: USERENVIRONMENT is not set and PutnamCollectibles could not be auto-detected.
        echo Expected one of:
        echo   %USERPROFILE%\OneDrive\PutnamCollectibles
        echo   %USERPROFILE%\Documents\PutnamCollectibles
        pause
        exit /b 1
    )
)

set "APP=%USERENVIRONMENT%\Putnam_OS\System\app\putnam_os.py"
set "LOGDIR=%USERENVIRONMENT%\Putnam_OS\System\logs"

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

if not exist "%APP%" (
    echo ERROR: Putnam OS app not found:
    echo %APP%
    echo [%date% %time%] ERROR app not found: %APP%>> "%LOGDIR%\startup.log"
    pause
    exit /b 1
)

echo [%date% %time%] Starting Putnam OS from %APP%>> "%LOGDIR%\startup.log"
py "%APP%"
if errorlevel 1 (
    echo.
    echo Putnam OS exited with an error.
    echo See: %LOGDIR%\startup.log
    echo [%date% %time%] Putnam OS exited with errorlevel %errorlevel%>> "%LOGDIR%\startup.log"
    pause
)
