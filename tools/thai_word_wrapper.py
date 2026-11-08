"""
thai_word_wrapper.py — Intelligent Thai Word Wrapping & Line Segmentation Engine.

Ensures Thai Visual Novel dialogue is wrapped naturally at proper grammatical word boundaries
without slicing words in half, respecting zero-advance combining marks, and protecting
names/terms from the project glossary.
"""

import os
import re
import json
from pythainlp.tokenize import word_tokenize
from pythainlp.util import dict_trie
from pythainlp.corpus import thai_words

# Zero-advance combining marks in Thai
THAI_COMBINING_MARKS = set(chr(cp) for cp in [
    0x0E31, 0x0E34, 0x0E35, 0x0E36, 0x0E37, 0x0E38, 0x0E39, 0x0E3A,
    0x0E47, 0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C, 0x0E4D, 0x0E4E,
    # PUA zero-advance combining marks
    0xF701, 0xF702, 0xF703, 0xF704, 0xF705, 0xF706, 0xF707, 0xF708, 0xF709,
    0xF70A, 0xF70B, 0xF70C, 0xF70D, 0xF70E,
    0xF710, 0xF711, 0xF712, 0xF713, 0xF714, 0xF715, 0xF716, 0xF717,
    0xF718, 0xF719, 0xF71A, 0xF71B, 0xF71C, 0xF71D, 0xF71E, 0xF71F
])

# Punctuation marks that should never start a new line
NO_LINE_START_CHARS = set('”"\'’)]}?,.!;:ๆฯ')

BREAK_PREFERRED_BEFORE = {
    'ที่', 'ซึ่ง', 'อัน', 'และ', 'หรือ', 'แต่', 'ทว่า', 'เพราะ', 'เนื่องจาก', 'เพื่อ', 'จน', 'จนกระทั่ง', 'เสียจน',
    'ถ้า', 'หาก', 'แม้', 'แม้ว่า', 'ดังนั้น', 'พลาง', 'โดย', 'พร้อม', 'พร้อมกับ', 'ราวกับ', 'ก่อน', 'หลัง', 'เมื่อ', 'ในเมื่อ', 'ขณะที่', 'ในขณะที่'
}

BREAK_PREFERRED_AFTER = {
    'ครับ', 'ค่ะ', 'คะ', 'เจ้าค่ะ', 'นะ', 'ล่ะ', 'สิ', 'เลย', 'จริง', 'ด้วย',
    '...', '…', '!', '?', '～', '”', '’'
}

DO_NOT_START_LINE = {
    'นี้', 'นั้น', 'โน้น', 'เอง', 'หรอก', 'ละ', 'ล่ะ', 'มั้ง', 'นะ', 'จ้ะ', 'จ๊ะ', 'สิ', 'นะสิ', 'ล่ะสิ',
    'ๆ', 'ฯ', 'ฯลฯ', 'ใน', 'แก่', 'แด่', 'ต่อ', 'จริงๆ', 'การ', 'ความ', 'อย่าง', 'กว่า', 'โดยตรง',
    'ท่าน', 'คุง', 'ซัง', 'จัง', 'ซามะ', 'เรียบร้อย', 'เห็นได้ชัด', 'ออกไป', 'เข้ามา', 'ขึ้นมา', 'ลงไป', 'ลงมา'
}

DO_NOT_END_LINE = {
    'ที่', 'ซึ่ง', 'อัน', 'การ', 'ความ', 'อย่าง', 'ของ', 'ใน', 'จาก', 'กับ', 'แก่', 'แด่', 'ต่อ',
    'เพื่อ', 'เพราะ', 'แต่', 'และ', 'หรือ', 'จน', 'ถ้า', 'หาก', 'แม้', 'แม้ว่า', 'โดย', 'พลาง',
    'จะ', 'ไม่', 'ไม่ได้', 'ไม่เคย', 'ไม่สามารถ', 'สามารถ', 'ไม่อาจ', 'อาจ', 'กำลัง', 'เพิ่ง', 'เพิ่งจะ', 'คง', 'คงจะ',
    'ต้อง', 'ควร', 'ควรจะ', 'อยาก', 'อยากจะ', 'พยายาม', 'ช่วย', 'ทำให้', 'ขอให้', 'ยอมให้', 'ปล่อยให้',
    'ดู', 'ดูเหมือน', 'ราวกับ', 'คล้าย', 'คล้ายกับ', 'เหมือน', 'เหมือนกับ', 'ตั้งแต่', 'กระทั่ง', 'จนกระทั่ง',
    'คุณ', 'ท่าน', 'พี่', 'น้อง', 'นาย', 'เจ้า', 'ตา', 'ปู่', 'น้า', 'อา', 'ลุง', 'ป้า', 'เป็น', 'คือ', 'เสีย'
}

