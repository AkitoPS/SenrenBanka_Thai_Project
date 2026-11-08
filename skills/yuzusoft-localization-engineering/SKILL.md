---
name: yuzusoft-localization-engineering
description: Use when localizing, translating, patching, reverse-engineering, or fixing typography, font rendering, crashes, or DRM issues in Yuzusoft or Kirikiri Z FreeMote visual novels (Senren*Banka, Riddle Joker, Cafe Stella, Sanoba Witch, etc.).
---

# Yuzusoft and Kirikiri Z localization engineering guide

## Overview

Modern visual novels by Yuzusoft (such as Senren＊Banka, Riddle Joker, Cafe Stella and the Reapers' Butterflies, and Sanoba Witch) run on a heavily customized Kirikiri Z engine using FreeMote PSB scenario bytecodes. They employ proprietary binary font files, encrypted virtual file systems, and strict Steam DRM checks.

This skill provides step-by-step technical procedures to unpack, patch, translate, synthesize pre-rendered fonts, resolve complex script typography, synchronize dynamic font-scaling tags, and deploy localized builds with zero crashes.

---

## Engine architecture and constraints

Before modifying files, verify the engine's core constraints:

1. **TVP_ARCHIVE_ONLY mode:** The engine is compiled to ignore loose files on disk. Every modified script, image, and font must be packaged inside an encrypted `.xp3` archive.
2. **Pre-rendered bitmap fonts (.tft):** The engine does not call Windows GDI, DirectWrite, or FreeType APIs for normal dialogue. Characters are drawn from pre-rasterized 8-bit alpha bitmaps embedded in `data.xp3`. If a character is absent from the font's Unicode index, the engine renders an empty white box (tofu).
3. **Dual-key XOR cipher:** Scenario scripts (`.ks.scn`) use two distinct single-byte XOR keys per file. Key 1 decrypts the header up to the offset specified in header offset 36 (`hdr[7]`). Key 2 decrypts the body and string tables from that offset to the end of the file.
4. **Authentic Steam DRM signature:** The archive index must begin with a 40-byte `sen:` chunk containing a specific 24-byte Steam signature. If the `sen:` chunk is incomplete, the engine drops the filename lookup table (`hnfn`) and falls back to stock archives.

---

## 1. XP3 archive injection and Steam DRM compliance

When assembling an overlay archive (such as `patch_extra.xp3`):

### Redirection pointer architecture
Do not append corrupt trailing PARIS chunks. Maintain authentic Kirikiri XP3 structure:
- Offset 11 contains the archive magic pointer pointing to offset 23.
- Offset 23 contains a redirection index segment of 32 bytes (`segm` chunk).
- Offset 32 contains an 8-byte little-endian integer pointing directly to the real compressed index at the end of the archive.
- Update this 8-byte pointer whenever the archive body size changes.

### Steam DRM signature in the sen: chunk
The compressed index must begin with an authentic `sen:` chunk:
- Total `sen:` chunk size: 40 bytes.
- Structure:
  - 4 bytes magic: `b'sen:'`
  - 8 bytes little-endian chunk size: `len(sen_body)`
  - Body:
    - 8 bytes `new_hnfn_offset`
    - 4 bytes `new_hnfn_uncompressed_size`
    - 4 bytes `new_hnfn_compressed_size`
    - 24 bytes Steam digital signature:
      `b'\n\x00CSK`\n\xff\x07N\xb1\x82S\x00t\x00e\x00a\x00m\x00\x00\x00'`

If this signature is omitted, the engine silently discards the `hnfn` table and ignores all localized files inside the patch.

---

## 2. Pre-rendered TFT font synthesis

To display languages outside Latin and CJK, you must synthesize custom `.tft` font binaries and inject them into `data.xp3`.

### Binary format of .tft
1. Magic header (22 bytes): `b"TVP pre-rendered font\x1a"`
2. Metric header: Ascent, descent, max advance, line height.
3. Index table: Array of `(Unicode_codepoint, Glyph_data_offset)`. This table must be sorted in strict ascending numerical order to allow the engine's internal binary search to function.
4. Glyph data blocks:
   - Header: `OriginX`, `OriginY`, `Width`, `Height`, `AdvanceX`, `AdvanceY`.
   - Data: 8-bit grayscale alpha channel bitmap.

### Multi-font matrix requirement
Yuzusoft games swap font sizes depending on the user interface state:
- Active dialogue box: typically uses a 32-pixel font (`font1_32.tft`).
- Backlog history screen: uses a larger 39-pixel font (`font1_39.tft`).
- Headings and choices: use `headfont_20.tft` through `headfont_36.tft`.
- System config and menus: use `sysfont_10.tft` through `sysfont_30.tft`.

Rule: You must inject the target language glyphs into all 20 font files in the matrix. Patching only the main dialogue font causes the backlog screen or menus to revert to tofu boxes.

---

## 3. Complex script typography (Thai and stacking marks)

Standard font renderers handle complex scripts dynamically. Pre-rendered bitmap engines do not. Apply these three structural modifications:

### Zero-advance width for combining marks
Upper vowels, lower vowels, and tone marks must not occupy horizontal space.
- In the glyph metric block, set `AdvanceX = 0`.
- Adjust `OriginX` to shift backward and center the mark over the preceding consonant.

### 3-tier Private Use Area (PUA) shaper
When stacking vowels and tone marks vertically (such as consonant + upper vowel + tone mark):
1. Use Unicode PUA codepoints (U+F700 through U+F71F).
2. Elevate tone marks to PUA variants when resting atop an upper vowel.
3. Shift vowels and tone marks leftward when placed over tall-stem consonants (such as ป, ฝ, ฟ, ฬ in Thai).
4. Decompose complex compound vowels (such as Sara Am ำ) into separate Nikhahit circle, elevated tone, and trailing vowel components.
5. Apply text shaping in the injection pipeline before strings are compiled into scenario bytecode.

### Grammatical word wrapping
Visual novel text boxes do not automatically wrap non-space-delimited scripts. Use a dictionary-based tokenizer (such as PyThaiNLP) to compute line breaks at grammatical word boundaries before inserting `\n` break tags. Never wrap lines mid-word.

---

## 4. Scenario bytecode and string pool injection

Scenario scripts (`.ks.scn`) are compiled FreeMote PSB binaries.

### Locating the string table
1. Parse the 8-integer header starting at offset 8:
   `hdr = struct.unpack_from('<IIIIIIII', dec, 8)`
2. Extract offsets:
   - `str_off = hdr[2]` (offset to string index array)
   - `str_data = hdr[3]` (base offset where string UTF-8 bytes begin)
   - `extra_off = hdr[4]` (boundary marking the end of string data)
3. Count and entry width:
   - `count = struct.unpack_from('<H', dec, str_off + 1)[0]`
   - `entry_type = dec[str_off + 3]`
   - Pointer width: `{0x0D: 1, 0x0E: 2, 0x0F: 3, 0x10: 4}.get(entry_type, 3)`
4. Read string offset list and extract null-terminated UTF-8 strings.

### Rebuilding the string table
When replacing text:
- Recalculate relative offsets from `str_data`.
- If new strings exceed original buffer space, append new string bytes and update `hdr[4]` (`extra_off`) and subsequent section pointers accordingly.
- Re-encrypt using the original single-byte keys `k1` and `k2`.

---

## 5. Dynamic font scaling and sibling string pools

In Kirikiri Z, dialogue lines frequently scale dynamically:
- Shouts and exclamations use tags like `%123;` (+123% scale) or `%115;`.
- Whispers and murmurs use tags like `%61;`, `%69;`, or `%76;` (reduced scale).

### The dual sibling string pool pitfall
Every scaled line is stored twice in the scenario bytecode:
1. **Display variant:** contains the tag prefix, e.g. `%123;Awawawawaaaaaahh!?`
2. **Backlog variant:** clean plain text without tags, e.g. `Awawawawaaaaaahh!?`

If an injector matches translations only against clean text:
- It replaces the backlog variant.
- It skips the display variant because of the leading `%XX;` tag.
- Result: The backlog shows localized text, but the active screen remains in English.

### Canonical matching algorithm
Always implement canonical variant matching:

```python
def canon_variant(t: str) -> str:
    """Strips sizing tags, escaped characters, and whitespace."""
    s = str(t).strip().replace('\r\n', '\n')
    s = re.sub(r'^%\d+;', '', s)
    s = s.replace(r'\%', '%').replace('\\n', '').replace('\\r', '')
    return re.sub(r'\s+', '', s)

def encode_for_pool(pool_str: str, shaped_translation: str) -> bytes:
    """Extracts tag prefix from display variant and reapplies it to translation."""
    clean_text = re.sub(r'^%\d+;', '', shaped_translation)
    match_tag = re.match(r'^(%\d+;)', pool_str)
    if match_tag:
        return (match_tag.group(1) + clean_text).encode('utf-8')
    return clean_text.encode('utf-8')
```

When a canonical match is found, replace both the display variant and the backlog variant simultaneously.

---

## 6. Runtime stability and save game protection

### Preventing KAG syntax crashes at start.ks:43
Translators often press Enter inside spreadsheet cells, producing raw `\r\n` characters. When embedded in scenario bytecode, raw newlines break KAG tag interpretation.
Rule: Sanitize all translated text by replacing `\r\n` and `\n` with standard spaces before compilation. Use explicit line break commands rather than raw byte newlines.

### Isolating Steam Cloud from local saves
When testing modified scenarios, Steam Cloud Synchronization can conflict with local game saves, causing loading hangs or state rollbacks.
Rule: Launch the executable with `-savecloud=no`:
```cmd
start "" "SenrenBanka.exe" -savecloud=no
```
This forces the engine to read and write saves strictly to the local directory, avoiding cloud desync.

---

## 7. Automated verification checklist

Before declaring a build complete, execute these automated verifications:

1. **Font matrix bit-for-bit check:** Verify that all 20 `.tft` files contain the full target Unicode range and PUA glyphs.
2. **Scenario string pool scan:** Iterate through all scenario bytecodes and verify:
   - Untranslated dialogue lines count = 0.
   - Untranslated lines with `%XX;` tags = 0.
3. **Steam signature validation:** Confirm offset 11 points to offset 23, offset 32 points to the real compressed index, and the `sen:` chunk length is exactly 40 bytes.
4. **Smoke test launch:** Run the engine process for at least 5 seconds to verify that it loads font caches into `%TEMP%` and terminates cleanly with exit code 0 or 1 without throwing unhandled exceptions.
