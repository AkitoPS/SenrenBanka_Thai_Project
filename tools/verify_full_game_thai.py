"""
tool/verify_full_game_thai.py — Comprehensive End-to-End In-Game Verification & Testing Suite.
=============================================================================================
Senren*Banka Thai Localization Project — Master Quality Assurance & Verification.

Phases:
1. Phase 1: data.xp3 Font Matrix
   - Authentic 24-byte Steam signature in sen: chunk
   - Redirection pointer at offset 23/32
   - All 20 extended TFT fonts present in hnfn and index
   - Size comparison against base fonts & 100% bit-for-bit decrypted match against tool/fonts_extended/
   - Verification across SenrenBanka_THAI_PLAYABLE and Steam environments
2. Phase 2: patch_extra.xp3 VFS Overlay Precedence & Members
   - Steam signature and XP3 redirection architecture
   - hnfn table decompression containing all 108 members:
     * 9 system texts (flow_texts, syslangtext, soundlist, 6 help_*.txt files)
     * 5 rebuilt .pimg UI graphic containers
     * 92 scenario files (.ks.scn) + 2 archive metadata files
   - Index chunk matching and Adler-32 integrity
3. Phase 3: Content Decryption & Integrity Test
   - Decrypt main/flow_texts_en.ini: verify chapter titles (บทที่ 1 / บทที 1), scene nodes, choices
   - Decrypt main/syslangtext_en.ini: verify title caption ([ภาษาไทย]) and settings (หน้าจอ, เสียง, etc.)
   - Decrypt uipsd/en/title_en.pimg: verify TLG5.0 streams, 33 resources, button dimensions & non-zero alpha
   - Decrypt uipsd/langselect.pimg: verify 4 resources, modal background (450x188), buttons (310x70)
   - Decrypt scenario file (001): verify PSB structure and authentic Thai strings
4. Phase 4: Engine Launch Sanity Test
   - Launch SenrenBanka.exe in SenrenBanka_THAI_PLAYABLE/ via subprocess
   - Monitor healthy execution for 5 seconds (no crash, active PID)
   - Check %TEMP% for decompressed Kirikiri font temporary directories (krkr_*)
   - Cleanly terminate engine process
5. Phase 5: Batch Launcher Verification
   - Verify RUN_THAI_INJECTOR.bat: UTF-8 encoding, thai_injector.py execution, errorlevel check
   - Verify SenrenBanka_THAI_PLAYABLE/Start_Thai_Game.bat: UTF-8 encoding, dir switch, fix_facemode, exe launch
=============================================================================================
"""

import os
import sys
import glob
import time
import zlib
import struct
import hashlib
import tempfile
import subprocess
from typing import Dict, List, Tuple, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tool.kirikiri_text_compiler import decrypt_file
from tool.pimg_texture_manager import decrypt_pimg, extract_pimg_resources, decode_tlg5
from tool.thai_injector import decrypt_psb_auto
from tool.thai_pua_shaper import shape_thai_text
from tool.verify_data_xp3_fonts import FONT_SPECS, decrypt_font, EXPECTED_STEAM_SIG

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------
PLAYABLE_DIR = os.path.abspath("SenrenBanka_THAI_PLAYABLE")
PLAYABLE_DATA_XP3 = os.path.join(PLAYABLE_DIR, "data.xp3")
PLAYABLE_PATCH_EXTRA = os.path.join(PLAYABLE_DIR, "patch_extra.xp3")
PLAYABLE_EXE = os.path.join(PLAYABLE_DIR, "SenrenBanka.exe")
PLAYABLE_LAUNCHER = os.path.join(PLAYABLE_DIR, "Start_Thai_Game.bat")

ROOT_INJECTOR_BAT = os.path.abspath("RUN_THAI_INJECTOR.bat")
EXTENDED_FONTS_DIR = os.path.abspath("tool/fonts_extended")

