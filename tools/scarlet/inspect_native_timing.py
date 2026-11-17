"""Find timing thunk candidates in Scarlet without borrowing Violet addresses.

This emits evidence only; a matching instruction is not semantic validation.
"""
import argparse
import json
import struct
import sys
import hashlib
import capstone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nso import Nso

ap = argparse.ArgumentParser()
ap.add_argument('main')
args = ap.parse_args()
n = Nso(args.main)
if not n.build_id.upper().startswith('421C5411B487EB4D'):
    sys.exit('Expected Scarlet 4.0.0 main')
lo, size = n.text[:2]
words = struct.unpack_from(f'<{size // 4}I', n.image, lo)
hits = []
cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
def disasm(start, length):
    return [f'{i.address:08x}: {i.mnemonic} {i.op_str}'
            for i in cs.disasm(bytes(n.image[start:start+length]), start)]
for i in range(len(words) - 2):
    # Object vtable load, slot 2 load, tail dispatch. No assumed address.
    if words[i:i+3] == (0xf9400008, 0xf9400903, 0xd61f0060):
        hits.append({'offset': hex(lo + i*4),
                     'context': [hex(w) for w in words[max(0,i-8):i+8]]})
for hit in hits:
    site = int(hit['offset'], 16)
    # Include every direct branch to the preceding eight instructions, without
    # guessing a function boundary from a pattern match.
    targets = set(range(site-32, site+4, 4))
    callers = []
    for i, w in enumerate(words):
        if w & 0x7c000000 != 0x14000000:
            continue
        imm = w & 0x3ffffff
        if imm & 0x2000000:
            imm -= 0x4000000
        pc = lo + 4*i
        target = pc + 4*imm
        if target in targets:
            callers.append({'site': hex(pc), 'target': hex(target),
                            'assembly': disasm(max(lo,pc-48), 64)})
    hit['assembly'] = disasm(site-32, 80)
    hit['direct_callers'] = callers
    hit['relocations'] = [{'slot':hex(off), 'target':hex(add)}
                          for off,typ,sym,add in n.relocs if typ == 1027 and add in targets]
print(json.dumps({'build_id': n.build_id, 'candidates': hits,
                  'sha256': hashlib.sha256(Path(args.main).read_bytes()).hexdigest(),
                  'status': 'candidates only; caller and runtime validation required'}, indent=2))
