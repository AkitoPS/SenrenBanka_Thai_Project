"""
steam_locator.py — Cross-drive Steam Library & Original Archive Locator for Senren*Banka.
Uses Windows Registry (HKCU/HKLM) and Steam libraryfolders.vdf with zero third-party deps.
Also inspects XP3 scenario archives to distinguish untouched English bases from Thai-modded files.
"""

import os
import re
import struct
import zlib

APP_FOLDER_NAME = "SenrenBanka"


def find_steam_libraries() -> list[str]:
    """Return existing Steam library root directories discovered on the system."""
    libs: list[str] = []
    seen: set[str] = set()

    def _add(p: str | None):
        if not p:
            return
        norm = os.path.normpath(p.strip().strip('"'))
        key = norm.lower()
        if key not in seen and os.path.isdir(norm):
            seen.add(key)
            libs.append(norm)

    if os.name == "nt":
        try:
            import winreg
            reg_queries = [
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ]
            for root_key, subkey, val_name in reg_queries:
                try:
                    with winreg.OpenKey(root_key, subkey) as k:
                        val, _ = winreg.QueryValueEx(k, val_name)
                        _add(val)
                except OSError:
                    pass
        except ImportError:
            pass

    for fallback in [
        r"C:\Program Files (x86)\Steam",
        r"C:\Program Files\Steam",
        r"D:\SteamLibrary",
        r"D:\Steam",
        r"E:\SteamLibrary",
        r"E:\Steam",
        r"F:\SteamLibrary",
        r"G:\SteamLibrary",
    ]:
        _add(fallback)

    # Parse libraryfolders.vdf from discovered Steam roots
    for base in list(libs):
        for vdf in (
            os.path.join(base, "steamapps", "libraryfolders.vdf"),
            os.path.join(base, "config", "libraryfolders.vdf"),
        ):
            if os.path.isfile(vdf):
                try:
                    with open(vdf, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    for m in re.finditer(r'"path"\s+"([^"]+)"', content):
                        _add(m.group(1).replace("\\\\", "\\"))
                except OSError:
                    pass

    return libs


def find_senren_steam_dir() -> str | None:
    """Locate the Senren*Banka installation directory (supports SENREN_STEAM_DIR override)."""
    override = os.environ.get("SENREN_STEAM_DIR")
    if override and os.path.isdir(override):
        return os.path.normpath(override)

    # Look for SenrenBanka.exe first
    for lib in find_steam_libraries():
        cand = os.path.join(lib, "steamapps", "common", APP_FOLDER_NAME)
        if os.path.isfile(os.path.join(cand, "SenrenBanka.exe")):
            return cand

    # Fallback: folder containing patch_extra.xp3 or data.xp3
    for lib in find_steam_libraries():
        cand = os.path.join(lib, "steamapps", "common", APP_FOLDER_NAME)
        if os.path.isfile(os.path.join(cand, "patch_extra.xp3")) or os.path.isfile(os.path.join(cand, "data.xp3")):
            return cand

    return None


def _decrypt_psb_strings_quick(enc: bytes) -> list[str]:
    """Quickly decrypt a PSB/SCN buffer and extract decoded UTF-8 strings."""
    if len(enc) < 40:
        return []

    k1 = None
    for cand in range(256):
        v = struct.unpack("<I", bytes([b ^ cand for b in enc[4:8]]))[0]
        h0 = struct.unpack("<I", bytes([b ^ cand for b in enc[8:12]]))[0]
        if v in (2, 3) and h0 in (0x24, 0x28, 0x2C):
            k1 = cand
            break
    if k1 is None:
        k1 = enc[1] ^ ord("S")

    head = bytes([b ^ k1 for b in enc[:40]])
    if head[:3] != b"PSB":
        return []
    hdr7 = struct.unpack("<I", head[36:40])[0]
    hdr = struct.unpack_from("<IIIIIIII", head, 8)
    str_off, str_data, extra_off, extra_data, extra_end = hdr[2], hdr[3], hdr[4], hdr[5], hdr[6]

    if str_off >= len(enc):
        return []

    k2 = None
    for cand in range(256):
        b0 = enc[str_off] ^ cand
        if b0 in (0x0C, 0x0D, 0x0E, 0x0F):
            cnt_sz = 2 if b0 == 0x0E else (1 if b0 == 0x0D else (3 if b0 == 0x0F else 0))
            if cnt_sz and str_off + 1 + cnt_sz < len(enc):
                wb = enc[str_off + 1 + cnt_sz] ^ cand
                if wb in (0x0D, 0x0E, 0x0F, 0x10):
                    val0 = enc[str_off + 2 + cnt_sz] ^ cand
                    if val0 == 0:
                        k2 = cand
                        break
    if k2 is None:
        k2 = k1

    dec = bytearray(len(enc))
    for i in range(min(hdr7, len(enc))):
        dec[i] = enc[i] ^ k1
    for i in range(hdr7, len(enc)):
        dec[i] = enc[i] ^ k2

    trailer_start = extra_data - 3 if (extra_data >= 3 and extra_end == len(dec)) else extra_off
    if extra_off < trailer_start:
        extra_off = trailer_start

    count = struct.unpack_from("<H", dec, str_off + 1)[0]
    entry_type = dec[str_off + 3]
    in_width = {0x0D: 1, 0x0E: 2, 0x0F: 3, 0x10: 4}.get(
        entry_type, entry_type - 0x0C if entry_type >= 0x0D else 3
    )

    strings: list[str] = []
    for i in range(count):
        pos = str_off + 4 + i * in_width
        if pos + in_width > len(dec):
            break
        val = int.from_bytes(dec[pos : pos + in_width], "little")
        st = str_data + val
        en = st
        while en < extra_off and en < len(dec) and dec[en] != 0:
            en += 1
        strings.append(dec[st:en].decode("utf-8", errors="replace"))
    return strings


def xp3_contains_thai_dialogue(xp3_path: str, sample_limit: int = 3) -> bool:
    """
    Inspect up to `sample_limit` .scn members in an XP3 archive and return True
    if any scenario string pool already contains Thai Unicode or Thai PUA glyphs.
    """
    if not xp3_path or not os.path.isfile(xp3_path):
        return False
    try:
        with open(xp3_path, "rb") as f:
            if f.read(11) != b"XP3\r\n \n\x1a\x8bg\x01":
                return False
            redir = struct.unpack("<Q", f.read(8))[0]
            if redir == 23:
                f.seek(redir + 9)
                real_idx = struct.unpack("<Q", f.read(8))[0]
            else:
                real_idx = redir
            f.seek(real_idx)
            f.read(1)  # flag
            csz, _usz = struct.unpack("<QQ", f.read(16))
            decomp = zlib.decompress(f.read(csz))

            sen_sz = struct.unpack("<Q", decomp[4:12])[0]
            sen_body = decomp[12 : 12 + sen_sz]
            hnfn_off = struct.unpack("<Q", sen_body[:8])[0]
            _hnfn_u, hnfn_c = struct.unpack("<II", sen_body[8:16])
            f.seek(hnfn_off)
            hnfn_decomp = zlib.decompress(f.read(hnfn_c))

            hash_to_name: dict[int, str] = {}
            pos = 0
            while pos < len(hnfn_decomp):
                if hnfn_decomp[pos : pos + 4] == b"hnfn":
                    cz = struct.unpack("<Q", hnfn_decomp[pos + 4 : pos + 12])[0]
                    cb = hnfn_decomp[pos + 12 : pos + 12 + cz]
                    pos += 12 + cz
                    rpos = 0
                    while rpos + 6 <= len(cb):
                        fhash = struct.unpack("<I", cb[rpos : rpos + 4])[0]
                        nlen = struct.unpack("<H", cb[rpos + 4 : rpos + 6])[0]
                        if rpos + 6 + nlen * 2 <= len(cb):
                            name = cb[rpos + 6 : rpos + 6 + nlen * 2].decode("utf-16le", errors="replace")
                            hash_to_name[fhash] = name
                            rpos += 6 + nlen * 2
                        else:
                            break
                else:
                    pos += 1

            scn_entries: list[tuple[str, int, int, int]] = []
            pos = 12 + sen_sz
            while pos < len(decomp):
                ct = decomp[pos : pos + 4]
                cz = struct.unpack("<Q", decomp[pos + 4 : pos + 12])[0]
                cb = decomp[pos + 12 : pos + 12 + cz]
                pos += 12 + cz
                if ct == b"File":
                    spos = 0
                    adlr, sflags, soff, sarc = 0, 0, 0, 0
                    while spos < len(cb):
                        st = cb[spos : spos + 4]
                        sz = struct.unpack("<Q", cb[spos + 4 : spos + 12])[0]
                        sd = cb[spos + 12 : spos + 12 + sz]
                        spos += 12 + sz
                        if st == b"adlr":
                            adlr = struct.unpack("<I", sd[:4])[0]
                        elif st == b"segm":
                            sflags, soff, _sorig, sarc = struct.unpack("<IQQQ", sd[:28])
                    name = hash_to_name.get(adlr, "")
                    if name.endswith(".scn"):
                        scn_entries.append((name, sflags, soff, sarc))

            scn_entries.sort(key=lambda x: x[0])
            for _name, sflags, soff, sarc in scn_entries[:sample_limit]:
                f.seek(soff)
                raw = f.read(sarc)
                if sflags == 1:
                    raw = zlib.decompress(raw)
                for s in _decrypt_psb_strings_quick(raw):
                    for ch in s:
                        cp = ord(ch)
                        if (0x0E01 <= cp <= 0x0E5B) or (0xF700 <= cp <= 0xF71F):
                            return True
        return False
    except Exception:
        return False
