# Font scaling tags and sibling string pools in Kirikiri Z and FreeMote PSB

## 1. Overview
In Yuzusoft's Kirikiri Z FreeMote scenario engine (such as in Senren＊Banka), text rendering is not strictly uniform in size. Dialogue lines frequently employ dynamic font-size alterations for emotional and dramatic emphasis:
- Shouting, screams, or grand announcements are scaled up (such as `+123%` or `+115%`).
- Whispers, murmurs, or mutterings are scaled down (such as `61%`, `69%`, or `76%`).

When attempting localization, these non-standard lines frequently revert to English despite having valid translations in spreadsheets. This document explains the root cause and the matching algorithm used to resolve it.

---

## 2. The Kirikiri tag system: `%<number>;`

In Kirikiri script compilation, font sizing inside dialogue strings is controlled by prefix tags formatted as:
`%<scaling_percentage>;<Dialogue Text>`

Examples from Senren＊Banka:
- `%123;MAKO'S TURNED INTO A HUSSYYYYYY!` (Large font, +123%)
- `%115;Wh-What the... Bllleeeuuurrrrggghhh!?` (Large font, +115%)
- `%69;Good grief, Master...` (Small font, 69%)
- `%76;Mutter, mutter...` (Small font, 76%)

In the scenario's compiled binary string table, these tags are embedded directly at the start of the string entry.

---

## 3. Dual sibling string pool architecture

The Kirikiri Z engine maintains two distinct rendering streams during visual novel playback:
1. The active dialogue window (Display): renders text with visual tags, sound triggers, and typography scaling.
2. The backlog history screen (Log): renders plain dialogue text in a unified history list, stripping transient visual tags.

Because of this dual-subsystem requirement, every dialogue line that contains a font scaling tag is stored twice in the scenario string table:

```text
[Scenario String Pool]
Index 214:  "%123;Awawawawaaaaaahh!?"       <-- Display Variant (Contains tag)
Index 215:  "Awawawawaaaaaahh!?"            <-- Backlog Variant (Clean text)
```

### The pitfall
Standard localization pipelines extract text from game scripts by matching clean strings against translation spreadsheets. 
- Spreadsheets typically hold only the clean variant: `Awawawawaaaaaahh!? -> อวาวาวาวาาาาาาา!?`
- If the injector performs exact matching:
  - It matches Index 215 (Backlog Variant) and replaces it with Thai.
  - It misses Index 214 (Display Variant) because `%123;` does not match the clean English string.
- Result: The active game screen continues to show English, while the backlog screen shows Thai.

---

## 4. The engineering solution: canonical variant pairing

To eliminate this discrepancy, the injection pipeline implements canonical matching and sibling synchronization:

```python
def canon_variant(t: str) -> str:
    """Strips sizing tags, escaped symbols, line breaks, and whitespace for canonical matching."""
    s = str(t).strip().replace('\r\n', '\n')
    s = re.sub(r'^%\d+;', '', s)
    s = s.replace(r'\%', '%')
    s = s.replace('\\n', '').replace('\\r', '')
    s = re.sub(r'\s+', '', s)
    return s

def encode_for_pool_entry(pool_str: str, shaped_th: str) -> bytes:
    """Preserves font-size tags on display variants while emitting clean text on backlog variants."""
    clean_shaped = re.sub(r'^%\d+;', '', shaped_th)
    m_pref = re.match(r'^(%\d+;)', pool_str)
    if m_pref:
        return (m_pref.group(1) + clean_shaped).encode('utf-8')
    return clean_shaped.encode('utf-8')
```

### Key principles:
1. Tag preservation: The injection engine extracts the tag prefix from the original string and prepends it to the newly shaped Thai string.
2. Sibling synchronization: When a canonical match is found, all sibling indices associated with that canonical string are simultaneously injected.
3. Typography shaping: Thai combining marks and tone indicators are shaped with zero-advance PUA glyphs before prefixing the `%XX;` tag, ensuring that the Kirikiri font renderer properly calculates bounding boxes at scaled sizes.
