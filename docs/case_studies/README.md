# ศูนย์รวมบทเรียนและกรณีศึกษาอุปสรรคการทำงาน (Lessons Learned & Critical Post-Mortems)

ยินดีต้อนรับสู่ศูนย์รวมบทเรียนเชิงวิศวกรรม (Engineering Post-Mortems) จากโปรเจกต์ม็อดแปลภาษาไทย **Senren * Banka** 
เอกสารชุดนี้บันทึก**อุปสรรคจริง วิกฤตการณ์จริง และความล้มเหลวที่เกิดขึ้นระหว่างการพัฒนา** พร้อมทั้งการวิเคราะห์สาเหตุเชิงลึก (Root Cause Analysis) และวิธีการแก้ไขที่พิสูจน์แล้ว เพื่อเป็นกรณีศึกษาที่มีค่ายิ่งสำหรับนำไปใช้ป้องกันปัญหาในเกมอื่นๆ ของค่าย Yuzusoft และเกมวิชวลโนเวลบนเอนจิน Kirikiri Z

---

## 🧭 สารบัญ 9 กรณีศึกษาวิกฤต (The 9 Critical Post-Mortems)

| # | กรณีศึกษา (Case Study) | ปัญหาที่พบ | สาเหตุเชิงลึก | บทเรียนและทางแก้ไข |
| :-: | :--- | :--- | :--- | :--- |
| **01** | [**`01_CASE_STUDY_SAVE_GAME_LOSS.md`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/01_CASE_STUDY_SAVE_GAME_LOSS.md) | เซฟเกมของผู้ใช้ 75 เซฟหายหมดทั้งในเกมและ Steam | Working Directory ไม่ตรงกัน + Steam Cloud Conflict | การแยกระบบ Backup เด็ดขาด และบังคับพาธด้วย `cd /d "%~dp0"` |
| **02** | [**`02_CASE_STUDY_KAG_SYNTAX_ERROR.md`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/02_CASE_STUDY_KAG_SYNTAX_ERROR.md) | เกมแครชขึ้นบั๊ก `start.ks:43 Syntax error` | มีตัวอักษรขึ้นบรรทัดใหม่ `\n` หลุดในสตริงบทพูด | KAG Lexer มองว่าคำสั่งแท็กฉีกขาด ต้องทำ String Sanitization |
| **03** | [**`03_CASE_STUDY_VFS_ARCHIVE_ONLY.md`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/03_CASE_STUDY_VFS_ARCHIVE_ONLY.md) | วางไฟล์ฟอนต์ในโฟลเดอร์ `font/` แล้วเกมเพิกเฉย | เอนจินรันในโหมด `TVP_ARCHIVE_ONLY` | พิสูจน์ด้วย ProcMon และฉีดไฟล์เข้า `data.xp3` โดยตรง |
| **04** | [**`04_CASE_STUDY_STEAM_DRM_AND_SEN_CHUNK.md`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/04_CASE_STUDY_STEAM_DRM_AND_SEN_CHUNK.md) | เกมเปิดไม่ติด / เด้ง Error เมื่อสร้างไฟล์ XP3 ใหม่ | ลายเซ็น Steam 24B หาย + พอยน์เตอร์ Redirection พัง | การคงโครงสร้าง `sen:` Chunk และรักษาตัวชี้ที่ไบต์ 23/32 |
| **05** | [**`05_CASE_STUDY_THAI_TYPOGRAPHY_AND_TOFU.md`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/05_CASE_STUDY_THAI_TYPOGRAPHY_AND_TOFU.md) | ตัวหนังสือเต้าหู้ `[]` และวรรณยุกต์ลอย/เว้นวรรคกว้าง | ไม่มี CTL + ฟอนต์เดิมเป็น Monospaced CJK | กำหนด Zero-Advance (`incX=0`) + สร้าง PUA $U+F700..U+F71F$ |
| **06** | [**`06_CASE_STUDY_DUAL_FONT_BACKLOG_BUG.md`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/06_CASE_STUDY_DUAL_FONT_BACKLOG_BUG.md) | บทพูดปกติสวยงาม แต่พอเปิดหน้า Backlog เป็นเต้าหู้ `[]` | เกมแยกใช้ฟอนต์ 2 ขนาด (`font1_32` และ `font1_39`) | ต้องสร้างและฉีดทั้ง 2 ขนาดเข้าสู่ `data.xp3` พร้อมคีย์ XOR เฉพาะ |
| **07** | [**`07_CASE_STUDY_NTFS_HARDLINK_HAZARD.md`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/07_CASE_STUDY_NTFS_HARDLINK_HAZARD.md) | แก้ไขไฟล์ในโฟลเดอร์หนึ่ง แต่อีกโฟลเดอร์ถูกแก้ตามไปด้วย | ใช้ NTFS Hard-link แชร์ไฟล์ขนาด 10GB | ต้องทำ Unlink (เขียนลงไฟล์ใหม่ก่อน Rename) ป้องกันผลกระทบข้ามสาย |
| **08** | [**`08_CASE_STUDY_DATASC_FACEMODE_AND_INSTALLER_SPECS.md`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/08_CASE_STUDY_DATASC_FACEMODE_AND_INSTALLER_SPECS.md) | บทพูดเป็นเต้าหู้ `[]` และสระเว้นวรรคห่าง แม้ไฟล์แพตช์จะถูกต้อง | คอนฟิก `datasc.ksd` มี `faceMode = 1` ทำให้ Fallback เป็น MS Gothic | บังคับ `faceMode = 0` และกำหนดให้เป็นขั้นตอนบังคับของตัวติดตั้งแพตช์ |
| **09** | [**`09_CASE_STUDY_STORAGE_REFACTORING_AND_ASSET_LIFECYCLE.md`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/09_CASE_STUDY_STORAGE_REFACTORING_AND_ASSET_LIFECYCLE.md) | โฟลเดอร์โปรเจกต์บวมโตถึง 160GB และไฟล์กระจัดกระจาย | การโคลนตัวเกม 10GB ซ้ำในขั้นตอนวิจัย Step 12-36 | กำหนดวงจรชีวิต Asset ปลดปล่อย .xp3 ซ้ำซ้อน คืนพื้นที่ 138GB คงโค้ดประวัติศาสตร์ไว้ครบ |

