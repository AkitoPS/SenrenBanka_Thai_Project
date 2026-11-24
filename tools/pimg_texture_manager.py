"""
tools/pimg_texture_manager.py — PIMG Container & TLG5.0 Texture Manager for Kirikiri Z / FreeMote.

Handles:
1. Dual-Key XOR cipher encryption and decryption for FreeMote PSB .pimg containers.
2. Direct XP3 archive member extraction.
3. Resource table parsing and container rebuilding.
4. Fast TLG5.0 decoder (supporting both LZSS mark=0 and uncompressed raw mark=1 blocks).
5. High-speed TLG5.0 encoder (vectorized NumPy diff filters with mark=1 raw blocks).
"""

import os
import sys
import struct
import zlib
import argparse
import numpy as np
from PIL import Image

# Known PIMG cipher profiles for Senren*Banka UI
PIMG_PROFILES = {
    'uipsd/en/title_en.pimg': {'k1': 0x03, 'k2': 0x02, 'split': 2124, 'anomalies': {}},
    'uipsd/en/afterstory_en.pimg': {'k1': 0x6F, 'k2': 0x01, 'split': 2124, 'anomalies': {}},
    'uipsd/en/flowchart_en.pimg': {'k1': 0x01, 'k2': 0xF5, 'split': 1850, 'anomalies': {}},
    'uipsd/en/sys_base_en.pimg': {'k1': 0x88, 'k2': 0xEF, 'split': 1850, 'anomalies': {10002: 0x80}},
    'uipsd/langselect.pimg': {'k1': 0xC7, 'k2': 0xBC, 'split': 1862, 'anomalies': {}},
    'uipsd/en/dialog_en.pimg': {'k1': 0x20, 'k2': 0xC0, 'split': 1850, 'anomalies': {}},
    'uipsd/en/sys_page0_en.pimg': {'k1': 0x01, 'k2': 0x28, 'split': 1850, 'anomalies': {}},
    'uipsd/en/sys_page1_en.pimg': {'k1': 0x24, 'k2': 0x15, 'split': 1850, 'anomalies': {12645: 0xE0}},
    'uipsd/en/sys_page2_en.pimg': {'k1': 0x32, 'k2': 0x01, 'split': 1850, 'anomalies': {}},
    'uipsd/en/sys_page3_en.pimg': {'k1': 0xCC, 'k2': 0xDD, 'split': 1850, 'anomalies': {}},
    'uipsd/en/sys_page4_en.pimg': {'k1': 0x88, 'k2': 0x01, 'split': 1850, 'anomalies': {}},
    'uipsd/en/sys_page5_en.pimg': {'k1': 0x09, 'k2': 0x01, 'split': 1866, 'anomalies': {}},
    'uipsd/en/sys_page6_en.pimg': {'k1': 0x20, 'k2': 0x04, 'split': 1850, 'anomalies': {}},
    'uipsd/en/sys_page7_en.pimg': {'k1': 0x60, 'k2': 0x01, 'split': 1850, 'anomalies': {}},
}

def resolve_profile(target: str | dict) -> dict:
    """Resolve cipher profile from string path or dict."""
    if isinstance(target, dict):
        return target
    norm = target.replace('\\', '/')
    for key, prof in PIMG_PROFILES.items():
        if norm == key or norm.endswith('/' + key) or os.path.basename(norm) == os.path.basename(key):
            return prof
    raise KeyError(f"No cipher profile found for: {target}")

def decrypt_pimg(enc_data: bytes, target_profile: str | dict) -> bytes:
    """Decrypt PIMG container using Dual-Key XOR cipher and profile anomalies."""
    prof = resolve_profile(target_profile)
    k1 = prof['k1']
    k2 = prof['k2']
    split = prof['split']
    anom = prof.get('anomalies', {})
    
    dec = bytearray(enc_data)
    for i in range(len(dec)):
        if i in anom:
            dec[i] ^= anom[i]
        elif i < split:
            dec[i] ^= k1
        else:
            dec[i] ^= k2
    return bytes(dec)

