# Senren＊Banka (千恋＊万花) Thai localization project
### โครงการแปลภาษาไทยและวิศวกรรมย้อนกลับระดับไบนารีสำหรับเกม Senren＊Banka (Steam 18+ Edition)

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
- [สำหรับนักพัฒนา: การคอมไพล์จาก source code (Developer guide)](#สำหรับนักพัฒนา-การคอมไพล์จาก-source-code-developer-guide)
- [โครงสร้างคลังเก็บข้อมูล (Repository structure)](#โครงสร้างคลังเก็บข้อมูล-repository-structure)
- [ข้อสงวนสิทธิ์ทางกฎหมาย (Legal disclaimer)](#ข้อสงวนสิทธิ์ทางกฎหมาย-legal-disclaimer)

---

## จุดเด่นของโปรเจกต์ (Key highlights)

- แปลบทสนทนาครบถ้วนทั้ง 92 ตอน (60,607 บรรทัด) ทั้งเนื้อเรื่องหลัก รูทเสริม และฉาก 18+ Uncensored ทุกฉาก
- รองรับขนาดตัวอักษรพิเศษ (Dynamic Font Scaling) ถอดรหัสและฉีดภาษาไทยลงใน Kirikiri Tags (`%123;`, `%115;`, `%61;`, `%69;`, `%76;`) ทั้งเสียงตะโกนและเสียงกระซิบ ไร้ตัวหนังสือภาษาอังกฤษตกค้าง
- ระบบฟอนต์ Pre-rendered TFT Matrix 20 ขนาด สร้างฟอนต์บิตแมประดับไบนารีรองรับทุกหน้าจอ (บทสนทนาสด, Backlog, หน้าต่างระบบ)
- ระบบจัดรูปสระวรรณยุกต์ 3 ระดับ (Thai PUA Typography Shaper) สระไม่ลอย วรรณยุกต์ไม่เดินหน้า ไม่ชนกับสระบน รองรับสระอำและพยัญชนะหางยาว
- ระบบตัดคำตามหลักไวยากรณ์ไทยด้วย PyThaiNLP ไม่ตัดคำขาดครึ่งบรรทัด
- รักษาความปลอดภัยและความเข้ากันได้กับ Steam ฝังลายเซ็น Steam DRM 24 ไบต์ในบล็อก `sen:` และมีระบบป้องกัน Save Game Desync ผ่าน `-savecloud=no`

---

## บันทึกการเดินทางและบทเรียนทางวิศวกรรม (The technical post-mortem)

โปรเจกต์นี้มีเอกสารบันทึกวิศวกรรมย้อนกลับที่อธิบายปัญหาจริงตั้งแต่ระดับไบนารี วิธีการตรวจสอบ และสถาปัตยกรรมที่ใช้แก้ปัญหาอย่างละเอียดทั้งสองภาษา:

- [อ่านบันทึกการเดินทางฉบับภาษาไทย (JOURNEY_TH.md)](JOURNEY_TH.md): ครอบคลุมตั้งแต่กำแพงโหมด TVP_ARCHIVE_ONLY, การแก้ปัญหาฟอนต์เต้าหู้, การสร้าง PUA Shaper, โครงสร้าง Backlog, การดึงบท 18+ จนถึงการแก้แท็กสเกลฟอนต์
- [Read the complete technical post-mortem in English (JOURNEY_EN.md)](JOURNEY_EN.md): Detailed reverse engineering chronicle covering Steam DRM signatures, pre-rendered TFT synthesis, VFS redirection pointers, and dual-sibling bytecode matching.

---

## สำหรับผู้เล่นทั่วไป: วิธีติดตั้งม็อด (Installation for players)

### วิธีการติดตั้ง:
1. ไปที่แท็บ [Releases](https://github.com/...) แล้วดาวน์โหลดไฟล์แพตช์ตัวเต็ม (`SenrenBanka_Thai_Mod_Full_v1.0.zip`)
2. แตกไฟล์ ZIP ออกมา
3. ดับเบิลคลิกที่ไฟล์ `Install_Thai_Mod.bat` ตัวติดตั้งจะค้นหาโฟลเดอร์ Steam สำรองไฟล์เดิม และติดตั้งม็อดภาษาไทยให้อัตโนมัติ
4. ดับเบิลคลิก `Start_Thai_Game.bat` เพื่อเข้าเล่นเกมได้อย่างปลอดภัย

คู่มือการติดตั้งฉบับละเอียดอยู่ที่ [mod_installer/README_INSTALL_TH.md](mod_installer/README_INSTALL_TH.md) (หรือ [English guide](mod_installer/README_INSTALL_EN.md))

---

## สำหรับนักพัฒนา: การคอมไพล์จาก source code (Developer guide)

หากต้องการศึกษาโค้ดหรือคอมไพล์แพตช์ `patch_extra.xp3` ด้วยตนเอง:

1. ติดตั้ง Python 3.10 ขึ้นไป
2. ติดตั้ง Dependencies:
   ```bash
   pip install -r tools/requirements.txt
   ```
3. สั่งรัน Universal Injector:
   ```bash
   python tools/thai_injector.py
   ```
   โปรแกรมจะอ่านบทแปลจาก `Senren_Banka_Thai_Progress.xlsx`, ถอดรหัส Scenario จากเกมต้นฉบับ, ประกอบฟอนต์, และสร้าง `patch_extra.xp3` ขึ้นมาใหม่ทันที
4. ตรวจสอบความถูกต้องด้วยชุดทดสอบอัตโนมัติ:
   ```bash
   python tools/verify_all_scenarios_and_scaled_fonts.py
   python tools/get_all_untranslated_lines.py
   ```

---

## โครงสร้างคลังเก็บข้อมูล (Repository structure)

```text
├── README.md                      # หน้าหลักแนะนำโครงการ
├── JOURNEY_TH.md                  # บันทึกการเดินทางและการแก้ปัญหาฉบับภาษาไทย
├── JOURNEY_EN.md                  # Technical post-mortem in English
├── LICENSE                        # สิทธิ์การใช้งานแบบ MIT พร้อมข้อสงวนสิทธิ์
├── mod_installer/                 # ชุดเครื่องมือติดตั้งสำหรับผู้เล่นทั่วไป
│   ├── Install_Thai_Mod.bat       # ตัวติดตั้งอัตโนมัติ
│   ├── Start_Thai_Game.bat        # ตัวเปิดเกมพร้อมระบบป้องกันเซฟเสียหาย
│   ├── Uninstall_Thai_Mod.bat     # ตัวถอนการติดตั้งและกู้คืนไฟล์เดิม
│   ├── README_INSTALL_TH.md       # คู่มือการติดตั้งภาษาไทย
│   └── patch_info.json            # ข้อมูล metadata ของม็อด
├── tools/                         # ซอร์สโค้ดเครื่องมือ reverse engineering ทั้งหมด
│   ├── thai_injector.py           # ตัวอัดฉีด scenario ครบ 92 ตอน
│   ├── thai_pua_shaper.py         # ตัวจัดรูปสระวรรณยุกต์ PUA
│   ├── thai_word_wrapper.py       # ตัวตัดคำและขึ้นบรรทัดใหม่
│   ├── kirikiri_text_compiler.py  # ตัวถอดรหัสและเข้ารหัส XOR
│   ├── patch_names_and_choices.py # ฐานข้อมูลชื่อตัวละคร ตัวเลือก และคำแปลแท็กขนาด
│   ├── build_extended_tft.py      # ตัวสร้างฟอนต์ TFT บิตแมป
│   ├── verify_full_game_thai.py   # ชุดทดสอบความสมบูรณ์แบบ end-to-end
│   └── requirements.txt           # รายการแพ็กเกจ Python ที่ต้องใช้
├── skills/                        # AGY Agentic Skill สำหรับนำไปใช้กับเกม Yuzusoft อื่นๆ
│   └── yuzusoft-localization-engineering/
│       └── SKILL.md               # พิมพ์เขียววิศวกรรมย้อนกลับและแก้ไขฟอนต์แบบสำเร็จรูป
├── docs/                          # คลังเอกสารทางเทคนิคเชิงลึก
│   ├── 01_ENGINE_AND_PROTECTIONS.md
│   ├── 02_XP3_ARCHIVE_SPEC_AND_INJECTION.md
│   ├── 03_PSB_SCENARIO_SYSTEM.md
│   ├── 04_THAI_TYPOGRAPHY_AND_TFT_FONTS.md
│   ├── 05_FONT_SCALING_AND_TAGGED_LINES.md
│   └── case_studies/              # 10 บทเรียนกรณีศึกษาข้อผิดพลาดจริงและการแก้ปัญหา
└── release_guide/                 # คู่มือการเผยแพร่ไฟล์ขนาดใหญ่บน GitHub Releases
    └── GITHUB_RELEASE_GUIDE.md
```

---

## ข้อสงวนสิทธิ์ทางกฎหมาย (Legal disclaimer)

1. โครงการนี้เป็นโครงการวิจัยทางวิศวกรรมย้อนกลับและการแปลภาษาเพื่อประโยชน์ทางการศึกษาและชุมชนผู้เล่นชาวไทย โดยไม่แสวงหาผลกำไรทางการค้า
2. ทรัพย์สินทางปัญญาและลิขสิทธิ์ตัวเกม *Senren＊Banka (千恋＊万花)*, งานภาพ, ดนตรีประกอบ, เสียงพากย์, และเนื้อเรื่องทั้งหมด เป็นกรรมสิทธิ์ของ YUZUSOFT / JUNOS INC. และผู้จัดจำหน่ายอย่างเป็นทางการ NekoNyan Ltd.
3. โครงการนี้ไม่มีการแจกจ่ายไฟล์ปฏิบัติการของตัวเกม (`SenrenBanka.exe`), ไฟล์เสียงพากย์, หรือภาพ CG ลิขสิทธิ์ใดๆ ผู้ใช้งานจำเป็นต้องเป็นเจ้าของตัวเกมลิขสิทธิ์แท้บนแพลตฟอร์ม Steam เพื่อใช้งานม็อดนี้
