"""Guard tests for native Lua load interception without any copyrighted NSO."""
import struct
import unittest
from types import SimpleNamespace

from lua_camera_native import (
    SCARLET_MAIN_BUILD, LOAD_SITE, LUA_LOADBUFFERX, RUN_SITE, LUA_PCALLK,
    bl_target, patches
)


def bl(src, dest):
    delta = dest - src
    assert delta % 4 == 0
    return 0x94000000 | ((delta // 4) & 0x03ffffff)


def module():
    data = bytearray(RUN_SITE + 4096)
    struct.pack_into('<I', data, LOAD_SITE, bl(LOAD_SITE, LUA_LOADBUFFERX))
    struct.pack_into('<I', data, RUN_SITE, bl(RUN_SITE, LUA_PCALLK))
    base = 0x7000000000
    return SimpleNamespace(
        base=base, lo=base, hi=base+len(data),
        nso=SimpleNamespace(image=data, build_id=SCARLET_MAIN_BUILD),
    )


class LuaCameraHookGuards(unittest.TestCase):
    def test_bl_sign_extension(self):
        self.assertEqual(bl_target(bl(0xE37F70, 0xE382A0), 0xE37F70), 0xE382A0)
        self.assertIsNone(bl_target(0xd65f03c0, 0xE37F70))

    def test_exact_two_calls_emit_hook(self):
        m = module()
        found = patches(m)
        self.assertEqual(list(found), [m.base + LOAD_SITE])
        output = found[m.base + LOAD_SITE](m, m.base + LOAD_SITE)
        self.assertIn('scarlet_lua_camera_before_load(c)', output)
        self.assertIn('rt_dispatch(c)', output)
        self.assertIn(f'0x{m.base + LUA_LOADBUFFERX:x}ull', output)
        self.assertIn(f'0x{m.base + LOAD_SITE + 4:x}ull', output)

    def test_other_build_rejected(self):
        m = module()
        m.nso.build_id = 'a' * 40
        with self.assertRaisesRegex(ValueError, 'exact 4.0.0'):
            patches(m)

    def test_wrong_loader_call_rejected(self):
        m = module()
        struct.pack_into('<I', m.nso.image, LOAD_SITE, bl(LOAD_SITE, LUA_PCALLK))
        with self.assertRaisesRegex(ValueError, 'load call mismatched'):
            patches(m)

    def test_wrong_main_run_call_rejected(self):
        m = module()
        struct.pack_into('<I', m.nso.image, RUN_SITE, 0xd503201f)
        with self.assertRaisesRegex(ValueError, 'load call mismatched'):
            patches(m)


if __name__ == '__main__':
    unittest.main()
