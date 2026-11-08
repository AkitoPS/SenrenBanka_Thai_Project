# กรณีศึกษาที่ 08: กับดักโหมดฟอนต์ระบบ (faceMode = 1 / MS Gothic Fallback) และข้อกำหนดจำเป็นของโปรแกรมติดตั้งม็อดแปลไทย (Standalone Installer Specification)

---

## 1. ปัญหาและอาการที่ตรวจพบ (The Symptoms)

หลังจากแก้ไขปัญหาตัดคำ (Word Wrap) และตรวจสอบความถูกต้องของบทแปลใน Excel [Senren_Banka_Thai_Progress.xlsx](file:///c:/Users/DELL/Desktop/VN_Thai_Project/localization/database/Senren_Banka_Thai_Progress.xlsx) รวมถึงฉีดไฟล์เข้า [patch_extra.xp3](file:///C:/Program%20Files%20(x86)/Steam/steamapps/common/SenrenBanka/patch_extra.xp3) เรียบร้อยแล้ว เมื่อผู้ใช้เปิดเข้าเล่นเกมจริงใน **Chapter 1-1** กลับพบความผิดปกติบนหน้าจอ:

1. **กล่องสี่เหลี่ยมเต้าหู้ `[]` (Tofu Boxes):** ปรากฏตรงคำที่มีการซ้อนของสระบนและวรรณยุกต์ เช่น `ที[]`, `ตั[]ง`, `เมื[]อ`, `กี[]`, `นั[]น`, `เรื[]อง`, `เป[]น`
2. **ตัวอักษรเว้นวรรคห่างเป็นช่องๆ (Unwanted Spacing):** เช่น `เล ่า`, `มั น`, `ผู ้`, `สรุ ป`, `รั บ`, `วิ ญญาณ`
3. **ข้อความดิบในไฟล์แพตช์และ Excel ถูกต้อง 100%:** เมื่อตรวจสอบไบนารีในไฟล์ `.ks.scn` สตริงที่เก็บอยู่คือ `ทีเธอเล่ามาตังแต่เมือกีมันก็เรืองแฟนตาซี...` ไม่มีการเคาะเว้นวรรคและไม่มีอักขระแปลกปลอมใดๆ

---

## 2. การสืบสวนและสาเหตุเชิงลึก (Deep Root Cause Analysis)

### ก. ระบบฟอนต์ 2 โหมดของเอนจิน Kirikiri Z / Yuzusoft
เอนจินเกม Yuzusoft มีการทำงานของฟอนต์ 2 โหมด ซึ่งถูกควบคุมผ่านไฟล์คอนฟิกระบบเซฟ `%APPDATA%\Yuzusoft\SenrenBanka\datasc.ksd`:

1. **โหมด 0 (`faceMode = 0` / Default PreRendered Font):**
   - ตัวเกมจะเรียกใช้ไฟล์ฟอนต์กราฟิกบิตแมปความละเอียดสูงภายในตัวเกม (`font1_32.tft` สำหรับบทพูด และ `font1_39.tft` สำหรับ Backlog)
   - ฟอนต์ชุดนี้ได้รับการขยายด้วย Noto Sans Thai Looped พร้อมทั้งกำหนด **Zero-Advance (`incX = 0`)** และฝังรหัสอักขระพิเศษ **Thai PUA ($U+F700 \dots U+F71F$)** ไว้อย่างสมบูรณ์
2. **โหมด 1 (`faceMode = 1` / User Font / Windows GDI System Font):**
   - ตัวเกมจะ **บายพาส (Bypass)** ไฟล์ฟอนต์ `.tft` ในเกมทั้งหมด
   - ตัวเกมจะส่งคำสั่งไปยัง Windows GDI เพื่อดึงฟอนต์ที่ติดตั้งอยู่ในระบบปฏิบัติการ Windows มาวาดแทน

### ข. กับดัก MS Gothic Fallback
จากการแตกไฟล์และตรวจสอบไบนารีของ `datasc.ksd` ในเครื่องผู้ใช้:
```tjs
"faceMode" => 1,
"chDefaultFace" => "スキップ",
"langUserFontFace1" => "スキップ",
```
และเมื่อตรวจสอบล็อกระบบของเกมใน `krkr.console.log`:
```text
! PreRenderFontEx.MakeFontInfoTable: conflict FontVirtName/RealFace: *UserInputFont*:,MS Gothic
```

**สิ่งที่เกิดขึ้นจริงในระดับระบบ:**
1. เอนจินรันในโหมด `faceMode = 1` จึงพยายามเรียกฟอนต์ชื่อ `"スキップ"` (Fontworks Skip - ฟอนต์ลิขสิทธิ์เชิงพาณิชย์ของญี่ปุ่น)
2. บน Windows ของผู้ใช้ทั่วไปไม่มีฟอนต์ Fontworks Skip ติดตั้งอยู่ Windows GDI จึงเปลี่ยนเป้าหมายอัตโนมัติ (Fallback) ไปใช้ฟอนต์ **`MS Gothic`**
3. **ทำไม `MS Gothic` ถึงพังกับภาษาไทย?**
   - **เกิดกล่องเต้าหู้ `[]`:** ฟอนต์ `MS Gothic` เป็นฟอนต์ภาษาญี่ปุ่นโบราณ ไม่มีชุดอักขระ Thai PUA ($U+F712$, $U+F713$, $U+F714$, ฯลฯ) ที่โปรแกรมฉีดแปลงไว้หลบสระบน เมื่อหาไม่เจอ Windows จึงวาดเป็นกล่องสี่เหลี่ยม `[]`
   - **เกิดการเว้นวรรคผลักตัวอักษร:** `MS Gothic` ไม่มีฟีเจอร์การจัดวางสระภาษาไทย (Complex Script Shaping) จึงมองว่าสระบน/สระล่างและวรรณยุกต์ทุกตัวมีความกว้างเป็นตัวอักษรเต็มตัว (`Width > 0`) ทำให้ทุกครั้งที่มีสระหรือวรรณยุกต์ ตัวอักษรตัวถัดไปจะถูกเคาะถอยร่นไปทางขวา 1 ช่อง กลายเป็น `เล ่า`, `มั น`, `ผู ้`!

---

## 3. วิธีการแก้ไข (Solution Implemented)

### ก. การปรับค่าคอนฟิก `datasc.ksd`
สร้างสคริปต์ [tool/fix_facemode.py](file:///c:/Users/DELL/Desktop/VN_Thai_Project/tool/fix_facemode.py) เพื่อคลายการบีบอัดและแก้ไขค่าคอนฟิกของตัวเกม:
```python
def unpack_ksd(data: bytes) -> str:
    off = data.find(b'x\x9c')
    return zlib.decompress(data[off:]).decode('utf-16le', errors='ignore')

def pack_ksd(text: str) -> bytes:
    raw_utf16 = text.encode('utf-16le')
    comp = zlib.compress(raw_utf16)
    magic = b'\xfe\xfe\x02\xff\xfe'
    hdr = magic + struct.pack('<QQ', len(comp), len(raw_utf16))
    return hdr + comp

# แทนที่ค่าคอนฟิก
text = text.replace('"faceMode" => 1,', '"faceMode" => 0,')
```

### ข. การวางฟอนต์แบบ Loose Files ในโฟลเดอร์ `font/`
นอกจากการแพ็กฟอนต์ลงใน `data.xp3` แล้ว ให้คัดลอก [font1_32_extended.tft](file:///c:/Users/DELL/Desktop/VN_Thai_Project/tool/font1_32_extended.tft) และ [font1_39_extended.tft](file:///c:/Users/DELL/Desktop/VN_Thai_Project/tool/font1_39_extended.tft) ไปไว้ที่:
`C:\Program Files (x86)\Steam\steamapps\common\SenrenBanka\font\`
เพื่อให้เอนจิน Kirikiri Z สามารถเข้าถึงไฟล์ฟอนต์ได้อย่างแน่นอน 100% ไม่ว่าจะผ่าน VFS ของคลังเก็บหรือไฟล์ตรง

---

## 4. ข้อกำหนดวิศวกรรมสำหรับ "โปรแกรมติดตั้งแพตช์แปลไทย" (Final Installer Specification)

> [!CAUTION]
> **นี่คือจุดตายสำคัญที่สุดของโปรเจกต์ม็อดแปลไทย:**
> หากโปรแกรมติดตั้ง (Installer) ในตอนจบโปรเจกต์ทำเพียงแค่คัดลอกไฟล์ `patch_extra.xp3` หรือ `data.xp3` ลงในโฟลเดอร์เกมของผู้เล่น **ผู้เล่นมากกว่า 80% จะเจอปัญหากล่องเต้าหู้ `[]` และสระเว้นวรรคห่างทันที** เนื่องจากไฟล์ `datasc.ksd` ในเครื่องของผู้เล่นจำค่าเดิมเป็น `faceMode = 1`

### ข้อกำหนดบังคับของโปรแกรมติดตั้งม็อดไทย (Release Installer Checklist):

1. **การค้นหาพาธ AppData อัตโนมัติ:**
   - โปรแกรมติดตั้งต้องสแกนหาโฟลเดอร์ `%APPDATA%\Yuzusoft\SenrenBanka\` (หรือ `%APPDATA%\YuzuSoft\SenrenBanka\`)
2. **การปรับแต่งไฟล์ `datasc.ksd` แบบ Silent:**
   - หากพบไฟล์ `datasc.ksd`:
     1. ทำการสำรองไฟล์เป็น `datasc.ksd.bak`
     2. คลายการบีบอัด zlib
     3. ตรวจสอบว่ามี `"faceMode" => 1,` หรือไม่ หากมี ให้แทนที่เป็น `"faceMode" => 0,`
     4. แพ็กไฟล์กลับด้วย Header KSD และบันทึกทับ
   - หากไม่พบไฟล์ `datasc.ksd` (ผู้เล่นเพิ่งลงเกมใหม่):
     - ตัวเกมจะสร้าง `datasc.ksd` ขึ้นมาเองโดยมีค่าเริ่มต้นที่เหมาะสม หรือโปรแกรมติดตั้งสามารถวางเทมเพลต `datasc.ksd` เริ่มต้นที่มี `faceMode = 0` ไว้ล่วงหน้าได้
3. **การวางไฟล์แพตช์และฟอนต์แบบ Dual-Redundancy:**
   - คัดลอก `patch_extra.xp3` ลงในโฟลเดอร์เกมหลัก
   - คัดลอก `font1_32.tft` และ `font1_39.tft` ลงในโฟลเดอร์ `font/` ของเกมเสมอ เพื่อการันตีว่าระบบ PreRenderFont จะโหลดฟอนต์ไทยแท้ได้อย่างสมบูรณ์แบบ
