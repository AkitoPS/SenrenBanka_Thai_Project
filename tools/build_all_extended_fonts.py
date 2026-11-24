"""
tools/build_all_extended_fonts.py — Universal TFT Font Matrix Generator

Generates all 20 extended TFT fonts into tools/fonts_extended/ with:
1. Complete Thai characters (U+0E01..U+0E5B) from Noto Sans Thai Looped
   (with Tahoma for U+0E27 Wo Waen).
2. PUA shaped characters (U+F700..U+F71F) for upper vowels, tone marks,
   cut-stem consonants, and descender vowels.
3. Zero-advance metrics for all combining marks and PUA marks.
4. Clean punctuation '!' and '?' from Leelawadee UI (Weight 600 Semibold).
5. Full preservation of all original Japanese glyphs.
6. Auto-extraction & decryption of base fonts from data.xp3 if not already present.
"""

import os
import sys
import glob
import shutil
import struct
import zlib
import ctypes
from ctypes import wintypes
from collections import Counter

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

# --- Windows GDI Structures ---

class FIXED(ctypes.Structure):
    _fields_ = [('fract', wintypes.WORD), ('value', wintypes.SHORT)]

class MAT2(ctypes.Structure):
    _fields_ = [
        ('eM11', FIXED), ('eM12', FIXED),
        ('eM21', FIXED), ('eM22', FIXED)
    ]

class POINT(ctypes.Structure):
    _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

class GLYPHMETRICS(ctypes.Structure):
    _fields_ = [
        ('gmBlackBoxX', wintypes.UINT),
        ('gmBlackBoxY', wintypes.UINT),
        ('gmptGlyphOrigin', POINT),
        ('gmCellIncX', wintypes.SHORT),
        ('gmCellIncY', wintypes.SHORT)
    ]

# --- TFT Compression & Decompression ---

def compress_tft_glyph(pixels):
    if not pixels:
        return b''
    out = bytearray()
    i = 0
    n = len(pixels)
    while i < n:
        val = min(64, max(0, pixels[i]))
        out.append(val)
        j = i + 1
        while j < n and min(64, max(0, pixels[j])) == val:
            j += 1
        run_len = j - i
        if run_len == 2:
            out.append(val)
        elif run_len > 2:
            repeats = run_len - 1
            while repeats > 0:
                chunk = min(repeats, 191)
                if chunk == 1:
                    out.append(val)
                    repeats -= 1
                else:
                    out.append(0x40 + chunk)
                    repeats -= chunk
        i = j
    return bytes(out)

def decompress_tft_glyph(data, total_pixels):
    dest = bytearray()
    ptr = 0
    while len(dest) < total_pixels and ptr < len(data):
        b = data[ptr]
        ptr += 1
        if b >= 0x41:
            length = b - 0x40
            last = dest[-1]
            dest.extend([last] * length)
        else:
            dest.append(b)
    return bytes(dest)

def decompress_tft_glyph_exact(data, total_pixels):
    dest = bytearray()
    ptr = 0
    while len(dest) < total_pixels and ptr < len(data):
        b = data[ptr]
        ptr += 1
        if b >= 0x41:
            if not dest:
                return None, ptr
            dest.extend([dest[-1]] * (b - 0x40))
        else:
            dest.append(b)
    return bytes(dest), ptr

# --- Thai Combining Marks (Zero-Advance) ---

THAI_COMBINING_MARKS = {
    0x0E31,  # ั (Mai Han-Akat)
    0x0E34, 0x0E35, 0x0E36, 0x0E37,  # ิ ี ึ ื
    0x0E38, 0x0E39, 0x0E3A,  # ุ ู ฺ
    0x0E47,  # ็ (Maitaikhu)
    0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C,  # ่ ้ ๊ ๋ ์
    0x0E4D,  # ํ (Nikkhahit)
    0x0E4E,  # ๎ (Yamakkan)
}

TARGET_FONTS = [
    # headfont (4)
    "headfont_20.tft", "headfont_24.tft", "headfont_30.tft", "headfont_36.tft",
    # sysfont (8)
    "sysfont_10.tft", "sysfont_12.tft", "sysfont_15.tft", "sysfont_16.tft",
    "sysfont_18.tft", "sysfont_20.tft", "sysfont_24.tft", "sysfont_30.tft",
    # font1 (8)
    "font1_10.tft", "font1_14.tft", "font1_20.tft", "font1_26.tft",
    "font1_32.tft", "font1_39.tft", "font1_48.tft", "font1_56.tft",
]

