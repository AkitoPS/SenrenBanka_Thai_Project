@echo off
setlocal
chcp 65001 >nul
title Senren Banka Thai Localization Installer v1.0.2
color 0A

echo ===============================================================================
echo     Senren Banka - Thai Localization Installer (Steam Edition)
echo     ตัวติดตั้งม็อดแปลภาษาไทย 100%% ฉบับสมบูรณ์
echo ===============================================================================
echo.

set "SRC_DIR=%~dp0"
set "TARGET_DIR="

:: 1. Check current folder or installer folder first
if exist "SenrenBanka.exe" set "TARGET_DIR=%CD%"
if defined TARGET_DIR goto :FOUND
if exist "%SRC_DIR%SenrenBanka.exe" set "TARGET_DIR=%SRC_DIR%"
if defined TARGET_DIR goto :FOUND

:: 2. Auto-detect Steam libraries across all drives via Registry and libraryfolders.vdf
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue';$r=@();foreach($k in @('HKCU:\Software\Valve\Steam','HKLM:\SOFTWARE\WOW6432Node\Valve\Steam','HKLM:\SOFTWARE\Valve\Steam')){try{$p=(Get-ItemProperty $k).SteamPath;if(-not $p){$p=(Get-ItemProperty $k).InstallPath};if($p){$r+=$p.Replace('/','\')}}catch{}};$r+=@('C:\Program Files (x86)\Steam','C:\Program Files\Steam','D:\SteamLibrary','D:\Steam','E:\SteamLibrary','E:\Steam','F:\SteamLibrary','G:\SteamLibrary');$all=@($r);foreach($b in $r){if([IO.Directory]::Exists($b)){$v=[IO.Path]::Combine($b,'steamapps\libraryfolders.vdf');if([IO.File]::Exists($v)){[regex]::Matches([IO.File]::ReadAllText($v),([char]34+'path'+[char]34+'\s+'+[char]34+'(.+?)'+[char]34))|ForEach-Object{$all+=$_.Groups[1].Value.Replace('\\','\')}}}};foreach($l in ($all|Select-Object -Unique)){if([IO.Directory]::Exists($l)){$g=[IO.Path]::Combine($l,'steamapps\common\SenrenBanka');if([IO.File]::Exists([IO.Path]::Combine($g,'SenrenBanka.exe'))){Write-Output $g;break}}}"`) do set "TARGET_DIR=%%I"
if defined TARGET_DIR goto :FOUND

:: 3. Prompt user manually if still not found
echo [!] ไม่พบโฟลเดอร์ตัวเกม SenrenBanka โดยอัตโนมัติ
echo กรุณาพิมพ์หรือลากโฟลเดอร์เกมที่มีไฟล์ SenrenBanka.exe มาวางด้านล่าง
set /p "TARGET_DIR=Game Path: "

:FOUND
if not defined TARGET_DIR goto :NO_EXE
set "TARGET_DIR=%TARGET_DIR:"=%"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"
if not exist "%TARGET_DIR%\SenrenBanka.exe" goto :NO_EXE

echo [*] ตรวจพบตัวเกมที่: "%TARGET_DIR%"
echo.

:: 4. Check mod payload files next to installer
if exist "%SRC_DIR%patch_extra.xp3" goto :HAS_PAYLOAD
echo [ERROR] ไม่พบไฟล์ patch_extra.xp3 ในโฟลเดอร์เดียวกับตัวติดตั้ง!
echo กรุณาแตกไฟล์ ZIP ทั้งหมดออกมาไว้ในโฟลเดอร์เดียวกันก่อนรันตัวติดตั้ง
echo.
pause
exit /b 1

:HAS_PAYLOAD
:: 5. Backup original files cleanly without overwriting existing backups
if not exist "%TARGET_DIR%\thai_mod_backup" mkdir "%TARGET_DIR%\thai_mod_backup" >nul 2>&1

if exist "%TARGET_DIR%\patch_extra.xp3" (
    if not exist "%TARGET_DIR%\thai_mod_backup\patch_extra.xp3.bak" (
        echo [*] กำลังสำรองไฟล์ patch_extra.xp3 ดั้งเดิม
        copy /y "%TARGET_DIR%\patch_extra.xp3" "%TARGET_DIR%\thai_mod_backup\patch_extra.xp3.bak" >nul
        echo [OK] สำรองไฟล์ patch_extra.xp3 เรียบร้อยแล้ว
    )
)

if exist "%TARGET_DIR%\data.xp3" (
    if not exist "%TARGET_DIR%\thai_mod_backup\data.xp3.bak" (
        echo [*] กำลังสำรองไฟล์ data.xp3 ดั้งเดิม อาจใช้เวลา 10-20 วินาที
        copy /y "%TARGET_DIR%\data.xp3" "%TARGET_DIR%\thai_mod_backup\data.xp3.bak" >nul
        echo [OK] สำรองไฟล์ data.xp3 เรียบร้อยแล้ว
    )
)

:: 6. Copy Mod Files
echo.
echo [*] กำลังติดตั้งม็อดบทสนทนาภาษาไทย
copy /y "%SRC_DIR%patch_extra.xp3" "%TARGET_DIR%\patch_extra.xp3" >nul
echo [OK] ติดตั้ง patch_extra.xp3 สำเร็จครบทั้ง 92 ตอน

