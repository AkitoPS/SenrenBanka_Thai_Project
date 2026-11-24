"""
tools/fix_facemode.py — Configures Senren*Banka to use Default Embedded TFT Fonts (faceMode = 0).
Fixes tofu boxes [] and horizontal space gaps caused by MS Gothic fallback.
"""

import os
import sys
import zlib
import struct
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

try:
    from tools.steam_locator import find_senren_steam_dir
except ImportError:
    from steam_locator import find_senren_steam_dir

APPDATA_DIR = os.path.join(os.environ.get('APPDATA', ''), 'Yuzusoft', 'SenrenBanka')
PLAYABLE_DIR = os.path.join(REPO_ROOT, "SenrenBanka_THAI_PLAYABLE")
BACKUP_DIR = os.path.join(REPO_ROOT, "archive", "appdata_backup")


def pack_ksd(text: str) -> bytes:
    raw_utf16 = text.encode('utf-16le')
    comp = zlib.compress(raw_utf16)
    magic = b'\xfe\xfe\x02\xff\xfe'
    hdr = magic + struct.pack('<QQ', len(comp), len(raw_utf16))
    return hdr + comp


def unpack_ksd(data: bytes) -> str:
    off = data.find(b'x\x9c')
    assert off >= 0, "Not a valid compressed KSD"
    return zlib.decompress(data[off:]).decode('utf-16le', errors='ignore')


def fix_ksd_file(sc_path: str) -> bool:
    if not os.path.exists(sc_path):
        return False

    print(f"\n[*] Processing datasc.ksd at: {sc_path}")
    # Backup next to datasc.ksd AND in archive/appdata_backup
    bak_beside = sc_path + ".bak"
    if not os.path.exists(bak_beside):
        shutil.copy2(sc_path, bak_beside)
        print(f"  [✓] Backed up beside file: {bak_beside}")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    parent_tag = "appdata" if "AppData" in sc_path else "playable"
    backup_file = os.path.join(BACKUP_DIR, f"datasc_{parent_tag}_backup.ksd")
    if not os.path.exists(backup_file):
        shutil.copy2(sc_path, backup_file)
        print(f"  [✓] Backed up to: {backup_file}")

    with open(sc_path, 'rb') as f:
        raw_data = f.read()
    text = unpack_ksd(raw_data)

    if '"faceMode" => 1,' in text:
        text = text.replace('"faceMode" => 1,', '"faceMode" => 0,')
        packed = pack_ksd(text)
        with open(sc_path, 'wb') as f:
            f.write(packed)
        print("  [✓] Replaced '\"faceMode\" => 1,' with '\"faceMode\" => 0,'")
    elif '"faceMode" => 0,' in text:
        print("  [✓] 'faceMode' is already set to 0 (Default Embedded Font mode).")
    else:
        print("  [!] 'faceMode' setting key not found in datasc.ksd.")
        return True

    with open(sc_path, 'rb') as f:
        verify_text = unpack_ksd(f.read())
    assert '"faceMode" => 0,' in verify_text, f"Verification failed for {sc_path}: faceMode is not 0"
    print(f"  [✓] Verified {sc_path}: faceMode == 0 confirmed!")
    return True


def main():
    print("=" * 65)
    print("FIXING SENREN＊BANKA FONT MODE (faceMode -> 0)")
    print("=" * 65)

    targets = [
        os.path.join(APPDATA_DIR, "datasc.ksd"),
        os.path.join(PLAYABLE_DIR, "savedata", "datasc.ksd"),
        os.path.join(REPO_ROOT, "savedata", "datasc.ksd"),
    ]

    fixed_any = False
    for t in targets:
        if os.path.exists(t):
            if fix_ksd_file(t):
                fixed_any = True

    if not fixed_any:
        print("[!] No datasc.ksd files found in AppData or savedata folders (normal if game not launched yet).")

    # Also sync loose extended fonts if tools/fonts_extended exists
    steam_dir = find_senren_steam_dir()
    ext_dir = os.path.join(TOOLS_DIR, "fonts_extended")
    if os.path.isdir(ext_dir):
        font_targets = [os.path.join(PLAYABLE_DIR, "font")] if os.path.isdir(PLAYABLE_DIR) else []
        if steam_dir:
            font_targets.append(os.path.join(steam_dir, "font"))

        for fdir in font_targets:
            os.makedirs(fdir, exist_ok=True)
            for fname in ("font1_32.tft", "font1_39.tft"):
                src = os.path.join(ext_dir, fname)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(fdir, fname))
                    print(f"[✓] Synced {fname} to {fdir}")

    print("\n" + "=" * 65)
    print("SUCCESS: FONT MODE CHECK/REPAIR COMPLETED!")
    print("=" * 65)


if __name__ == '__main__':
    main()
