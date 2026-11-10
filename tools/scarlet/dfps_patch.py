"""Opt-in import of the original Scarlet 4.0.0 Dynamic FPS ASM patch.

The player supplies the .pchtxt. No mod code or game files are distributed.
Writes only to the decompressed NSO image in memory during AOT generation.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

MAIN_BUILD_ID = "421C5411B487EB4D049DD065FEC9547773E8E598"
PATCH_ENTRIES = 153
PATCH_FNV64 = 0x005C31864D041832
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3


class PatchError(ValueError):
    pass


def parse_patch(content: str) -> list[tuple[int, bytes]]:
    """Reject patches different from the reviewed Scarlet 4.0.0 ASM variant."""
    build = None
    shift = None
    enabled = False
    stopped = False
    entries = []
    seen = set()
    digest = FNV_OFFSET
    for lineno, raw in enumerate(content.splitlines(), 1):
        s = raw.split("//", 1)[0].strip()
        if not s or s.startswith("#") or s.startswith("@Fl4sh_") or s.startswith("https:"):
            continue
        if s.startswith("@nsobid-"):
            if build is not None:
                raise PatchError("duplicate build ID")
            build = s.partition("-")[2].upper()
        elif s == "@flag print_values":
            pass
        elif s.startswith("@flag offset_shift"):
            if shift is not None:
                raise PatchError("duplicate offset shift")
            shift = s.removeprefix("@flag offset_shift").strip()
        elif s == "@enabled" and not enabled and not stopped:
            enabled = True
        elif s == "@stop" and enabled and not stopped:
            stopped = True
            enabled = False
        elif re.fullmatch(r"[0-9A-Fa-f]{8}\s+[0-9A-Fa-f]{8}(?:[0-9A-Fa-f]{8})?", s):
            if not enabled or stopped:
                raise PatchError(f"line {lineno}: data outside enabled block")
            address, hexdata = s.split()
            off, payload = int(address, 16), bytes.fromhex(hexdata)
            if off % 4 or off in seen:
                raise PatchError(f"line {lineno}: unaligned or duplicate patch offset")
            seen.add(off)
            entries.append((off, payload))
            for b in off.to_bytes(4, "little") + bytes((len(payload),)) + payload:
                digest = (digest ^ b) * FNV_PRIME & 0xFFFFFFFFFFFFFFFF
        else:
            raise PatchError(f"line {lineno}: unsupported patch directive or payload")
    if build != MAIN_BUILD_ID or shift != "0x100" or not stopped:
        raise PatchError("not the expected Scarlet v4.0.0 ASM patch")
    if len(entries) != PATCH_ENTRIES or digest != PATCH_FNV64:
        raise PatchError("patch differs from reviewed Dynamic FPS ASM payload")
    return entries


def load_patch(path: str | Path) -> list[tuple[int, bytes]]:
    p = Path(path)
    if not p.is_file() or p.stat().st_size > 64 * 1024:
        raise PatchError("missing or oversized Dynamic FPS patch file")
    return parse_patch(p.read_text(encoding="utf-8-sig"))


def apply_nso(nso, path: str | Path) -> int:
    if nso.build_id.upper() != MAIN_BUILD_ID:
        raise PatchError("Dynamic FPS requires Scarlet 4.0.0 main build " + MAIN_BUILD_ID)
    patches = load_patch(path)
    spans = [nso.text, nso.rodata, nso.data]
    spans.append((nso.data[0] + nso.data[1], nso.bss_size))
    # Validate every address before writing anything.
    for off, payload in patches:
        if off + len(payload) > len(nso.image) or not any(
            lo <= off and off + len(payload) <= lo + size for lo, size in spans
        ):
            raise PatchError(f"patch offset 0x{off:08x} outside NSO segments/BSS")
    for off, payload in patches:
        nso.image[off:off + len(payload)] = payload
    return len(patches)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify user-supplied Scarlet Dynamic FPS ASM .pchtxt")
    ap.add_argument("patch", type=Path)
    args = ap.parse_args()
    try:
        patches = load_patch(args.patch)
    except (OSError, UnicodeError, PatchError) as exc:
        ap.error(str(exc))
    print(f"Validated {len(patches)} Scarlet 4.0.0 Dynamic FPS patch entries; no game files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
