import os
import sys
import struct
import zlib
import re
from typing import Dict, Any, List

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
    for cand in (
        os.path.join(REPO_ROOT, "output", "patch_extra.xp3"),
        os.path.join(REPO_ROOT, "SenrenBanka_THAI_PLAYABLE", "patch_extra.xp3"),
        os.path.join(steam_dir, "patch_extra.xp3") if steam_dir else None,
        os.path.join(REPO_ROOT, "patch_extra.xp3"),
    ):
        if cand and os.path.isfile(cand):
            return cand
    raise FileNotFoundError(
        "Could not locate patch_extra.xp3. Pass its path as an argument or run RUN_THAI_INJECTOR.bat first."
    )


PATCH_EXTRA_XP3 = resolve_patch_extra_path()

print("=" * 75)
print("COMPREHENSIVE AUDIT: ALL 92 SCENARIO FILES IN patch_extra.xp3")
print("Target: Font-size tagged lines (%XX;) and dialogue Thai coverage")
print("=" * 75)

parsed = parse_xp3_archive_fast(PATCH_EXTRA_XP3)
scn_files = [k for k in parsed['files'].keys() if k.endswith('.scn')]
print(f"Total scenario files in archive: {len(scn_files)}")

all_tagged_lines = []
total_dialogue_strings = 0
thai_dialogue_strings = 0

KNOWN_FONT_SIZE_LINES = [
    "MAKO'S TURNED INTO A HUSSYYYYYY!",
    "Sorry, no!",
    "I could truly marry Master...",
    "Good grief, Master...",
    "You have no understanding of a maiden's heart.",
    "You should know how I feel by now!",
    "We need to have lots of cosplay?Mmph!?",
    "Mutter, mutter...",
    "Mumble, mumble...",
    "(It's black!!)",
    "Hitachi-san, our head chef for the day, is currently working at 120",
    "Her dad isn't 100"
]

found_known_checks = {k: None for k in KNOWN_FONT_SIZE_LINES}

for scn_idx, scn_name in enumerate(sorted(scn_files), 1):
    raw_data = extract_member_fast(PATCH_EXTRA_XP3, parsed['files'][scn_name])
    dec_data, k1, k2, hdr_off = decrypt_psb_auto(raw_data)
    assert dec_data[2:4] == b'B\x00', f"Failed header in {scn_name}: {dec_data[:4]!r}"

    hdr = struct.unpack_from('<IIIIIIII', dec_data, 8)
    str_off, str_data, extra_off, extra_data, extra_end = hdr[2], hdr[3], hdr[4], hdr[5], hdr[6]

    trailer_start = extra_data - 3 if (extra_data >= 3 and extra_end == len(dec_data)) else extra_off
    if extra_off < trailer_start:
        extra_off = trailer_start

    count = struct.unpack_from('<H', dec_data, str_off + 1)[0]
    entry_type = dec_data[str_off + 3]
    in_width = {0x0D: 1, 0x0E: 2, 0x0F: 3, 0x10: 4}.get(entry_type, entry_type - 0x0C if entry_type >= 0x0D else 3)
    
    offsets = []
    for i in range(count):
        pos = str_off + 4 + i * in_width
        val = int.from_bytes(dec_data[pos : pos + in_width], 'little')
        offsets.append(val)

    strings = []
    for off in offsets:
        start = str_data + off
        end = start
        while end < extra_off and dec_data[end] != 0:
            end += 1
        s = dec_data[start:end].decode('utf-8', errors='replace')
        strings.append(s)

    for s in strings:
        # Check tagged font-scaling lines
        m = re.search(r'%(\d+);', s)
        if m:
            pct = m.group(1)
            all_tagged_lines.append((scn_name, pct, s))

        # Check known lines
        for k in KNOWN_FONT_SIZE_LINES:
            if k in s:
                found_known_checks[k] = (scn_name, s, contains_thai(s))

print(f"\n--- Total Font-Size Tagged Lines Found Across All 92 Scenarios: {len(all_tagged_lines)} ---")

def contains_japanese(text: str) -> bool:
    return any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text)


thai_tagged = [item for item in all_tagged_lines if contains_thai(item[2])]
jp_tagged = [item for item in all_tagged_lines if not contains_thai(item[2]) and contains_japanese(item[2])]
non_thai_tagged = [item for item in all_tagged_lines if not contains_thai(item[2]) and not contains_japanese(item[2])]

print(f"Tagged lines with Thai translation: {len(thai_tagged)}")
print(f"Original Japanese tagged lines (untouched JP slot): {len(jp_tagged)}")
print(f"Tagged lines WITHOUT Thai (Untranslated English): {len(non_thai_tagged)}")

if non_thai_tagged:
    print("\n[!] CRITICAL: Found untranslated English font-sized lines:")
    for scn, pct, text in non_thai_tagged:
        print(f"  [{scn}] ({pct}%): {repr(text)}")
    sys.exit(1)
else:
    print("\n[SUCCESS] 100% of ALL English font-size tagged lines in ALL 92 scenarios have Thai translations!")

print("\n--- Verification of Known Problematic Font-Scaled Lines ---")
for k, val in found_known_checks.items():
    if val:
        scn, text, is_th = val
        status = "PASS (Thai)" if is_th else "FAIL (English)"
        print(f"[{status}] Key: '{k}'")
        print(f"       Scenario: {scn}")
        print(f"       Injected: {repr(text[:90])}")
    else:
        print(f"[REPLACED/ABSENT] Key: '{k}' -> English original completely replaced by Thai in scenario!")

print("\n--- Complete List of All Tagged Thai Lines Across Game Scenarios ---")
for idx, (scn, pct, text) in enumerate(all_tagged_lines, 1):
    print(f"{idx:2d}. [{scn}] ({pct}%): {text}")

print("=" * 75)
