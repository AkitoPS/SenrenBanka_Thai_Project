"""
tools/inject_all_fonts_data_xp3.py — Master Data Archive Injector for data.xp3

Injects into data.xp3 cleanly:
1. All 20 extended TFT fonts (from tools/fonts_extended/)
2. All 9 localized Thai system & flowchart text files (from localization/system/)
3. Any rebuilt Thai UI texture containers present in localization/textures/rebuilt_th/
   (optional: skips cleanly if not present on disk, preserving original member bytes)
"""

import os
import sys
import struct
import zlib
import shutil
import io

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

try:
    from tools.kirikiri_text_compiler import encrypt_file
    from tools.steam_locator import find_senren_steam_dir
    from tools.verify_data_xp3_fonts import verify_data_xp3
except ImportError:
    from kirikiri_text_compiler import encrypt_file
    from steam_locator import find_senren_steam_dir
    from verify_data_xp3_fonts import verify_data_xp3

EXTENDED_FONTS_DIR = os.path.join(TOOLS_DIR, "fonts_extended")
SYSTEM_TEXT_DIR = os.path.join(REPO_ROOT, "localization", "system")
REBUILT_PIMG_DIR = os.path.join(REPO_ROOT, "localization", "textures", "rebuilt_th")
LOOSE_FONT_DIR = os.path.join(REPO_ROOT, "SenrenBanka_THAI_PLAYABLE", "font")
OUTPUT_DATA_XP3 = os.path.join(REPO_ROOT, "output", "data.xp3")

# 9 Thai System & Flowchart Text Specifications in data.xp3
SYSTEM_TEXT_SPECS = {
    'main/flow_texts_en.ini': {
        'member_idx': 219,
        'adlr': 0x58a55f1f,
        'disk_path': 'localization/system/flow_texts_th.ini',
        'sflags': 0
    },
    'main/help_exch_en.txt': {
        'member_idx': 223,
        'adlr': 0x5bd163c2,
        'disk_path': 'localization/system/help_exch_th.txt',
        'sflags': 1
    },
    'main/help_file_en.txt': {
        'member_idx': 227,
        'adlr': 0x32700d6b,
        'disk_path': 'localization/system/help_file_th.txt',
        'sflags': 1
    },
    'main/help_flow_en.txt': {
        'member_idx': 231,
        'adlr': 0xffd4d03b,
        'disk_path': 'localization/system/help_flow_th.txt',
        'sflags': 1
    },
    'main/help_lang_en.txt': {
        'member_idx': 235,
        'adlr': 0x786767f5,
        'disk_path': 'localization/system/help_lang_th.txt',
        'sflags': 1
    },
    'main/help_sys_en.txt': {
        'member_idx': 239,
        'adlr': 0xbf9ed865,
        'disk_path': 'localization/system/help_sys_th.txt',
        'sflags': 1
    },
    'main/help_tui_en.txt': {
        'member_idx': 243,
        'adlr': 0xfea39adc,
        'disk_path': 'localization/system/help_tui_th.txt',
        'sflags': 1
    },
    'main/soundlist_en.csv': {
        'member_idx': 268,
        'adlr': 0x01eaa3ca,
        'disk_path': 'localization/system/soundlist_th.csv',
        'sflags': 0
    },
    'main/syslangtext_en.ini': {
        'member_idx': 279,
        'adlr': 0x67eb1fe2,
        'disk_path': 'localization/system/syslangtext_th.ini',
        'sflags': 0
    }
}