def rasterize_thai_glyph(hdc, cp, gm, mat, gdi32):
    GGO_GRAY8_BITMAP = 6
    size = gdi32.GetGlyphOutlineW(hdc, cp, GGO_GRAY8_BITMAP, ctypes.byref(gm), 0, None, ctypes.byref(mat))
    if size == -1 or size == 0:
        return {
            'w': 0, 'h': 0, 'ox': 0, 'oy': 0,
            'incX': gm.gmCellIncX, 'incY': 0, 'inc': gm.gmCellIncX,
            'pixels': []
        }
    buf = (ctypes.c_ubyte * size)()
    gdi32.GetGlyphOutlineW(hdc, cp, GGO_GRAY8_BITMAP, ctypes.byref(gm), size, buf, ctypes.byref(mat))
    pitch = (gm.gmBlackBoxX + 3) & ~3
    pixels = []
    for y in range(gm.gmBlackBoxY):
        for x in range(gm.gmBlackBoxX):
            pixels.append(buf[y * pitch + x])
    return {
        'w': gm.gmBlackBoxX,
        'h': gm.gmBlackBoxY,
        'ox': gm.gmptGlyphOrigin.x,
        'oy': gm.gmptGlyphOrigin.y,
        'incX': gm.gmCellIncX,
        'incY': gm.gmCellIncY,
        'inc': gm.gmCellIncX,
        'pixels': pixels
    }