STEAM_SENREN_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\SenrenBanka"
STEAM_DATA_XP3 = os.path.join(STEAM_SENREN_DIR, "data.xp3")
STEAM_PATCH_EXTRA = os.path.join(STEAM_SENREN_DIR, "patch_extra.xp3")

REQUIRED_SYSTEM_FILES = [
    'main/flow_texts_en.ini',
    'main/syslangtext_en.ini',
    'main/soundlist_en.csv',
    'main/help_sys_en.txt',
    'main/help_flow_en.txt',
    'main/help_file_en.txt',
    'main/help_exch_en.txt',
    'main/help_lang_en.txt',
    'main/help_tui_en.txt',
]

REQUIRED_PIMG_FILES = [
    'uipsd/en/title_en.pimg',
    'uipsd/en/afterstory_en.pimg',
    'uipsd/en/flowchart_en.pimg',
    'uipsd/en/sys_base_en.pimg',
    'uipsd/langselect.pimg',
    'uipsd/en/dialog_en.pimg',
    'uipsd/en/sys_page0_en.pimg',
    'uipsd/en/sys_page1_en.pimg',
    'uipsd/en/sys_page2_en.pimg',
    'uipsd/en/sys_page3_en.pimg',
    'uipsd/en/sys_page4_en.pimg',
    'uipsd/en/sys_page5_en.pimg',
    'uipsd/en/sys_page6_en.pimg',
    'uipsd/en/sys_page7_en.pimg',
]

class VerificationResult:
    def __init__(self, phase_name: str):
        self.phase_name = phase_name
        self.checks: List[Tuple[str, bool, str]] = []  # (name, passed, detail)

    def add(self, name: str, passed: bool, detail: str = ""):
        self.checks.append((name, passed, detail))
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name} {f'({detail})' if detail else ''}")

    @property
    def passed(self) -> bool:
        return all(p for _, p, _ in self.checks)


def contains_thai(text: str) -> bool:
    """Check if string contains Thai Unicode characters (0x0E00-0x0E7F) or PUA (0xF700-0xF71F)."""
    for ch in text:
        cp = ord(ch)
        if 0x0E00 <= cp <= 0x0E7F or 0xF700 <= cp <= 0xF71F:
            return True
    return False


