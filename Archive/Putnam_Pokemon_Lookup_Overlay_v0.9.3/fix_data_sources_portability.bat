@echo off
cd /d "%~dp0"
"%USERPROFILE%\AppData\Local\Python\pythoncore-3.14-64\python.exe" ".\tools\fix_data_sources_portability_p0_2.py"
pause