def generate_thai_glyphs(font_height, shift_left, elevate_tone, elevate_am):
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hdc = user32.GetDC(0)

    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansThaiLooped-Regular.ttf'))
    res = gdi32.AddFontResourceExW(font_path, 0x10, 0)
    assert res > 0, f"Failed to load font from {font_path}"

    hfont = gdi32.CreateFontW(font_height, 0, 0, 0, 400, False, False, False, 222, 0, 0, 4, 0, 'Noto Sans Thai Looped')
    old_font = gdi32.SelectObject(hdc, hfont)

    mat = MAT2()
    mat.eM11.value = 1
    mat.eM22.value = 1
    gm = GLYPHMETRICS()

    glyphs = {}

    # 1. Base Thai characters (U+0E01..U+0E5B)
    for cp in range(0x0E01, 0x0E5C):
        if cp == 0x0E27:
            # Use Tahoma for ว (Wo Waen) to avoid Noto Sans' wide flat bottom loop that looks like an underline
            hfont_tahoma = gdi32.CreateFontW(font_height, 0, 0, 0, 400, False, False, False, 222, 0, 0, 4, 0, 'Tahoma')
            gdi32.SelectObject(hdc, hfont_tahoma)
            g = rasterize_thai_glyph(hdc, cp, gm, mat, gdi32)
            gdi32.SelectObject(hdc, hfont)
            gdi32.DeleteObject(hfont_tahoma)
        else:
            g = rasterize_thai_glyph(hdc, cp, gm, mat, gdi32)
        if cp in THAI_COMBINING_MARKS:
            g['incX'] = 0
            g['incY'] = 0
            g['inc'] = 0
        glyphs[cp] = g

    # 2. PUA Characters (U+F700..U+F71F)
    # 0xF700: ฐ without lower curve
    base_tho = glyphs[0x0E10]
    crop_h = max(1, base_tho['oy'])
    cropped_pix = base_tho['pixels'][:crop_h * base_tho['w']]
    glyphs[0xF700] = {
        'w': base_tho['w'], 'h': crop_h,
        'ox': base_tho['ox'], 'oy': base_tho['oy'],
        'incX': base_tho['incX'], 'incY': 0, 'inc': base_tho['inc'],
        'pixels': cropped_pix
    }

    # 0xF701..0xF704: Upper vowels shifted left for tall consonants
    for i, base_cp in enumerate([0x0E34, 0x0E35, 0x0E36, 0x0E37]):
        pua_cp = 0xF701 + i
        b = glyphs[base_cp]
        glyphs[pua_cp] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'] - shift_left, 'oy': b['oy'],
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    # 0xF705..0xF709: Tone marks shifted left for tall consonants
    for i, base_cp in enumerate([0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C]):
        pua_cp = 0xF705 + i
        b = glyphs[base_cp]
        glyphs[pua_cp] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'] - shift_left, 'oy': b['oy'],
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    # 0xF70A..0xF70E: Tone marks normal lower level
    for i, base_cp in enumerate([0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C]):
        pua_cp = 0xF70A + i
        b = glyphs[base_cp]
        glyphs[pua_cp] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'], 'oy': b['oy'],
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    # 0xF70F: ญ without lower curve
    base_yo = glyphs[0x0E0D]
    crop_h = max(1, base_yo['oy'])
    cropped_pix = base_yo['pixels'][:crop_h * base_yo['w']]
    glyphs[0xF70F] = {
        'w': base_yo['w'], 'h': crop_h,
        'ox': base_yo['ox'], 'oy': base_yo['oy'],
        'incX': base_yo['incX'], 'incY': 0, 'inc': base_yo['inc'],
        'pixels': cropped_pix
    }

    # 0xF710: ั shifted left
    b = glyphs[0x0E31]
    glyphs[0xF710] = {
        'w': b['w'], 'h': b['h'],
        'ox': b['ox'] - shift_left, 'oy': b['oy'],
        'incX': 0, 'incY': 0, 'inc': 0,
        'pixels': list(b['pixels'])
    }

    # 0xF711: ํ shifted left
    b = glyphs[0x0E4D]
    glyphs[0xF711] = {
        'w': b['w'], 'h': b['h'],
        'ox': b['ox'] - shift_left, 'oy': b['oy'],
        'incX': 0, 'incY': 0, 'inc': 0,
        'pixels': list(b['pixels'])
    }

    # 0xF712: ็ shifted left
    b = glyphs[0x0E47]
    glyphs[0xF712] = {
        'w': b['w'], 'h': b['h'],
        'ox': b['ox'] - shift_left, 'oy': b['oy'],
        'incX': 0, 'incY': 0, 'inc': 0,
        'pixels': list(b['pixels'])
    }

    # 0xF713..0xF717: Tone marks at HIGH level (above upper vowels)
    for i, base_cp in enumerate([0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C]):
        pua_cp = 0xF713 + i
        b = glyphs[base_cp]
        glyphs[pua_cp] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'], 'oy': b['oy'] + elevate_tone,
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    # 0xF718..0xF71A: Lower vowels shifted down for descenders
    for i, base_cp in enumerate([0x0E38, 0x0E39, 0x0E3A]):
        pua_cp = 0xF718 + i
        b = glyphs[base_cp]
        glyphs[pua_cp] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'], 'oy': b['oy'] - shift_left,
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    # 0xF71B..0xF71F: Tone marks at HIGH-LEFT level (above upper vowels on tall consonants)
    for i, base_cp in enumerate([0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C]):
        pua_cp = 0xF71B + i
        b = glyphs[base_cp]
        glyphs[pua_cp] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'] - shift_left, 'oy': b['oy'] + elevate_tone,
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    # 3. Punctuation: Rasterize '!' (0x21) and '?' (0x3F) from Leelawadee UI (Weight 600 Semibold)
    hfont_punct = gdi32.CreateFontW(font_height, 0, 0, 0, 600, False, False, False, 222, 0, 0, 4, 0, 'Leelawadee UI')
    gdi32.SelectObject(hdc, hfont_punct)
    glyphs[0x21] = rasterize_thai_glyph(hdc, 0x21, gm, mat, gdi32)
    glyphs[0x3F] = rasterize_thai_glyph(hdc, 0x3F, gm, mat, gdi32)
    gdi32.SelectObject(hdc, hfont)
    gdi32.DeleteObject(hfont_punct)

    gdi32.SelectObject(hdc, old_font)
    gdi32.DeleteObject(hfont)
    user32.ReleaseDC(0, hdc)
    gdi32.RemoveFontResourceExW(font_path, 0x10, 0)
    return glyphs

# --- Decryption of TFT from XP3 if needed ---

