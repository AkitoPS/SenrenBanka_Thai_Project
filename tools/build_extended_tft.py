"""
build_extended_tft.py — Standalone Generator for Thai Extended TFT Fonts
Generates custom TVP pre-rendered font (.tft) files from any TrueType/OpenType font
with complete Thai Base, Combining Marks (Zero-Advance), and PUA Shaper Glyphs.
"""

import os
import sys
import struct
import ctypes
from ctypes import wintypes

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

def compress_tft_glyph(pixels):
    """Encodes grayscale pixels (0..64) with TFT Run-Length Encoding."""
    if not pixels:
        return b''
    out = bytearray()
    i = 0
    n = len(pixels)
    while i < n:
        val = pixels[i]
        assert val <= 64, f"Pixel value {val} exceeds 64!"
        out.append(val)
        j = i + 1
        while j < n and pixels[j] == val:
            j += 1
        repeats = j - i - 1
        while repeats > 0:
            chunk = min(repeats, 191)
            out.append(0x40 + chunk)
            repeats -= chunk
        i = j
    return bytes(out)

def decompress_tft_glyph(data, total_pixels):
    """Decodes TFT Run-Length Encoded glyph pixels."""
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

THAI_COMBINING_MARKS = {
    0x0E31,  # ั (Mai Han-Akat)
    0x0E34, 0x0E35, 0x0E36, 0x0E37,  # ิ ี ึ ื
    0x0E38, 0x0E39, 0x0E3A,  # ุ ู ฺ
    0x0E47,  # ็ (Maitaikhu)
    0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C,  # ่ ้ ๊ ๋ ์
    0x0E4D,  # ํ (Nikkhahit)
    0x0E4E,  # ๎ (Yamakkan)
}

def rasterize_glyph(hdc, cp, gm, mat, gdi32):
    GGO_GRAY8_BITMAP = 6
    size = gdi32.GetGlyphOutlineW(hdc, cp, GGO_GRAY8_BITMAP, ctypes.byref(gm), 0, None, ctypes.byref(mat))
    if size <= 0:
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

def generate_thai_glyphs(ttf_path: str, font_name: str, font_height: int, shift_left: int = 5, elevate_tone: int = 8, elevate_am: int = 9):
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hdc = user32.GetDC(0)

    res = gdi32.AddFontResourceExW(os.path.abspath(ttf_path), 0x10, 0)
    assert res > 0, f"Failed to load font from {ttf_path}"

    hfont = gdi32.CreateFontW(font_height, 0, 0, 0, 400, False, False, False, 222, 0, 0, 4, 0, font_name)
    old_font = gdi32.SelectObject(hdc, hfont)

    mat = MAT2()
    mat.eM11.value = 1
    mat.eM22.value = 1
    gm = GLYPHMETRICS()

    glyphs = {}

    # 1. Base Thai characters (U+0E01..U+0E5B)
    for cp in range(0x0E01, 0x0E5C):
        g = rasterize_glyph(hdc, cp, gm, mat, gdi32)
        if cp in THAI_COMBINING_MARKS:
            g['incX'] = 0
            g['incY'] = 0
            g['inc'] = 0
        glyphs[cp] = g

    # 2. PUA Characters (U+F700..U+F71F)
    # 0xF700: ฐ truncated
    base_tho = glyphs[0x0E10]
    crop_h = max(1, base_tho['oy'])
    glyphs[0xF700] = {
        'w': base_tho['w'], 'h': crop_h,
        'ox': base_tho['ox'], 'oy': base_tho['oy'],
        'incX': base_tho['incX'], 'incY': 0, 'inc': base_tho['inc'],
        'pixels': base_tho['pixels'][:crop_h * base_tho['w']]
    }

    # 0xF701..0xF704: Upper vowels shifted left for tall consonants
    for i, base_cp in enumerate([0x0E34, 0x0E35, 0x0E36, 0x0E37]):
        b = glyphs[base_cp]
        glyphs[0xF701 + i] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'] - shift_left, 'oy': b['oy'],
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    # 0xF705..0xF709: Tone marks shifted left
    for i, base_cp in enumerate([0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C]):
        b = glyphs[base_cp]
        glyphs[0xF705 + i] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'] - shift_left, 'oy': b['oy'],
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    # 0xF70A..0xF70E: Tone marks normal lower level
    for i, base_cp in enumerate([0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C]):
        b = glyphs[base_cp]
        glyphs[0xF70A + i] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'], 'oy': b['oy'],
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    # 0xF70F: ญ truncated
    base_yo = glyphs[0x0E0D]
    crop_h = max(1, base_yo['oy'])
    glyphs[0xF70F] = {
        'w': base_yo['w'], 'h': crop_h,
        'ox': base_yo['ox'], 'oy': base_yo['oy'],
        'incX': base_yo['incX'], 'incY': 0, 'inc': base_yo['inc'],
        'pixels': base_yo['pixels'][:crop_h * base_yo['w']]
    }

    # 0xF710: ั shifted left
    b = glyphs[0x0E31]
    glyphs[0xF710] = {
        'w': b['w'], 'h': b['h'],
        'ox': b['ox'] - shift_left, 'oy': b['oy'],
        'incX': 0, 'incY': 0, 'inc': 0,
        'pixels': list(b['pixels'])
    }

    # 0xF713..0xF717: Tone marks at HIGH level (above upper vowels)
    for i, base_cp in enumerate([0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C]):
        b = glyphs[base_cp]
        glyphs[0xF713 + i] = {
            'w': b['w'], 'h': b['h'],
            'ox': b['ox'], 'oy': b['oy'] + elevate_tone,
            'incX': 0, 'incY': 0, 'inc': 0,
            'pixels': list(b['pixels'])
        }

    gdi32.SelectObject(hdc, old_font)
    gdi32.DeleteObject(hfont)
    user32.ReleaseDC(0, hdc)
    gdi32.RemoveFontResourceExW(os.path.abspath(ttf_path), 0x10, 0)
    return glyphs

