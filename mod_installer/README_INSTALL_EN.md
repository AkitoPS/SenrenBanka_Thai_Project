# Senren＊Banka Thai localization: installation guide

This guide covers installing the Thai localization mod for Senren＊Banka on Steam.

---

## Prerequisites
1. A legitimate copy of Senren＊Banka on Steam (compatible with both the standard release and the 18+ Uncensored Edition).
2. Downloaded release package from [Releases](https://github.com/AkitoPS/SenrenBanka_Thai_Project/releases):
   - `patch_extra.xp3` (Thai scenario files for all 92 chapters)
   - `data.xp3` (Pre-rendered TFT font matrix and localized UI textures)
   - Installer batch scripts

---

## Installation steps

1. Extract the downloaded release ZIP.
2. Ensure `patch_extra.xp3` and `data.xp3` are in the same folder as `Install_Thai_Mod.bat`.
3. Double-click `Install_Thai_Mod.bat`.
4. The installer automatically locates your Steam directory, backs up original files to `thai_mod_backup/`, and deploys the patch.
5. Once complete, launch the game.

---

## Launching the game
- Recommended: Double-click `Start_Thai_Game.bat` in the game directory. This launches the game with `-savecloud=no` to prevent Steam Cloud save desynchronization.
- Alternative: Launch normally through Steam.

---

## Uninstallation
- Double-click `Uninstall_Thai_Mod.bat` to restore original files from backup, or
- In Steam, right-click Senren＊Banka, select Properties, go to Installed Files, and click Verify integrity of game files.
