import os
import sys
import struct
import zlib
import re

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
sys.path.insert(0, 'tool')

from tool.verify_full_game_thai import parse_xp3_archive_fast, extract_member_fast, contains_thai
from tool.thai_injector import decrypt_psb_auto

parsed = parse_xp3_archive_fast('SenrenBanka_THAI_PLAYABLE/patch_extra.xp3')
scn_files = [k for k in parsed['files'].keys() if k.endswith('.scn')]

all_untranslated_dialogue = {}

for scn_name in sorted(scn_files):
    raw = extract_member_fast('SenrenBanka_THAI_PLAYABLE/patch_extra.xp3', parsed['files'][scn_name])
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
        while en < len(dec) and dec[en] != 0: en += 1
        strings.append(dec[st:en].decode('utf-8', errors='replace'))

    for s in strings:
        if contains_thai(s): continue
        if any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in s): continue
        if any(c in s for c in ['_', '*', '(', ')', '=', '::', '/', '\\', '#', '&']): 
            # allow \%
            if not ('\\%' in s or '\\n' in s or '\\r' in s):
                continue
        # ignore chapter headers like 'chapter 1-1'
        if re.match(r'^chapter\s+\d+-\d+$', s.strip()):
            continue
        # ignore asset names, technical symbols, sound files
        if any(s.endswith(ext) for ext in ['.tlg', '.ks', '.ogg', '.png', '.wav']):
            continue
        words = s.strip().split()
        if len(words) >= 2 and any(w.isalpha() for w in words):
            all_untranslated_dialogue.setdefault(scn_name, set()).add(s)

print(f"Total scenario files with untranslated English lines: {len(all_untranslated_dialogue)}")
total_distinct_lines = 0
for scn_name, lines in sorted(all_untranslated_dialogue.items()):
    print(f"\n[{scn_name}] ({len(lines)} lines):")
    for s in sorted(lines):
        print(f"  - {repr(s)}")
        total_distinct_lines += 1

print(f"\nGRAND TOTAL UNTRANSLATED ENGLISH DIALOGUE LINES: {total_distinct_lines}")
