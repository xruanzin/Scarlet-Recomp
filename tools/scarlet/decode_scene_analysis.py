"""Bounded offline descriptor inspection; no runtime integration or data patches.

Reports exact ASCII class names and candidate binary identifiers separately.
Without a descriptor schema, proximity and binary matches are not semantic proof.
"""
import argparse
import ctypes
import hashlib
import json
import re
from pathlib import Path

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('manifest',type=Path)
ap.add_argument('decoder',type=Path)
a=ap.parse_args()
records=json.loads(a.manifest.read_text(encoding='utf-8-sig'))
budget=128*1024*1024
total=sum(r['packed'] if r['compression']==-1 else r['unpacked'] for r in records)
if total>budget: raise ValueError('Decoded analysis exceeds128MiB budget')
dll=ctypes.CDLL(str(a.decoder.resolve()))
dll.ooz_decompress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
dll.ooz_decompress.restype=ctypes.c_int
names=['CEAB931B40E0610B8','C26DB1063E23DD14B','CD00CF28AF6D6C9ED','C51C789C764D66E76']
reports=[]
for r in records:
    p=Path(r['path'])
    if p.resolve().parent!=a.manifest.resolve().parent: raise ValueError('Input escapes analysis directory')
    raw=p.read_bytes()
    if len(raw)!=r['packed'] or hashlib.sha256(raw).hexdigest()!=r['sha256']: raise ValueError('Packed identity mismatch')
    codec=r['compression']
    if codec==-1: data=raw; returned=len(raw)
    elif codec==3:
        size=r['unpacked']
        if not 0<size<=budget: raise ValueError('Invalid decoded length')
        src=ctypes.create_string_buffer(raw,len(raw)+64)
        dst=ctypes.create_string_buffer(size+64)
        returned=dll.ooz_decompress(src,len(raw),dst,size)
        if returned!=size: raise ValueError(f'{p}: decoder returned{returned},expected{size}')
        data=dst.raw[:size]
    else: raise ValueError(f'Unsupported codec{codec}')
    dest=p.with_suffix('.decoded')
    if dest.exists() and dest.read_bytes()!=data: raise ValueError('Different analysis output already exists')
    dest.write_bytes(data)
    hits=[]
    for name in names:
        for encoding,needle in [('ascii',name.encode()),('candidate-u64-le',int(name[1:],16).to_bytes(8,'little'))]:
            pos=0
            while (pos:=data.find(needle,pos))>=0:
                nearby=[s.decode('ascii') for s in re.findall(rb'[ -~]{5,}',data[max(0,pos-256):pos+512])]
                hits.append(dict(name=name,encoding=encoding,offset=pos,nearby=nearby)); pos+=len(needle)
    strings=[s.decode('ascii') for s in re.findall(rb'[ -~]{5,}',data)]
    relevant=[s for s in strings if re.search(r'camera|interior|house|room|\.trscn|\.trscr|\.lua',s,re.I)]
    reports.append(dict(pack=r['pack'],file=str(dest),packed_sha256=r['sha256'],decoded_sha256=hashlib.sha256(data).hexdigest(),bytes_returned=returned,codec=codec,hits=hits,context_strings=relevant))
out=a.manifest.parent/'descriptor-report.json'
out.write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(dict(members=len(reports),decoded_bytes=total,matched_files=sum(bool(r['hits']) for r in reports),report=str(out))))
