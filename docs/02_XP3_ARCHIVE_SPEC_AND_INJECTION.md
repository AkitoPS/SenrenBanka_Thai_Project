# 02. โครงสร้างไบนารี XP3 และการฉีดไฟล์ (XP3 Archive Specification & Injection)

เอกสารนี้ระบุรายละเอียดระดับไบนารี (Binary Specification) ของไฟล์คลัง `.xp3` ในเอนจิน Kirikiri Z ของ Yuzusoft และขั้นตอนการคำนวณ Offset ในการสร้างไฟล์ใหม่

---

## 1. โครงสร้างระดับไบนารีของ XP3 (XP3 Header & Redirection)

ไฟล์ `.xp3` ในเกมของ Yuzusoft ประกอบด้วยส่วนประกอบหลักดังนี้:

```text
+-------------------------------------------------------------+
| Offset 00..10 (11 Bytes): Magic b'XP3\r\n \n\x1a\x8bg\x01'   |
+-------------------------------------------------------------+
| Offset 11..18 (8 Bytes):  redir_off = 23 (Little-Endian)   |
+-------------------------------------------------------------+
| Offset 19..22 (4 Bytes):  Dummy / Padding                   |
+-------------------------------------------------------------+
| Offset 23     (1 Byte):   Flag = 0x80                       |
| Offset 24..31 (8 Bytes):  Len = 0                           |
| Offset 32..39 (8 Bytes):  real_idx_off (ชี้ไปที่ดัชนีท้ายไฟล์) |
+-------------------------------------------------------------+
| Offset 40..End-of-Data:   Data Payloads (เนื้อหาไฟล์ต่างๆ)   |
+-------------------------------------------------------------+
| Offset hnfn_off:          hnfn Compressed Data (ตารางชื่อไฟล์)|
+-------------------------------------------------------------+
| Offset real_idx_off:      Compressed Index Block            |
|   - 1 Byte:               Flag (0x01 = zlib compressed)     |
|   - 8 Bytes (uint64):     comp_sz (ขนาดบีบอัด)              |
|   - 8 Bytes (uint64):     uncomp_sz (ขนาดคลายบีบอัด)        |
|   - comp_sz Bytes:        zlib payload                      |
+-------------------------------------------------------------+
```

### กลไก Redirection ที่ Offset 23
เอนจิน Kirikiri Z รุ่นของ Yuzusoft **ไม่อ่าน Index ที่ Offset 11 ตรงๆ** แต่จะอ่านตัวชี้ `redir_off` ที่ Offset 11 ซึ่งมีค่าเป็น `23`:
* ที่ Offset 23 จะมีไบต์ `0x80`
* ถัดไป 8 ไบต์คือ Length
* **ที่ Offset 32 (Offset $23 + 9$) คือตัวชี้พิกัด `real_idx_off` ที่แท้จริง (uint64 little-endian)**

> [!CAUTION]
> หากเขียนโปรแกรมแก้ไข XP3 โดยนำ `real_idx_off` ไปใส่ทับที่ Offset 11 โดยตรง เอนจินจะมองว่าพิกัดนั้นคือ `redir_off` และพยายามอ่าน Offset 23 จากท้ายไฟล์ ส่งผลให้เกิดข้อผิดพลาด EOF Error ทันที

---

## 2. โครงสร้างดัชนีคลายบีบอัด (Decompressed Index Structure)

เมื่อคลายการบีบอัดบล็อกดัชนีด้วย `zlib.decompress()` ข้อมูลภายในจะแบ่งเป็น Chunk ย่อยๆ:

### 1. `sen:` Chunk (Steam Extension Chunk - ขนาด 52 ไบต์)
* `0..3` (4B): Magic `b'sen:'`
* `4..11` (8B): Chunk Length = `40` (uint64)
* `12..19` (8B): `hnfn_off` พิกัดของตารางชื่อไฟล์ใน Archive
* `20..23` (4B): `hnfn_uncomp` ขนาดตารางก่อนบีบอัด
* `24..27` (4B): `hnfn_comp` ขนาดตารางหลังบีบอัด
* `28..51` (24B): Steam Digital Signature
  `b'\n\x00CSK`\n\xff\x07N\xb1\x82S\x00t\x00e\x00a\x00m\x00\x00\x00'`

### 2. `File` Chunks (รายการไฟล์แต่ละไฟล์)
แต่ละไฟล์ใน Archive จะเริ่มต้นด้วย Magic `b'File'` และมี Sub-chunks ภายใน:
* **`info` Chunk:**
  - `iflags` (4B): แฟล็กการเข้ารหัส (`0x80000000` = Encrypted, `0x00000000` = Plaintext)
  - `orig_sz` (8B): ขนาดจริงของไฟล์
  - `arc_sz` (8B): ขนาดที่จัดเก็บใน Archive
  - `name_len` (2B): จำนวนตัวอักษรของชื่อไฟล์
  - `name` (name_len * 2 Bytes): ชื่อไฟล์เข้ารหัส UTF-16LE
* **`segm` Chunk:**
  - `sflags` (4B): แฟล็กการบีบอัด (0 = ไม่บีบอัด, 1 = zlib)
  - `offset` (8B): พิกัดเริ่มต้นของไฟล์ใน Archive (uint64)
  - `orig_sz` (8B), `arc_sz` (8B)
