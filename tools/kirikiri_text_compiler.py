"""
tool/kirikiri_text_compiler.py — Kirikiri Mode 1 & Dual-Key XOR Text Compiler.

Handles compilation (encryption) and decompilation (decryption) of Kirikiri engine text
assets (INI, TXT, CSV) according to Kirikiri Crypt Mode 1:
1. Normalization & Thai PUA shaping via tool.thai_pua_shaper.shape_thai_text.
2. UTF-16LE encoding with 16-bit bit-pair permutation:
   u' = ((u & 0xAAAA) >> 1) | ((u & 0x5555) << 1)
3. 5-byte magic header: b'\\xFE\\xFE\\x01\\xFF\\xFE'
4. Dual-Key XOR stream encryption:
   - byte[i] ^= k1 for i < split
   - byte[i] ^= k2 for i >= split
"""

import os
import sys
import argparse
from typing import Tuple, Dict, Any, Optional

try:
    from tool.thai_pua_shaper import shape_thai_text
except ImportError:
    from thai_pua_shaper import shape_thai_text

KIRIKIRI_MODE1_MAGIC = b'\xfe\xfe\x01\xff\xfe'

FILE_PROFILES: Dict[str, Dict[str, Any]] = {
    'main/flow_texts_en.ini': {'k1': 0x08, 'k2': 0x63, 'split': 2122, 'anomalies': {}},
    'main/syslangtext_en.ini': {'k1': 0x62, 'k2': 0x01, 'split': 2134, 'anomalies': {}},
    'main/soundlist_en.csv': {'k1': 0x13, 'k2': 0xE4, 'split': 2102, 'anomalies': {}},
    'main/help_flow_en.txt': {'k1': 0x4D, 'k2': 0x4D, 'split': 1887, 'anomalies': {}},
    'main/help_sys_en.txt': {'k1': 0x05, 'k2': 0x01, 'split': 1881, 'anomalies': {32768: 0xDA}},
    'main/help_file_en.txt': {'k1': 0x79, 'k2': 0xAD, 'split': 2134, 'anomalies': {}},
    'main/help_exch_en.txt': {'k1': 0x63, 'k2': 0x17, 'split': 2102, 'anomalies': {}},
    'main/help_lang_en.txt': {'k1': 0x32, 'k2': 0x32, 'split': 431, 'anomalies': {}},
    'main/help_tui_en.txt': {'k1': 0x23, 'k2': 0x0C, 'split': 1865, 'anomalies': {}},
}

# Alternate / extracted keys from patch.xp3 / test variants
ALT_PROFILES: Dict[str, Dict[str, Any]] = {
    'main/help_exch_en.txt': {'k1': 0x5B, 'k2': 0x5B, 'split': 2000, 'anomalies': {}},
    'main/help_lang_en.txt': {'k1': 0x78, 'k2': 0x78, 'split': 2000, 'anomalies': {}},
    'main/help_tui_en.txt': {'k1': 0xFE, 'k2': 0xFE, 'split': 2000, 'anomalies': {}},
}


def bit_pair_swap(u: int) -> int:
    """
    Apply Kirikiri Mode 1 bit-pair permutation to a 16-bit unsigned integer.
    u' = ((u & 0xAAAA) >> 1) | ((u & 0x5555) << 1)
    This operation is an involution: bit_pair_swap(bit_pair_swap(u)) == u.
    """
    return ((u & 0xAAAA) >> 1) | ((u & 0x5555) << 1)


def _is_valid_text_char(c: int) -> bool:
    """Check if 16-bit character code belongs to plausible visual/control text ranges."""
    return (
        c in (0x09, 0x0A, 0x0D) or             # Tab, LF, CR
        (0x20 <= c <= 0x7E) or                 # Printable ASCII
        (0x0E00 <= c <= 0x0E7F) or             # Thai Unicode block
        (0x2000 <= c <= 0x2700) or             # Punctuation, arrows, geometric symbols
        (0x3000 <= c <= 0x9FFF) or             # CJK symbols, kana, kanji
        (0xF700 <= c <= 0xF71F) or             # Thai PUA pre-composed glyphs
        (0xFF00 <= c <= 0xFFEF)                # Fullwidth forms
    )


def _char_plausibility(u: int) -> int:
    """Evaluate text plausibility score for a 16-bit decoded character."""
    if not _is_valid_text_char(u):
        return -50
    if u in (0x0A, 0x0D, 0x09, 0x20):
        return 5
    if 0x20 <= u <= 0x7E:
        return 3
    if 0x0E00 <= u <= 0x0E5B or 0xF700 <= u <= 0xF71F:
        return 2
    if 0x3040 <= u <= 0x30FF:
        return 2
    if 0x2000 <= u <= 0x2700 or 0xFF00 <= u <= 0xFFEF:
        return 2
    if 0x4E00 <= u <= 0x9FFF:
        return 1
    return 0