def encrypt_pimg(dec_data: bytes, target_profile: str | dict) -> bytes:
    """Encrypt PIMG container using Dual-Key XOR cipher (symmetric XOR)."""
    return decrypt_pimg(dec_data, target_profile)

def decrypt_pimg_metadata_with_k2(enc_data: bytes, target_profile: str | dict) -> bytes:
    """Decrypt bytes 40..end purely with k2, so metadata bytes can be copied bit-for-bit if needed."""
    prof = resolve_profile(target_profile)
    k1 = prof['k1']
    k2 = prof['k2']
    dec = bytearray(enc_data)
    for i in range(40):
        dec[i] ^= k1
    for i in range(40, len(dec)):
        dec[i] ^= k2
    return bytes(dec)

def extract_file_from_xp3(xp3_path: str, filename: str) -> bytes | None:
    """Extract a single file payload directly from an XP3 archive."""
    with open(xp3_path, 'rb') as f:
        magic = f.read(11)
        if magic != b"XP3\r\n \n\x1a\x8bg\x01":
            raise ValueError(f"Invalid XP3 magic in {xp3_path}")
        f.seek(23 + 9)
        real_idx_off = struct.unpack('<Q', f.read(8))[0]
        
        f.seek(real_idx_off)
        idx_flag = f.read(1)[0]
        comp_sz, uncomp_sz = struct.unpack('<QQ', f.read(16))
        idx_decomp = zlib.decompress(f.read(comp_sz))
        
        # sen: chunk
        sen_sz = struct.unpack('<Q', idx_decomp[4:12])[0]
        sen_body = idx_decomp[12:12+sen_sz]
        hnfn_off = struct.unpack('<Q', sen_body[:8])[0]
        hnfn_uncomp, hnfn_comp = struct.unpack('<II', sen_body[8:16])
        
        # hnfn table
        f.seek(hnfn_off)
        hnfn_decomp = zlib.decompress(f.read(hnfn_comp))
        hash_to_name = {}
        hpos = 0
        while hpos < len(hnfn_decomp):
            if hnfn_decomp[hpos:hpos+4] == b'hnfn':
                cz = struct.unpack('<Q', hnfn_decomp[hpos+4:hpos+12])[0]
                cb = hnfn_decomp[hpos+12:hpos+12+cz]
                hpos += 12 + cz
                rpos = 0
                while rpos + 6 <= len(cb):
                    fhash = struct.unpack('<I', cb[rpos:rpos+4])[0]
                    nlen = struct.unpack('<H', cb[rpos+4:rpos+6])[0]
                    if rpos + 6 + nlen * 2 <= len(cb):
                        name = cb[rpos+6 : rpos+6+nlen*2].decode('utf-16le', errors='replace')
                        rpos += 6 + nlen * 2
                        hash_to_name[fhash] = name
                    else:
                        break
            else:
                hpos += 1

        # File chunks
        pos = 12 + sen_sz
        target_norm = filename.replace('\\', '/')
        while pos < len(idx_decomp):
            ctype = idx_decomp[pos:pos+4]
            csz = struct.unpack('<Q', idx_decomp[pos+4:pos+12])[0]
            cbody = idx_decomp[pos+12:pos+12+csz]
            pos += 12 + csz
            if ctype == b'File':
                spos = 0
                finfo = {}
                while spos < len(cbody):
                    stype = cbody[spos:spos+4]
                    ssz = struct.unpack('<Q', cbody[spos+4:spos+12])[0]
                    sdata = cbody[spos+12:spos+12+ssz]
                    spos += 12 + ssz
                    if stype == b'adlr':
                        finfo['adlr'] = struct.unpack('<I', sdata[:4])[0]
                    elif stype == b'segm':
                        sflags, soff, sorig, sarc = struct.unpack('<IQQQ', sdata[:28])
                        finfo['soff'] = soff
                        finfo['sorig'] = sorig
                        finfo['sarc'] = sarc
                fname = hash_to_name.get(finfo.get('adlr'), '').replace('\\', '/')
                if fname == target_norm or os.path.basename(fname) == os.path.basename(target_norm):
                    f.seek(finfo['soff'])
                    return f.read(finfo['sarc'])
    return None

