# Reverse engineering and technical post-mortem: Senren＊Banka 100% Thai localization

A technical chronicle of cracking, patching, and rendering Thai text natively on Yuzusoft's Kirikiri Z and FreeMote PSB scenario engine (Steam 18+ Uncensored Edition).

Written by: The Senren＊Banka Thai Localization Project Team

---

## Executive summary

Senren＊Banka contains 60,607 dialogue lines distributed across 92 compiled scenario scripts (`.ks.scn`). Achieving complete localization required far more than translating text in a spreadsheet: it required reverse-engineering proprietary binary font formats, satisfying Steam digital rights management checks, and adapting the Kirikiri Z virtual file system to handle dynamic typography.

This document records the technical hurdles encountered, how we debugged them at the kernel and bytecode levels, and the architectural solutions that brought the game to 100% Thai completion with zero regressions.

---

## 1. Initial roadblock: locked font architecture (TVP_ARCHIVE_ONLY)

When localizing standard visual novels, the usual approach is simple: drop a TrueType font (`.ttf`) into the game folder, then modify script files like `Config.tjs` to point to it. For modern Yuzusoft releases, this fails immediately.

Low-level inspection of `SenrenBanka.exe` revealed three major constraints:
1. The executable is compiled with `TVP_ARCHIVE_ONLY` enabled. The engine completely ignores loose files on disk. Every script, texture, and font must reside inside an encrypted `.xp3` container.
2. The engine bypasses Windows font rendering APIs (GDI, DirectWrite, and FreeType) during standard dialogue execution.
3. Text is rendered using TVP Pre-rendered Bitmap Fonts (`.tft`) stored deep within `data.xp3`. The stock font files contain rasterized glyphs for Japanese kanji, kana, and basic Latin ASCII, but lack the entire Thai Unicode block (U+0E01 through U+0E5B).

There were no shortcuts. To display Thai, we had to reverse-engineer the `.tft` binary format and inject rasterized Thai glyphs directly into the game's compiled font archives.

---

## 2. Ghost patch mystery: Steam DRM signatures and the hnfn table

Before tackling font generation, we needed the game to load modified dialogue scripts. We translated the Prologue scenario (`001・アーサー王ver1.07.ks.scn`), encrypted it with the engine's dual-key XOR cipher (`0x01` for the header, `0x98` for the body), and packed it into an overlay archive named `patch_extra.xp3`.

The result was perplexing:
- The game launched cleanly with no errors.
- Starting a new game showed 100% English dialogue, as if our patch did not exist.

We attached Sysinternals Process Monitor (Procmon) to trace the engine's file I/O:

```text
[Procmon Log Trace]
1. SenrenBanka.exe -> FASTIO_READ | patch_extra.xp3 | Offset: 53,873,038 (Read Index) -> SUCCESS
2. SenrenBanka.exe -> CLOSE       | patch_extra.xp3
3. SenrenBanka.exe -> FASTIO_READ | adult.xp3       | Offset: 99,359,774 (Fallback!)   -> SUCCESS
```

The trace showed that the engine opened `patch_extra.xp3`, read its index header, immediately closed it, and fell back to the original English archive in `adult.xp3`.