def _score_key_on_tail(data: bytes, k: int, tail_start: int) -> int:
    """Score a key candidate on character data."""
    score = 0
    for i in range(tail_start, len(data) - 1, 2):
        u = (data[i] ^ k) | ((data[i+1] ^ k) << 8)
        u_orig = bit_pair_swap(u)
        score += _char_plausibility(u_orig)
    return score



def encrypt_kirikiri_text(
    text: str,
    k1: int = 0x08,
    k2: int = 0x63,
    split: int = 2122,
    apply_shaping: bool = True,
    anomalies: Optional[Dict[int, int]] = None
) -> bytes:
    """
    Encrypt unencrypted text using Kirikiri Mode 1 and Dual-Key XOR cipher.
    
    Args:
        text: Input string.
        k1: Primary XOR key (applied to bytes 0 .. split - 1).
        k2: Secondary XOR key (applied to bytes split .. end).
        split: Byte offset boundary between k1 and k2.
        apply_shaping: If True, applies Thai PUA shaping before encoding.
        anomalies: Optional dict mapping byte index -> override XOR key.
    
    Returns:
        Encrypted byte sequence starting with magic b'\xFE\xFE\x01\xFF\xFE' ^ k1.
    """
    if apply_shaping:
        text = shape_thai_text(text)

    # 1. Transform to UTF-16LE with bit-pair permutation
    payload = bytearray()
    for char in text:
        u = ord(char)
        if u > 0xFFFF:
            u_high = 0xD800 + ((u - 0x10000) >> 10)
            u_low = 0xDC00 + ((u - 0x10000) & 0x3FF)
            p_high = bit_pair_swap(u_high)
            p_low = bit_pair_swap(u_low)
            payload.append(p_high & 0xFF)
            payload.append((p_high >> 8) & 0xFF)
            payload.append(p_low & 0xFF)
            payload.append((p_low >> 8) & 0xFF)
        else:
            p = bit_pair_swap(u)
            payload.append(p & 0xFF)
            payload.append((p >> 8) & 0xFF)

    # 2. Assemble magic prefix + permuted UTF-16LE payload
    raw_buffer = bytearray(KIRIKIRI_MODE1_MAGIC + payload)

    # 3. Dual-Key XOR (+ single-byte anomalies)
    anom = anomalies or {}
    for i in range(len(raw_buffer)):
        if i in anom:
            key = anom[i]
        else:
            key = k1 if i < split else k2
        raw_buffer[i] ^= key

    return bytes(raw_buffer)


def decrypt_kirikiri_text(
    data: bytes,
    k1: int = 0x08,
    k2: int = 0x63,
    split: int = 2122,
    anomalies: Optional[Dict[int, int]] = None
) -> str:
    """
    Decrypt Kirikiri Mode 1 encrypted data with Dual-Key XOR cipher.
    
    Args:
        data: Encrypted byte sequence.
        k1: Primary XOR key.
        k2: Secondary XOR key.
        split: Byte offset boundary.
        anomalies: Optional dict mapping byte index -> override XOR key.
    
    Returns:
        Decrypted UTF-8 string.
    
    Raises:
        ValueError: If magic prefix is corrupted or payload length is invalid.
    """
    if len(data) < len(KIRIKIRI_MODE1_MAGIC):
        raise ValueError(f"Data length ({len(data)}) too short for Kirikiri Mode 1 header")

    # 1. Dual-Key XOR inverse
    anom = anomalies or {}
    buf = bytearray(data)
    for i in range(len(buf)):
        if i in anom:
            key = anom[i]
        else:
            key = k1 if i < split else k2
        buf[i] ^= key

    # 2. Verify magic prefix
    magic_len = len(KIRIKIRI_MODE1_MAGIC)
    if buf[:magic_len] != KIRIKIRI_MODE1_MAGIC:
        raise ValueError(
            f"Invalid Kirikiri Mode 1 magic prefix: expected {KIRIKIRI_MODE1_MAGIC.hex()}, got {bytes(buf[:magic_len]).hex()}"
        )

    # 3. Unswap bit pairs
    payload = buf[magic_len:]
    if len(payload) % 2 != 0:
        raise ValueError(f"Invalid payload length: {len(payload)} (expected even number of bytes)")

    chars = []
    for i in range(0, len(payload), 2):
        u_prime = payload[i] | (payload[i+1] << 8)
        u = bit_pair_swap(u_prime)
        chars.append(chr(u))

    return "".join(chars)


