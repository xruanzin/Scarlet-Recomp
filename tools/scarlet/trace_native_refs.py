"""Read-only direct branch and address-reference evidence for exact Scarlet NSO."""
import argparse,bisect,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nso import Nso
from analyze import eh_frame_functions
ap=argparse.ArgumentParser();ap.add_argument('main');ap.add_argument('targets',nargs='+')
a=ap.parse_args();n=Nso(a.main)
assert n.build_id=='421c5411b487eb4d049dd065fec9547773e8e598'
targets={int(s,16) for s in a.targets}; starts=sorted(eh_frame_functions(n))
def emit(pc,kind,target):
    k=bisect.bisect_right(starts,pc)-1
    print(kind,hex(pc),'target',hex(target),'function',hex(starts[k]) if k>=0 else '?')
for off,typ,sym,add in n.relocs:
    if add in targets: emit(off,'RELOC',add)
lo,size=n.text;words=struct.unpack_from(f'<{size//4}I',n.image,lo)
for i,w in enumerate(words):
    pc=lo+i*4
    if w&0x7c000000==0x14000000:
        imm=w&0x3ffffff
        if imm&(1<<25):imm-=1<<26
        target=pc+imm*4
        if target in targets:emit(pc,'BL' if w&0x80000000 else 'B',target)
    if w&0x9f000000==0x90000000:
        rd=w&31;imm=((w>>29)&3)|(((w>>5)&0x7ffff)<<2)
        if imm&(1<<20):imm-=1<<21
        page=(pc&~4095)+(imm<<12)
        if not any(t&~4095==page for t in targets):continue
        for j in range(i+1,min(i+10,len(words))):
            x=words[j]
            if x&0xffc00000==0x91000000 and (x>>5)&31==rd:
                addr=page+((x>>10)&0xfff)
                if addr in targets:emit(lo+j*4,'ADRP_ADD',addr)
