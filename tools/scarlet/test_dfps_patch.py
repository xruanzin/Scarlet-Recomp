#!/usr/bin/env python3
"""Offline regression checks for the user-supplied Scarlet Dynamic FPS ASM mod ZIP."""
import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scarlet.dfps_patch import MAIN_BUILD_ID, PatchError, apply_nso, parse_patch


def run(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        candidates = [n for n in zf.namelist() if
                      n.endswith("[ASM] Final Release/exefs/3.0.1-4.0.0.pchtxt")]
        assert len(candidates) == 1, "Dynamic FPS ASM patch missing or ambiguous"
        source = zf.read(candidates[0]).decode("utf-8-sig")
    entries = parse_patch(source)
    assert len(entries) == 153
    assert entries[0][0] == 0x02B7A874
    for altered in (
        source.replace("21008052", "22008052", 1),
        source.replace(MAIN_BUILD_ID, "0" * len(MAIN_BUILD_ID), 1),
        source.replace("@flag offset_shift 0x100", "@flag offset_shift 0x200", 1),
    ):
        try:
            parse_patch(altered)
        except PatchError:
            pass
        else:
            raise AssertionError("Modified/incorrect patch unexpectedly accepted")

    # A synthetic NSO image tests byte placement and all-or-nothing validation.
    # It contains NO game code and is never written to disk.
    class FakeNso:
        build_id = MAIN_BUILD_ID
        text = (0, 0x4000000)
        rodata = (0x4000000, 0x380000)
        data = (0x4380000, 0x10000)
        bss_size = 0x1000
        image = bytearray(0x4391000)

    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        patch = Path(directory) / "dynamic.pchtxt"
        patch.write_text(source, encoding="utf-8")
        nso = FakeNso()
        assert apply_nso(nso, patch) == 153
        assert nso.image[0x02B7A874:0x02B7A878] == bytes.fromhex("21008052")
        assert nso.image[0x01760EC8:0x01760ECC] == bytes.fromhex("E007BFA9")
        bad = FakeNso()
        bad.image = bytearray(0x200000)
        before = bytes(bad.image[:128])
        try:
            apply_nso(bad, patch)
        except PatchError:
            assert bytes(bad.image[:128]) == before, "partial modification detected"
        else:
            raise AssertionError("Out-of-bounds patch unexpectedly accepted")
    print("PASS: 153 reviewed entries; rejection guards; atomic NSO-image patching.")
    print("NOTE: Synthetic tests cannot prove Scarlet AOT compilation, 60 FPS or battle stability.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mod_zip", type=Path, help="Original user-owned Fl4sh Scarlet mods ZIP")
    args = ap.parse_args()
    run(args.mod_zip)