def parse_psb_array(data: bytes, offset: int) -> tuple[list[int], int]:
    """Parse PSB integer array at given offset. Returns (elements, next_offset)."""
    assert data[offset] == 0x0D, f"Expected PSB array opcode 0x0D at offset {offset}, got {data[offset]}"
    count = data[offset+1]
    bpe_flag = data[offset+2]
    bpe = bpe_flag - 12
    pos = offset + 3
    arr = []
    for _ in range(count):
        val = int.from_bytes(data[pos:pos+bpe], 'little')
        arr.append(val)
        pos += bpe
    return arr, pos

def serialize_psb_array(values: list[int], min_bpe: int = 1) -> tuple[bytes, int]:
    """Serialize list of integers into PSB array [0x0D, count, bpe_flag, elements...]."""
    max_val = max(values) if values else 0
    needed_bpe = 1
    while (1 << (needed_bpe * 8)) <= max_val:
        needed_bpe += 1
    bpe = max(min_bpe, needed_bpe)
    bpe_flag = bpe + 12
    out = bytearray([0x0D, len(values), bpe_flag])
    for v in values:
        out.extend(v.to_bytes(bpe, 'little'))
    return bytes(out), bpe

def extract_pimg_resources(dec_psb: bytes) -> list[bytes]:
    """Extract all raw resource byte payloads from a decrypted PSB container."""
    if not dec_psb.startswith(b'PSB\x00'):
        raise ValueError("Decrypted container does not start with b'PSB\\x00'")
    fields = struct.unpack('<4s9I', dec_psb[:40])
    res_off_table, res_len_table, res_data_start = fields[6], fields[7], fields[8]
    
    offsets, _ = parse_psb_array(dec_psb, res_off_table)
    lengths, _ = parse_psb_array(dec_psb, res_len_table)
    
    resources = []
    for off, sz in zip(offsets, lengths):
        payload = dec_psb[res_data_start + off : res_data_start + off + sz]
        resources.append(bytes(payload))
    return resources

