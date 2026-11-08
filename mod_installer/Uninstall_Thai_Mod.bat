@echo off
chcp 65001 >nul
title Senren＊Banka - ตัวถอนการติดตั้งม็อดภาษาไทย
color 0C

echo ===============================================================================
echo     Senren＊Banka - ถอนการติดตั้งม็อดภาษาไทย (Restore Original Backup)
echo ===============================================================================
echo.

set "TARGET_DIR=%CD%"
if not exist "%TARGET_DIR%\SenrenBanka.exe" (
    if exist "C:\Program Files (x86)\Steam\steamapps\common\SenrenBanka\SenrenBanka.exe" (
        set "TARGET_DIR=C:\Program Files (x86)\Steam\steamapps\common\SenrenBanka"
    )
)

if not exist "%TARGET_DIR%\thai_mod_backup" (
    echo [!] ไม่พบโฟลเดอร์สำรองข้อมูล thai_mod_backup!
    echo หากต้องการกู้คืนไฟล์ดั้งเดิม ให้ใช้เมนู "Verify integrity of game files" ใน Steam
    pause
    exit /b 1
)

echo [*] กำลังกู้คืนไฟล์ต้นฉบับเดิม...
if exist "%TARGET_DIR%\thai_mod_backup\patch_extra.xp3.bak" (
    copy /y "%TARGET_DIR%\thai_mod_backup\patch_extra.xp3.bak" "%TARGET_DIR%\patch_extra.xp3" >nul
    echo  [✓] คืนค่า patch_extra.xp3 เดิมแล้ว
) else (
    if exist "%TARGET_DIR%\patch_extra.xp3" del /f /q "%TARGET_DIR%\patch_extra.xp3"
    echo  [✓] ลบ patch_extra.xp3 เรียบร้อย
)

if exist "%TARGET_DIR%\thai_mod_backup\data.xp3.bak" (
    copy /y "%TARGET_DIR%\thai_mod_backup\data.xp3.bak" "%TARGET_DIR%\data.xp3" >nul
    echo  [✓] คืนค่า data.xp3 เดิมแล้ว
)

echo.
echo [✓] ถอนการติดตั้งและกู้คืนตัวเกมเป็นภาษาอังกฤษเรียบร้อยแล้ว
pause
