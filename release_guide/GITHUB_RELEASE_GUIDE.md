# GitHub release and asset distribution guide

## 1. Overview and file size limitations
GitHub enforces strict file size constraints on git repositories:
- Maximum individual commit file size: 100 MB (files larger than 100 MB will be rejected by `git push`).
- Recommended repository size: under 1 GB.

In our project:
- `patch_extra.xp3` is about 175 MB (contains 92 scenarios, Thai dialogue, and choice branches).
- `data.xp3` is about 1,011 MB (contains the full 20 pre-rendered TFT font matrices, textures, and system audio/scripts).

Because both exceed the 100 MB limit, they should not be committed directly into git history. Instead, distribute them as assets on GitHub Releases, where GitHub allows asset files up to 2 GB each.

---

## 2. Packaging the release files

Before creating a GitHub release, package the mod files into zip archives:

### Package A: Full playable mod (`SenrenBanka_Thai_Mod_Full_v1.0.zip`)
Include:
1. `patch_extra.xp3` (175 MB)
2. `data.xp3` (1,011 MB)
3. The contents of `mod_installer/`:
   - `Install_Thai_Mod.bat`
   - `Start_Thai_Game.bat`
   - `Uninstall_Thai_Mod.bat`
   - `README_INSTALL_TH.md`
   - `README_INSTALL_EN.md`
   - `patch_info.json`

### Package B: Scenario-only patch (`SenrenBanka_Thai_Patch_ScenarioOnly_v1.0.zip`)
For users who already have the Thai font matrix:
1. `patch_extra.xp3` (175 MB)
2. `mod_installer/` batch scripts

---

## 3. Creating the release on GitHub

1. Open your repository on GitHub.
2. On the right sidebar, click Releases, then Draft a new release.
3. Fill in the release details:
   - Tag version: `v1.0.0`
   - Release title: `Senren＊Banka Thai Localization v1.0.0`
   - Description: Overview and installation instructions.
4. Attach `SenrenBanka_Thai_Mod_Full_v1.0.zip` or the individual `.xp3` files.
5. Click Publish release.

---

## 4. Alternative: Standalone injector
Users can also clone this repository, run `RUN_THAI_INJECTOR.bat` (or `python tools/thai_injector.py`), and generate `patch_extra.xp3` directly from their local Steam game files.