def detect_keys_from_encrypted(data: bytes) -> Tuple[int, int, int]:
    """
    Analyze encrypted data to automatically deduce (k1, k2, split).
    
    1. Extracts k1 directly from the first 5 magic bytes: data[0] ^ 0xFE.
    2. Tests if k1 decodes the entire file with high plausibility.
    3. Scores candidate k2 keys against trailing text.
    4. Accurately determines split boundary.
    
    Returns:
        (k1, k2, split)
    """
    magic_len = len(KIRIKIRI_MODE1_MAGIC)
    if len(data) < magic_len:
        raise ValueError("Data too short to detect Kirikiri magic")

    k1 = data[0] ^ KIRIKIRI_MODE1_MAGIC[0]
    for i in range(magic_len):
        if data[i] ^ KIRIKIRI_MODE1_MAGIC[i] != k1:
            raise ValueError(f"Magic header mismatch at byte {i}")

    payload_len = len(data) - magic_len
    if payload_len < 2:
        return k1, k1, len(data)

    # 1. Search for best k2 on trailing chunk
    tail_len = min(300, payload_len)
    tail_start = len(data) - tail_len
    if (tail_start - magic_len) % 2 != 0:
        tail_start += 1

    score_k1 = _score_key_on_tail(data, k1, tail_start)

    best_k2 = k1
    best_score = score_k1
    for cand_k2 in range(256):
        sc = _score_key_on_tail(data, cand_k2, tail_start)
        if sc > best_score:
            best_score = sc
            best_k2 = cand_k2

    # If best key on tail is k1, it's a single key stream
    if best_k2 == k1 or best_score <= 0:
        return k1, k1, len(data)

    # 2. Dual-key stream: Find split transition between k1 and k2
    char_indices = list(range(magic_len, len(data) - 1, 2))
    diffs = []
    for i in char_indices:
        u1 = bit_pair_swap((data[i] ^ k1) | ((data[i+1] ^ k1) << 8))
        u2 = bit_pair_swap((data[i] ^ best_k2) | ((data[i+1] ^ best_k2) << 8))
        d = _char_plausibility(u1) - _char_plausibility(u2)
        diffs.append((i, d))

    window = 5
    cand_s = None
    for idx in range(len(diffs) - window):
        avg = sum(diffs[idx + w][1] for w in range(window))
        if avg < 0:
            cand_s = diffs[idx][0]
            break

    if cand_s is None:
        return k1, best_k2, len(data)

    best_s = cand_s
    best_exact_score = -1e9
    for s in range(max(magic_len, cand_s - 16), min(len(data), cand_s + 16)):
        score = 0
        mid_char = magic_len + ((s - magic_len) // 2) * 2
        for i in range(max(magic_len, mid_char - 20), min(len(data) - 1, mid_char + 22), 2):
            b0 = data[i] ^ (k1 if i < s else best_k2)
            b1 = data[i+1] ^ (k1 if i + 1 < s else best_k2)
            u = bit_pair_swap(b0 | (b1 << 8))
            score += _char_plausibility(u)
        if score > best_exact_score:
            best_exact_score = score
            best_s = s

    return k1, best_k2, best_s


def _normalize_profile_key(name: str) -> str:
    """Normalize file name or profile key for lookup."""
    clean = name.replace('\\', '/').strip().lower()
    if clean.startswith('./'):
        clean = clean[2:]
    return clean


def get_file_profile(filename_or_profile_key: str) -> Optional[Dict[str, Any]]:
    """Look up cipher profile by file path or key."""
    norm = _normalize_profile_key(filename_or_profile_key)
    
    # Exact match
    for k, v in FILE_PROFILES.items():
        if _normalize_profile_key(k) == norm:
            return v
    
    # Match basename if full path wasn't provided
    base = os.path.basename(norm)
    for k, v in FILE_PROFILES.items():
        if os.path.basename(k).lower() == base:
            return v

    # Support _th -> _en mapping (e.g. syslangtext_th.ini -> syslangtext_en.ini)
    norm_en = norm.replace('_th.', '_en.')
    base_en = base.replace('_th.', '_en.')
    for k, v in FILE_PROFILES.items():
        if _normalize_profile_key(k) == norm_en or os.path.basename(k).lower() == base_en:
            return v

    return None


def encrypt_file(text: str, filename_or_profile_key: str, apply_shaping: bool = True) -> bytes:
    """
    Encrypt text using the predefined profile for a file.
    
    Args:
        text: String content.
        filename_or_profile_key: Target path (e.g. 'main/flow_texts_en.ini') or key.
        apply_shaping: Whether to apply Thai PUA shaping.
    
    Returns:
        Encrypted bytes.
    """
    prof = get_file_profile(filename_or_profile_key)
    if not prof:
        raise KeyError(f"No encryption profile found for '{filename_or_profile_key}'")

    return encrypt_kirikiri_text(
        text,
        k1=prof['k1'],
        k2=prof['k2'],
        split=prof['split'],
        apply_shaping=apply_shaping,
        anomalies=prof.get('anomalies')
    )


def decrypt_file(data: bytes, filename_or_profile_key: str) -> str:
    """
    Decrypt data using the file's profile, with automatic fallback / key detection.
    
    Args:
        data: Encrypted byte sequence.
        filename_or_profile_key: File name or profile key.
    
    Returns:
        Decrypted UTF-8 string.
    """
    prof = get_file_profile(filename_or_profile_key)
    
    if len(data) >= len(KIRIKIRI_MODE1_MAGIC):
        actual_k1 = data[0] ^ KIRIKIRI_MODE1_MAGIC[0]
        
        # Check standard profile
        if prof and prof['k1'] == actual_k1:
            try:
                return decrypt_kirikiri_text(
                    data, k1=prof['k1'], k2=prof['k2'], split=prof['split'],
                    anomalies=prof.get('anomalies')
                )
            except Exception:
                pass
        
        # Check alternate profiles for XP3 builds
        norm = _normalize_profile_key(filename_or_profile_key)
        for alt_k, alt_v in ALT_PROFILES.items():
            if _normalize_profile_key(alt_k) == norm or os.path.basename(alt_k).lower() == os.path.basename(norm):
                if alt_v['k1'] == actual_k1:
                    try:
                        return decrypt_kirikiri_text(
                            data, k1=alt_v['k1'], k2=alt_v['k2'], split=alt_v['split'],
                            anomalies=alt_v.get('anomalies')
                        )
                    except Exception:
                        pass
        
        # Automatic key and split detection
        try:
            det_k1, det_k2, det_split = detect_keys_from_encrypted(data)
            return decrypt_kirikiri_text(data, k1=det_k1, k2=det_k2, split=det_split)
        except Exception:
            pass

    # Fallback to standard profile decryption attempt
    if prof:
        return decrypt_kirikiri_text(
            data, k1=prof['k1'], k2=prof['k2'], split=prof['split'],
            anomalies=prof.get('anomalies')
        )
    
    raise KeyError(f"Unable to decrypt '{filename_or_profile_key}': no profile or valid key detected")


def main():
    parser = argparse.ArgumentParser(description="Kirikiri Mode 1 & Dual-Key XOR Text Compiler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Encrypt
    enc_parser = subparsers.add_parser("encrypt", help="Encrypt text file")
    enc_parser.add_argument("input", help="Path to plaintext input file")
    enc_parser.add_argument("output", help="Path to encrypted output file")
    enc_parser.add_argument("--profile", "-p", required=True, help="Profile key or target file path")
    enc_parser.add_argument("--no-shaping", action="store_true", help="Disable Thai PUA shaping")

    # Decrypt
    dec_parser = subparsers.add_parser("decrypt", help="Decrypt encrypted text file")
    dec_parser.add_argument("input", help="Path to encrypted input file")
    dec_parser.add_argument("output", help="Path to plaintext output file")
    dec_parser.add_argument("--profile", "-p", help="Profile key or target file path (optional)")

    # Detect
    det_parser = subparsers.add_parser("detect", help="Detect keys and split of encrypted file")
    det_parser.add_argument("input", help="Path to encrypted input file")

    args = parser.parse_args()

    if args.command == "encrypt":
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
        enc = encrypt_file(text, args.profile, apply_shaping=not args.no_shaping)
        with open(args.output, 'wb') as f:
            f.write(enc)
        print(f"[OK] Encrypted {len(text)} chars -> {len(enc)} bytes ({args.output})")

    elif args.command == "decrypt":
        with open(args.input, 'rb') as f:
            data = f.read()
        profile_key = args.profile or os.path.basename(args.input)
        text = decrypt_file(data, profile_key)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"[OK] Decrypted {len(data)} bytes -> {len(text)} chars ({args.output})")

    elif args.command == "detect":
        with open(args.input, 'rb') as f:
            data = f.read()
        k1, k2, s = detect_keys_from_encrypted(data)
        print(f"File: {args.input}")
        print(f"k1: 0x{k1:02X} ({k1})")
        print(f"k2: 0x{k2:02X} ({k2})")
        print(f"split: {s}")


if __name__ == '__main__':
    main()