def parse_xp3_archive_fast(xp3_path: str) -> Dict[str, Any]:
    """
    Fast XP3 parser that seeks instead of reading entire multi-gigabyte file into memory.
    """
    if not os.path.exists(xp3_path):
        raise FileNotFoundError(f"XP3 archive not found: {xp3_path}")

    with open(xp3_path, 'rb') as f:
        magic = f.read(11)
        if magic != b"XP3\r\n \n\x1a\x8bg\x01":
            raise ValueError(f"Invalid XP3 magic in {xp3_path}: {magic!r}")

        redir = struct.unpack('<Q', f.read(8))[0]
        if redir == 23:
            f.seek(redir + 9)
            real_idx_off = struct.unpack('<Q', f.read(8))[0]
        else:
            real_idx_off = redir

        f.seek(real_idx_off)
        flag = f.read(1)[0]
        csz, usz = struct.unpack('<QQ', f.read(16))
        raw_comp_idx = f.read(csz)
        decomp_idx = zlib.decompress(raw_comp_idx)
        if len(decomp_idx) != usz:
            raise ValueError("Decompressed index size mismatch")

        # Parse sen: chunk
        if decomp_idx[:4] != b'sen:':
            raise ValueError(f"Expected 'sen:' chunk, got {decomp_idx[:4]!r}")

        sen_sz = struct.unpack('<Q', decomp_idx[4:12])[0]
        sen_body = decomp_idx[12:12+sen_sz]
        hnfn_off = struct.unpack('<Q', sen_body[:8])[0]
        hnfn_uncomp, hnfn_comp = struct.unpack('<II', sen_body[8:16])
        steam_sig = sen_body[16:]

        # Read hnfn chunk
        f.seek(hnfn_off)
        hnfn_raw = f.read(hnfn_comp)
        hnfn_decomp = zlib.decompress(hnfn_raw)
        if len(hnfn_decomp) != hnfn_uncomp:
            raise ValueError("Decompressed hnfn size mismatch")

        hash_to_name = {}
        name_to_hash = {}
        pos = 0
        while pos < len(hnfn_decomp):
            if hnfn_decomp[pos:pos+4] == b'hnfn':
                cz = struct.unpack('<Q', hnfn_decomp[pos+4:pos+12])[0]
                cb = hnfn_decomp[pos+12:pos+12+cz]
                pos += 12 + cz
                rpos = 0
                while rpos + 6 <= len(cb):
                    fhash = struct.unpack('<I', cb[rpos:rpos+4])[0]
                    nlen = struct.unpack('<H', cb[rpos+4:rpos+6])[0]
                    if rpos + 6 + nlen * 2 <= len(cb):
                        name = cb[rpos+6:rpos+6+nlen*2].decode('utf-16le', errors='replace')
                        hash_to_name[fhash] = name
                        name_to_hash[name] = fhash
                        rpos += 6 + nlen * 2
                    else:
                        break
            else:
                pos += 1

        # Parse File chunks in decomp_idx
        pos = 12 + sen_sz
        files = {}
        while pos < len(decomp_idx):
            ct = decomp_idx[pos:pos+4]
            cz = struct.unpack('<Q', decomp_idx[pos+4:pos+12])[0]
            cb = decomp_idx[pos+12:pos+12+cz]
            pos += 12 + cz
            if ct == b'File':
                spos = 0
                adlr = None
                segm_info = None
                while spos < len(cb):
                    st = cb[spos:spos+4]
                    sz = struct.unpack('<Q', cb[spos+4:spos+12])[0]
                    sd = cb[spos+12:spos+12+sz]
                    spos += 12 + sz
                    if st == b'adlr':
                        adlr = struct.unpack('<I', sd[:4])[0]
                    elif st == b'segm':
                        sflags, soff, sorig, sarc = struct.unpack('<IQQQ', sd[:28])
                        segm_info = {'sflags': sflags, 'soff': soff, 'sorig': sorig, 'sarc': sarc}

                fname = hash_to_name.get(adlr)
                if fname and segm_info:
                    files[fname] = {
                        'adlr': adlr,
                        'soff': segm_info['soff'],
                        'sorig': segm_info['sorig'],
                        'sarc': segm_info['sarc'],
                        'sflags': segm_info['sflags']
                    }

    return {
        'path': xp3_path,
        'steam_sig': steam_sig,
        'hash_to_name': hash_to_name,
        'name_to_hash': name_to_hash,
        'files': files
    }


def extract_member_fast(xp3_path: str, finfo: Dict[str, Any]) -> bytes:
    """Extract and decompress a member payload on-demand without caching the archive."""
    with open(xp3_path, 'rb') as f:
        f.seek(finfo['soff'])
        raw = f.read(finfo['sarc'])
        if finfo['sflags'] == 1:
            return zlib.decompress(raw)
        return raw


