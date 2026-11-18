#!/usr/bin/env python3
"""Unit tests: synthetic headers only, never game assets."""
import struct
import tempfile
import unittest
from pathlib import Path

from preflight import KNOWN_MAIN_PREFIXES, exefs_info, inspect, nsp_info, nso_build_id


def write_exefs(root, version):
    folder = root / "exefs"
    folder.mkdir(parents=True, exist_ok=True)
    def nso(prefix):
        hdr = bytearray(0x60)
        hdr[:4] = b"NSO0"
        hdr[0x40:0x48] = bytes.fromhex(prefix)
        return hdr
    (folder / "main").write_bytes(nso(KNOWN_MAIN_PREFIXES[version]))
    (folder / "sdk").write_bytes(nso("0123456789abcdef"))
    (folder / "main.npdm").write_bytes(b"test")
    return folder


def write_nsp(path, filename="example.nca"):
    names = filename.encode() + b"\0"
    payload = b"ABCD"
    with path.open("wb") as f:
        f.write(struct.pack("<4sIII", b"PFS0", 1, len(names), 0))
        f.write(struct.pack("<QQII", 0, len(payload), 0, 0))
        f.write(names)
        f.write(payload)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_recognizes_4_0_0_exefs(self):
        base = self.root / "game"
        write_exefs(base, "4.0.0")
        result = inspect(base)
        self.assertTrue(result["ready_for_aot"])
        self.assertEqual(result["base"]["recognized_version"], "4.0.0")

    def test_rejects_base_1_0_0_even_with_nsp(self):
        base = self.root / "base"
        write_exefs(base, "1.0.0")
        nsp = self.root / "Pokemon Scarlet v4.0.0.nsp"
        write_nsp(nsp)
        result = inspect(base, update_nsp=nsp)
        self.assertFalse(result["ready_for_aot"])
        self.assertEqual(result["update_nsp"]["nca_count"], 1)
        self.assertFalse(result["update_nsp"]["version_verified"])

    def test_selects_decrypted_update_exefs(self):
        base, updated = self.root / "base", self.root / "update"
        write_exefs(base, "1.0.0")
        update_dir = write_exefs(updated, "4.0.0")
        result = inspect(base, update_exefs=updated)
        self.assertTrue(result["ready_for_aot"])
        self.assertEqual(result["selected_exefs"], str(update_dir.resolve()))

    def test_wrong_update_not_accepted(self):
        base, updated = self.root / "base", self.root / "update"
        write_exefs(base, "1.0.0")
        write_exefs(updated, "1.0.0")
        self.assertFalse(inspect(base, update_exefs=updated)["ready_for_aot"])

    def test_invalid_nso(self):
        file = self.root / "main"
        file.write_bytes(b"not an NSO")
        with self.assertRaises(ValueError):
            nso_build_id(file)

    def test_missing_sdk(self):
        folder = write_exefs(self.root / "base", "4.0.0")
        (folder / "sdk").unlink()
        with self.assertRaisesRegex(ValueError, "sdk"):
            exefs_info(folder)

    def test_truncated_pfs0(self):
        file = self.root / "bad.nsp"
        file.write_bytes(struct.pack("<4sIII", b"PFS0", 1, 500, 0))
        with self.assertRaises(ValueError):
            nsp_info(file)

    def test_bad_nsp_filename_index(self):
        file = self.root / "bad_index.nsp"
        file.write_bytes(struct.pack("<4sIII", b"PFS0", 1, 2, 0)
                         + struct.pack("<QQII", 0, 1, 2, 0) + b"x\0" + b"X")
        with self.assertRaises(ValueError):
            nsp_info(file)


if __name__ == "__main__":
    unittest.main()
