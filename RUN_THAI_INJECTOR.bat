@echo off
chcp 65001 > nul
title Senren＊Banka - Universal Thai Injector

echo ======================================================================
echo    Senren＊Banka - Universal Thai Localization Injector
echo ======================================================================
echo.

python tools/thai_injector.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ======================================================================
    echo [ERROR] Injection failed with error code %ERRORLEVEL%!
    echo Please check the error message above.
    echo ======================================================================
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ======================================================================
echo Completed successfully! Press any key to exit.
echo ======================================================================
pause