# Rebuilt Thai .pimg Texture Containers in data.xp3
PIMG_MEMBER_SPECS = {
    'uipsd/en/afterstory_en.pimg': {
        'member_idx': 1157,
        'adlr': 0xad8d8e9b,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/afterstory_en.pimg',
        'sflags': 0
    },
    'uipsd/en/dialog_en.pimg': {
        'member_idx': 1159,
        'adlr': 0x051c85fb,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/dialog_en.pimg',
        'sflags': 0,
        'optional': True
    },
    'uipsd/en/flowchart_en.pimg': {
        'member_idx': 1162,
        'adlr': 0xdee398fd,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/flowchart_en.pimg',
        'sflags': 0
    },
    'uipsd/en/sys_base_en.pimg': {
        'member_idx': 1169,
        'adlr': 0x315ae04b,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/sys_base_en.pimg',
        'sflags': 0
    },
    'uipsd/en/sys_page0_en.pimg': {
        'member_idx': 1170,
        'adlr': 0xe00731f7,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/sys_page0_en.pimg',
        'sflags': 0,
        'optional': True
    },
    'uipsd/en/sys_page1_en.pimg': {
        'member_idx': 1171,
        'adlr': 0xd8c196be,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/sys_page1_en.pimg',
        'sflags': 0,
        'optional': True
    },
    'uipsd/en/sys_page2_en.pimg': {
        'member_idx': 1172,
        'adlr': 0xe2923c01,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/sys_page2_en.pimg',
        'sflags': 0,
        'optional': True
    },
    'uipsd/en/sys_page3_en.pimg': {
        'member_idx': 1173,
        'adlr': 0xc624fdcd,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/sys_page3_en.pimg',
        'sflags': 0,
        'optional': True
    },
    'uipsd/en/sys_page4_en.pimg': {
        'member_idx': 1174,
        'adlr': 0x1e8f5611,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/sys_page4_en.pimg',
        'sflags': 0,
        'optional': True
    },
    'uipsd/en/sys_page5_en.pimg': {
        'member_idx': 1175,
        'adlr': 0xd34b1e77,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/sys_page5_en.pimg',
        'sflags': 0,
        'optional': True
    },
    'uipsd/en/sys_page6_en.pimg': {
        'member_idx': 1176,
        'adlr': 0x883cc4b6,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/sys_page6_en.pimg',
        'sflags': 0,
        'optional': True
    },
    'uipsd/en/sys_page7_en.pimg': {
        'member_idx': 1177,
        'adlr': 0x3ef0edbe,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/sys_page7_en.pimg',
        'sflags': 0,
        'optional': True
    },
    'uipsd/en/title_en.pimg': {
        'member_idx': 1178,
        'adlr': 0xae7b5576,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/en/title_en.pimg',
        'sflags': 0
    },
    'uipsd/langselect.pimg': {
        'member_idx': 1209,
        'adlr': 0x9ea9389b,
        'disk_path': 'localization/textures/rebuilt_th/uipsd/langselect.pimg',
        'sflags': 0
    }
}