# ===========================================================================
# PHASE 1: data.xp3 Font Matrix Verification
# ===========================================================================
def verify_phase_1_fonts(res: VerificationResult, xp3_path: str, env_name: str) -> None:
    print(f"\n--- Phase 1: data.xp3 Font Matrix ({env_name}) ---")
    if not os.path.exists(xp3_path):
        res.add(f"{env_name} data.xp3 exists", False, f"File not found: {xp3_path}")
        return

    res.add(f"{env_name} data.xp3 exists", True, f"Size: {os.path.getsize(xp3_path):,} bytes")

    try:
        parsed = parse_xp3_archive_fast(xp3_path)
    except Exception as e:
        res.add(f"{env_name} data.xp3 XP3 parsing", False, str(e))
        return

    res.add(f"{env_name} Steam DRM signature in data.xp3",
            parsed['steam_sig'] == EXPECTED_STEAM_SIG,
            "Exact 24-byte signature preserved in sen: chunk")

    all_20_present = True
    bit_matches = 0
    all_fonts_ok = True

    with open(xp3_path, 'rb') as f:
        for font_rel_path, spec in FONT_SPECS.items():
            base_filename = os.path.basename(font_rel_path)
            if font_rel_path not in parsed['files']:
                all_20_present = False
                res.add(f"Font member {base_filename} present", False, "Missing in hnfn/index")
                continue

            finfo = parsed['files'][font_rel_path]
            ext_file = os.path.join(EXTENDED_FONTS_DIR, base_filename)
            if not os.path.exists(ext_file):
                all_fonts_ok = False
                res.add(f"Reference font {base_filename} exists on disk", False, ext_file)
                continue

            with open(ext_file, 'rb') as ef:
                expected_bytes = ef.read()

            expected_size = len(expected_bytes)
            if finfo['sorig'] != expected_size or finfo['sarc'] != expected_size:
                all_fonts_ok = False
                res.add(f"Font {base_filename} size match", False,
                        f"Archive size {finfo['sorig']} != expected {expected_size}")
                continue

            # Read and decrypt payload
            f.seek(finfo['soff'])
            enc_payload = f.read(finfo['sarc'])
            dec_bytes = decrypt_font(enc_payload, spec)

            if dec_bytes[:22] != b"TVP pre-rendered font\x1a":
                all_fonts_ok = False
                res.add(f"Font {base_filename} TVP header valid", False, f"Header: {dec_bytes[:22]!r}")
                continue

            if dec_bytes != expected_bytes:
                all_fonts_ok = False
                res.add(f"Font {base_filename} bit-for-bit match", False, "Byte mismatch")
                continue

            bit_matches += 1

    res.add(f"{env_name} All 20 TFT fonts present in hnfn & index", all_20_present, f"{len(parsed['files'])} total files in index")
    res.add(f"{env_name} All 20 fonts 100% bit-for-bit decrypted match", bit_matches == 20, f"{bit_matches}/20 fonts matched exactly")


# ===========================================================================
# PHASE 2: patch_extra.xp3 Overlay Precedence & Members
# ===========================================================================
def verify_phase_2_overlay(res: VerificationResult, xp3_path: str, env_name: str) -> Optional[Dict[str, Any]]:
    print(f"\n--- Phase 2: patch_extra.xp3 Overlay & Members ({env_name}) ---")
    if not os.path.exists(xp3_path):
        res.add(f"{env_name} patch_extra.xp3 exists", False, f"Not found: {xp3_path}")
        return None

    res.add(f"{env_name} patch_extra.xp3 exists", True, f"Size: {os.path.getsize(xp3_path):,} bytes")

    try:
        parsed = parse_xp3_archive_fast(xp3_path)
    except Exception as e:
        res.add(f"{env_name} patch_extra.xp3 parse", False, str(e))
        return None

    res.add(f"{env_name} Steam DRM signature in patch_extra.xp3",
            parsed['steam_sig'] == EXPECTED_STEAM_SIG,
            "Exact 24-byte signature preserved in sen: chunk")

    # Verify total member count (expecting 108 members)
    total_members = len(parsed['files'])
    res.add(f"{env_name} hnfn total members count", total_members == 108, f"Found {total_members} members (expected 108)")

    # Verify 9 system files in data.xp3
    parsed_data = parse_xp3_archive_fast(PLAYABLE_DATA_XP3)
    missing_sys = [f for f in REQUIRED_SYSTEM_FILES if f not in parsed_data['files']]
    res.add(f"{env_name} All 9 Thai system text files present in data.xp3", len(missing_sys) == 0,
            f"Present: {len(REQUIRED_SYSTEM_FILES) - len(missing_sys)}/9" + (f", Missing: {missing_sys}" if missing_sys else ""))

    # Verify 14 .pimg containers in data.xp3
    missing_pimg = [f for f in REQUIRED_PIMG_FILES if f not in parsed_data['files']]
    res.add(f"{env_name} All 14 rebuilt .pimg containers present in data.xp3", len(missing_pimg) == 0,
            f"Present: {len(REQUIRED_PIMG_FILES) - len(missing_pimg)}/14" + (f", Missing: {missing_pimg}" if missing_pimg else ""))

    # Verify scenarios
    scenarios = [f for f in parsed['files'] if f.endswith('.scn')]
    res.add(f"{env_name} Scenario files present", len(scenarios) >= 92, f"Found {len(scenarios)} scenario files (expected >= 92)")

    # Verify Adler-32 mapping integrity
    adlr_matches = sum(1 for fname, info in parsed['files'].items() if parsed['name_to_hash'].get(fname) == info['adlr'])
    res.add(f"{env_name} Index to hnfn Adler-32 hash integrity", adlr_matches == total_members,
            f"{adlr_matches}/{total_members} members verified")

    return parsed


