@echo off
setlocal
chcp 65001 >nul
title Senren Banka - Uninstall Thai Mod
color 0C

echo ===============================================================================
echo     Senren Banka - ถอนการติดตั้งม็อดภาษาไทย และกู้คืนไฟล์ต้นฉบับเดิม
echo ===============================================================================
echo.

set "SRC_DIR=%~dp0"
set "TARGET_DIR="

if exist "SenrenBanka.exe" set "TARGET_DIR=%CD%"
if defined TARGET_DIR goto :UFOUND
if exist "%SRC_DIR%SenrenBanka.exe" set "TARGET_DIR=%SRC_DIR%"
if defined TARGET_DIR goto :UFOUND

for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue';$r=@();foreach($k in @('HKCU:\Software\Valve\Steam','HKLM:\SOFTWARE\WOW6432Node\Valve\Steam','HKLM:\SOFTWARE\Valve\Steam')){try{$p=(Get-ItemProperty $k).SteamPath;if(-not $p){$p=(Get-ItemProperty $k).InstallPath};if($p){$r+=$p.Replace('/','\')}}catch{}};$r+=@('C:\Program Files (x86)\Steam','C:\Program Files\Steam','D:\SteamLibrary','D:\Steam','E:\SteamLibrary','E:\Steam','F:\SteamLibrary','G:\SteamLibrary');$all=@($r);foreach($b in $r){if([IO.Directory]::Exists($b)){$v=[IO.Path]::Combine($b,'steamapps\libraryfolders.vdf');if([IO.File]::Exists($v)){[regex]::Matches([IO.File]::ReadAllText($v),([char]34+'path'+[char]34+'\s+'+[char]34+'(.+?)'+[char]34))|ForEach-Object{$all+=$_.Groups[1].Value.Replace('\\','\')}}}};foreach($l in ($all|Select-Object -Unique)){if([IO.Directory]::Exists($l)){$g=[IO.Path]::Combine($l,'steamapps\common\SenrenBanka');if([IO.File]::Exists([IO.Path]::Combine($g,'SenrenBanka.exe'))){Write-Output $g;break}}}"`) do set "TARGET_DIR=%%I"
if defined TARGET_DIR goto :UFOUND

echo [!] ไม่พบโฟลเดอร์ตัวเกม SenrenBanka โดยอัตโนมัติ
set /p "TARGET_DIR=Game Path: "

:UFOUND
if not defined TARGET_DIR goto :NO_BACKUP
set "TARGET_DIR=%TARGET_DIR:"=%"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"
if not exist "%TARGET_DIR%\thai_mod_backup" goto :NO_BACKUP

echo [*] พบโฟลเดอร์เกมที่: "%TARGET_DIR%"
echo [*] กำลังกู้คืนไฟล์ต้นฉบับเดิม
echo.

if exist "%TARGET_DIR%\thai_mod_backup\patch_extra.xp3.bak" (
    copy /y "%TARGET_DIR%\thai_mod_backup\patch_extra.xp3.bak" "%TARGET_DIR%\patch_extra.xp3" >nul
    echo [OK] คืนค่า patch_extra.xp3 เดิมเรียบร้อยแล้ว
) else (
    if exist "%TARGET_DIR%\patch_extra.xp3" del /f /q "%TARGET_DIR%\patch_extra.xp3" >nul 2>&1
    echo [OK] ลบไฟล์ม็อด patch_extra.xp3 เรียบร้อยแล้ว
)

if exist "%TARGET_DIR%\thai_mod_backup\data.xp3.bak" (
    copy /y "%TARGET_DIR%\thai_mod_backup\data.xp3.bak" "%TARGET_DIR%\data.xp3" >nul
    echo [OK] คืนค่า data.xp3 เดิมเรียบร้อยแล้ว
)

echo.
echo ===============================================================================
echo     [OK] ถอนการติดตั้งและกู้คืนตัวเกมเป็นภาษาดั้งเดิมเรียบร้อยแล้ว
echo ===============================================================================
echo.
pause
exit /b 0

:NO_BACKUP
echo [!] ไม่พบโฟลเดอร์สำรองข้อมูล thai_mod_backup ใน: "%TARGET_DIR%"
echo หากต้องการกู้คืนไฟล์ดั้งเดิม ให้ใช้เมนู Verify integrity of game files ใน Steam
echo.
pause
exit /b 1