def rebuild_pimg(orig_enc_pimg: bytes, target_profile: str | dict, replaced_resources: dict[int, bytes]) -> bytes:
    """
    Rebuild PIMG container with replaced resources.
    Preserves the exact encrypted bytes of the metadata region (bytes 40..res_off_table)
    from orig_enc_pimg so that any cxdec split boundary or single-byte anomaly in
    0..res_off_table is 100% untouched!
    
    Args:
        orig_enc_pimg: Original encrypted PIMG container bytes.
        target_profile: Path or dict representing the cipher profile.
        replaced_resources: Dict mapping resource index to new raw TLG bytes.
    Returns:
        New re-encrypted PIMG container bytes.
    """
    prof = resolve_profile(target_profile)
    k1 = prof['k1']
    k2 = prof['k2']
    dec = decrypt_pimg(orig_enc_pimg, prof)
    fields = list(struct.unpack('<4s9I', dec[:40]))
    res_off_table, res_len_table, res_data_start = fields[6], fields[7], fields[8]
    
    orig_offsets, _ = parse_psb_array(dec, res_off_table)
    orig_lengths, _ = parse_psb_array(dec, res_len_table)
    
    # Build list of new resources
    new_resources = []
    for i in range(len(orig_offsets)):
        if i in replaced_resources:
            new_resources.append(replaced_resources[i])
        else:
            new_resources.append(dec[res_data_start + orig_offsets[i] : res_data_start + orig_offsets[i] + orig_lengths[i]])
            
    new_lengths = [len(r) for r in new_resources]
    new_offsets = []
    cur_off = 0
    for sz in new_lengths:
        new_offsets.append(cur_off)
        cur_off += sz
        
    orig_off_bpe = dec[res_off_table + 2] - 12
    orig_len_bpe = dec[res_len_table + 2] - 12
    
    off_bytes, _ = serialize_psb_array(new_offsets, min_bpe=orig_off_bpe)
    len_bytes, _ = serialize_psb_array(new_lengths, min_bpe=orig_len_bpe)
    
    new_res_off_table = res_off_table
    new_res_len_table = new_res_off_table + len(off_bytes)
    new_res_data_start = new_res_len_table + len(len_bytes)
    padding_len = (16 - (new_res_data_start % 16)) % 16
    new_res_data_start += padding_len
    
    # Update PSB Header (bytes 0..40) and encrypt with k1
    new_header = bytearray(dec[:40])
    new_header[24:28] = struct.pack('<I', new_res_off_table)
    new_header[28:32] = struct.pack('<I', new_res_len_table)
    new_header[32:36] = struct.pack('<I', new_res_data_start)
    enc_header = bytes(b ^ k1 for b in new_header)
    
    # Preserve original encrypted bytes 40..res_off_table verbatim!
    # Wait: if split > res_off_table (as in langselect where res_off_table=871 and split=1862),
    # then encrypt_pimg(rebuilt_dec, prof) handles it if we know split, or if res_off_table > 2200,
    # preserving orig_enc_pimg[40:res_off_table] is 100% immune to split/anomalies in 40..res_off_table!
    if res_off_table >= 2165:
        tail_dec = bytearray()
        tail_dec.extend(off_bytes)
        tail_dec.extend(len_bytes)
        tail_dec.extend(b'\x00' * padding_len)
        for r in new_resources:
            tail_dec.extend(r)
        # Note: if there are anomalies at >= res_off_table, apply them ONLY if the byte offset did not shift,
        # wait: cxdec anomalies are tied to file byte offset `i`!
        anom = prof.get('anomalies', {})
        rebuilt_enc = bytearray()
        rebuilt_enc.extend(enc_header)
        rebuilt_enc.extend(orig_enc_pimg[40:res_off_table])
        for idx_tail, b in enumerate(tail_dec):
            file_off = res_off_table + idx_tail
            key = anom.get(file_off, k2)
            rebuilt_enc.append(b ^ key)
        return bytes(rebuilt_enc)
    else:
        meta_part = dec[40:res_off_table]
        rebuilt_dec = bytearray()
        rebuilt_dec.extend(new_header)
        rebuilt_dec.extend(meta_part)
        rebuilt_dec.extend(off_bytes)
        rebuilt_dec.extend(len_bytes)
        rebuilt_dec.extend(b'\x00' * padding_len)
        for r in new_resources:
            rebuilt_dec.extend(r)
        return encrypt_pimg(bytes(rebuilt_dec), prof)

def decompress_slide(inbuf: bytes, inbuf_size: int, text: bytearray, initial_r: int) -> tuple[bytes, int]:
    """Decompress Kirikiri TLG5 sliding dictionary (LZSS) block."""
    outbuf = bytearray()
    r = initial_r
    flags = 0
    i = 0
    while i < inbuf_size:
        if ((flags >> 1) & 256) == 0:
            flags = (inbuf[i] | 0xff00)
            i += 1
        else:
            flags >>= 1
            
        if (flags & 1) != 0:
            mpos = inbuf[i] | ((inbuf[i+1] & 0x0f) << 8)
            mlen = (inbuf[i+1] & 0xf0) >> 4
            i += 2
            mlen += 3
            if mlen == 18:
                mlen += inbuf[i]
                i += 1
            while mlen > 0:
                c = text[mpos]
                outbuf.append(c)
                text[r] = c
                mpos = (mpos + 1) & 4095
                r = (r + 1) & 4095
                mlen -= 1
        else:
            c = inbuf[i]
            i += 1
            outbuf.append(c)
            text[r] = c
            r = (r + 1) & 4095
    return bytes(outbuf), r