Inspecting the raw index block at the end of `patch_extra.xp3` revealed the cause:
- The archive index begins with a chunk named `sen:`.
- Generic XP3 packing tools write a 16-byte `sen:` body.
- Legitimate Steam releases require a 40-byte `sen:` chunk, carrying a 24-byte proprietary Steam DRM signature:
  `\n\x00CSK`\n\xff\x07N\xb1\x82S\x00t\x00e\x00a\x00m\x00\x00\x00`
- If the `sen:` chunk is shorter than 40 bytes, the engine treats the archive as unauthorized and discards the entire `hnfn` (hash-to-filename) lookup table. Without `hnfn`, the virtual file system cannot resolve internal file paths, causing the engine to fall back to the base game files.

When we updated our archive builder to include the exact 24-byte Steam signature, the engine accepted our patch.

---

## 3. Tofu boxes and pre-rendered TFT font generation

With DRM checks satisfied, text appeared on screen, but every character rendered as an empty white rectangular box (the tofu glyph). The stock `.tft` font lacked glyph bitmaps for the Thai codepoints.

A `.tft` binary file consists of:
1. A 22-byte magic header: `TVP pre-rendered font\x1a`
2. Metric headers specifying font height, ascent, and descent
3. A sorted index table pairing Unicode codepoints with data offsets
4. 8-bit grayscale alpha bitmaps for each glyph

We developed `build_extended_tft.py` to:
1. Rasterize Thai TrueType fonts at exact pixel heights matching Yuzusoft's Japanese metrics.
2. Render the full Thai Unicode block (U+0E01 through U+0E5B).
3. Append glyph records and reconstruct the binary search index table in strict ascending Unicode order so the engine's internal binary search can locate glyphs.

With this generator, legible Thai characters rendered on screen for the first time.

---

## 4. Complex script challenges: zero-advance widths and PUA typography

Digital Thai typography presents unique challenges that break standard western text renderers:

### Advancing tone marks
Latin and CJK characters advance horizontally as they are typed. Thai, however, relies on upper vowels, lower vowels, and tone marks that must stack above or below a base consonant without advancing the cursor (Advance Width must be 0).
Because the game's font metrics treated every glyph as an advancing character, the word "ที่นี่" rendered as "ท  ี่  น  ี่", with vowels detached and drifting into empty space.

Fix: We patched the glyph metrics in the TFT header for all vowels and diacritics (U+0E31, U+0E34 through U+0E3A, U+0E47 through U+0E4E), setting `AdvanceX` to 0 and adjusting `OriginX` to center the mark over the preceding consonant.

### Vertical stacking collisions
When a consonant, upper vowel, and tone mark stack together (as in "ปี่", "ปี้", "ที่"), the marks collided into an illegible black blob. Furthermore, tall consonants like ป, ฝ, and ฟ pierced straight through the upper vowels.

Fix: We built `thai_pua_shaper.py` using codepoints in the Unicode Private Use Area (PUA: U+F700 through U+F71F), similar to commercial desktop publishing software:
1. Tone elevation: Elevates tone marks when an upper vowel is present below them (e.g., standard Mai Tho U+0E49 becomes elevated PUA U+F70B).
2. Tall consonant shifting: Shifts vowels and tones slightly leftward when following tall-stemmed consonants.
3. Sara Am decomposition: Decomposes Sara Am (ำ) into a separate upper Nikhahit circle, an elevated tone mark, and a trailing Sara Aa.

Baking these 32 PUA glyph variants into the TFT fonts resolved all collision and stacking issues.

---

## 5. The backlog screen and the 20-font matrix

After dialogue text rendered cleanly, opening the dialogue history (Backlog) revealed a new issue: the entire history screen was filled with tofu boxes once again.

Script disassembly revealed that the engine uses different font sizes depending on the window context:
- Active dialogue uses 32-pixel font (`font1_32.tft`).
- Backlog history uses 39-pixel font (`font1_39.tft`).
- Headings and system menus use various files from `headfont_*.tft` and `sysfont_*.tft`.

Because we had only patched the 32-pixel font, the backlog failed. We resolved this by building a complete 20-font matrix covering every size used across the title:
- 7 system fonts (`sysfont_10.tft` through `sysfont_30.tft`)
- 4 heading fonts (`headfont_20.tft` through `headfont_36.tft`)
- 9 dialogue fonts (`font1_10.tft` through `font1_56.tft`)

Packing this matrix into `data.xp3` eliminated tofu boxes across the entire game.

---

## 6. KAG script crashes and save data desynchronization

During testing, two severe operational bugs emerged:

### Game freezes and save data corruption
Some testers reported that saving worked, but loading a save caused the game to hang indefinitely.
This was caused by a race condition between Steam Cloud Synchronization and local NTFS hard links. The engine froze while waiting for cloud lock release.
Fix: We created `Start_Thai_Game.bat` passing `-savecloud=no`, which forces the engine to read and write save files locally, bypassing cloud synchronization locks.

### Hard crash at start.ks line 43
Skipping text occasionally triggered a fatal crash: `KAG Script Error at start.ks line 43: Syntax error`.
This occurred because translators had inadvertently entered raw newlines (`\r\n`) inside spreadsheet cells. When compiled into PSB bytecode, raw newlines broke the KAG line parser.
Fix: We added `sanitize_text()` to the injection pipeline, converting raw newlines into regular spaces and normalizing irregular quotation marks prior to compilation.

---

## 7. Harvesting adult scenarios from adult.xp3

On Steam's Uncensored 18+ Edition, scenario files are split:
- `patch_extra.xp3` contains only 25 common route scenarios.
- The remaining 67 scenarios (including all adult scenes and after-stories) are located in `adult.xp3`.

If we only patched `patch_extra.xp3`, adult scenes reverted to English.

We built the Harvester Pipeline into `thai_injector.py`:
1. Indexes translated dialogue across all 92 chapters.
2. Identifies matching scenario scripts from both `patch_extra.xp3` and `adult.xp3`.
3. Extracts scenarios from `adult.xp3`, decrypts them, injects Thai translations, and re-encrypts them with their original keys.
4. Merges all 92 scenarios into a single `patch_extra.xp3` archive with valid redirection pointers at offset 32.

This allows players to install a single `patch_extra.xp3` file without modifying their base `adult.xp3` archive.

---

## 8. Localizing UI graphics and flowcharts (.pimg)

Main menus and chapter flowcharts are stored as `.pimg` containers. Internally, these are FreeMote PSB files containing TLG5-compressed bitmaps with alpha channels.

We built tools to unpack all 33 texture resources from `title_en.pimg` and `langselect.pimg`, redrew the button graphics in Thai (Start, Load, Flowchart, and Language Select), and re-encoded them with TLG5 compression while preserving 8-bit alpha transparency.

---

## 9. Dynamic font scaling: Kirikiri %XX; tags and sibling string pools

The final persistent defect involved non-standard text:
Why did shouting or whispering lines still appear in English, even after being translated in the spreadsheet?

Deep inspection of scenario string pools revealed Kirikiri's font scaling mechanism:
1. **Font control tags (`%<number>;`)**: Shouts are prefixed with scaling tags like `%123;` (+123% scale), while whispers use `%69;` or `%76;` (small scale).
2. **Dual sibling strings**: For every line with a scaling tag, the compiled bytecode stores two distinct strings:
   - Display variant: contains the tag prefix, e.g., `%123;Awawawawaaaaaahh!?`
   - Backlog variant: contains clean text without the tag, e.g., `Awawawawaaaaaahh!?`
3. **The matching mismatch**: Spreadsheets only contain clean text without tags. When the injector performed exact matching:
   - It matched and replaced the backlog variant.
   - It skipped the display variant because of the leading `%123;` tag.
   - Consequently, the backlog screen showed Thai, while the active dialogue box remained in English.

Fix: We implemented canonical string matching in `thai_injector.py` and `patch_names_and_choices.py`:
- Strips tags to find canonical matches.
- Extracts the original `%XX;` tag from the display variant and prepends it to the shaped Thai text.
- Replaces both sibling variants simultaneously.

Verification across all 92 scenarios confirmed:
- Remaining English font-tagged lines: 0
- Remaining untranslated English lines: 0 (excluding two lines where Lena intentionally speaks broken Japanese in romaji)

Every line, regardless of font size or context, now renders completely in Thai.

---

## Conclusion

This project demonstrates that proprietary engines like Kirikiri Z can be fully adapted for complex non-Latin scripts when binary font formats, file security checks, and engine bytecodes are understood.

The tools, specifications, and scripts in this repository are published to assist future localization engineers and visual novel fan translation efforts.