def decrypt_tft_buffer(raw: bytes) -> bytearray:
    exp_magic = b"TVP pre-rendered font\x1a"
    cand_k1 = [raw[i] ^ exp_magic[i] for i in range(len(exp_magic))]
    k1 = Counter(cand_k1).most_common(1)[0][0]

    dec_hdr = bytearray([b ^ k1 for b in raw[:36]])
    dec_hdr[:22] = exp_magic
    version = dec_hdr[22]
    uflag = dec_hdr[23]
    count, ch_off, idx_off = struct.unpack('<III', dec_hdr[24:36])

    sample_size = min(count, 50)
    cand_k2 = []
    for i in range(sample_size):
        cand_k2.append(raw[idx_off + i*20 + 18])
        cand_k2.append(raw[idx_off + i*20 + 19])
    k2 = Counter(cand_k2).most_common(1)[0][0]

    metric_records = []
    for i in range(count):
        rec = bytes([b ^ k2 for b in raw[idx_off + i*20 : idx_off + (i+1)*20]])
        off, w, h = struct.unpack('<IHh', rec[:8])
        if w > 0 and h > 0:
            metric_records.append((off, w, h))
    metric_records.sort(key=lambda x: x[0])

    ok1_offsets = []
    ok2_offsets = []
    for idx in range(len(metric_records)):
        off, w, h = metric_records[idx]
        if off > 5000: break
        total = w * h
        next_off = metric_records[idx+1][0] if idx + 1 < len(metric_records) else off + total * 2
        data_len = next_off - off
        b1 = bytes([b ^ k1 for b in raw[off:next_off]])
        p1, ptr1 = decompress_tft_glyph_exact(b1, total)
        ok1 = (p1 is not None and len(p1) == total and ptr1 == data_len and max(p1) <= 64)
        b2 = bytes([b ^ k2 for b in raw[off:next_off]])
        p2, ptr2 = decompress_tft_glyph_exact(b2, total)
        ok2 = (p2 is not None and len(p2) == total and ptr2 == data_len and max(p2) <= 64)
        if ok1 and not ok2:
            ok1_offsets.append(off)
        elif not ok1 and ok2:
            ok2_offsets.append(off)

    last_ok1_off = max(ok1_offsets) if ok1_offsets else 0
    first_ok2_off = min(ok2_offsets) if ok2_offsets else len(raw)
    straddle_glyphs = [(off, w, h) for off, w, h in metric_records if last_ok1_off < off < first_ok2_off]

    found_split = None
    if straddle_glyphs:
        s_off, s_w, s_h = straddle_glyphs[-1]
        s_total = s_w * s_h
        next_offs = [off for off, _, _ in metric_records if off > s_off]
        next_limit = next_offs[0] if next_offs else s_off + 2000
        s_data_len = next_limit - s_off
        for s in range(s_off, next_limit):
            test_b = bytearray(raw[s_off : next_limit])
            for i in range(len(test_b)):
                key = k1 if (s_off + i) < s else k2
                test_b[i] ^= key
            p, ptr = decompress_tft_glyph_exact(test_b, s_total)
            if p is not None and len(p) == s_total and ptr == s_data_len and max(p) <= 64:
                found_split = s
                break
    if found_split is None:
        found_split = (last_ok1_off + first_ok2_off) // 2

    dec = bytearray(len(raw))
    for i in range(found_split): dec[i] = raw[i] ^ k1
    for i in range(found_split, len(raw)): dec[i] = raw[i] ^ k2
    dec[:36] = dec_hdr

    # Auto-fix single-byte glitches
    for i in range(count):
        rec = dec[idx_off + i*20 : idx_off + (i+1)*20]
        off, w, h = struct.unpack('<IHh', rec[:8])
        if w > 0 and h > 0:
            total = w * h
            try:
                pix = decompress_tft_glyph(dec[off:], total)
                if len(pix) == total and max(pix) <= 64:
                    continue
            except:
                pass
            fixed = False
            search_len = min(len(dec) - off, 128)
            for pos in range(off, off + search_len):
                orig_val = dec[pos]
                for cand in range(256):
                    if cand == orig_val: continue
                    dec[pos] = cand
                    try:
                        p = decompress_tft_glyph(dec[off:], total)
                        if len(p) == total and max(p) <= 64:
                            fixed = True
                            break
                    except:
                        pass
                if fixed: break
                dec[pos] = orig_val
            assert fixed, f"Failed to fix glyph {i} at offset {off}"

    return dec

