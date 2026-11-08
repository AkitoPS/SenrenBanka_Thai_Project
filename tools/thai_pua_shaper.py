"""
Thai PUA / Pre-composed Glyph Shaper for Build-time Scenario Injection.
Translates standard Unicode Thai strings into Thai PUA (U+F700..U+F71A)
based on standard Microsoft / C90 typography rules for renderers lacking OpenType GPOS/GSUB.
"""

TALL_CONSONANTS = {'\u0E1B', '\u0E1D', '\u0E1F', '\u0E2C'}  # ป ฝ ฟ ฬ
DESCENDER_CONSONANTS = {'\u0E0E', '\u0E0F', '\u0E24'}  # ฎ ฏ ฤ
SHIFTED_UPPER_VOWELS = {'\uF701', '\uF702', '\uF703', '\uF704', '\uF710', '\uF711', '\uF712'}
UPPER_VOWELS = {'\u0E31', '\u0E34', '\u0E35', '\u0E36', '\u0E37', '\u0E47', '\u0E4D'}  # ั ิ ี ึ ื ็ ํ
LOWER_VOWELS = {'\u0E38', '\u0E39', '\u0E3A'}  # ุ ู ฺ
TONE_MARKS = {'\u0E48': 0, '\u0E49': 1, '\u0E4A': 2, '\u0E4B': 3, '\u0E4C': 4}  # ่ ้ ๊ ๋ ์

def shape_thai_text(text: str) -> str:
    """
    Transform standard Unicode Thai into PUA-encoded Thai string.
    Leaves non-Thai and already well-positioned characters intact.
    Handles Sara Am + Tone mark decomposition cleanly (Nikkhahit + High Tone + Sara Aa).
    """
    if not text:
        return text

    # Pass 1: Normalization & Sara Am decomposition
    chars = list(text)
    i = 0
    norm_chars = []
    while i < len(chars):
        # Tone mark + Sara Am -> Nikkhahit + Tone mark + Sara Aa
        if i + 1 < len(chars) and chars[i] in TONE_MARKS and chars[i+1] == '\u0E33':
            norm_chars.append('\u0E4D')
            norm_chars.append(chars[i])
            norm_chars.append('\u0E32')
            i += 2
        # Sara Am + Tone mark -> Nikkhahit + Tone mark + Sara Aa
        elif i + 1 < len(chars) and chars[i] == '\u0E33' and chars[i+1] in TONE_MARKS:
            norm_chars.append('\u0E4D')
            norm_chars.append(chars[i+1])
            norm_chars.append('\u0E32')
            i += 2
        # Tone mark + Upper vowel -> Upper vowel + Tone mark
        elif i + 1 < len(chars) and chars[i] in TONE_MARKS and chars[i+1] in UPPER_VOWELS:
            norm_chars.append(chars[i+1])
            norm_chars.append(chars[i])
            i += 2
        # Tone mark + Lower vowel -> Lower vowel + Tone mark (Normalize wrong typing order)
        elif i + 1 < len(chars) and chars[i] in TONE_MARKS and chars[i+1] in LOWER_VOWELS:
            norm_chars.append(chars[i+1])
            norm_chars.append(chars[i])
            i += 2
        else:
            norm_chars.append(chars[i])
            i += 1

    decomposed = norm_chars

    # Pass 2: PUA shaping
    out = []
    n = len(decomposed)
    for idx, ch in enumerate(decomposed):
        prev = out[-1] if out else None
        next1 = decomposed[idx + 1] if idx + 1 < n else None

        # 1. Base consonants with descenders (ญ, ฐ) before lower vowel
        if ch == '\u0E10' and next1 in LOWER_VOWELS:  # ฐ
            out.append('\uF700')
            continue
        elif ch == '\u0E0D' and next1 in LOWER_VOWELS:  # ญ
            out.append('\uF70F')
            continue

        # 2. Tone marks (่ ้ ๊ ๋ ์)
        if ch in TONE_MARKS:
            tone_idx = TONE_MARKS[ch]
            # Level 2 shifted left (High-Left) if preceded by shifted upper vowel on tall consonant (e.g. ปี้, ฟื้น)
            if prev in SHIFTED_UPPER_VOWELS:
                out.append(chr(0xF71B + tone_idx))
                continue
            # Level 2 (Shifted High) if preceded by normal upper vowel (including Nikkhahit \u0E4D)
            elif prev in UPPER_VOWELS:
                out.append(chr(0xF713 + tone_idx))
                continue
            # Shifted Low-Left if preceded by tall consonant directly OR tall consonant with lower vowel
            elif prev in TALL_CONSONANTS or (prev in LOWER_VOWELS and len(out) >= 2 and out[-2] in TALL_CONSONANTS):
                out.append(chr(0xF705 + tone_idx))
                continue
            # Standard tone mark on normal base consonant
            else:
                out.append(ch)
                continue

        # 3. Upper vowels (ิ ี ึ ื ั ํ ็) on tall consonants
        if ch in UPPER_VOWELS and prev in TALL_CONSONANTS:
            code = ord(ch)
            if 0x0E34 <= code <= 0x0E37:
                out.append(chr(0xF701 + (code - 0x0E34)))
                continue
            elif ch == '\u0E31':  # ั
                out.append('\uF710')
                continue
            elif ch == '\u0E4D':  # ํ
                out.append('\uF711')
                continue
            elif ch == '\u0E47':  # ็
                out.append('\uF712')
                continue

        # 4. Lower vowels (ุ ู ฺ) on descender consonants
        if ch in LOWER_VOWELS and prev in DESCENDER_CONSONANTS:
            out.append(chr(0xF718 + (ord(ch) - 0x0E38)))
            continue

        # Default: keep original
        out.append(ch)

    return ''.join(out)

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    test_cases = [
        "ที่", "นี่", "พี่", "มี", "เป็น", "เมื่อ", "เก่ง", "ต้อง", "น้ำ",
        "ปู่", "ปู้", "ฝุ่น", "ปี้", "ฟื้น", "ป่า",
        "ภาษาไทย", "ภาษา", "ไทย", "ทดสอบ", "สวัสดี", "Thai Test: สวัสดีครับ"
    ]
    for tc in test_cases:
        res = shape_thai_text(tc)
        codes = [f"U+{ord(c):04X}" for c in res]
        print(f"{tc:25s} -> {' '.join(codes)}")