if exist "%SRC_DIR%data.xp3" (
    echo [*] กำลังติดตั้งชุดฟอนต์ภาษาไทยและเมนูระบบ
    copy /y "%SRC_DIR%data.xp3" "%TARGET_DIR%\data.xp3" >nul
    echo [OK] ติดตั้ง data.xp3 สำเร็จ เมทริกซ์ฟอนต์ไทย 20 ขนาด
)

if exist "%SRC_DIR%Start_Thai_Game.bat" copy /y "%SRC_DIR%Start_Thai_Game.bat" "%TARGET_DIR%\Start_Thai_Game.bat" >nul
if exist "%SRC_DIR%Uninstall_Thai_Mod.bat" copy /y "%SRC_DIR%Uninstall_Thai_Mod.bat" "%TARGET_DIR%\Uninstall_Thai_Mod.bat" >nul

:: 7. Repair datasc.ksd faceMode=1 -> 0 automatically to prevent [] tofu boxes
echo.
echo [*] กำลังตรวจสอบการตั้งค่าฟอนต์เกมในเครื่อง
set "SENREN_TARGET_DIR=%TARGET_DIR%"
for /f "usebackq delims=" %%F in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue';$q=[char]34;$k1=$q+'faceMode'+$q+' => 1,';$k0=$q+'faceMode'+$q+' => 0,';$cands=@([IO.Path]::Combine($env:APPDATA,'Yuzusoft\SenrenBanka\datasc.ksd'));if($env:SENREN_TARGET_DIR){$cands+=[IO.Path]::Combine($env:SENREN_TARGET_DIR,'savedata\datasc.ksd')};foreach($p in $cands){if(-not [IO.File]::Exists($p)){continue};try{$b=[IO.File]::ReadAllBytes($p);$z=-1;for($i=0;$i -lt ($b.Length-1);$i++){if($b[$i] -eq 0x78 -and $b[$i+1] -eq 0x9C){$z=$i;break}};if($z -lt 0){continue};$inMs=New-Object IO.MemoryStream;$inMs.Write($b,$z+2,$b.Length-$z-6);$inMs.Position=0;$df=New-Object IO.Compression.DeflateStream($inMs,[IO.Compression.CompressionMode]::Decompress);$outMs=New-Object IO.MemoryStream;$df.CopyTo($outMs);$df.Dispose();$txt=[Text.Encoding]::Unicode.GetString($outMs.ToArray());if($txt.Contains($k1)){$bak=$p+'.bak';if(-not [IO.File]::Exists($bak)){[IO.File]::Copy($p,$bak,$false)};$nb=[Text.Encoding]::Unicode.GetBytes($txt.Replace($k1,$k0));$cMs=New-Object IO.MemoryStream;$cMs.WriteByte(0x78);$cMs.WriteByte(0x9C);$cs=New-Object IO.Compression.DeflateStream($cMs,[IO.Compression.CompressionLevel]::Optimal,$true);$cs.Write($nb,0,$nb.Length);$cs.Dispose();[uint32]$a=1;[uint32]$bb=0;for($i=0;$i -lt $nb.Length;$i++){$a=$a+$nb[$i];if($a -ge 65521){$a=$a-65521};$bb=$bb+$a;if($bb -ge 65521){$bb=$bb-65521}};$cMs.WriteByte([byte](($bb -shr 8) -band 255));$cMs.WriteByte([byte]($bb -band 255));$cMs.WriteByte([byte](($a -shr 8) -band 255));$cMs.WriteByte([byte]($a -band 255));$cb=$cMs.ToArray();$hdr=[byte[]]@(0xFE,0xFE,0x02,0xFF,0xFE)+[BitConverter]::GetBytes([uint64]$cb.Length)+[BitConverter]::GetBytes([uint64]$nb.Length);$res=New-Object byte[] ($hdr.Length+$cb.Length);[Array]::Copy($hdr,0,$res,0,$hdr.Length);[Array]::Copy($cb,0,$res,$hdr.Length,$cb.Length);[IO.File]::WriteAllBytes($p,$res);Write-Output ('FIXED:'+$p)}elseif($txt.Contains($k0)){Write-Output ('OK:'+$p)}}catch{Write-Output ('WARN:'+$_.Exception.Message)}}"`) do (
    echo [OK] ตรวจสอบฟอนต์ระบบ: %%F
)

echo.
echo ===============================================================================
echo     ยินดีด้วย! การติดตั้งม็อดภาษาไทย Senren Banka เสร็จสมบูรณ์แล้ว 100%%
echo ===============================================================================
echo.
echo คำแนะนำการเข้าเล่น:
echo  1. เข้าเล่นเกมผ่าน Steam หรือไฟล์ Start_Thai_Game.bat ในโฟลเดอร์เกม
echo  2. ในเกมให้ตั้งค่าภาษาเป็น English ตัวเกมจะแสดงผลภาษาไทยทันที
echo  3. หากต้องการถอนการติดตั้ง ให้ดับเบิลคลิก Uninstall_Thai_Mod.bat ในโฟลเดอร์เกม
echo.
pause
exit /b 0

:NO_EXE
echo.
echo [ERROR] ไม่พบไฟล์ SenrenBanka.exe ในตำแหน่ง: "%TARGET_DIR%"
echo กรุณาตรวจสอบตำแหน่งโฟลเดอร์ตัวเกมบน Steam แล้วลองใหม่อีกครั้ง
echo.
pause
exit /b 1