def build_extended_tft(base_tft_path: str, output_tft_path: str, ttf_path: str, font_name: str, font_height: int, shift_left: int = 5, elevate_tone: int = 8):
    with open(base_tft_path, 'rb') as f:
        data = f.read()

    assert data[:22] == b"TVP pre-rendered font\x1a", "Invalid TFT magic"
    version = data[22]
    uflag = data[23]
    orig_count = struct.unpack('<I', data[24:28])[0]
    orig_ch_off = struct.unpack('<I', data[28:32])[0]
    orig_idx_off = struct.unpack('<I', data[32:36])[0]

    orig_chars = struct.unpack(f'<{orig_count}H', data[orig_ch_off : orig_ch_off + orig_count*2])

    existing_glyphs = {}
    for i in range(orig_count):
        cp = orig_chars[i]
        rec = data[orig_idx_off + i*20 : orig_idx_off + (i+1)*20]
        off, w, h, ox, oy, incX, incY, inc, res = struct.unpack('<IHhhhhhhH', rec)
        total_pix = w * h
        pix = decompress_tft_glyph(data[off:], total_pix) if total_pix > 0 else b''
        existing_glyphs[cp] = {
            'w': w, 'h': h, 'ox': ox, 'oy': oy,
            'incX': incX, 'incY': incY, 'inc': inc,
            'pixels': list(pix)
        }

    thai_glyphs = generate_thai_glyphs(ttf_path, font_name, font_height, shift_left, elevate_tone)

    all_glyphs = dict(existing_glyphs)
    for cp, g in thai_glyphs.items():
        all_glyphs[cp] = g

    sorted_cps = sorted(all_glyphs.keys())
    total_count = len(sorted_cps)

    cur_data_off = 36
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

        metric_records.append(struct.pack(
            '<IHhhhhhhH', glyph_off, w, h, g['ox'], g['oy'], g['incX'], g['incY'], g['inc'], 0
        ))

    new_ch_index_off = cur_data_off
    new_index_off = new_ch_index_off + total_count * 2

    header = bytearray(b"TVP pre-rendered font\x1a")
    header.append(version)
    header.append(uflag)
    header.extend(struct.pack('<III', total_count, new_ch_index_off, new_index_off))

    ch_index_bytes = bytearray()
    for cp in sorted_cps:
        ch_index_bytes.extend(struct.pack('<H', cp))

    metric_bytes = b''.join(metric_records)
    full_tft = bytes(header) + bytes(comp_data_blocks) + bytes(ch_index_bytes) + metric_bytes

    with open(output_tft_path, 'wb') as f:
        f.write(full_tft)

    print(f"Generated {output_tft_path} ({len(full_tft):,} bytes, {total_count} glyphs).")

if __name__ == '__main__':
    print("Usage: build_extended_tft(base_tft, out_tft, ttf, font_name, height)")
