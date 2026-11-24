import os
import sys
import struct
import zlib
import re

sys.stdout.reconfigure(encoding='utf-8')
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

try:
    from tools.verify_full_game_thai import parse_xp3_archive_fast, extract_member_fast, contains_thai
    from tools.thai_injector import decrypt_psb_auto
    from tools.steam_locator import find_senren_steam_dir
except ImportError:
    from verify_full_game_thai import parse_xp3_archive_fast, extract_member_fast, contains_thai
    from thai_injector import decrypt_psb_auto
    from steam_locator import find_senren_steam_dir


def resolve_patch_extra_path() -> str:
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        return sys.argv[1]
    steam_dir = find_senren_steam_dir()
    candidates = [
        os.path.join(REPO_ROOT, "output", "patch_extra.xp3"),
        os.path.join(REPO_ROOT, "SenrenBanka_THAI_PLAYABLE", "patch_extra.xp3"),
        os.path.join(steam_dir, "patch_extra.xp3") if steam_dir else None,
        os.path.join(REPO_ROOT, "patch_extra.xp3"),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    raise FileNotFoundError(
        "Could not locate patch_extra.xp3. Pass its path as an argument or run RUN_THAI_INJECTOR.bat first."
    )


patch_extra_path = resolve_patch_extra_path()
print(f"[*] Auditing archive: {patch_extra_path}")
parsed = parse_xp3_archive_fast(patch_extra_path)
scn_files = [k for k in parsed['files'].keys() if k.endswith('.scn')]

# Intentional foreign-POV Romaji lines documented in JOURNEY_TH.md (Ch 418 young Lena POV)
INTENTIONAL_ROMAJI = {
    'Saa, mou shinpai arimasenyo.',
    'Ah, shinpai shitetandayo?',
}

all_untranslated_dialogue = {}
romaji_verified = 0

for scn_name in sorted(scn_files):
    raw = extract_member_fast(patch_extra_path, parsed['files'][scn_name])
    dec, _, _, _ = decrypt_psb_auto(raw)
    hdr = struct.unpack_from('<IIIIIIII', dec, 8)
    str_off, str_data, extra_off = hdr[2], hdr[3], hdr[4]
    count = struct.unpack_from('<H', dec, str_off + 1)[0]
    entry_type = dec[str_off + 3]
    in_width = {0x0D: 1, 0x0E: 2, 0x0F: 3, 0x10: 4}.get(entry_type, 3)
    strings = []
    for i in range(count):
        pos = str_off + 4 + i * in_width
        val = int.from_bytes(dec[pos : pos + in_width], 'little')
        st = str_data + val
        en = st
        while en < len(dec) and dec[en] != 0:
            en += 1
        strings.append(dec[st:en].decode('utf-8', errors='replace'))

    for s in strings:
        if s.strip() in INTENTIONAL_ROMAJI:
            romaji_verified += 1
            continue
        if contains_thai(s):
            continue
        if any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in s):
            continue
        if any(c in s for c in ['_', '*', '(', ')', '=', '::', '/', '\\', '#', '&']):
            if not ('\\%' in s or '\\n' in s or '\\r' in s):
                continue
        if re.match(r'^chapter\s+\d+-\d+$', s.strip()):
            continue
        if any(s.endswith(ext) for ext in ['.tlg', '.ks', '.ogg', '.png', '.wav']):
            continue
        words = s.strip().split()
        if len(words) >= 2 and any(w.isalpha() for w in words):
            all_untranslated_dialogue.setdefault(scn_name, set()).add(s)

if romaji_verified:
    print(f"[INFO] Verified {romaji_verified} intentional Ch 418 Romaji lines intact")
print(f"Total scenario files with untranslated English lines: {len(all_untranslated_dialogue)}")
total_distinct_lines = 0
for scn_name, lines in sorted(all_untranslated_dialogue.items()):
    print(f"\n[{scn_name}] ({len(lines)} lines):")
    for s in sorted(lines):
        print(f"  - {repr(s)}")
        total_distinct_lines += 1

print(f"\nGRAND TOTAL UNTRANSLATED ENGLISH DIALOGUE LINES: {total_distinct_lines}")
sys.exit(1 if total_distinct_lines > 0 else 0)
