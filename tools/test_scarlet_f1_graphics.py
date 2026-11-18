"""Source regression checks for the isolated Scarlet F1 graphics workstream.

These checks cover menu wiring and invariant guards only. They do not replace
compiling the Vulkan backend or testing Scarlet 4.0.0 in game.
Run: python tools/test_scarlet_f1_graphics.py
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def src(name):
    return (ROOT / name).read_text(encoding="utf-8")


class ScarletF1GraphicsChecks(unittest.TestCase):
    def test_resolution_modes_are_persistent(self):
        settings = src("runtime/settings.c")
        header = src("runtime/settings.h")
        for enum, key in (("RES_720P", "720p"), ("RES_1440P", "1440p")):
            self.assertIn(enum, header)
            self.assertIn('return "' + key + '"', settings)
            self.assertIn('!strcmp(val, "' + key + '")', settings)

    def test_resolution_modes_have_exact_scales(self):
        scale = src("runtime/nvn/output_scale.c")
        self.assertIn("mode == RES_720P", scale)
        self.assertIn("720.0 / 1080.0", scale)
        self.assertIn("mode == RES_1440P", scale)
        self.assertIn("1440.0 / 1080.0", scale)

    def test_f1_controls_are_wired(self):
        menu = src("runtime/ui/menu.mm")
        self.assertIn("RES_720P, RES_Q25", menu)
        self.assertIn("RES_X15, RES_1440P, 2, 3, 4", menu)
        self.assertIn('TR("Sun shadow map"', menu)
        self.assertIn('TR("Shadow sharpness"', menu)

    def test_shadow_scaling_is_guarded_for_scarlet(self):
        tex = src("runtime/nvn/vulkan/textures.c")
        self.assertIn("g_program_id == UINT64_C(0x0100a3d008c5c000)", tex)
        self.assertIn("t->width != 2048", tex)
        self.assertIn("!renderer_format_is_depth(t->format)", tex)
        self.assertIn("scarlet && k > 2 ? 2 : k", tex)
        self.assertIn("(scarlet ? 4096u : 8192u)", tex)


if __name__ == "__main__":
    unittest.main()