# Exact 20 TFT Font Specifications
FONT_SPECS = {
    'font1_10.tft': {
        'member_idx': 4,
        'adlr': 0x50634ba9,
        'k1': 0x76, 'k2': 0x13, 'split': 2134,
        'anomalies': {28377: 0x5f}
    },
    'font1_14.tft': {
        'member_idx': 5,
        'adlr': 0xaff04db3,
        'k1': 0xb4, 'k2': 0x1, 'split': 2150,
        'anomalies': {}
    },
    'font1_20.tft': {
        'member_idx': 6,
        'adlr': 0x2a7bb10e,
        'k1': 0x1, 'k2': 0x5e, 'split': 2106,
        'anomalies': {15958: 0xfd, 44140: 0x7}
    },
    'font1_26.tft': {
        'member_idx': 7,
        'adlr': 0xe9c76dda,
        'k1': 0xde, 'k2': 0x91, 'split': 2118,
        'anomalies': {3563: 0x17, 49843: 0xc}
    },
    'font1_32.tft': {
        'member_idx': 8,
        'adlr': 0xcfdd73fc,
        'k1': 0x54, 'k2': 0x56, 'split': 2154,
        'anomalies': {53: 0xac, 32158: 0x94, 60494: 0xea}
    },
    'font1_39.tft': {
        'member_idx': 9,
        'adlr': 0x9fe15f6a,
        'k1': 0x43, 'k2': 0x4c, 'split': 2134,
        'anomalies': {25420: 0x19, 65365: 0x2f}
    },
    'font1_48.tft': {
        'member_idx': 10,
        'adlr': 0x14d4dd79,
        'k1': 0x9, 'k2': 0x5a, 'split': 2150,
        'anomalies': {}
    },
    'font1_56.tft': {
        'member_idx': 11,
        'adlr': 0xa992635b,
        'k1': 0x1f, 'k2': 0xc4, 'split': 2118,
        'anomalies': {}
    },
    'headfont_20.tft': {
        'member_idx': 12,
        'adlr': 0xa3286087,
        'k1': 0x56, 'k2': 0xd3, 'split': 1850,
        'anomalies': {14861: 0x16, 60744: 0x6a}
    },
    'headfont_24.tft': {
        'member_idx': 13,
        'adlr': 0x91626338,
        'k1': 0x4e, 'k2': 0x27, 'split': 2150,
        'anomalies': {41186: 0x68, 50733: 0x1e}
    },
    'headfont_30.tft': {
        'member_idx': 14,
        'adlr': 0x9dd325c0,
        'k1': 0x1, 'k2': 0x16, 'split': 2102,
        'anomalies': {10100: 0x29}
    },
    'headfont_36.tft': {
        'member_idx': 15,
        'adlr': 0xb030b12b,
        'k1': 0xb8, 'k2': 0xa5, 'split': 2134,
        'anomalies': {48319: 0xc1, 58543: 0x9b}
    },
    'sysfont_10.tft': {
        'member_idx': 39,
        'adlr': 0xc02bf934,
        'k1': 0xa4, 'k2': 0x8, 'split': 2154,
        'anomalies': {2602: 0x76, 53476: 0x29}
    },
    'sysfont_12.tft': {
        'member_idx': 40,
        'adlr': 0x5186d0,
        'k1': 0x51, 'k2': 0x7b, 'split': 1862,
        'anomalies': {55123: 0xf1}
    },
    'sysfont_15.tft': {
        'member_idx': 41,
        'adlr': 0xf67bb03a,
        'k1': 0x94, 'k2': 0xe2, 'split': 1894,
        'anomalies': {18146: 0x98, 23674: 0xa4}
    },
    'sysfont_16.tft': {
        'member_idx': 42,
        'adlr': 0x6dfe97cf,
        'k1': 0x99, 'k2': 0x5f, 'split': 2106,
        'anomalies': {32540: 0x85}
    },
    'sysfont_18.tft': {
        'member_idx': 43,
        'adlr': 0x9251827c,
        'k1': 0x6, 'k2': 0x5a, 'split': 1898,
        'anomalies': {2: 0x25, 36358: 0xed, 46938: 0x5c}
    },
    'sysfont_20.tft': {
        'member_idx': 44,
        'adlr': 0x7d89578b,
        'k1': 0x4c, 'k2': 0x79, 'split': 2102,
        'anomalies': {2177: 0xa4, 58496: 0xbd}
    },
    'sysfont_24.tft': {
        'member_idx': 45,
        'adlr': 0x8b1d04d7,
        'k1': 0x4c, 'k2': 0x13, 'split': 1866,
        'anomalies': {1678: 0xcc, 22035: 0x25, 28470: 0x45}
    },
    'sysfont_30.tft': {
        'member_idx': 46,
        'adlr': 0xe1286c47,
        'k1': 0x1f, 'k2': 0x75, 'split': 1850,
        'anomalies': {27564: 0x69}
    }
}

def encrypt_font(raw_bytes: bytes, spec: dict) -> bytes:
    k1 = spec['k1']
    k2 = spec['k2']
    split = spec['split']
    anom = spec['anomalies']
    enc = bytearray(len(raw_bytes))
    for i in range(len(raw_bytes)):
        if i in anom:
            k = anom[i]
        elif i < split:
            k = k1
        else:
            k = k2
        enc[i] = raw_bytes[i] ^ k
    return bytes(enc)

