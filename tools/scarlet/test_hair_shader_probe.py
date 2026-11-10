#!/usr/bin/env python3
"""Compile the real Maxwell translator in an isolated harness and test material-3 gating.

Run with Python from any directory. Requires a C compiler on PATH (MSYS2 clang/gcc on Windows).
No game assets, AOT, Vulkan or network access are required.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "runtime/nvn/maxwell/translate.c"
int main(int argc, char **argv) {
    int mode = atoi(argv[1]);
    int incompatible = atoi(argv[2]);
    ShaderKey key = {0};
    key.glsl = 1;
    key.scarlet_hair_mode = (uint8_t)mode;
    Ctx *c = calloc(1, sizeof *c);
    c->glsl = 1;
    c->key = &key;
    c->stage = STAGE_FRAGMENT;
    c->info = calloc(1, sizeof *c->info);
    c->ipa_mode = -1;
    c->omap_target = 15;
    c->reg_used[47] = 1;
    if (mode == 3) {
        c->uses_rscale = true;
        c->info->ntex = 5;
        c->info->tex[4].type = TEXTYPE_2D;
    }
    sp(&c->body, "    r47 = 24u;\n");
    unsigned long long w = 0x3800000000000000ull |
        (0x303ull << 20) | (7ull << 16) |
        ((unsigned long long)(incompatible ? 46 : 47) << 8) | 62ull;
    emit_insn(c, w, 8);
    ShaderInfo *s = glsl_finish(c, false, false);
    if (!s || !s->msl) return 3;
    puts(s->msl);
    maxwell_free(s);
    return 0;
}
"""

class MaterialMask(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc = os.environ.get("CC") or shutil.which("clang") or shutil.which("gcc")
        if not cc:
            raise unittest.SkipTest("Requires clang or gcc (MSYS2 UCRT64 on Windows)")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        src = Path(cls.tmp.name) / "hair_probe.c"
        src.write_text(HARNESS, encoding="utf-8")
        cls.exe = Path(cls.tmp.name) / ("hair_probe.exe" if os.name == "nt" else "hair_probe")
        p = subprocess.run([cc, "-O0", "-std=gnu11", "-I", str(ROOT),
                            str(src), "-lm", "-o", str(cls.exe)],
                           text=True, capture_output=True)
        if p.returncode:
            raise AssertionError("Translator harness compilation failed:\n" + p.stderr)

    def shader(self, mode, incompatible=False):
        p = subprocess.run([str(self.exe), str(mode), "1" if incompatible else "0"],
                           text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout, p.stderr

    def test_baseline_unchanged(self):
        out, _ = self.shader(0)
        self.assertNotIn("scarlet_hair", out)

    def test_mask_only_on_exact_bfe(self):
        source, log = self.shader(1)
        self.assertIn("if (r62 == 3u)", source)
        self.assertIn("if (scarlet_hair) c0.rgb = vec3(1.0, 0.0, 1.0)", source)
        self.assertIn("extractor found", log)
        other, log = self.shader(1, incompatible=True)
        self.assertNotIn("if (r62 == 3u)", other)
        self.assertIn("NOT FOUND", log)

    def test_albedo_chroma_mode_is_only_material_three(self):
        shader, _ = self.shader(3)
        self.assertIn("if (scarlet_hair) {", shader)
        self.assertIn("texelFetch(t4,", shader)
        self.assertIn("c0.rgb = hb * clamp(ll / lb, 0.25, 2.0);", shader)
        incompatible, _ = self.shader(3, incompatible=True)
        self.assertNotIn("texelFetch(t4,", incompatible)

    def test_isotropic_only_material_three(self):
        source, _ = self.shader(2)
        self.assertIn("if (r62 == 3u)", source)
        self.assertIn("r62 = 0u; r6 = 0u; r7 = 0u; r32 = 0u;", source)
        self.assertNotIn("c0.rgb = vec3(1.0, 0.0, 1.0)", source)

if __name__ == "__main__":
    unittest.main()
