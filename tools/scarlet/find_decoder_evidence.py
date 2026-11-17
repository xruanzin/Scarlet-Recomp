"""Find Scarlet decoder/parser names and ADRP+ADD references, without borrowed offsets."""
import argparse
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nso import Nso
from analyze import eh_frame_functions
import bisect

ap=argparse.ArgumentParser()
ap.add_argument('main')
ap.add_argument('--needle', action='append', help='Only investigate these exact strings')
a=ap.parse_args()
n=Nso(a.main)
assert n.build_id=='421c5411b487eb4d049dd065fec9547773e8e598'
starts=sorted(eh_frame_functions(n))
targets={}
needles = [s.encode() for s in a.needle] if a.needle else (b'OodleLZ_Decompress',b'attempt to load a %s chunk',b'Lua 5.4',b'not enough memory',b'main.blua',b'f8F2B0552',b'f750133BA',b'fC98FCA27')
for needle in needles:
    at=0
    while True:
        at=n.image.find(needle,at)
        if at<0:break
        targets[at]=needle.decode()
        print('STRING',hex(at),repr(n.cstr(at)))
        at+=len(needle)
for off,typ,sym,add in n.relocs:
    if add in targets:
        print('STRING_RELOC',hex(off),typ,hex(add),targets[add])
        for oo,tt,ss,aa in n.relocs:
            if off-32<=oo<off+40: print('NEAR_RELOC',hex(oo),tt,hex(aa))
for name,info,shndx,value,size in n.syms:
    if 'lua' in name.lower() or 'oodle' in name.lower(): print('SYMBOL',name,hex(value),size)
lo,size=n.text
w=struct.unpack_from(f'<{size//4}I',n.image,lo)
for i,v in enumerate(w):
    if v&0x9f000000 != 0x90000000:continue
    rd=v&31
    imm=((v>>29)&3)|(((v>>5)&0x7ffff)<<2)
    if imm&(1<<20):imm-=1<<21
    page=((lo+i*4)&~4095)+(imm<<12)
    if not any(t&~4095==page for t in targets):continue
    for j in range(i+1,min(i+8,len(w))):
        x=w[j]
        if x&0xffc00000==0x91000000 and (x>>5)&31==rd:
            addr=page+((x>>10)&0xfff)
            if addr in targets:
                pc=lo+j*4
                k=bisect.bisect_right(starts,pc)-1
                print('REF',hex(pc),'function',hex(starts[k]) if k>=0 else '?',repr(targets[addr]))