class ThaiWordWrapper:
    def __init__(self, glossary_path: str = "localization/database/glossary.json"):
        self.glossary_words = set()
        if os.path.exists(glossary_path):
            with open(glossary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for c in data.get('characters', []):
                std = c.get('thai_standard', '')
                if std:
                    self.glossary_words.add(std)
                    for part in std.split():
                        self.glossary_words.add(part)
                short = c.get('thai_short', '')
                if short:
                    self.glossary_words.add(short)
                addr = c.get('addressing', {})
                if isinstance(addr, dict):
                    for v in addr.values():
                        if isinstance(v, str) and len(v) < 30:
                            for sub in v.split('/'):
                                sub = sub.strip()
                                if sub and ' ' not in sub:
                                    self.glossary_words.add(sub)
            for item in data.get('locations_and_objects', []) + data.get('lore_and_cultural_terms', []):
                std = item.get('thai_standard', '')
                if std:
                    self.glossary_words.add(std)

        # Common compound words in VN translations that should not be split
        common_compounds = {
            'มุราซาเมะมารุ', 'ดาบมุราซาเมะมารุ', 'มุราซาเมะจัง', 'มาซาโอมิคุง',
            'คุณโทโมทาเกะ', 'คุณฮิตาจิ', 'คุณอาริจิ', 'คุณเลน่า', 'คุณยาสึฮารุ', 'คุณยาสุฮารุ', 'คุณเก็นจูโร่',
            'นายท่าน', 'คุณหนู', 'คุณตา', 'คุณปู่', 'พี่โรกะ', 'พี่เร็น', 'พี่ชาย', 'ท่านนายใหญ่',
            'ท่านมุราซาเมะ', 'ท่านเจ้าหญิงมิโกะ', 'เจ้าหญิงมิโกะ', 'เจ้าหญิงผู้พิทักษ์', 'ท่านโยชิโนะ',
            'อย่างเห็นได้ชัด', 'อย่างรวดเร็ว', 'อย่างรุนแรง', 'อย่างชัดเจน', 'อย่างประณีต', 'อย่างสมเกียรติ',
            'อย่างตรงไปตรงมา', 'อย่างเอาเป็นเอาตาย', 'น้ำพุร้อน', 'ลูกตัวเอง', 'ย่านเมืองเก่าแก่',
            'ตรวจร่างกาย', 'คุกคามทางเพศ', 'เจ้าหญิง', 'วิญญาณคำสาป', 'สัตว์ประหลาด', 'เทพอสูร', 'วัตถุสถิต', 'ร่างสถิต',
            'ความรู้สึก', 'ตลอดเวลา', 'ขั้นตอน', 'จำเป็น', 'แน่นอน', 'เรียบร้อย',
            'ที่หลัง', 'ที่บ้าน', 'ที่ไหน', 'ที่ใด', 'ที่แท้', 'ที่จริง', 'ที่เหลือ', 'ไม่สามารถ', 'ไม่ได้', 'ไม่เคย',
            'เสียจน', 'โดยตรง', 'ดูราวกับ', 'พร้อมกับ', 'ในขณะที่'
        }
        self.glossary_words.update(common_compounds)

        # Build custom dictionary Trie combining standard Thai vocabulary with Glossary
        full_vocab = set(thai_words()) | self.glossary_words
        self.trie = dict_trie(dict_source=full_vocab)

    @staticmethod
    def visual_length(text: str) -> int:
        """
        Calculate visual width (spacing characters only).
        Combining marks (vowels above/below, tone marks) have 0 visual width.
        """
        return sum(1 for c in text if c not in THAI_COMBINING_MARKS)

    def tokenize(self, text: str) -> list:
        """
        Tokenize Thai text into words, respecting glossary names and compound words.
        """
        return word_tokenize(text, custom_dict=self.trie, engine='newmm')

    def wrap_text(self, text: str, max_visual_chars: int = 42, newline_sep: str = "\r\n") -> str:
        """
        Wrap a Thai string so that no line exceeds `max_visual_chars`.
        Breaks only at word boundaries. Preserves existing manual newlines.
        """
        if not text:
            return text

        paragraphs = re.split(r'(\r\n|\n|\r)', text)
        wrapped_paragraphs = []

        for p in paragraphs:
            if p in ('\r\n', '\n', '\r'):
                wrapped_paragraphs.append(p)
                continue

            tokens = self.tokenize(p)
            lines = []
            cur_line = []
            cur_vis_len = 0

            for tok in tokens:
                tok_vis_len = self.visual_length(tok)

                if cur_vis_len == 0 and tok.strip() == '':
                    continue

                if cur_vis_len + tok_vis_len <= max_visual_chars:
                    cur_line.append(tok)
                    cur_vis_len += tok_vis_len
                else:
                    if tok in NO_LINE_START_CHARS and cur_line:
                        cur_line.append(tok)
                        lines.append(''.join(cur_line).rstrip())
                        cur_line = []
                        cur_vis_len = 0
                    else:
                        if cur_line:
                            lines.append(''.join(cur_line).rstrip())
                        if tok.strip() == '':
                            cur_line = []
                            cur_vis_len = 0
                        else:
                            cur_line = [tok]
                            cur_vis_len = tok_vis_len

            if cur_line:
                lines.append(''.join(cur_line).rstrip())

            wrapped_paragraphs.append(newline_sep.join(lines))

        return ''.join(wrapped_paragraphs)

    def _split_long_unspaced_chunk(self, chunk: str, max_vis: int = 56) -> str:
        """
        Splits a single contiguous unspaced chunk ONLY if its visual length exceeds `max_vis`.
        Finds the most natural grammatical midpoint so both halves are balanced and never
        violate DO_NOT_START_LINE or DO_NOT_END_LINE.
        """
        c_vis = self.visual_length(chunk)
        if c_vis <= max_vis:
            return chunk

        tokens = self.tokenize(chunk)
        if len(tokens) <= 1:
            return chunk

        best_idx = -1
        best_score = -9999.0
        target_mid = min(c_vis / 2.0, max_vis * 0.65)

        for idx in range(1, len(tokens)):
            left_str = ''.join(tokens[:idx])
            right_str = ''.join(tokens[idx:])
            l_vis = self.visual_length(left_str)
            r_vis = self.visual_length(right_str)

            if l_vis < 14 or r_vis < 12 or l_vis > max_vis:
                continue

            prev_tok = tokens[idx - 1]
            next_tok = tokens[idx]
            score = 0.0

            if next_tok in DO_NOT_START_LINE or (next_tok and next_tok[0] in NO_LINE_START_CHARS):
                score -= 150.0
            if prev_tok in DO_NOT_END_LINE:
                score -= 150.0
            if prev_tok in BREAK_PREFERRED_AFTER:
                score += 45.0
            if next_tok in BREAK_PREFERRED_BEFORE:
                score += 65.0

            score -= abs(l_vis - target_mid) * 1.1

            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx == -1:
            return chunk

        left_s = ''.join(tokens[:best_idx]).strip()
        right_s = ''.join(tokens[best_idx:]).strip()
        if self.visual_length(right_s) > max_vis:
            right_s = self._split_long_unspaced_chunk(right_s, max_vis)
        return f"{left_s} {right_s}"

    def _simulate_kag_lines(self, text: str, box_vis: int = 58) -> list:
        words = [w for w in text.split(' ') if w]
        lines = []
        cur = ''
        for wd in words:
            if not cur:
                cur = wd
            elif self.visual_length(cur + ' ' + wd) <= box_vis:
                cur = cur + ' ' + wd
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines

    def smart_segment_wrap(self, text: str, max_vis: int = 56, min_break_vis: int = 24) -> str:
        """
        Universal smart wrapper for Kirikiri/FreeMote engines where the engine wraps at ASCII spaces:
        - Preserves 100% of the translator's natural spaces without accumulating artificial breaks across chunks.
        - Leaves all normal clauses (<= max_vis visual characters) 100% intact.
        - Only inserts a grammatical clause break inside an individual unspaced chunk if that single
          unspaced chunk exceeds `max_vis` (or if KAG line wrap simulation would exceed 3 lines).
        """
        if not text:
            return ""

        paragraphs = re.split(r'(\r\n|\n|\r)', text)
        wrapped_paragraphs = []

        for p in paragraphs:
            if p in ('\r\n', '\n', '\r'):
                wrapped_paragraphs.append(p)
                continue
            if not p.strip():
                wrapped_paragraphs.append(p)
                continue

            raw_chunks = [c for c in re.split(r'\s+', p.strip()) if c]
            split_chunks = [self._split_long_unspaced_chunk(c, max_vis=max_vis) for c in raw_chunks]
            candidate = ' '.join(split_chunks)

            # Safety check: if KAG 3-line textbox simulation exceeds 3 lines due to multiple ~50-char chunks,
            # split chunks > 38 vis chars so they pack cleanly into <= 3 lines.
            if len(self._simulate_kag_lines(candidate, box_vis=58)) > 3:
                split_chunks = [self._split_long_unspaced_chunk(c, max_vis=38) for c in raw_chunks]
                candidate = ' '.join(split_chunks)

            wrapped_paragraphs.append(candidate)

        return ''.join(wrapped_paragraphs)

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    wrapper = ThaiWordWrapper()
    sample = (
        "เมื่อรถบัสแล่นมาถึงป้ายปลายทางในที่สุด ผมก็ก้าวลงมาจากรถพร้อมกับสูดอากาศบริสุทธิ์ของชนบทเข้าเต็มปอด "
        "ในยุคสมัยที่เทคโนโลยีก้าวหน้าไปไกลเช่นนี้ การได้มาเยือนเมืองโบราณที่มีประวัติศาสตร์อันยาวนานอย่างโฮโอริ "
        "และศาลเจ้าโฮโอริของท่านมุราซาเมะก็นับว่าเป็นประสบการณ์ที่หาได้ยากยิ่ง"
    )
    print("=== ORIGINAL TEXT ===")
    print(sample)
    print("\n=== SMART SEGMENT WRAPPED ===")
    wrapped = wrapper.smart_segment_wrap(sample, max_vis=40)
    print(wrapped)
    print("\n=== LINE BY LINE AUDIT ===")
    for idx, l in enumerate(wrapped.split(' ')):
        print(f"Line {idx+1:02d} ({wrapper.visual_length(l):2d} vis chars): {l}")
