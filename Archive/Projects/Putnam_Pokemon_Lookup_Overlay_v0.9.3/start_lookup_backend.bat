@echo off
cd /d "%~dp0backend"
echo Starting Putnam Pokemon Lookup backend...
echo URL: http://127.0.0.1:8790/viewer.html
echo.
"%USERPROFILE%\AppData\Local\Python\pythoncore-3.14-64\python.exe" viewer_server.py
pause