def decode_tlg5(tlg_data: bytes) -> Image.Image:
    """
    Decode TLG5.0 image (RGBA or RGB) into a PIL RGBA Image.
    Supports both LZSS compressed blocks (mark=0) and raw blocks (mark=1).
    Reconstructs pixel colors via 2D cumulative sums using NumPy.
    """
    if not tlg_data.startswith(b'TLG5.0\x00raw\x1a'):
        raise ValueError("Invalid TLG5.0 header")
    colors = tlg_data[11]
    if colors not in (3, 4):
        raise ValueError(f"Unsupported color count: {colors}")
        
    width, height, blockheight = struct.unpack('<III', tlg_data[12:24])
    blockcount = (height - 1) // blockheight + 1
    
    pos = 24 + blockcount * 4
    text = bytearray(4096)
    r = 0
    channel_bufs = [bytearray() for _ in range(4)]
    
    for y_blk in range(0, height, blockheight):
        y_lim = min(y_blk + blockheight, height)
        h_blk = y_lim - y_blk
        expected_blk_bytes = h_blk * width
        
        for c in range(colors):
            mark = tlg_data[pos]
            sz = struct.unpack('<I', tlg_data[pos+1:pos+5])[0]
            pos += 5
            payload = tlg_data[pos:pos+sz]
            pos += sz
            if mark == 0:
                decomp, r = decompress_slide(payload, sz, text, r)
                channel_bufs[c].extend(decomp[:expected_blk_bytes])
            elif mark == 1:
                channel_bufs[c].extend(payload[:expected_blk_bytes])
            else:
                raise ValueError(f"Unknown TLG5 block mark: {mark}")
                
    b_ch = np.frombuffer(channel_bufs[0], dtype=np.uint8).reshape((height, width))
    g_ch = np.frombuffer(channel_bufs[1], dtype=np.uint8).reshape((height, width))
    r_ch = np.frombuffer(channel_bufs[2], dtype=np.uint8).reshape((height, width))
    a_ch = np.frombuffer(channel_bufs[3], dtype=np.uint8).reshape((height, width)) if colors == 4 else np.full((height, width), 255, dtype=np.uint8)
    
    c0 = b_ch + g_ch
    c1 = g_ch
    c2 = r_ch + g_ch
    c3 = a_ch
    
    B = np.cumsum(np.cumsum(c0, axis=1, dtype=np.uint8), axis=0, dtype=np.uint8)
    G = np.cumsum(np.cumsum(c1, axis=1, dtype=np.uint8), axis=0, dtype=np.uint8)
    R = np.cumsum(np.cumsum(c2, axis=1, dtype=np.uint8), axis=0, dtype=np.uint8)
    A = np.cumsum(np.cumsum(c3, axis=1, dtype=np.uint8), axis=0, dtype=np.uint8)
    
    rgba = np.stack([R, G, B, A], axis=-1)
    return Image.fromarray(rgba, 'RGBA')

