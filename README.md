# Senren＊Banka (千恋＊万花) Thai localization project
### โครงการแปลภาษาไทยและวิศวกรรมย้อนกลับระดับไบนารีสำหรับเกม Senren＊Banka (Steam Edition)

[![Status](https://img.shields.io/badge/Status-100%25_Playable-brightgreen.svg)]()
[![Engine](https://img.shields.io/badge/Engine-Kirikiri_Z_/_FreeMote_PSB-blue.svg)]()
[![Language](https://img.shields.io/badge/Language-Thai_(ภาษาไทย)-red.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows_/_Steam-black.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## สารบัญ / Table of contents
- [จุดเด่นของโปรเจกต์ (Key highlights)](#จุดเด่นของโปรเจกต์-key-highlights)
- [บันทึกการเดินทางและบทเรียนทางวิศวกรรม (The technical post-mortem)](#บันทึกการเดินทางและบทเรียนทางวิศวกรรม-the-technical-post-mortem)
- [สำหรับผู้เล่นทั่วไป: วิธีติดตั้งม็อด (Installation for players)](#สำหรับผู้เล่นทั่วไป-วิธีติดตั้งม็อด-installation-for-players)
- [สำหรับนักแปลและนักพัฒนา: แก้คำแปลด้วย Excel และคอมไพล์จาก source code (Developer guide)](#สำหรับนักแปลและนักพัฒนา-แก้คำแปลด้วย-excel-และคอมไพล์จาก-source-code-developer-guide)
- [โครงสร้างคลังเก็บข้อมูล (Repository structure)](#โครงสร้างคลังเก็บข้อมูล-repository-structure)
- [ข้อสงวนสิทธิ์ทางกฎหมาย (Legal disclaimer)](#ข้อสงวนสิทธิ์ทางกฎหมาย-legal-disclaimer)

---

## จุดเด่นของโปรเจกต์ (Key highlights)

- แปลบทสนทนาครบถ้วนทั้ง 92 ตอน (60,607 บรรทัด) ทั้งเนื้อเรื่องหลัก รูทตัวละคร และเนื้อหาเสริม Free DLC ครบทุกฉาก
- รองรับขนาดตัวอักษรพิเศษ (Dynamic Font Scaling) ถอดรหัสและฉีดภาษาไทยลงใน Kirikiri Tags (`%123;`, `%115;`, `%61;`, `%69;`, `%76;`) ทั้งเสียงตะโกนและเสียงกระซิบ ไร้ตัวหนังสือภาษาอังกฤษตกค้าง
- ระบบฟอนต์ Pre-rendered TFT Matrix 20 ขนาด สร้างฟอนต์บิตแมประดับไบนารีรองรับทุกหน้าจอ (บทสนทนาสด, Backlog, หน้าต่างระบบ)
- ระบบจัดรูปสระวรรณยุกต์ 3 ระดับ (Thai PUA Typography Shaper) สระไม่ลอย วรรณยุกต์ไม่เดินหน้า ไม่ชนกับสระบน รองรับสระอำและพยัญชนะหางยาว
- ระบบตัดคำตามหลักไวยากรณ์ไทยด้วย PyThaiNLP ไม่ตัดคำขาดครึ่งบรรทัด
- รักษาความปลอดภัยและความเข้ากันได้กับ Steam ฝังลายเซ็น Steam DRM 24 ไบต์ในบล็อก `sen:` และมีระบบป้องกัน Save Game Desync ผ่าน `-savecloud=no`
- ตัวติดตั้งอัตโนมัติค้นหาโฟลเดอร์เกม Steam ข้ามไดรฟ์ และซ่อมค่า `faceMode = 0` ใน `datasc.ksd` เพื่อป้องกันปัญหาฟอนต์สี่เหลี่ยมในเครื่องผู้เล่น

---

## หมายเหตุเกี่ยวกับการแปลและการพัฒนาต่อ (AI translation and open development notice)

- **การแปลด้วย AI**: บทสนทนาในโปรเจกต์นี้ได้รับการแปลและเรียบเรียงโดยใช้ปัญญาประดิษฐ์ (AI) ช่วยแปล แม้จะผ่านการตรวจทานและแก้ไขมาอย่างต่อเนื่อง แต่อาจยังมีจุดที่คำแปลคลาดเคลื่อน หลุดบริบท หรือสำนวนไม่ลื่นไหลหลงเหลืออยู่บ้าง
- **เปิดกว้างสำหรับการนำไปพัฒนาต่อ**: ผู้สนใจทุกคนสามารถนำไฟล์สคริปต์ ฐานข้อมูลคำแปล เครื่องมือ และบทเรียนในคลังนี้ ไปใช้งาน ดัดแปลง แก้ไขขัดเกลาสำนวนต่อ หรือพอร์ตไปลงอุปกรณ์และแพลตฟอร์มอื่นๆ (เช่น Steam Deck, Handhelds, หรืออุปกรณ์อื่นๆ) ได้อย่างอิสระเต็มที่ตามต้องการ

---

## บันทึกการเดินทางและบทเรียนทางวิศวกรรม (The technical post-mortem)

โปรเจกต์นี้มีเอกสารบันทึกวิศวกรรมย้อนกลับที่อธิบายปัญหาจริงตั้งแต่ระดับไบนารี วิธีการตรวจสอบ และสถาปัตยกรรมที่ใช้แก้ปัญหาอย่างละเอียดทั้งสองภาษา:

- [อ่านบันทึกการเดินทางฉบับภาษาไทย (JOURNEY_TH.md)](JOURNEY_TH.md): ครอบคลุมตั้งแต่กำแพงโหมด TVP_ARCHIVE_ONLY, การแก้ปัญหาฟอนต์เต้าหู้, การสร้าง PUA Shaper, โครงสร้าง Backlog, การดึงบทเสริม จนถึงการแก้แท็กสเกลฟอนต์
- [Read the complete technical post-mortem in English (JOURNEY_EN.md)](JOURNEY_EN.md): Detailed reverse engineering chronicle covering Steam DRM signatures, pre-rendered TFT synthesis, VFS redirection pointers, and dual-sibling bytecode matching.
- [คัมภีร์วิศวกรรมย้อนกลับฉบับสมบูรณ์ตั้งแต่ศูนย์ถึงปล่อยม็อด (docs/00_MASTER_PLAYBOOK_FROM_ZERO_TO_RELEASE.md)](docs/00_MASTER_PLAYBOOK_FROM_ZERO_TO_RELEASE.md)

---

## สำหรับผู้เล่นทั่วไป: วิธีติดตั้งม็อด (Installation for players)

### วิธีการติดตั้ง:
1. ไปที่หน้า [Releases (เวอร์ชันล่าสุด)](https://github.com/AkitoPS/SenrenBanka_Thai_Project/releases/latest) แล้วดาวน์โหลดไฟล์แพตช์ตัวเต็ม (`SenrenBanka_Thai_Mod_Full_v1.0.2.zip`)
2. แตกไฟล์ ZIP ออกมาไว้ในโฟลเดอร์เดียวกัน
3. ดับเบิลคลิกที่ไฟล์ `Install_Thai_Mod.bat` ตัวติดตั้งจะค้นหาโฟลเดอร์ Steam ทุกไดรฟ์ให้อัตโนมัติ สำรองไฟล์เดิม ตั้งค่าฟอนต์ระบบ (`datasc.ksd`) และติดตั้งม็อดภาษาไทยให้จนเสร็จ
4. เข้าเล่นเกมผ่าน Steam หรือ `Start_Thai_Game.bat` ได้ตามปกติ (ในเกมเลือกภาษาเป็น English ม็อดจะแสดงผลเป็นภาษาไทยทันที)

คู่มือการติดตั้งฉบับละเอียดอยู่ที่ [mod_installer/README_INSTALL_TH.md](mod_installer/README_INSTALL_TH.md) (หรือ [English guide](mod_installer/README_INSTALL_EN.md))

---

## สำหรับนักแปลและนักพัฒนา: แก้คำแปลด้วย Excel และคอมไพล์จาก source code (Developer guide)

ผู้ที่ต้องการแก้สำนวนในบทแปลหรือศึกษาวิธีสร้างม็อด สามารถทำตามขั้นตอนนี้ได้ทันที:

1. **เตรียมสภาพแวดล้อม:** ติดตั้งตัวเกม Senren＊Banka ของแท้บน Steam และติดตั้ง Python 3.10 ขึ้นไป จากนั้นรันคำสั่งติดตั้งไลบรารี:
   ```bash
   pip install -r tools/requirements.txt
   ```
2. **ติดตั้งชุดฟอนต์ภาษาไทย (ถ้ายังไม่ได้ลง):** ให้ติดตั้ง `data.xp3` จากชุด [Releases](https://github.com/AkitoPS/SenrenBanka_Thai_Project/releases/latest) ลงในโฟลเดอร์เกม Steam ก่อน (หรือสร้างฟอนต์ `.tft` ใหม่เองด้วย `python tools/build_all_extended_fonts.py` และ `python tools/inject_all_fonts_data_xp3.py`)
3. **แก้ไขบทแปลภาษาไทย:** เปิดไฟล์ [Senren_Banka_Thai_Progress.xlsx](Senren_Banka_Thai_Progress.xlsx) เลือกชีตตามรูทที่ต้องการ แล้วแก้ข้อความภาษาไทยใน **คอลัมน์ F (`แปลภาษาไทย (Thai Translation)`)** แล้วกดบันทึก (ห้ามแก้ไขข้อความต้นฉบับภาษาอังกฤษในคอลัมน์ E) สามารถดูแนวทางสำนวนและคำศัพท์ได้ที่ [MASTER_TRANSLATION_BIBLE.md](localization/database/MASTER_TRANSLATION_BIBLE.md) และ [glossary.json](localization/database/glossary.json)
4. **คอมไพล์และอัปเดตแพตช์ด้วย 1 คลิก:** ดับเบิลคลิกไฟล์ [RUN_THAI_INJECTOR.bat](RUN_THAI_INJECTOR.bat) (หรือรัน `python tools/thai_injector.py`)
   - ในการรันครั้งแรก ระบบจะค้นหาโฟลเดอร์เกม Steam ข้ามไดรฟ์ให้อัตโนมัติ พร้อมตรวจหาและสำรองไฟล์ `patch_extra.xp3` ต้นฉบับภาษาอังกฤษเก็บไว้ใน `archive/original_game_backup/` (หรือดึงจาก `thai_mod_backup/` หากเคยติดตั้งม็อดแล้ว) เพื่อป้องกันการเขียนทับไฟล์ฐาน ทำให้แก้ไขคำแปลและรันซ้ำกี่รอบก็ไม่พัง
   - ผลลัพธ์ `patch_extra.xp3` ตัวใหม่จะถูกสร้างไว้ใน `output/patch_extra.xp3` และคัดลอกเข้าโฟลเดอร์เกม Steam ให้อัตโนมัติ
5. **ตรวจสอบความสมบูรณ์ด้วยชุดทดสอบอัตโนมัติ:**
   ```bash
   python tools/verify_all_scenarios_and_scaled_fonts.py
   python tools/get_all_untranslated_lines.py
   python tools/verify_data_xp3_fonts.py
   python tools/verify_full_game_thai.py
   ```

---

## โครงสร้างคลังเก็บข้อมูล (Repository structure)

```text
├── README.md                          # หน้าหลักแนะนำโครงการ
├── JOURNEY_TH.md                      # บันทึกการเดินทางและการแก้ปัญหาฉบับภาษาไทย
├── JOURNEY_EN.md                      # Technical post-mortem in English
├── LICENSE                            # สิทธิ์การใช้งานแบบ MIT พร้อมข้อสงวนสิทธิ์
├── RUN_THAI_INJECTOR.bat              # สคริปต์ 1 คลิกสำหรับคอมไพล์บทแปลจาก Excel เข้าเกม
├── Senren_Banka_Thai_Progress.xlsx    # ฐานข้อมูลบทแปลทั้งเกม 92 ตอน (68,555 แถว)
├── localization/                      # คลังคำศัพท์ คัมภีร์สำนวน และไฟล์ข้อความระบบภาษาไทย
│   ├── database/
│   │   ├── MASTER_TRANSLATION_BIBLE.md
│   │   ├── glossary.json
│   │   └── route_breakdown.json
│   └── system/                        # ไฟล์เมนูระบบ Flowchart และวิธีเล่นภาษาไทย 9 ไฟล์
├── mod_installer/                     # ชุดเครื่องมือติดตั้งสำหรับผู้เล่นทั่วไป
│   ├── Install_Thai_Mod.bat           # ตัวติดตั้งอัตโนมัติ (ค้นหาทุกไดรฟ์ + แก้ faceMode)
│   ├── Start_Thai_Game.bat            # ตัวเปิดเกมพร้อมระบบป้องกันเซฟเสียหาย
│   ├── Uninstall_Thai_Mod.bat         # ตัวถอนการติดตั้งและกู้คืนไฟล์เดิม
│   ├── README_INSTALL_TH.md           # คู่มือการติดตั้งภาษาไทย
│   ├── README_INSTALL_EN.md           # คู่มือการติดตั้งภาษาอังกฤษ
│   └── patch_info.json                # ข้อมูล metadata ของม็อด
├── tools/                             # ซอร์สโค้ดเครื่องมือ reverse engineering และตรวจสอบทั้งหมด
│   ├── steam_locator.py               # ตัวค้นหาโฟลเดอร์ Steam ข้ามไดรฟ์ผ่าน Registry/VDF
│   ├── thai_injector.py               # ตัวอัดฉีด scenario ครบ 92 ตอน
│   ├── thai_pua_shaper.py             # ตัวจัดรูปสระวรรณยุกต์ PUA
│   ├── thai_word_wrapper.py           # ตัวตัดคำและขึ้นบรรทัดใหม่
│   ├── kirikiri_text_compiler.py      # ตัวถอดรหัสและเข้ารหัส XOR ข้อความระบบ
│   ├── patch_names_and_choices.py     # ฐานข้อมูลชื่อตัวละคร ตัวเลือก และคำแปลแท็กขนาด
│   ├── pimg_texture_manager.py        # ตัวจัดการรูปภาพ UI และแปลงไฟล์ TLG5.0/.pimg
│   ├── build_extended_tft.py          # ตัวสร้างฟอนต์ TFT ต้นแบบรายไฟล์
│   ├── build_all_extended_fonts.py    # ตัวสร้างฟอนต์ TFT ภาษาไทยครบทั้ง 20 ขนาดอัตโนมัติ
│   ├── inject_all_fonts_data_xp3.py   # ตัวฉีดฟอนต์และไฟล์ระบบเข้า data.xp3
│   ├── fix_facemode.py                # สคริปต์แก้ค่า datasc.ksd ป้องกันฟอนต์เต้าหู้
│   ├── verify_data_xp3_fonts.py       # ตัวตรวจความถูกต้องฟอนต์ใน data.xp3
│   ├── verify_all_scenarios_and_scaled_fonts.py
│   ├── get_all_untranslated_lines.py
│   ├── verify_full_game_thai.py       # ชุดทดสอบความสมบูรณ์แบบ end-to-end
│   ├── fonts/                         # ฟอนต์ NotoSansThaiLooped-Regular.ttf และ OFL.txt
│   └── requirements.txt               # รายการแพ็กเกจ Python ที่ต้องใช้
├── skills/                            # AGY Agentic Skill สำหรับนำไปใช้กับเกม Yuzusoft อื่นๆ
│   └── yuzusoft-localization-engineering/
│       └── SKILL.md                   # พิมพ์เขียววิศวกรรมย้อนกลับและแก้ไขฟอนต์แบบสำเร็จรูป
├── docs/                              # คลังเอกสารทางเทคนิคเชิงลึก
│   ├── 00_MASTER_PLAYBOOK_FROM_ZERO_TO_RELEASE.md
│   ├── 01_ENGINE_AND_PROTECTIONS.md
│   ├── 02_XP3_ARCHIVE_SPEC_AND_INJECTION.md
│   ├── 03_PSB_SCENARIO_SYSTEM.md
│   ├── 04_THAI_TYPOGRAPHY_AND_TFT_FONTS.md
│   ├── 05_FONT_SCALING_AND_TAGGED_LINES.md
│   ├── 05_WORKFLOW_AND_BATCH_TRANSLATION.md
│   ├── 06_ADAPTATION_GUIDE_OTHER_YUZUSOFT.md
│   └── case_studies/                  # 10 บทเรียนกรณีศึกษาข้อผิดพลาดจริงและการแก้ปัญหา
└── release_guide/                     # คู่มือการเผยแพร่ไฟล์ขนาดใหญ่บน GitHub Releases
    └── GITHUB_RELEASE_GUIDE.md
```

---

## ข้อสงวนสิทธิ์ทางกฎหมาย (Legal disclaimer)

1. โครงการนี้เป็นโครงการวิจัยทางวิศวกรรมย้อนกลับและการแปลภาษาเพื่อประโยชน์ทางการศึกษาและชุมชนผู้เล่นชาวไทย โดยไม่แสวงหาผลกำไรทางการค้า
2. ทรัพย์สินทางปัญญาและลิขสิทธิ์ตัวเกม *Senren＊Banka (千恋＊万花)*, งานภาพ, ดนตรีประกอบ, เสียงพากย์, และเนื้อเรื่องทั้งหมด เป็นกรรมสิทธิ์ของ YUZUSOFT / JUNOS INC. และผู้จัดจำหน่ายอย่างเป็นทางการ NekoNyan Ltd.
3. โครงการนี้ไม่มีการแจกจ่ายไฟล์ปฏิบัติการของตัวเกม (`SenrenBanka.exe`), ไฟล์เสียงพากย์, หรือภาพ CG ลิขสิทธิ์ใดๆ ผู้ใช้งานจำเป็นต้องเป็นเจ้าของตัวเกมลิขสิทธิ์แท้บนแพลตฟอร์ม Steam เพื่อใช้งานม็อดนี้
