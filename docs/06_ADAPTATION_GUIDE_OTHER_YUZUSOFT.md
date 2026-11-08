# 06. คู่มือการนำไปประยุกต์ใช้กับเกม Yuzusoft อื่นๆ (Adaptation Guide for Other Titles)

เอกสารนี้คือคู่มือแบบทีละขั้นตอน (Step-by-Step Cookbook) สำหรับนำชุดความรู้และเครื่องมือนี้ไปดัดแปลงแปลเกมอื่นๆ ของค่าย **Yuzusoft** เช่น:
* *Sanoba Witch (サノバウィッチ / Sabbat of the Witch)*
* *Riddle Joker (リドルジョーカー)*
* *Cafe Stella and the Reaper's Butterflies (喫茶ステラと死神の蝶)*
* *Tenshi Souzou "Re-Boot!" (天使☆騒々 RE-BOOT!)*
* *Noble ☆ Works, Dracu-Riot!, Amairo Islenauts*

---

## 1. เช็กลิสต์การเริ่มโปรเจกต์ใหม่ (Master Checklist)

```text
[ ] ขั้นที่ 1: ตรวจสอบเวอร์ชันเอนจิน และสำรองข้อมูลต้นฉบับ (Backup)
[ ] ขั้นที่ 2: ถอดรหัส Index ของ data.xp3 และอ่านตาราง hnfn
[ ] ขั้นที่ 3: ระบุตำแหน่งไฟล์ฟอนต์ (font1_32, font1_39) และค้นหา XOR Key
[ ] ขั้นที่ 4: สกัดฟอนต์เดิมออกมาเป็น Base TFT Template
[ ] ขั้นที่ 5: สร้าง Extended Thai TFT ด้วย Noto Sans Thai Looped
[ ] ขั้นที่ 6: ฉีดฟอนต์ใหม่กลับเข้าสู่ data.xp3 และทดสอบเปิดเกม
[ ] ขั้นที่ 7: ค้นหา XOR Key ของไฟล์สคริปต์สเกนาริโอ (.ks.scn)
[ ] ขั้นที่ 8: สร้างแพตช์ทดสอบ Prologue สั้นๆ ลง patch_extra.xp3
[ ] ขั้นที่ 9: ตรวจสอบความถูกต้องทางสายตา (Visual Verification)
[ ] ขั้นที่ 10: เริ่มกระบวนการแปลแบบเต็มรูปแบบ
```

---

## 2. ขั้นตอนปฏิบัติการทีละขั้น (Detailed Step-by-Step)

### ขั้นที่ 1: ตรวจสอบและสำรองข้อมูล
1. ทำสำเนาไฟล์ต้นฉบับทั้งหมดเก็บไว้ในโฟลเดอร์ `original/` เสมอ ห้ามทำงานบนโฟลเดอร์เกมของ Steam โดยตรงโดยไม่มี Backup
2. ตรวจสอบว่าในโฟลเดอร์เกมมีไฟล์ `data.xp3`, `scn.xp3`, `patch.xp3` ครบถ้วนหรือไม่

### ขั้นที่ 2 & 3: การหาตำแหน่งฟอนต์และ Brute-force หา XOR Key ใน `data.xp3`
ในเกมใหม่ สมาชิกที่เป็นฟอนต์อาจไม่ได้อยู่ที่ Member 8 และ 9 เสมอไป และ XOR Key อาจแตกต่างกัน เราสามารถใช้โค้ด Python นี้ค้นหาได้อัตโนมัติ:

```python
"""ค้นหาไฟล์ฟอนต์และ XOR Key ใน data.xp3 ของเกมใดๆ"""

import struct, zlib


def brute_force_tft_key(xp3_path):
  with open(xp3_path, 'rb') as f:
    f.seek(23)
    f.read(9)
    real_idx_off = struct.unpack('<Q', f.read(8))[0]
    f.seek(real_idx_off)
    f.read(1)
    zlen, olen = struct.unpack('<QQ', f.read(16))
    decomp = zlib.decompress(f.read(zlen))

  # ค้นหาใน hnfn เพื่อดูว่าฟอนต์อยู่ที่ member ใด
  sen_body = decomp[12:52]
  hnfn_off, ulen, clen = struct.unpack('<QII', sen_body[:16])
  with open(xp3_path, 'rb') as f:
    f.seek(hnfn_off)
    hnfn_data = zlib.decompress(f.read(clen))

  # TFT Magic ที่ต้องการ: b'TVP pre-rendered font\x1a'
  TARGET_HEADER = b'TVP pre-rendered font\x1a'

  # วนลูปตรวจทุกไฟล์ใน index
  # ... (ดูสคริปต์เต็มใน method/tools/)
```

> [!TIP]
> **สูตรการถอดรหัสฟอนต์ของ Yuzusoft:**
> ฟอนต์ `.tft` จะขึ้นต้นด้วย `TVP pre-rendered font\x1a` เสมอ หากเรานำไบต์แรกของ Member นั้นมา XOR กับตัวอักษร `'T'` (`0x54`) เราจะได้ **Key ที่ 1** ทันทีในเสี้ยววินาที!
> ```python
> key1 = member_bytes[0] ^ ord('T')
> ```

### ขั้นที่ 4 & 5: การสร้างฟอนต์ไทยขยาย
1. นำฟอนต์ `.ttf` ที่ต้องการ (แนะนำ **Noto Sans Thai Looped**) มาวางในโฟลเดอร์เครื่องมือ
2. รันคำสั่ง `python method/tools/build_extended_tft.py` เพื่อสร้างทั้ง:
   - `font1_32_extended.tft` (สำหรับบทพูด)
   - `font1_39_extended.tft` (สำหรับ Backlog)
3. เครื่องมือจะคำนวณ Zero-advance และสร้าง PUA $U+F700 \dots U+F71F$ ให้โดยอัตโนมัติ

### ขั้นที่ 6: ฉีดเข้าสู่ `data.xp3`
1. รันสคริปต์ `method/tools/inject_data_xp3_fonts.py`
2. สคริปต์จะคำนวณ Delta, ปรับ Offset ใน Segm, รักษาตาราง `hnfn` และคงลายเซ็น Steam 24 ไบต์ให้อัตโนมัติ

### ขั้นที่ 7 & 8: การหา XOR Key ของบทพูด PSB (`.ks.scn`)
ไฟล์สเกนาริโอจะขึ้นต้นด้วย `PSB\x00` เสมอ ดังนั้นเราสามารถหา Key ได้ทันที:
```python
key_psb = scenario_bytes[0] ^ ord('P')  # ใน Senren Banka คือ 0x01
```
และจุดตัด `hdr7` จะอยู่ที่ไบต์ 36..39 เสมอ:
```python
head = bytes([b ^ key_psb for b in scenario_bytes[:40]])
hdr7 = struct.unpack('<I', head[36:40])[0]
key_body = scenario_bytes[hdr7] ^ 0x00  # หา Key ส่วนตัว
```

### ขั้นที่ 9: ทดสอบเปิดเกม
1. เปิดเกมและกดเริ่มเกมใหม่
2. ตรวจสอบว่าบทสนทนาภาษาไทยแสดงผลสมบูรณ์
3. กดปุ่มลูกกลิ้งเมาส์ขึ้น (หรือคลิก Log) เพื่อเปิดหน้าต่าง Backlog ตรวจสอบว่าไม่มีตัวหนังสือเต้าหู้ `[]` และสระไม่ลอย
4. เมื่อผ่านขั้นตอนนี้ แสดงว่าโครงสร้างระบบพร้อมสำหรับการแปลเนื้อหาทั้งหมด 100%!