---

## 🗄️ คลังรายงานทางเทคนิคฉบับเต็มทั้ง 52 ฉบับ (All Historical Reports)

รายงานการสืบสวนและการทดลองดั้งเดิมตั้งแต่ก้าวแรกของการวิจัย ถูกจัดเก็บไว้ในโฟลเดอร์ [**`lessons_learned/all_reports/`**](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports):

* **ระยะที่ 1: การวิเคราะห์โครงสร้างพื้นฐานและถอดรหัส (STEP 01 - STEP 10)**
  - [`STEP01_26_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP01_26_FINDINGS.md)
  - [`STEP10A_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP10A_FINDINGS.md), [`STEP10B_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP10B_FINDINGS.md)
* **ระยะที่ 2: การเจาะโครงสร้างสคริปต์ PSB และ Steam DRM (STEP 11 - STEP 27)**
  - [`STEP16_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP16_FINDINGS.md)
  - [`STEP26_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP26_FINDINGS.md), [`STEP27_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP27_FINDINGS.md)
* **ระยะที่ 3: ปัญหา VFS, Canary Build และ Process Monitor (STEP 28 - STEP 34)**
  - [`STEP28_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP28_FINDINGS.md), [`STEP28B_CANARY_FOLLOWUP_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP28B_CANARY_FOLLOWUP_FINDINGS.md)
  - [`STEP29_VALID_PATCH2_XP3_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP29_VALID_PATCH2_XP3_FINDINGS.md)
  - [`STEP31_PATCH_EXTRA_SHADOW_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP31_PATCH_EXTRA_SHADOW_FINDINGS.md)
* **ระยะที่ 4: มหากาพย์การแก้ปัญหาระบบฟอนต์ Pre-rendered TFT และ PUA (STEP 35 - STEP 44)**
  - [`STEP35_THAI_RENDERING_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP35_THAI_RENDERING_FINDINGS.md)
  - [`STEP36_THAI_RENDERING_POC_FINDINGS.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP36_THAI_RENDERING_POC_FINDINGS.md)
  - [`STEP37_DATA_XP3_TFT_INJECTION_REPORT.md`](file:///c:/Users/DELL/Desktop/VN_Thai_Project/lessons_learned/all_reports/STEP37_DATA_XP3_TFT_INJECTION_REPORT.md)
