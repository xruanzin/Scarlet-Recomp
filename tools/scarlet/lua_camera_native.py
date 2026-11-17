"""Identity-guarded Scarlet Lua script-load injection.

Modeled after KarPur's Lua load interception, but uses a private script copy,
not a mod or on-disk data replacement. The C runtime hashes the complete
decompressed main.blua before patching one identified controller step.

The known candidate offsets came from Violet 4.0.0. They are NOT assumed
compatible: both BL instructions must resolve to precisely the expected
local functions in the user's *Scarlet* main NSO, or generation stops.
"""

from __future__ import annotations
import struct

SCARLET_MAIN_BUILD = "421c5411b487eb4d049dd065fec9547773e8e598"

# Call to luaL_loadbufferx for the main Haxe-compiled Lua chunk.
LOAD_SITE = 0xE37F70
LUA_LOADBUFFERX = 0xE382A0
# The subsequent run checks that we are in the main-script loader,
# not one of the game's many other Lua chunk loads.
RUN_SITE = 0xE37F94
LUA_PCALLK = 0xB5DDD0


def bl_target(word: int, site: int) -> int | None:
    if (word & 0xFC000000) != 0x94000000:
        return None
    disp = word & 0x03FFFFFF
    if disp & 0x02000000:
        disp -= 0x04000000
    return site + disp * 4


def patches(module):
    if module.nso.build_id != SCARLET_MAIN_BUILD:
        raise ValueError("Scarlet camera Lua hook requires the exact 4.0.0 main NSO")
    info = (
        (LOAD_SITE, LUA_LOADBUFFERX),
        (RUN_SITE, LUA_PCALLK),
    )
    for site, target in info:
        if module.base + site < module.lo or module.base + site >= module.hi:
            raise ValueError(f"Scarlet Lua call {site:#x} outside code")
        actual = struct.unpack_from("<I", module.nso.image, site)[0]
        got = bl_target(actual, site)
        if got != target:
            raise ValueError(
                f"Scarlet Lua load call mismatched at {site:#x}: "
                f"expected BL {target:#x}, got {actual:#010x} / {got!r}; "
                "leave gameplay unmodified, inspect Scarlet call sites first"
            )

    def inject(module, address):
        # Use the same rt_dispatch sequence as tools/gen.py's BL handling;
        # a patched instruction does not emit normal direct-call references.
        guest_load = module.base + LUA_LOADBUFFERX
        guest_return = address + 4
        return (
            "{ extern void scarlet_lua_camera_before_load(Cpu *); "
            "scarlet_lua_camera_before_load(c); "
            f"c->x[30] = 0x{guest_return:x}ull; "
            f"c->pc = 0x{guest_load:x}ull; rt_dispatch(c); }}"
        )

    return {module.base + LOAD_SITE: inject}