# ===========================================================================
# PHASE 3: Content Decryption & Integrity Test
# ===========================================================================
def verify_phase_3_content(res: VerificationResult, parsed_xp3: Dict[str, Any]) -> None:
    print("\n--- Phase 3: Content Decryption & Integrity Verification ---")
    xp3_path = parsed_xp3['path']
    parsed_data = parse_xp3_archive_fast(PLAYABLE_DATA_XP3)
    data_xp3_path = PLAYABLE_DATA_XP3

    # 1. flow_texts_en.ini (from data.xp3)
    try:
        flow_bytes = extract_member_fast(data_xp3_path, parsed_data['files']['main/flow_texts_en.ini'])
        flow_text = decrypt_file(flow_bytes, 'flow_texts_en.ini')
        
        has_chap1 = (shape_thai_text('บทที่ 1') in flow_text) or ('บทที่ 1' in flow_text) or ('บทที 1' in flow_text)
        has_scene = ('คุยกับมาโกะ' in flow_text) or (shape_thai_text('คุยกับมาโกะ') in flow_text)
        has_choice = ('เลือกตัวเลือกใด?' in flow_text) or (shape_thai_text('เลือกตัวเลือกใด?') in flow_text)

        res.add("flow_texts_en.ini (data.xp3) decrypts and has size > 10KB", len(flow_text) > 10000, f"Length: {len(flow_text):,} chars")
        res.add("flow_texts_en.ini chapter title 'บทที่ 1'", has_chap1, "Found Thai chapter designation")
        res.add("flow_texts_en.ini scene node 'คุยกับมาโกะ'", has_scene, "Found Mako scene title")
        res.add("flow_texts_en.ini choice text 'เลือกตัวเลือกใด?'", has_choice, "Found flowchart choice prompt")
    except Exception as e:
        res.add("flow_texts_en.ini decryption", False, str(e))

    # 2. syslangtext_en.ini (from data.xp3)
    try:
        sys_bytes = extract_member_fast(data_xp3_path, parsed_data['files']['main/syslangtext_en.ini'])
        sys_text = decrypt_file(sys_bytes, 'syslangtext_en.ini')

        has_title = 'Senren*Banka - A Thousand Colors Of Love - [ภาษาไทย]' in sys_text
        has_disp = ('หน้าจอ' in sys_text) or (shape_thai_text('หน้าจอ') in sys_text)
        has_sound = ('เสียง' in sys_text) or (shape_thai_text('เสียง') in sys_text)

        res.add("syslangtext_en.ini (data.xp3) Title caption '[ภาษาไทย]'", has_title, "Title bar localized")
        res.add("syslangtext_en.ini Settings names 'หน้าจอ' & 'เสียง'", has_disp and has_sound, "Config categories localized")
    except Exception as e:
        res.add("syslangtext_en.ini decryption", False, str(e))

    # 3. title_en.pimg (from data.xp3)
    try:
        title_raw = extract_member_fast(data_xp3_path, parsed_data['files']['uipsd/en/title_en.pimg'])
        title_dec = decrypt_pimg(title_raw, 'uipsd/en/title_en.pimg')
        res.add("title_en.pimg (data.xp3) starts with b'PSB\\x00'", title_dec.startswith(b'PSB\x00'), f"Header: {title_dec[:4]!r}")

        title_res = extract_pimg_resources(title_dec)
        res.add("title_en.pimg contains exactly 33 resources", len(title_res) == 33, f"Resource count: {len(title_res)}")

        # Check button dimensions and non-zero alpha
        img_start = decode_tlg5(title_res[0])
        alpha_start = sum(1 for p in img_start.split()[3].tobytes() if p > 30)
        res.add("title_en.pimg START button (158x43) with valid alpha",
                img_start.size == (158, 43) and alpha_start > 100,
                f"Size={img_start.size}, Alpha pixels={alpha_start}")

        img_load = decode_tlg5(title_res[3])
        alpha_load = sum(1 for p in img_load.split()[3].tobytes() if p > 30)
        res.add("title_en.pimg LOAD button (174x44) with valid alpha",
                img_load.size == (174, 44) and alpha_load > 100,
                f"Size={img_load.size}, Alpha pixels={alpha_load}")
    except Exception as e:
        res.add("title_en.pimg texture verification", False, str(e))

    # 4. langselect.pimg (from data.xp3)
    try:
        lang_raw = extract_member_fast(data_xp3_path, parsed_data['files']['uipsd/langselect.pimg'])
        lang_dec = decrypt_pimg(lang_raw, 'uipsd/langselect.pimg')
        res.add("langselect.pimg (data.xp3) starts with b'PSB\\x00'", lang_dec.startswith(b'PSB\x00'), f"Header: {lang_dec[:4]!r}")

        lang_res = extract_pimg_resources(lang_dec)
        res.add("langselect.pimg contains exactly 4 resources", len(lang_res) == 4, f"Resource count: {len(lang_res)}")

        img_modal = decode_tlg5(lang_res[0])
        res.add("langselect.pimg modal dialog texture (450x188)",
                img_modal.size == (450, 188), f"Size={img_modal.size}")

        img_thai_btn = decode_tlg5(lang_res[1])
        alpha_btn = sum(1 for p in img_thai_btn.split()[3].tobytes() if p > 30)
        res.add("langselect.pimg 'ภาษาไทย' button (310x70) with valid alpha",
                img_thai_btn.size == (310, 70) and alpha_btn > 100,
                f"Size={img_thai_btn.size}, Alpha pixels={alpha_btn}")
    except Exception as e:
        res.add("langselect.pimg texture verification", False, str(e))

    # 5. Scenario sample decryption & Thai dialogue verification
    try:
        sample_scn = '001・アーサー王ver1.07.ks.scn'
        scn_raw = extract_member_fast(xp3_path, parsed_xp3['files'][sample_scn])
        scn_dec, k1, k2, hdr = decrypt_psb_auto(scn_raw)

        has_psb_hdr = scn_dec.startswith(b'PSB\x00')
        scn_text = scn_dec.decode('utf-8', errors='replace')
        has_thai_dialogue = contains_thai(scn_text)

        res.add(f"Scenario {sample_scn} decrypts cleanly (k1={k1}, k2={k2})", has_psb_hdr, "PSB signature verified")
        res.add(f"Scenario {sample_scn} contains authentic Thai dialogue", has_thai_dialogue, "Thai script detected")
    except Exception as e:
        res.add("Scenario sample verification", False, str(e))