* **`adlr` Chunk:**
  - ค่า Adler32 Checksum (4B) ของไฟล์ต้นฉบับ
* **`time` Chunk:**
  - ค่า File Timestamp (8B)

---

## 3. ตาราง `hnfn` (Hash Name to File Name Mapping)

ใน `data.xp3` ชื่อไฟล์ใน `info` Chunk มักจะไม่ใช่ชื่อไฟล์จริง แต่เป็นชื่อ Hash 32 ตัวอักษร เช่น:
* Member 8: `1203927249aefb82c64b9593d5ade725`
* Member 9: `a93f5d637ed6f855e4a4981953d6c653`

เอนจินจะเชื่อมโยงชื่อ Hash เข้ากับ Path จริงของไฟล์ (`font/font1_32.tft`) ผ่าน **ตาราง `hnfn`**:
* ตาราง `hnfn` ถูกจัดเก็บแยกต่างหากที่ตำแหน่ง `hnfn_off`
* บันทึกแต่ละระเบียนใน `hnfn` ประกอบด้วย:
  - Magic: `b'hnfn'` (4 ไบต์)
  - Record Size: 8 ไบต์ (ปกติคือ 42 = `0x2A`)
  - **Adler32 Checksum (4 ไบต์):** ค่าตรงกับ `adlr` ของไฟล์นั้นในดัชนีหลัก
  - Name Length (2 ไบต์) + ชื่อ Path เต็มในแบบ UTF-16LE (เช่น `font/font1_32.tft\x00`)

| Member | Hash Name | Adler32 | File Path ในตาราง `hnfn` | ขนาดต้นฉบับ |
| :---: | :---: | :---: | :---: | :---: |
| **8** | `1203927249aefb82c64b9593d5ade725` | `0xcfdd73fc` | `font/font1_32.tft` | 1,389,504 ไบต์ |
| **9** | `a93f5d637ed6f855e4a4981953d6c653` | `0x9fe15f6a` | `font/font1_39.tft` | 1,692,596 ไบต์ |

> [!TIP]
> เมื่อเราฉีดไฟล์ฟอนต์ใหม่แทนที่ Member 8 และ 9 เราต้องคงค่า **Adler32 เดิม (`0xcfdd73fc` และ `0x9fe15f6a`)** ไว้ใน `adlr` chunk เพื่อให้เอนจินยังคงจับคู่ชื่อ `font/font1_32.tft` ได้ถูกต้องโดยไม่ต้องไปแก้ไขตาราง `hnfn` ที่ซับซ้อน

---

## 4. อัลกอริทึมการฉีดไฟล์และปรับพิกัด (Offset Shifting Algorithm)

เมื่อเราขยายขนาดไฟล์ฟอนต์ เช่น:
* `font1_32`: ขนาดเพิ่มขึ้น $\Delta_1 = 1,418,695 - 1,389,504 = +29,191$ ไบต์
* `font1_39`: ขนาดเพิ่มขึ้น $\Delta_2 = 1,728,848 - 1,692,596 = +36,252$ ไบต์
* ผลรวมการเปลี่ยนแปลง: $\Delta_{\text{total}} = \Delta_1 + \Delta_2 = +65,443$ ไบต์

เราต้องคำนวณและปรับโครงสร้าง Archive ตามลำดับดังนี้:

```python
# 1. จัดเรียงเนื้อหาไฟล์ใหม่
part1 = orig[:orig_m8_off]  # ไฟล์ที่ 0..7 อยู่ที่เดิม
part2 = font32_encrypted  # Member 8 (ขนาดใหม่)
part3 = (
    b""  # ไฟล์ระหว่าง 8 กับ 9 (ใน data.xp3 สองไฟล์นี้อยู่ติดกันพอดี)
)
part4 = font39_encrypted  # Member 9 (ขนาดใหม่)
part5 = orig[
    orig_m9_off + orig_size39 : orig_hnfn_off
]  # ไฟล์ที่ 10..1277 ทั้งหมด

# 2. คำนวณตำแหน่ง hnfn ใหม่
new_hnfn_off = orig_hnfn_off + total_delta
part6 = orig_hnfn_comp_data  # ตาราง hnfn

# 3. อัปเดต segm chunk ใน Index
# - ไฟล์ 0..7: offset เดิม
# - ไฟล์ 8: offset เดิม (1,784,260)
# - ไฟล์ 9: offset เดิม + delta32 (3,202,955)
# - ไฟล์ 10..1277: offset เดิม + total_delta

# 4. ประกอบ sen: chunk ใหม่
new_sen_body = (
    struct.pack('<QII', new_hnfn_off, orig_hnfn_uncomp, orig_hnfn_comp)
    + steam_sig
)
new_sen_chunk = b'sen:' + struct.pack('<Q', 40) + new_sen_body

# 5. บีบอัดดัชนีและต่อท้ายไฟล์
full_new_idx = new_sen_chunk + new_idx_body
new_idx_comp = zlib.compress(full_new_idx)
new_real_idx_off = new_hnfn_off + len(part6)

# 6. อัปเดตพิกัดชี้ที่ไบต์ 32 (redir_off + 9)
struct.pack_into('<Q', new_archive, 32, new_real_idx_off)
```