def build_injected_archive(source_xp3_path: str, fonts_dir: str) -> bytearray:
    print(f"Reading source XP3 archive: {source_xp3_path} ...")
    with open(source_xp3_path, 'rb') as f:
        orig = f.read()

    orig_total_size = len(orig)
    print(f"Source size: {orig_total_size:,} bytes")

    # 1. Parse XP3 header and redirection
    assert orig[:11] == b"XP3\r\n \n\x1a\x8bg\x01", "Invalid XP3 magic"
    redir_off = struct.unpack('<Q', orig[11:19])[0]  # 23
    assert orig[redir_off] == 0x80, f"Expected 0x80 at offset {redir_off}"
    orig_real_idx_off = struct.unpack('<Q', orig[redir_off+9:redir_off+17])[0]

    # 2. Decompress original index
    comp_sz, uncomp_sz = struct.unpack('<QQ', orig[orig_real_idx_off+1:orig_real_idx_off+17])
    orig_idx_decomp = zlib.decompress(orig[orig_real_idx_off+17:orig_real_idx_off+17+comp_sz])
    assert len(orig_idx_decomp) == uncomp_sz

    # 3. Parse sen: chunk
    assert orig_idx_decomp[:4] == b'sen:', "Missing sen: chunk"
    sen_sz = struct.unpack('<Q', orig_idx_decomp[4:12])[0]
    assert sen_sz == 40
    sen_body = orig_idx_decomp[12:12+sen_sz]
    orig_hnfn_off = struct.unpack('<Q', sen_body[:8])[0]
    orig_hnfn_uncomp, orig_hnfn_comp = struct.unpack('<II', sen_body[8:16])
    steam_sig = sen_body[16:]
    assert len(steam_sig) == 24, "Steam signature size mismatch"

    orig_hnfn_comp_data = orig[orig_hnfn_off:orig_hnfn_off+orig_hnfn_comp]
    assert len(orig_hnfn_comp_data) == orig_hnfn_comp

    # 4. Prepare all replacement payloads (20 extended TFT fonts + optional system texts + optional .pimg)
    print(f"Loading and encrypting all 20 extended fonts from {fonts_dir} ...")
    replaced_members = {}

    for fontname, spec in FONT_SPECS.items():
        m_idx = spec['member_idx']
        fpath = os.path.join(fonts_dir, fontname)
        assert os.path.exists(fpath), f"Missing extended font file: {fpath} (run tools/build_all_extended_fonts.py first)"
        with open(fpath, 'rb') as fp:
            raw = fp.read()
        assert raw[:22] == b"TVP pre-rendered font\x1a", f"Invalid font magic in {fpath}"
        enc = encrypt_font(raw, spec)
        assert len(enc) == len(raw)
        replaced_members[m_idx] = {
            'stored': enc,
            'sorig': len(enc),
            'sarc': len(enc),
            'sflags': 0,
            'name': f"font/{fontname}"
        }

    # Optional UI injection only when --include-ui flag is explicitly passed
    inject_ui = "--include-ui" in sys.argv
    sys_count = 0
    pimg_count = 0
    if inject_ui:
        for mem_name, spec in SYSTEM_TEXT_SPECS.items():
            disk_path = os.path.join(REPO_ROOT, spec['disk_path'])
            if not os.path.isfile(disk_path):
                print(f"  [skip] System text not present on disk: {spec['disk_path']}")
                continue
            with open(disk_path, 'r', encoding='utf-8') as sf:
                text_content = sf.read()
            enc_raw = encrypt_file(text_content, mem_name, apply_shaping=True)
            stored = zlib.compress(enc_raw) if spec['sflags'] == 1 else enc_raw
            replaced_members[spec['member_idx']] = {
                'stored': stored,
                'sorig': len(enc_raw),
                'sarc': len(stored),
                'sflags': spec['sflags'],
                'name': mem_name
            }
            sys_count += 1

        for mem_name, spec in PIMG_MEMBER_SPECS.items():
            disk_path = os.path.join(REPO_ROOT, spec['disk_path'])
            if not os.path.isfile(disk_path):
                print(f"  [skip] PIMG container not present on disk: {spec['disk_path']}")
                continue
            with open(disk_path, 'rb') as pf:
                stored = pf.read()
            replaced_members[spec['member_idx']] = {
                'stored': stored,
                'sorig': len(stored),
                'sarc': len(stored),
                'sflags': spec['sflags'],
                'name': mem_name
            }
            pimg_count += 1
        print(f"Total members to replace in data.xp3: {len(replaced_members)} (20 fonts, {sys_count} system texts, {pimg_count} .pimg containers)")
    else:
        print(f"Total members to replace in data.xp3: {len(replaced_members)} (20 extended TFT fonts; pass --include-ui to inject system texts/.pimg)")

    # 5. Parse all File entries in index to record their offsets and sizes
    pos = 12 + sen_sz
    file_count = 0
    file_records = []  # list of dicts

    while pos < len(orig_idx_decomp):
        ctype = orig_idx_decomp[pos:pos+4]
        csz = struct.unpack('<Q', orig_idx_decomp[pos+4:pos+12])[0]
        cbody = orig_idx_decomp[pos+12:pos+12+csz]
        pos += 12 + csz

        if ctype == b'File':
            sub_pos = 0
            rec = {
                'index': file_count,
                'subchunks': [],
                'soff': 0, 'sorig': 0, 'sarc': 0, 'sflags': 0,
                'iflags': 0, 'iorig': 0, 'iarc': 0, 'inlen': 0, 'iname_bytes': b'',
                'adlr': 0
            }
            while sub_pos < len(cbody):
                stype = cbody[sub_pos:sub_pos+4]
                ssz = struct.unpack('<Q', cbody[sub_pos+4:sub_pos+12])[0]
                sdata = cbody[sub_pos+12:sub_pos+12+ssz]
                sub_pos += 12 + ssz

                if stype == b'segm':
                    sflags, soff, sorig, sarc = struct.unpack('<IQQQ', sdata[:28])
                    rec['sflags'] = sflags
                    rec['soff'] = soff
                    rec['sorig'] = sorig
                    rec['sarc'] = sarc
                elif stype == b'info':
                    iflags, iorig, iarc, inlen = struct.unpack('<IQQH', sdata[:22])
                    rec['iflags'] = iflags
                    rec['iorig'] = iorig
                    rec['iarc'] = iarc
                    rec['inlen'] = inlen
                    rec['iname_bytes'] = sdata[22:]
                elif stype == b'adlr':
                    rec['adlr'] = struct.unpack('<I', sdata[:4])[0]

                rec['subchunks'].append((stype, ssz, sdata))

            file_records.append(rec)
            file_count += 1

    assert file_count == 1278, f"Expected 1278 files, got {file_count}"
    print(f"Parsed {file_count} file entries from source index.")

    # Verify all replaced members are in ascending physical offset order
    sorted_rep_indices = sorted(replaced_members.keys(), key=lambda m: file_records[m]['soff'])
    for i in range(len(sorted_rep_indices) - 1):
        m_a = sorted_rep_indices[i]
        m_b = sorted_rep_indices[i + 1]
        assert file_records[m_a]['soff'] + file_records[m_a]['sarc'] <= file_records[m_b]['soff'], \
            f"Overlapping or out-of-order members: {m_a} and {m_b}"

    # 6. Compute new offsets and deltas
    shift = 0
    new_offsets = []
    new_orig_sizes = []
    new_arc_sizes = []
    new_sflags_list = []

    for k in range(file_count):
        rec = file_records[k]
        if k in replaced_members:
            rep = replaced_members[k]
            new_offsets.append(rec['soff'] + shift)
            new_orig_sizes.append(rep['sorig'])
            new_arc_sizes.append(rep['sarc'])
            new_sflags_list.append(rep['sflags'])
            delta = rep['sarc'] - rec['sarc']
            shift += delta
        else:
            new_offsets.append(rec['soff'] + shift)
            new_orig_sizes.append(rec['sorig'])
            new_arc_sizes.append(rec['sarc'])
            new_sflags_list.append(rec['sflags'])

    total_delta = shift
    new_hnfn_off = orig_hnfn_off + total_delta
    print(f"Total archive delta: {total_delta:+d} bytes")
    print(f"New hnfn_off: {new_hnfn_off:,} bytes (was {orig_hnfn_off:,})")

    # 7. Build new Index body (preserving original 32-char MD5 iname_bytes and original adlr!)
    new_idx_body = bytearray()
    for k in range(file_count):
        rec = file_records[k]
        is_replaced = (k in replaced_members)
        new_file_body = bytearray()

        for stype, ssz, sdata in rec['subchunks']:
            if stype == b'segm':
                new_sflags = new_sflags_list[k]
                new_off = new_offsets[k]
                new_orig = new_orig_sizes[k]
                new_arc = new_arc_sizes[k]
                segm_bytes = struct.pack('<IQQQ', new_sflags, new_off, new_orig, new_arc)
                new_file_body.extend(b'segm' + struct.pack('<Q', 28) + segm_bytes)
            elif stype == b'info':
                new_iflags = 0x80000000 if is_replaced else rec['iflags']
                new_iorig = new_orig_sizes[k]
                new_iarc = new_arc_sizes[k]
                info_bytes = struct.pack('<IQQH', new_iflags, new_iorig, new_iarc, rec['inlen']) + rec['iname_bytes']
                new_file_body.extend(b'info' + struct.pack('<Q', len(info_bytes)) + info_bytes)
            else:
                # time, adlr, and any other chunks copied as-is!
                new_file_body.extend(stype + struct.pack('<Q', ssz) + sdata)

        new_idx_body.extend(b'File' + struct.pack('<Q', len(new_file_body)) + new_file_body)

    # 8. Assemble physical archive slices cleanly for arbitrary sorted replaced_members
    sorted_rep_indices = sorted(replaced_members.keys(), key=lambda m: file_records[m]['soff'])
    new_archive = bytearray()
    cur_orig_pos = 0

    for m_idx in sorted_rep_indices:
        rec = file_records[m_idx]
        if rec['soff'] > cur_orig_pos:
            new_archive.extend(orig[cur_orig_pos : rec['soff']])
        new_archive.extend(replaced_members[m_idx]['stored'])
        cur_orig_pos = rec['soff'] + rec['sarc']

    if cur_orig_pos < orig_hnfn_off:
        new_archive.extend(orig[cur_orig_pos : orig_hnfn_off])

    assert len(new_archive) == new_hnfn_off, f"Assembled length {len(new_archive)} != new_hnfn_off {new_hnfn_off}"

    # 9. Reconstruct sen: chunk and recompress Index
    new_sen_body = struct.pack('<QII', new_hnfn_off, orig_hnfn_uncomp, orig_hnfn_comp) + steam_sig
    assert len(new_sen_body) == 40
    new_sen_chunk = b'sen:' + struct.pack('<Q', 40) + new_sen_body

    full_new_idx_decomp = new_sen_chunk + new_idx_body
    new_idx_comp = zlib.compress(full_new_idx_decomp)

    new_real_idx_off = new_hnfn_off + len(orig_hnfn_comp_data)

    idx_block = bytearray([0x01]) + struct.pack('<QQ', len(new_idx_comp), len(full_new_idx_decomp)) + new_idx_comp

    new_archive.extend(orig_hnfn_comp_data)
    new_archive.extend(idx_block)

    # 10. Update redirection pointer at byte 32 (redir_off + 9)
    struct.pack_into('<Q', new_archive, redir_off + 9, new_real_idx_off)

    print(f"New data.xp3 created: {len(new_archive):,} bytes (Delta: {len(new_archive) - orig_total_size:+d})")
    return new_archive