def encode_tlg5(img: Image.Image, blockheight: int = 4) -> bytes:
    """
    Encode PIL RGBA Image to TLG5.0 bytes.
    Uses reverse delta filtering across rows and columns and writes mark=1 raw blocks,
    which are natively and efficiently loaded by Kirikiri Z.
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    width, height = img.size
    
    arr = np.array(img, dtype=np.uint8)
    bgra = np.empty_like(arr)
    bgra[:, :, 0] = arr[:, :, 2] # Blue
    bgra[:, :, 1] = arr[:, :, 1] # Green
    bgra[:, :, 2] = arr[:, :, 0] # Red
    bgra[:, :, 3] = arr[:, :, 3] # Alpha
    
    # Vertical difference
    V = np.empty_like(bgra)
    V[0] = bgra[0]
    V[1:] = bgra[1:] - bgra[:-1]
    
    # Horizontal difference
    c = np.empty_like(V)
    c[:, 0] = V[:, 0]
    c[:, 1:] = V[:, 1:] - V[:, :-1]
    
    # Chroma difference
    buf = np.empty_like(c)
    buf[:, :, 0] = c[:, :, 0] - c[:, :, 1] # B - G
    buf[:, :, 1] = c[:, :, 1]              # G
    buf[:, :, 2] = c[:, :, 2] - c[:, :, 1] # R - G
    buf[:, :, 3] = c[:, :, 3]              # A
    
    colors = 4
    hdr = bytearray(b'TLG5.0\x00raw\x1a')
    hdr.append(colors)
    hdr.extend(struct.pack('<III', width, height, blockheight))
    
    blocks_data = bytearray()
    block_sizes = []
    
    for y_blk in range(0, height, blockheight):
        y_lim = min(y_blk + blockheight, height)
        blk_buf = buf[y_blk:y_lim]
        
        blk_bytes = bytearray()
        for ch in range(colors):
            ch_data = blk_buf[:, :, ch].tobytes()
            blk_bytes.append(1) # mark = 1 (raw uncompressed)
            blk_bytes.extend(struct.pack('<I', len(ch_data)))
            blk_bytes.extend(ch_data)
            
        block_sizes.append(len(blk_bytes))
        blocks_data.extend(blk_bytes)
        
    block_table = bytearray()
    for sz in block_sizes:
        block_table.extend(struct.pack('<I', sz))
        
    return bytes(hdr + block_table + blocks_data)

def export_all_pimg_layers(xp3_path: str, output_dir: str):
    """Export all PNG layers from known PIMG files in XP3 to output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 75)
    print(f"EXPORTING PIMG TEXTURE LAYERS FROM: {xp3_path}")
    print(f"OUTPUT DIRECTORY: {output_dir}")
    print("=" * 75)
    
    for pimg_path, prof in PIMG_PROFILES.items():
        base_name = os.path.splitext(os.path.basename(pimg_path))[0]
        pimg_out_dir = os.path.join(output_dir, base_name)
        os.makedirs(pimg_out_dir, exist_ok=True)
        
        print(f"\nProcessing: {pimg_path} -> {pimg_out_dir}")
        raw = extract_file_from_xp3(xp3_path, pimg_path)
        if raw is None:
            print(f"[ERROR] Could not find {pimg_path} in XP3!")
            continue
            
        dec = decrypt_pimg(raw, prof)
        resources = extract_pimg_resources(dec)
        print(f"  Found {len(resources)} resources.")
        
        for idx, res_bytes in enumerate(resources):
            try:
                img = decode_tlg5(res_bytes)
                out_png = os.path.join(pimg_out_dir, f"res_{idx:03d}_{img.width}x{img.height}.png")
                img.save(out_png)
                print(f"    Exported res_{idx:03d}: {img.width}x{img.height} -> {os.path.basename(out_png)}")
            except Exception as e:
                print(f"    [FAIL] Failed to decode res_{idx:03d}: {e}")

if __name__ == '__main__':
    try:
        from tools.steam_locator import find_senren_steam_dir
    except ImportError:
        from steam_locator import find_senren_steam_dir

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    steam_dir = find_senren_steam_dir()
    default_xp3 = next(
        (p for p in [
            os.path.join(repo_root, 'output', 'data.xp3'),
            os.path.join(repo_root, 'SenrenBanka_THAI_PLAYABLE', 'data.xp3'),
            os.path.join(steam_dir, 'data.xp3') if steam_dir else None,
        ] if p and os.path.isfile(p)),
        'SenrenBanka_THAI_PLAYABLE/data.xp3'
    )

    parser = argparse.ArgumentParser(description="PIMG Texture Manager for Senren*Banka")
    parser.add_argument('--export-all', action='store_true', help='Export all layers from data.xp3')
    parser.add_argument('--xp3', default=default_xp3, help='Path to data.xp3')
    parser.add_argument('--out-dir', default='localization/textures/original_en', help='Output directory for exported PNGs')
    args = parser.parse_args()
    
    if args.export_all:
        export_all_pimg_layers(args.xp3, args.out_dir)
    else:
        parser.print_help()