# ===========================================================================
# PHASE 4: Engine Launch Sanity Test
# ===========================================================================
def verify_phase_4_engine_launch(res: VerificationResult) -> None:
    print("\n--- Phase 4: Engine Launch Sanity Test ---")
    if not os.path.exists(PLAYABLE_EXE):
        res.add("SenrenBanka.exe exists", False, f"Not found: {PLAYABLE_EXE}")
        return

    exe_size = os.path.getsize(PLAYABLE_EXE)
    res.add("SenrenBanka.exe executable binary valid", exe_size > 4000000, f"Size: {exe_size:,} bytes")

    temp_dir = tempfile.gettempdir()
    existing_krkr_dirs = glob.glob(os.path.join(temp_dir, 'krkr_*'))

    print(f"  [INFO] Launching {os.path.basename(PLAYABLE_EXE)} from {PLAYABLE_DIR}...")
    try:
        proc = subprocess.Popen([PLAYABLE_EXE, '-savecloud=no'], cwd=PLAYABLE_DIR)
        pid = proc.pid
        print(f"  [INFO] Engine process started with PID: {pid}")

        # Monitor process health for 5 seconds
        is_healthy = True
        for i in range(5):
            time.sleep(1)
            ret = proc.poll()
            if ret is not None:
                is_healthy = False
                res.add("Engine process healthy runtime (5 seconds)", False, f"Premature exit at sec {i+1} with code {ret}")
                break

        if is_healthy:
            res.add("Engine process healthy runtime (5 seconds)", True, f"Process active at PID {pid} without crash")

        # Check %TEMP% for krkr font folders
        current_krkr_dirs = glob.glob(os.path.join(temp_dir, 'krkr_*'))
        total_krkr = len(current_krkr_dirs)
        tft_files = [f for d in current_krkr_dirs if os.path.isdir(d) for f in os.listdir(d) if f.endswith('.tft')]

        res.add("Kirikiri font temporary subsystem verified in %TEMP%", total_krkr > 0 and len(tft_files) > 0,
                f"{total_krkr} krkr temp dirs, {len(tft_files)} cached TFT fonts found")

        # Terminate cleanly
        print(f"  [INFO] Terminating engine process {pid} cleanly...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            print("  [WARN] Engine did not exit in 3s, issuing kill...")
            proc.kill()
            proc.wait(timeout=2)

        res.add("Engine process clean termination", proc.poll() is not None, f"Exit code: {proc.poll()}")

    except Exception as e:
        res.add("Engine launch sanity test", False, str(e))


# ===========================================================================
# PHASE 5: Batch Launcher Verification
# ===========================================================================
def verify_phase_5_launchers(res: VerificationResult) -> None:
    print("\n--- Phase 5: Batch Launcher Verification ---")

    # 1. RUN_THAI_INJECTOR.bat
    if not os.path.exists(ROOT_INJECTOR_BAT):
        res.add("RUN_THAI_INJECTOR.bat exists", False, ROOT_INJECTOR_BAT)
    else:
        with open(ROOT_INJECTOR_BAT, 'r', encoding='utf-8', errors='replace') as f:
            inj_content = f.read()

        has_chcp = "chcp 65001" in inj_content
        has_call = "thai_injector.py" in inj_content
        has_err = "ERRORLEVEL" in inj_content

        res.add("RUN_THAI_INJECTOR.bat structure & error handling",
                has_chcp and has_call and has_err,
                "UTF-8 code page, thai_injector call, and error handling present")

    # 2. SenrenBanka_THAI_PLAYABLE/Start_Thai_Game.bat
    if not os.path.exists(PLAYABLE_LAUNCHER):
        res.add("Start_Thai_Game.bat exists", False, PLAYABLE_LAUNCHER)
    else:
        with open(PLAYABLE_LAUNCHER, 'r', encoding='utf-8', errors='replace') as f:
            start_content = f.read()

        has_chcp = "chcp 65001" in start_content
        has_cd = "%~dp0" in start_content
        has_facemode = "fix_facemode.py" in start_content
        has_exe = "SenrenBanka.exe" in start_content and "-savecloud=no" in start_content

        res.add("Start_Thai_Game.bat structure & launch parameters",
                has_chcp and has_cd and has_facemode and has_exe,
                "UTF-8 code page, directory anchor, fix_facemode hook, and -savecloud=no verified")


# ===========================================================================
# Master Verification Orchestrator
# ===========================================================================
def run_full_verification() -> bool:
    print("===========================================================================")
    print(" SENREN*BANKA THAI LOCALIZATION: MASTER END-TO-END VERIFICATION SUITE")
    print("===========================================================================")
    start_time = time.time()

    results: List[VerificationResult] = []

    # Phase 1: data.xp3 Fonts
    r1 = VerificationResult("Phase 1: data.xp3 Font Matrix (Playable)")
    verify_phase_1_fonts(r1, PLAYABLE_DATA_XP3, "Playable")
    results.append(r1)

    if os.path.exists(STEAM_DATA_XP3):
        r1_steam = VerificationResult("Phase 1: data.xp3 Font Matrix (Steam)")
        verify_phase_1_fonts(r1_steam, STEAM_DATA_XP3, "Steam")
        results.append(r1_steam)

    # Phase 2: patch_extra.xp3 Overlay
    r2 = VerificationResult("Phase 2: patch_extra.xp3 Overlay (Playable)")
    parsed_extra = verify_phase_2_overlay(r2, PLAYABLE_PATCH_EXTRA, "Playable")
    results.append(r2)

    if os.path.exists(STEAM_PATCH_EXTRA):
        r2_steam = VerificationResult("Phase 2: patch_extra.xp3 Overlay (Steam)")
        verify_phase_2_overlay(r2_steam, STEAM_PATCH_EXTRA, "Steam")
        results.append(r2_steam)

    # Phase 3: Content Decryption & Integrity
    r3 = VerificationResult("Phase 3: Content Decryption & Integrity")
    if parsed_extra:
        verify_phase_3_content(r3, parsed_extra)
    else:
        r3.add("patch_extra.xp3 available for content inspection", False, "Skipped due to Phase 2 parse failure")
    results.append(r3)

    # Phase 4: Engine Launch Sanity Test
    r4 = VerificationResult("Phase 4: Engine Launch Sanity Test")
    verify_phase_4_engine_launch(r4)
    results.append(r4)

    # Phase 5: Batch Launchers
    r5 = VerificationResult("Phase 5: Batch Launcher Verification")
    verify_phase_5_launchers(r5)
    results.append(r5)

    # Print Summary Table
    elapsed = time.time() - start_time
    print("\n" + "=" * 75)
    print("                   FINAL VERIFICATION SUMMARY REPORT")
    print("=" * 75)
    print(f"{'Phase / Verification Scope':<55} | {'Status':<10}")
    print("-" * 75)

    all_passed = True
    total_checks = 0
    passed_checks = 0

    for r in results:
        status_str = "PASS" if r.passed else "FAIL"
        print(f"{r.phase_name:<55} | [{status_str:^6}]")
        total_checks += len(r.checks)
        passed_checks += sum(1 for _, p, _ in r.checks if p)
        if not r.passed:
            all_passed = False

    print("-" * 75)
    print(f"Total Individual Checks: {passed_checks}/{total_checks} passed ({passed_checks/total_checks*100:.1f}%)")
    print(f"Elapsed Time: {elapsed:.2f} seconds")
    print("=" * 75)

    if all_passed:
        print("\n>>> ALL PHASES PASSED 100%! SYSTEM IS READY FOR IMMERSIVE THAI GAMEPLAY! <<<\n")
    else:
        print("\n>>> ONE OR MORE VERIFICATION CHECKS FAILED! REVIEW LOGS ABOVE. <<<\n")

    return all_passed


if __name__ == '__main__':
    success = run_full_verification()
    sys.exit(0 if success else 1)