def inject_all():
    print("=" * 75)
    print("INJECTING EXTENDED THAI TFT FONTS & SYSTEM TEXTS INTO DATA.XP3")
    print("=" * 75)

    steam_dir = find_senren_steam_dir()
    source_candidates = [
        os.path.join(REPO_ROOT, "archive", "original_game_backup", "data.xp3"),
        os.path.join(steam_dir, "thai_mod_backup", "data.xp3.bak") if steam_dir else None,
        os.path.join(steam_dir, "data.xp3") if steam_dir else None,
        os.path.join(REPO_ROOT, "SenrenBanka_THAI_PLAYABLE", "data.xp3"),
    ]
    source_xp3 = next((p for p in source_candidates if p and os.path.isfile(p)), None)
    assert source_xp3, f"No valid source data.xp3 found in {source_candidates}"
    print(f"Selected source archive: {source_xp3}")

    # 2. Build new archive
    new_archive = build_injected_archive(source_xp3, EXTENDED_FONTS_DIR)

    # 3. Write to output/ and optional Playable/Steam targets
    target_paths = [OUTPUT_DATA_XP3]
    playable_dir = os.path.join(REPO_ROOT, "SenrenBanka_THAI_PLAYABLE")
    if os.path.isdir(playable_dir):
        target_paths.append(os.path.join(playable_dir, "data.xp3"))
    if steam_dir and os.path.isdir(steam_dir):
        bak_path = os.path.join(steam_dir, "thai_mod_backup", "data.xp3.bak")
        steam_data = os.path.join(steam_dir, "data.xp3")
        if os.path.isfile(steam_data) and not os.path.isfile(bak_path):
            os.makedirs(os.path.dirname(bak_path), exist_ok=True)
            shutil.copy2(steam_data, bak_path)
            print(f"[✓] Backed up original Steam data.xp3 -> {bak_path}")
        target_paths.append(steam_data)

    for target in target_paths:
        target_dir = os.path.dirname(target)
        os.makedirs(target_dir, exist_ok=True)
        print(f"\nWriting to target: {target} ...")
        tmp_target = target + ".tmp"
        with open(tmp_target, 'wb') as tf:
            tf.write(new_archive)

        assert os.path.getsize(tmp_target) == len(new_archive), "Written temp file size mismatch"

        if os.path.exists(target):
            try:
                os.remove(target)
            except Exception as e:
                print(f"[WARN] Failed to remove {target} directly ({e}), attempting rename replace...")
        shutil.move(tmp_target, target)
        print(f"[SUCCESS] Successfully updated: {target}")

    # 4. Synchronize loose extended fonts only if SenrenBanka_THAI_PLAYABLE exists
    if os.path.isdir(playable_dir):
        print(f"\nSynchronizing all 20 extended fonts to {LOOSE_FONT_DIR} ...")
        os.makedirs(LOOSE_FONT_DIR, exist_ok=True)
        synced_count = 0
        for fontname in FONT_SPECS.keys():
            src_font = os.path.join(EXTENDED_FONTS_DIR, fontname)
            dst_font = os.path.join(LOOSE_FONT_DIR, fontname)
            shutil.copy2(src_font, dst_font)
            synced_count += 1
        print(f"[SUCCESS] Synchronized {synced_count} fonts to {LOOSE_FONT_DIR}.")

    # 5. Run verification on output/data.xp3 (and Steam if updated)
    print("\n" + "=" * 75)
    print("RUNNING POST-INJECTION VERIFICATION...")
    print("=" * 75)
    assert verify_data_xp3(OUTPUT_DATA_XP3, EXTENDED_FONTS_DIR), "output/data.xp3 verification FAILED!"

    if steam_dir and os.path.isfile(os.path.join(steam_dir, "data.xp3")):
        assert verify_data_xp3(os.path.join(steam_dir, "data.xp3"), EXTENDED_FONTS_DIR), "Steam data.xp3 verification FAILED!"

    print("\n" + "=" * 75)
    print("ALL TARGET ARCHIVES INJECTED AND VERIFIED 100% PERFECTLY!")
    print("=" * 75)

if __name__ == '__main__':
    inject_all()