def ensure_base_fonts(base_dir: str):
    os.makedirs(base_dir, exist_ok=True)
    missing = [f for f in TARGET_FONTS if not os.path.isfile(os.path.join(base_dir, f))]
    if not missing:
        return

    # Check tools/<f>_orig.tft
    for f in list(missing):
        name_no_ext = f[:-4]
        tool_orig = os.path.join(TOOLS_DIR, f'{name_no_ext}_orig.tft')
        if os.path.isfile(tool_orig):
            shutil.copyfile(tool_orig, os.path.join(base_dir, f))
            missing.remove(f)

    # Check %TEMP%/krkr_*
    if missing:
        for temp_tft in glob.glob(os.path.expandvars('%TEMP%/krkr_*/*.tft')):
            b = os.path.basename(temp_tft)
            if b in missing:
                shutil.copyfile(temp_tft, os.path.join(base_dir, b))
                missing.remove(b)

    # Decrypt remaining from data.xp3 (searches backup, Steam all drives, local)
    if missing:
        steam_dir = find_senren_steam_dir()
        xp3_candidates = [
            os.path.join(REPO_ROOT, 'archive', 'original_game_backup', 'data.xp3'),
            os.path.join(steam_dir, 'thai_mod_backup', 'data.xp3.bak') if steam_dir else None,
            os.path.join(steam_dir, 'data.xp3') if steam_dir else None,
            os.path.join(REPO_ROOT, 'SenrenBanka_THAI_PLAYABLE', 'data.xp3'),
            os.path.join(REPO_ROOT, 'data.xp3'),
        ]
        xp3_path = next((p for p in xp3_candidates if p and os.path.isfile(p)), None)
        assert xp3_path, f"Cannot find data.xp3 to decrypt missing fonts: {missing}"

        with open(xp3_path, 'rb') as f: orig = f.read()
        redir = struct.unpack('<Q', orig[11:19])[0]
        real_idx = struct.unpack('<Q', orig[redir + 9:redir + 17])[0] if redir == 23 else redir
        csz, usz = struct.unpack('<QQ', orig[real_idx+1:real_idx+17])
        decomp = zlib.decompress(orig[real_idx+17:real_idx+17+csz])
        sen_sz = struct.unpack('<Q', decomp[4:12])[0]
        sen_body = decomp[12:12+sen_sz]
        hnfn_off = struct.unpack('<Q', sen_body[:8])[0]
        hnfn_uncomp, hnfn_comp = struct.unpack('<II', sen_body[8:16])
        hnfn_decomp = zlib.decompress(orig[hnfn_off:hnfn_off+hnfn_comp])

        hash_to_name = {}
        pos = 0
        while pos < len(hnfn_decomp):
            if hnfn_decomp[pos:pos+4] == b'hnfn':
                cz = struct.unpack('<Q', hnfn_decomp[pos+4:pos+12])[0]
                cb = hnfn_decomp[pos+12:pos+12+cz]
                pos += 12 + cz
                rpos = 0
                while rpos + 6 <= len(cb):
                    fhash = struct.unpack('<I', cb[rpos:rpos+4])[0]
                    nlen = struct.unpack('<H', cb[rpos+4:rpos+6])[0]
                    if rpos + 6 + nlen*2 <= len(cb):
                        name = cb[rpos+6 : rpos+6+nlen*2].decode('utf-16le', errors='replace')
                        rpos += 6 + nlen*2
                        hash_to_name[fhash] = name
                    else: break
            else: pos += 1

        pos = 12 + sen_sz
        while pos < len(decomp) and missing:
            ct = decomp[pos:pos+4]
            cz = struct.unpack('<Q', decomp[pos+4:pos+12])[0]
            cb = decomp[pos+12:pos+12+cz]
            pos += 12 + cz
            if ct == b'File':
                spos = 0
                adlr, soff, sorig, sarc, sflags = 0, 0, 0, 0, 0
                while spos < len(cb):
                    st = cb[spos:spos+4]
                    sz = struct.unpack('<Q', cb[spos+4:spos+12])[0]
                    sd = cb[spos+12:spos+12+sz]
                    spos += 12 + sz
                    if st == b'adlr': adlr = struct.unpack('<I', sd[:4])[0]
                    elif st == b'segm': sflags, soff, sorig, sarc = struct.unpack('<IQQQ', sd[:28])
                name = hash_to_name.get(adlr, '')
                base = os.path.basename(name)
                if base in missing:
                    raw = orig[soff:soff+sarc]
                    if sflags & 7 == 1: raw = zlib.decompress(raw)
                    dec = decrypt_tft_buffer(raw)
                    with open(os.path.join(base_dir, base), 'wb') as df:
                        df.write(dec)
                    missing.remove(base)

# --- Core TFT Extension Logic ---

