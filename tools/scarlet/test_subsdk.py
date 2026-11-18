#!/usr/bin/env python3
"""Synthetic tests for extending an existing Scarlet AOT cache; no game content."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import extend_subsdk0
import link_probe
from preflight import KNOWN_MAIN_PREFIXES


def nso(prefix):
    b = bytearray(0x60)
    b[:4] = b"NSO0"
    b[0x40:0x48] = bytes.fromhex(prefix)
    return bytes(b)


class ExistingAotCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch_root = patch.object(extend_subsdk0, "ROOT", self.root)
        self.patch_root.start()
        self.patch_link_root = patch.object(link_probe, "ROOT", self.root)
        self.patch_link_root.start()
        self.exefs = self.root / "exefs"
        self.exefs.mkdir()
        self.main_id = KNOWN_MAIN_PREFIXES["4.0.0"] + ("00" * 24)
        (self.exefs / "main").write_bytes(nso(KNOWN_MAIN_PREFIXES["4.0.0"]))
        (self.exefs / "sdk").write_bytes(nso("0123456789abcdef"))
        (self.exefs / "subsdk0").write_bytes(nso("1122334455667788"))
        (self.exefs / "main.npdm").write_bytes(b"NPDM")
        self.cache_id = "0123456789abcdef"
        self.g = self.root / "generated-scarlet" / self.cache_id
        self.b = self.root / "build" / "scarlet" / self.cache_id
        (self.g / "main").mkdir(parents=True)
        (self.b / "obj" / "main").mkdir(parents=True)
        (self.b / "obj" / "sdk").mkdir(parents=True)
        (self.g / "main" / "main_build_id.txt").write_text(self.main_id.upper() + "\n")
        (self.b / "obj" / "main" / "main_table.o").write_bytes(b"synthetic")
        (self.b / "obj" / "sdk" / "sdk_table.o").write_bytes(b"synthetic")
        (self.b / "aot-complete.json").write_text(json.dumps({
            "game": "Pokemon Scarlet", "version": "4.0.0",
            "main_build_id": self.main_id,
        }))

    def tearDown(self):
        self.patch_link_root.stop()
        self.patch_root.stop()
        self.tmp.cleanup()

    def test_check_only_accepts_completed_main_sdk_cache(self):
        self.assertEqual(extend_subsdk0.main([
            "--exefs", str(self.exefs),
            "--cache-id", self.cache_id,
            "--check-only",
        ]), 0)
        self.assertFalse((self.b / "subsdk0-complete.json").exists())

    def test_rejects_different_cached_game_version(self):
        cache = json.loads((self.b / "aot-complete.json").read_text())
        cache["main_build_id"] = "00" * 32
        (self.b / "aot-complete.json").write_text(json.dumps(cache))
        self.assertEqual(extend_subsdk0.main([
            "--exefs", str(self.exefs), "--cache-id", self.cache_id, "--check-only",
        ]), 1)

    def test_rejects_missing_subsdk0(self):
        (self.exefs / "subsdk0").unlink()
        self.assertEqual(extend_subsdk0.main([
            "--exefs", str(self.exefs), "--cache-id", self.cache_id, "--check-only",
        ]), 1)

    def test_link_probe_requires_subsdk_completion(self):
        self.assertEqual(link_probe.main([
            "--exefs", str(self.exefs), "--cache-id", self.cache_id, "--check-only",
        ]), 1)

    def test_link_probe_accepts_completed_subsdk_cache_without_building(self):
        sub_id = "1122334455667788" + ("00" * 24)
        (self.b / "subsdk0-complete.json").write_text(json.dumps({
            "cache_id": self.cache_id, "main_build_id": self.main_id,
            "subsdk0_build_id": sub_id,
        }))
        (self.b / "obj" / "subsdk0").mkdir(parents=True)
        (self.b / "obj" / "subsdk0" / "subsdk0_table.o").write_bytes(b"synthetic")
        (self.b / "obj" / "tools").mkdir(parents=True)
        (self.b / "obj" / "tools" / "gamelib_entry.o").write_bytes(b"synthetic")
        self.assertEqual(link_probe.main([
            "--exefs", str(self.exefs), "--cache-id", self.cache_id, "--check-only",
        ]), 0)

    def test_rejects_invalid_cache_id(self):
        with self.assertRaisesRegex(ValueError, "16 lower-case"):
            extend_subsdk0.existing_cache("../wrong", self.main_id)


if __name__ == "__main__":
    unittest.main()
