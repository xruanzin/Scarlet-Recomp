"""Read-only address/reference evidence for the Scarlet timing candidate table."""
import json
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nso import Nso
import capstone

n = Nso(sys.argv[1])
assert n.build_id == '421c5411b487eb4d049dd065fec9547773e8e598'
cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
def asm(a, length):
    return [f'{i.address:08x}: {i.mnemonic} {i.op_str}' for i in cs.disasm(bytes(n.image[a:a+length]), a)]
relocs = {off:add for off,typ,sym,add in n.relocs if typ == 1027}
slot = 0x46d8bc0  # derived by disassembling the scanned Scarlet candidate
table = relocs.get(slot, n.u64(slot))
out = {'slot':hex(slot), 'table':hex(table), 'words':[], 'references':[]}
if table < len(n.image)-128:
    out['words'] = [n.u64(table+i*8) for i in range(16)]
lo, size = n.text
for off in range(lo,lo+size-24,4):
    w = n.u32(off)
    if w & 0x9f000000 != 0x90000000:
        continue
    imm = ((w>>29)&3) | (((w>>5)&0x7ffff)<<2)
    if imm & 0x100000: imm -= 0x200000
    page = (off & ~4095) + (imm << 12)
    if page in {slot & ~4095, table & ~4095, 0x4440000}:
        out['references'].append(asm(off, 24))
print(json.dumps(out,indent=2))
