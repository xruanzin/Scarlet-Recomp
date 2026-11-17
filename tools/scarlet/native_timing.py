"""Scarlet 4.0.0 native clock supply and validated consumer observations.

Offsets were recovered by scanning the supplied Scarlet NSO and resolving its
relocations (build/native-timing-callers.json and native-timing-table.json).
Only the validated clock-1 producer supplies dynamic time. Consumer probes
preserve the original instructions and never override game-local time modes.
"""
import struct

BUILD = '421c5411b487eb4d049dd065fec9547773e8e598'
SITES = {0x92dd2c: 0xf001ed48, 0x2b7b314: 0xb000dae8,
         0x2b7b340: 0xb000dae8}

def patches(module):
    n = module.nso
    if n.build_id != BUILD:
        raise ValueError('Native timing requires exact Scarlet 4.0.0 build')
    if struct.unpack_from('<5Q', n.image, 0x3c2fba8) != (
            16666667, 33333334, 50000000, 66666667, 83333334):
        raise ValueError('Scarlet timing table differs')
    if not any(off == 0x46d8bc0 and typ == 1027 and add == 0x3c2fba8
               for off, typ, sym, add in n.relocs):
        raise ValueError('Scarlet timing table relocation differs')
    result = {}
    position = (0x910043e3, 0xaa1303e0, 0xaa1f03e2, 0x3d8007e2, 0x9400002d)
    if struct.unpack_from('<5I', n.image, 0xc92cd8) != position:
        raise ValueError('Scarlet position setter differs')
    getter_position = (0xd100a100, 0xd63f0020, 0x3d8003e0, 0x1e22c000,
                       0xaa1303e0, 0x97c745a7, 0x3dc003e0)
    if struct.unpack_from('<7I', n.image, 0x19756f0) != getter_position:
        raise ValueError('Scarlet position getter differs')
    required = {(0x44c2a78, 0xc92c30), (0x44c2a68, 0x1975680)}
    if not required.issubset({(off, add) for off, typ, sym, add in n.relocs if typ == 1027}):
        raise ValueError('Scarlet position setter registration differs')
    def position_probe(m, a):
        return ('{ extern void scarlet_position_observe(Cpu *, uint64_t); '
                'memcpy((void *)(uintptr_t)(c->sp + 16), &c->v[2], 16); '
                'scarlet_position_observe(c, 0xc92ce4ull); }')
    result[module.base + 0xc92ce4] = position_probe
    def position_read_probe(m, a):
        return ('{ extern void scarlet_position_observe(Cpu *, uint64_t); '
                'memcpy((void *)(uintptr_t)c->sp, &c->v[0], 16); '
                'scarlet_position_observe(c, 0x19756f8ull); }')
    result[module.base + 0x19756f8] = position_read_probe
    effective = (0x52911129, 0x72a7a109, 0x1e270120, 0x3944a288,
                 0x720002bf, 0x1e201d00, 0xf9401289, 0x7100011f,
                 0x1e280c08, 0xa9406128)
    if struct.unpack_from('<10I', n.image, 0xd07ab4) != effective:
        raise ValueError('Scarlet downstream time selection differs')
    def effective_probe(m, a):
        return ('{ extern void scarlet_timing_effective(Cpu *); '
                'scarlet_timing_effective(c); '
                'c->x[8] = LD64(c->x[9]); c->x[24] = LD64(c->x[9] + 8); }')
    result[module.base + 0xd07ad8] = effective_probe
    # Live getter caller 7000d07a4c consumes clock 1 as integer nanoseconds,
    # converts it to double, divides by 1e9, then passes float seconds onward.
    consumer = (0xfd400400, 0xd2d9aca8, 0xf2e839a8, 0x9e670101,
                0x5e61d800, 0x1e611800)
    if struct.unpack_from('<6I', n.image, 0xd07a4c) != consumer:
        raise ValueError('Scarlet clock-1 seconds consumer differs')
    if struct.unpack_from('<3I', n.image, 0x92dd14) != (0x8b21d008, 0x91002100, 0xd65f03c0):
        raise ValueError('Scarlet timing getter differs')
    def getter(m, a):
        return ('{ extern void scarlet_timing_read(Cpu *); '
                'c->x[0] = c->x[8] + 8; scarlet_timing_read(c); }')
    result[module.base + 0x92dd18] = getter
    for site, adrp in SITES.items():
        expected = (adrp, 0xf945e108, 0xf862d902,
                    0xf9400008, 0xf9400903, 0xd61f0060)
        if struct.unpack_from('<6I', n.image, site-12) != expected:
            raise ValueError(f'Scarlet timing thunk differs at {site:#x}')
        def emit(m, a, site=site):
            return ('{ extern void scarlet_timing_observe(Cpu *, uint64_t); '
                    f'scarlet_timing_observe(c, 0x{site:x}ull); '
                    'memcpy(&c->x[8], (const void *)(uintptr_t)c->x[0], 8); }')
        result[module.base + site] = emit
    return result
