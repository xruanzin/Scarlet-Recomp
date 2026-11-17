"""Validate FlatBuffers tables directly referencing identified camera strings.

Field numbers remain unnamed until a schema is recovered. This does not infer
types from proximity: every displayed string has a bounded uoffset and length.
"""
import argparse,json
from pathlib import Path
from inspect_script_archive import Table,value,bounded
ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('file',type=Path)
a=ap.parse_args(); data=a.file.read_bytes(); matches=[]
for p in range(0,len(data)-4,4):
    try:
        t=Table(data,p)
        if len(t.slots)>32 or not t.slots: continue
        strings=[]
        for i in range(len(t.slots)):
            f=t.field(i)
            if f is None: continue
            off=value(data,f,'I')
            if off<4: continue
            s=f+off
            try:
                n=value(data,s,'I')
                if n<5 or n>512: continue
                raw=bounded(data,s+4,n)
                if value(data,s+4+n,'B')!=0 or any(b<32 or b>126 for b in raw): continue
                strings.append(dict(slot=i,field=hex(f),target=hex(s),text=raw.decode()))
            except (ValueError,IndexError): pass
        if any('CD00CF28AF6D6C9ED' in s['text'] or 'InteriorCameraBehavior.hx' in s['text'] for s in strings):
            matches.append(dict(table=hex(p),slots=t.slots,strings=strings))
    except (ValueError,IndexError): pass
print(json.dumps(dict(file=str(a.file),root=hex(value(data,0,'I')),tables=matches),indent=2))
