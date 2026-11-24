"""
tools/verify_data_xp3_fonts.py — Verification script for multi-font injection in data.xp3.

Verifies:
1. XP3 magic, redirection pointer at offset 23, and real_idx_off at offset 32.
2. sen: chunk structure, hnfn boundaries, and authentic 24-byte Steam signature.
3. hnfn table decompression and presence of all 20 font paths.
4. Decrypted payload verification: every font decrypts to b"TVP pre-rendered font\\x1a"
   and contains Thai Unicode + PUA glyph codepoints (plus bit-for-bit match if
   tools/fonts_extended/ is present on disk).
5. Total archive integrity: continuity, no gaps, index bounds.
"""

import os
import sys
import struct
import zlib

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

EXPECTED_STEAM_SIG = b'\n\x00CSK`\n\xff\x07N\xb1\x82S\x00t\x00e\x00a\x00m\x00\x00\x00'

FONT_SPECS = {
    'font/font1_10.tft': {'member_idx': 4, 'adlr': 0x50634ba9, 'k1': 0x76, 'k2': 0x13, 'split': 2134, 'anomalies': {28377: 0x5f}},
    'font/font1_14.tft': {'member_idx': 5, 'adlr': 0xaff04db3, 'k1': 0xb4, 'k2': 0x1, 'split': 2150, 'anomalies': {}},
    'font/font1_20.tft': {'member_idx': 6, 'adlr': 0x2a7bb10e, 'k1': 0x1, 'k2': 0x5e, 'split': 2106, 'anomalies': {15958: 0xfd, 44140: 0x7}},
    'font/font1_26.tft': {'member_idx': 7, 'adlr': 0xe9c76dda, 'k1': 0xde, 'k2': 0x91, 'split': 2118, 'anomalies': {3563: 0x17, 49843: 0xc}},
    'font/font1_32.tft': {'member_idx': 8, 'adlr': 0xcfdd73fc, 'k1': 0x54, 'k2': 0x56, 'split': 2154, 'anomalies': {53: 0xac, 32158: 0x94, 60494: 0xea}},
    'font/font1_39.tft': {'member_idx': 9, 'adlr': 0x9fe15f6a, 'k1': 0x43, 'k2': 0x4c, 'split': 2134, 'anomalies': {25420: 0x19, 65365: 0x2f}},
    'font/font1_48.tft': {'member_idx': 10, 'adlr': 0x14d4dd79, 'k1': 0x9, 'k2': 0x5a, 'split': 2150, 'anomalies': {}},
    'font/font1_56.tft': {'member_idx': 11, 'adlr': 0xa992635b, 'k1': 0x1f, 'k2': 0xc4, 'split': 2118, 'anomalies': {}},
    'font/headfont_20.tft': {'member_idx': 12, 'adlr': 0xa3286087, 'k1': 0x56, 'k2': 0xd3, 'split': 1850, 'anomalies': {14861: 0x16, 60744: 0x6a}},
    'font/headfont_24.tft': {'member_idx': 13, 'adlr': 0x91626338, 'k1': 0x4e, 'k2': 0x27, 'split': 2150, 'anomalies': {41186: 0x68, 50733: 0x1e}},
    'font/headfont_30.tft': {'member_idx': 14, 'adlr': 0x9dd325c0, 'k1': 0x1, 'k2': 0x16, 'split': 2102, 'anomalies': {10100: 0x29}},
    'font/headfont_36.tft': {'member_idx': 15, 'adlr': 0xb030b12b, 'k1': 0xb8, 'k2': 0xa5, 'split': 2134, 'anomalies': {48319: 0xc1, 58543: 0x9b}},
    'font/sysfont_10.tft': {'member_idx': 39, 'adlr': 0xc02bf934, 'k1': 0xa4, 'k2': 0x8, 'split': 2154, 'anomalies': {2602: 0x76, 53476: 0x29}},
    'font/sysfont_12.tft': {'member_idx': 40, 'adlr': 0x5186d0, 'k1': 0x51, 'k2': 0x7b, 'split': 1862, 'anomalies': {55123: 0xf1}},
    'font/sysfont_15.tft': {'member_idx': 41, 'adlr': 0xf67bb03a, 'k1': 0x94, 'k2': 0xe2, 'split': 1894, 'anomalies': {18146: 0x98, 23674: 0xa4}},
    'font/sysfont_16.tft': {'member_idx': 42, 'adlr': 0x6dfe97cf, 'k1': 0x99, 'k2': 0x5f, 'split': 2106, 'anomalies': {32540: 0x85}},
    'font/sysfont_18.tft': {'member_idx': 43, 'adlr': 0x9251827c, 'k1': 0x6, 'k2': 0x5a, 'split': 1898, 'anomalies': {2: 0x25, 36358: 0xed, 46938: 0x5c}},
    'font/sysfont_20.tft': {'member_idx': 44, 'adlr': 0x7d89578b, 'k1': 0x4c, 'k2': 0x79, 'split': 2102, 'anomalies': {2177: 0xa4, 58496: 0xbd}},
    'font/sysfont_24.tft': {'member_idx': 45, 'adlr': 0x8b1d04d7, 'k1': 0x4c, 'k2': 0x13, 'split': 1866, 'anomalies': {1678: 0xcc, 22035: 0x25, 28470: 0x45}},
    'font/sysfont_30.tft': {'member_idx': 46, 'adlr': 0xe1286c47, 'k1': 0x1f, 'k2': 0x75, 'split': 1850, 'anomalies': {27564: 0x69}},
}


