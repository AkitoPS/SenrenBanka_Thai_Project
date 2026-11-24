@echo off
chcp 65001 >nul
title Senren Banka - Universal Thai Injector
cd /d "%~dp0"

echo ======================================================================
echo    Senren Banka - Universal Thai Localization Injector
echo ======================================================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not found on PATH!
    echo Please install Python 3.10+ and run: pip install -r tools/requirements.txt
    echo.
    pause
    exit /b 1
)

python tools/thai_injector.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ======================================================================
    echo [ERROR] Injection failed with error code %ERRORLEVEL%!
    echo If dependencies are missing, run: pip install -r tools/requirements.txt
    echo ======================================================================
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ======================================================================
echo Completed successfully! Output saved to output/patch_extra.xp3
echo Press any key to exit.
echo ======================================================================
pause
