@echo off
setlocal
if "%USERENVIRONMENT%"=="" set "USERENVIRONMENT=%USERPROFILE%\OneDrive\PutnamCollectibles"
py "%USERENVIRONMENT%\Putnam_OS\modules\Bulk_Price_Reviser\app\main.py"
pause
