@echo off
chcp 65001 >nul
title Senren＊Banka Thai Localization Installer v1.0
color 0A

echo ===============================================================================
echo     Senren＊Banka (千恋＊万花) - ตัวติดตั้งม็อดแปลภาษาไทย (Steam Edition)
echo ===============================================================================
echo.

set "TARGET_DIR="

:: 1. Check current directory first
if exist "SenrenBanka.exe" (
    set "TARGET_DIR=%CD%"
    goto :FOUND
)

:: 2. Check standard Steam library paths
if exist "C:\Program Files (x86)\Steam\steamapps\common\SenrenBanka\SenrenBanka.exe" (
    set "TARGET_DIR=C:\Program Files (x86)\Steam\steamapps\common\SenrenBanka"
    goto :FOUND
)
if exist "D:\SteamLibrary\steamapps\common\SenrenBanka\SenrenBanka.exe" (
    set "TARGET_DIR=D:\SteamLibrary\steamapps\common\SenrenBanka"
    goto :FOUND
)
if exist "E:\SteamLibrary\steamapps\common\SenrenBanka\SenrenBanka.exe" (
    set "TARGET_DIR=E:\SteamLibrary\steamapps\common\SenrenBanka"
    goto :FOUND
)

echo [!] ไม่พบโฟลเดอร์ตัวเกม SenrenBanka โดยอัตโนมัติ
echo กรุณาคัดลอกไฟล์ทั้งหมดในโฟลเดอร์นี้ ไปวางในโฟลเดอร์เกมของคุณที่มีไฟล์ SenrenBanka.exe
echo หรือพิมพ์ Path ของโฟลเดอร์เกมด้านล่าง:
set /p TARGET_DIR="Game Path: "

if not exist "%TARGET_DIR%\SenrenBanka.exe" (
    echo [ERROR] ไม่พบไฟล์ SenrenBanka.exe ในตำแหน่งที่ระบุ!
    pause
    exit /b 1
)

:FOUND
echo [*] พบตัวเกมที่: "%TARGET_DIR%"
echo.

:: 3. Check for patch files
if not exist "patch_extra.xp3" (
    echo [ERROR] ไม่พบไฟล์ patch_extra.xp3 ในโฟลเดอร์ติดตั้งนี้!
    echo กรุณาดาวน์โหลดไฟล์ม็อดฉบับเต็มจาก GitHub Releases มาวางคู่กับตัวติดตั้งนี้
    pause
    exit /b 1
)

:: 4. Create Backup
echo [*] กำลังสำรองข้อมูลไฟล์เดิม...
if not exist "%TARGET_DIR%\thai_mod_backup" mkdir "%TARGET_DIR%\thai_mod_backup"

if exist "%TARGET_DIR%\patch_extra.xp3" (
    if not exist "%TARGET_DIR%\thai_mod_backup\patch_extra.xp3.bak" (
        copy /y "%TARGET_DIR%\patch_extra.xp3" "%TARGET_DIR%\thai_mod_backup\patch_extra.xp3.bak" >nul
        echo  [✓] สำรองไฟล์ patch_extra.xp3 เรียบร้อย
    )
)

if exist "%TARGET_DIR%\data.xp3" (
    if not exist "%TARGET_DIR%\thai_mod_backup\data.xp3.bak" (
        echo  [*] กำลังสำรองไฟล์ data.xp3 (ขนาด ~1GB อาจใช้เวลา 10-20 วินาที)...
        copy /y "%TARGET_DIR%\data.xp3" "%TARGET_DIR%\thai_mod_backup\data.xp3.bak" >nul
        echo  [✓] สำรองไฟล์ data.xp3 เรียบร้อย
    )
)

:: 5. Copy Mod Files
echo.
echo [*] กำลังติดตั้งม็อดภาษาไทย...
copy /y "patch_extra.xp3" "%TARGET_DIR%\patch_extra.xp3" >nul
echo  [✓] คัดลอก patch_extra.xp3 (บทสนทนาภาษาไทยครบ 92 ตอน) สำเร็จ

if exist "data.xp3" (
    echo  [*] กำลังติดตั้งชุดฟอนต์ไทยและ UI ภาษาไทย (data.xp3)...
    copy /y "data.xp3" "%TARGET_DIR%\data.xp3" >nul
    echo  [✓] คัดลอก data.xp3 สำเร็จ
)

if exist "Start_Thai_Game.bat" (
    copy /y "Start_Thai_Game.bat" "%TARGET_DIR%\Start_Thai_Game.bat" >nul
)
if exist "Uninstall_Thai_Mod.bat" (
    copy /y "Uninstall_Thai_Mod.bat" "%TARGET_DIR%\Uninstall_Thai_Mod.bat" >nul
)

echo.
echo ===============================================================================
echo     ยินดีด้วย! การติดตั้งม็อดภาษาไทย Senren＊Banka เสร็จสมบูรณ์แล้ว 100%%
echo ===============================================================================
echo.
echo วิธีเข้าเล่น:
echo  1. เข้าเล่นผ่าน Steam ได้ตามปกติ หรือ
echo  2. ดับเบิลคลิกที่ไฟล์ Start_Thai_Game.bat ในโฟลเดอร์เกมเพื่อความปลอดภัยของเซฟ
echo.
pause
