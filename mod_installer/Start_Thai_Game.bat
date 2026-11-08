@echo off
chcp 65001 >nul
title Senren＊Banka - Launch Thai Game
cd /d "%~dp0"

:: Start game with Steam Cloud safe parameter to protect local saves
start "" "SenrenBanka.exe" -savecloud=no
