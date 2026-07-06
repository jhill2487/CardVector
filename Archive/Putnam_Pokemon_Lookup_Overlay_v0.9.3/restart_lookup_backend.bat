@echo off
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