def extend_single_tft(base_tft_path: str, output_tft_path: str, font_size: int):
    # Proportional typography scaling
    font_height = -round(font_size * 1.125)
    shift_left = max(2, round(font_size * 5 / 32))
    elevate_tone = max(3, round(font_size * 8 / 32))
    elevate_am = max(3, round(font_size * 9 / 32))

    with open(base_tft_path, 'rb') as f:
        data = f.read()

    assert data[:22] == b"TVP pre-rendered font\x1a", f"Invalid magic in {base_tft_path}"
    version = data[22]
    uflag = data[23]
    orig_count, orig_ch_off, orig_idx_off = struct.unpack('<III', data[24:36])
    orig_chars = struct.unpack(f'<{orig_count}H', data[orig_ch_off : orig_ch_off + orig_count*2])

    existing_glyphs = {}
    for i in range(orig_count):
        cp = orig_chars[i]
        rec = data[orig_idx_off + i*20 : orig_idx_off + (i+1)*20]
        off, w, h, ox, oy, incX, incY, inc, res = struct.unpack('<IHhhhhhhH', rec)
        total_pix = w * h
        if total_pix > 0:
            pix = decompress_tft_glyph(data[off:], total_pix)
        else:
            pix = b''
        existing_glyphs[cp] = {
            'w': w, 'h': h, 'ox': ox, 'oy': oy,
            'incX': incX, 'incY': incY, 'inc': inc,
            'pixels': list(pix)
        }

    # Generate Thai & PUA glyphs
    thai_glyphs = generate_thai_glyphs(font_height, shift_left, elevate_tone, elevate_am)

    all_glyphs = dict(existing_glyphs)
    for cp, g in thai_glyphs.items():
        all_glyphs[cp] = g
    sorted_cps = sorted(all_glyphs.keys())
    total_count = len(sorted_cps)

    hdr_len = 36
    cur_data_off = hdr_len
    comp_data_blocks = bytearray()
    metric_records = []

    for cp in sorted_cps:
        g = all_glyphs[cp]
        w, h = g['w'], g['h']
        if w > 0 and h > 0 and len(g['pixels']) == w * h:
            comp_bytes = compress_tft_glyph(g['pixels'])
            glyph_off = cur_data_off
            comp_data_blocks.extend(comp_bytes)
            cur_data_off += len(comp_bytes)
        else:
            glyph_off = 0

        rec = struct.pack(
            '<IHhhhhhhH',
            glyph_off,
            w,
            h,
            g['ox'],
            g['oy'],
            g['incX'],
            g['incY'],
            g['inc'],
            0
        )
        metric_records.append(rec)

    new_ch_index_off = cur_data_off
    new_index_off = new_ch_index_off + total_count * 2

    header = bytearray()
    header.extend(b"TVP pre-rendered font\x1a")
    header.append(version)
    header.append(uflag)
    header.extend(struct.pack('<III', total_count, new_ch_index_off, new_index_off))
    assert len(header) == 36

    ch_index_bytes = bytearray()
    for cp in sorted_cps:
        ch_index_bytes.extend(struct.pack('<H', cp))

    metric_bytes = b''.join(metric_records)
    full_tft = bytes(header) + bytes(comp_data_blocks) + bytes(ch_index_bytes) + metric_bytes

    os.makedirs(os.path.dirname(output_tft_path), exist_ok=True)
    with open(output_tft_path, 'wb') as f:
        f.write(full_tft)

    return total_count, len(full_tft)

def build_all():
    base_dir = os.path.join(os.path.dirname(__file__), 'fonts_base')
    output_dir = os.path.join(os.path.dirname(__file__), 'fonts_extended')
    ensure_base_fonts(base_dir)

    print("=" * 70)
    print("Building all 20 Extended TFT Fonts with Thai Typography Matrix")
    print("=" * 70)

    success_count = 0
    for font_name in TARGET_FONTS:
        # Extract size from filename e.g. headfont_20.tft -> 20
        size_str = font_name.split('_')[1].split('.')[0]
        font_size = int(size_str)

        base_path = os.path.join(base_dir, font_name)
        out_path = os.path.join(output_dir, font_name)

        total_glyphs, out_bytes = extend_single_tft(base_path, out_path, font_size)
        print(f"[{success_count+1:2d}/20] {font_name:16s} (size={font_size:2d}) -> {total_glyphs:4d} glyphs, {out_bytes:8d} bytes")
        success_count += 1

    print("=" * 70)
    print(f"SUCCESS: Generated all {success_count}/20 extended TFT fonts into {output_dir}")
    print("=" * 70)

if __name__ == '__main__':
    build_all()