def decrypt_font(enc_bytes: bytes, spec: dict) -> bytes:
    k1 = spec['k1']
    k2 = spec['k2']
    split = spec['split']
    anom = spec['anomalies']
    dec = bytearray(len(enc_bytes))
    for i in range(len(enc_bytes)):
        if i in anom:
            k = anom[i]
        elif i < split:
            k = k1
        else:
            k = k2
        dec[i] = enc_bytes[i] ^ k
    return bytes(dec)


def tft_has_thai_glyphs(dec_bytes: bytes) -> bool:
    """Return True if a decrypted TVP TFT font includes Thai Unicode + PUA glyphs."""
    if len(dec_bytes) < 36 or dec_bytes[:22] != b"TVP pre-rendered font\x1a":
        return False
    count, ch_off, _idx_off = struct.unpack('<III', dec_bytes[24:36])
    if ch_off + count * 2 > len(dec_bytes):
        return False
    cps = set(struct.unpack(f'<{count}H', dec_bytes[ch_off : ch_off + count * 2]))
    return (0x0E01 in cps) and (0x0E49 in cps) and (0xF700 in cps) and (0xF713 in cps)


def verify_data_xp3(target_xp3: str, extended_fonts_dir: str | None = None) -> bool:
    if extended_fonts_dir is None:
        extended_fonts_dir = os.path.join(TOOLS_DIR, "fonts_extended")

    print("=" * 75)
    print(f"VERIFYING MULTI-FONT INJECTION IN: {target_xp3}")
    print("=" * 75)

    if not os.path.exists(target_xp3):
        print(f"[ERROR] Target file does not exist: {target_xp3}")
        return False

    total_size = os.path.getsize(target_xp3)
    print(f"File size: {total_size:,} bytes")

    with open(target_xp3, 'rb') as f:
        magic = f.read(11)
        if magic != b"XP3\r\n \n\x1a\x8bg\x01":
            print(f"[FAIL] Invalid XP3 magic: {magic}")
            return False
        redir_off = struct.unpack('<Q', f.read(8))[0]
        if redir_off != 23:
            print(f"[FAIL] Expected redir_off == 23, got {redir_off}")
            return False

        f.seek(redir_off)
        redir_flag = f.read(1)[0]
        if redir_flag != 0x80:
            print(f"[FAIL] Expected redir flag 0x80 at offset 23, got {hex(redir_flag)}")
            return False

        f.seek(redir_off + 9)
        real_idx_off = struct.unpack('<Q', f.read(8))[0]
        print(f"[OK] Header valid. Redirection at offset 23 -> real_idx_off = {real_idx_off:,}")

        f.seek(real_idx_off)
        idx_flag = f.read(1)[0]
        if idx_flag != 0x01:
            print(f"[FAIL] Expected zlib index flag 0x01, got {hex(idx_flag)}")
            return False
        comp_sz, uncomp_sz = struct.unpack('<QQ', f.read(16))
        idx_comp = f.read(comp_sz)
        if len(idx_comp) != comp_sz:
            print(f"[FAIL] Truncated index data: got {len(idx_comp)}, expected {comp_sz}")
            return False

        expected_total = real_idx_off + 1 + 16 + comp_sz
        if total_size != expected_total:
            print(f"[FAIL] Archive size mismatch: file has {total_size:,}, expected {expected_total:,}")
            return False
        print(f"[OK] Compressed index valid (comp_sz={comp_sz:,}, uncomp_sz={uncomp_sz:,}).")

        idx_decomp = zlib.decompress(idx_comp)
        if len(idx_decomp) != uncomp_sz:
            print(f"[FAIL] Decompressed index size mismatch: got {len(idx_decomp)}, expected {uncomp_sz}")
            return False

        if idx_decomp[:4] != b'sen:':
            print(f"[FAIL] First index chunk is not 'sen:', got {idx_decomp[:4]}")
            return False
        sen_sz = struct.unpack('<Q', idx_decomp[4:12])[0]
        if sen_sz != 40:
            print(f"[FAIL] Expected sen: chunk body size 40, got {sen_sz}")
            return False
        sen_body = idx_decomp[12:12+sen_sz]
        hnfn_off = struct.unpack('<Q', sen_body[:8])[0]
        hnfn_uncomp, hnfn_comp = struct.unpack('<II', sen_body[8:16])
        steam_sig = sen_body[16:]

        if steam_sig != EXPECTED_STEAM_SIG:
            print("[FAIL] Steam DRM digital signature corrupted or mismatch!")
            return False
        print(f"[OK] sen: chunk verified. Steam signature intact! hnfn_off={hnfn_off:,}")

        if hnfn_off + hnfn_comp != real_idx_off:
            print(f"[FAIL] Gap/overlap between hnfn table and index: {real_idx_off - (hnfn_off + hnfn_comp)}")
            return False
        print("[OK] hnfn block boundary perfectly adjacent to real_idx_off.")

        f.seek(hnfn_off)
        hnfn_raw = f.read(hnfn_comp)
        hnfn_decomp = zlib.decompress(hnfn_raw)
        if len(hnfn_decomp) != hnfn_uncomp:
            print("[FAIL] hnfn decompression size mismatch")
            return False

        hash_to_name = {}
        hpos = 0
        while hpos < len(hnfn_decomp):
            if hnfn_decomp[hpos:hpos+4] == b'hnfn':
                cz = struct.unpack('<Q', hnfn_decomp[hpos+4:hpos+12])[0]
                cb = hnfn_decomp[hpos+12:hpos+12+cz]
                hpos += 12 + cz
                rpos = 0
                while rpos + 6 <= len(cb):
                    fhash = struct.unpack('<I', cb[rpos:rpos+4])[0]
                    nlen = struct.unpack('<H', cb[rpos+4:rpos+6])[0]
                    if rpos + 6 + nlen*2 <= len(cb):
                        name = cb[rpos+6 : rpos+6+nlen*2].decode('utf-16le', errors='replace')
                        rpos += 6 + nlen*2
                        hash_to_name[fhash] = name
                    else:
                        break
            else:
                hpos += 1

        print(f"[OK] hnfn table successfully decoded with {len(hash_to_name)} file mappings.")

        pos = 12 + sen_sz
        files = []
        while pos < len(idx_decomp):
            ctype = idx_decomp[pos:pos+4]
            csz = struct.unpack('<Q', idx_decomp[pos+4:pos+12])[0]
            cbody = idx_decomp[pos+12:pos+12+csz]
            pos += 12 + csz
            if ctype == b'File':
                spos = 0
                finfo = {'index': len(files), 'sflags': 0, 'soff': 0, 'sorig': 0, 'sarc': 0, 'adlr': 0, 'iflags': 0, 'name': ''}
                while spos < len(cbody):
                    stype = cbody[spos:spos+4]
                    ssz = struct.unpack('<Q', cbody[spos+4:spos+12])[0]
                    sdata = cbody[spos+12:spos+12+ssz]
                    spos += 12 + ssz
                    if stype == b'adlr':
                        finfo['adlr'] = struct.unpack('<I', sdata[:4])[0]
                    elif stype == b'segm':
                        sflags, soff, sorig, sarc = struct.unpack('<IQQQ', sdata[:28])
                        finfo['sflags'], finfo['soff'], finfo['sorig'], finfo['sarc'] = sflags, soff, sorig, sarc
                    elif stype == b'info':
                        iflags, _iorig, _iarc, inlen = struct.unpack('<IQQH', sdata[:22])
                        finfo['iflags'] = iflags
                        finfo['name_hash'] = sdata[22:22+inlen*2].decode('utf-16le', errors='replace')
                finfo['name'] = hash_to_name.get(finfo['adlr'], finfo.get('name_hash', ''))
                files.append(finfo)

        if len(files) != 1278:
            print(f"[FAIL] Expected 1278 files in index, got {len(files)}")
            return False
        print("[OK] All 1,278 file entries parsed.")

        last_f = files[-1]
        if last_f['soff'] + last_f['sarc'] != hnfn_off:
            print(f"[FAIL] Last file data end ({last_f['soff'] + last_f['sarc']}) != hnfn_off ({hnfn_off})")
            return False
        print("[OK] Trailing file payload seamlessly connects to hnfn_off.")

        has_ext_dir = os.path.isdir(extended_fonts_dir)
        print("\n" + "-" * 75)
        if has_ext_dir:
            print(f"VERIFYING ALL 20 TFT FONTS (BIT-FOR-BIT AGAINST {extended_fonts_dir}):")
        else:
            print("VERIFYING ALL 20 TFT FONTS (THAI + PUA GLYPH INDEX CHECK):")
        print("-" * 75)
        all_fonts_ok = True

        for font_rel_path, spec in FONT_SPECS.items():
            base_filename = os.path.basename(font_rel_path)
            m_idx = spec['member_idx']
            finfo = files[m_idx]

            if finfo['adlr'] != spec['adlr']:
                print(f"[FAIL] {base_filename} (Member {m_idx}): adlr mismatch!")
                all_fonts_ok = False
                continue

            if finfo['sflags'] != 0 or finfo['iflags'] != 0x80000000:
                print(f"[FAIL] {base_filename} (Member {m_idx}): unexpected flags sflags={finfo['sflags']}, iflags={hex(finfo['iflags'])}")
                all_fonts_ok = False
                continue

            f.seek(finfo['soff'])
            enc_payload = f.read(finfo['sarc'])
            dec_bytes = decrypt_font(enc_payload, spec)
            if dec_bytes[:22] != b"TVP pre-rendered font\x1a":
                print(f"[FAIL] {base_filename} (Member {m_idx}): decrypted header magic mismatch")
                all_fonts_ok = False
                continue

            if not tft_has_thai_glyphs(dec_bytes):
                print(f"[FAIL] {base_filename} (Member {m_idx}): missing Thai/PUA glyph range!")
                all_fonts_ok = False
                continue

            mode_label = "THAI+PUA OK"
            if has_ext_dir:
                ext_file_path = os.path.join(extended_fonts_dir, base_filename)
                if not os.path.exists(ext_file_path):
                    print(f"[FAIL] Reference extended font missing: {ext_file_path}")
                    all_fonts_ok = False
                    continue
                with open(ext_file_path, 'rb') as ef:
                    expected_bytes = ef.read()
                if dec_bytes != expected_bytes:
                    print(f"[FAIL] {base_filename} (Member {m_idx}): bit-for-bit mismatch against {ext_file_path}")
                    all_fonts_ok = False
                    continue
                mode_label = "100% BIT-FOR-BIT MATCH"

            print(f"[PASS] Member {m_idx:2d} | {base_filename:16s} | Offset: {finfo['soff']:10,d} | Size: {len(dec_bytes):9,d} B | {mode_label}")

        print("-" * 75)
        if all_fonts_ok:
            print("[SUCCESS] ALL 20 EXTENDED FONTS VERIFIED IN DATA.XP3!")
            print("=" * 75)
            return True
        else:
            print("[FAILURE] ONE OR MORE FONTS FAILED VERIFICATION.")
            print("=" * 75)
            return False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        steam_dir = find_senren_steam_dir()
        target = next(
            (p for p in [
                os.path.join(REPO_ROOT, "output", "data.xp3"),
                os.path.join(REPO_ROOT, "SenrenBanka_THAI_PLAYABLE", "data.xp3"),
                os.path.join(steam_dir, "data.xp3") if steam_dir else None,
            ] if p and os.path.isfile(p)),
            os.path.join(REPO_ROOT, "SenrenBanka_THAI_PLAYABLE", "data.xp3"),
        )
    fonts_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(TOOLS_DIR, "fonts_extended")
    success = verify_data_xp3(target, fonts_dir)
    sys.exit(0 if success else 1)
