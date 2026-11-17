"""Focused Scarlet disassembly for temporal storage and consumers; read-only."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nso import Nso
import capstone

p = argparse.ArgumentParser()
p.add_argument('main')
p.add_argument('ranges', nargs='*', help='hex offset:hex length')
a = p.parse_args()
n = Nso(a.main)
assert n.build_id == '421c5411b487eb4d049dd065fec9547773e8e598'
cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
for spec in a.ranges:
    offset, length = (int(x,16) for x in spec.split(':'))
    print(f'\nRANGE {offset:x}:{length:x}')
    for i in cs.disasm(bytes(n.image[offset:offset+length]), offset):
        print(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic} {i.op_str}')
print('\nTIMING VTABLE RELOCATIONS')
for off,typ,sym,add in n.relocs:
    if 0x4440120 <= off < 0x44401f0:
        print(f'{off:x} type={typ} target={add:x}')
