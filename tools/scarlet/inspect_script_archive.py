"""Inspect Scarlet script archive members without changing game data.

Trinity field layout reference: Grunttanamo/KarPur tools/trpfs.py (MIT).
All offsets/counts are checked against the containing mapped file/table.
Compressed members remain compressed; this tool never patches constants.
"""
import argparse
import hashlib
import json
import mmap
import re
import struct
from pathlib import Path

def value(buf, pos, fmt):
    size=struct.calcsize('<'+fmt)
    if pos < 0 or pos+size > len(buf): raise ValueError('Out-of-bounds scalar')
    return struct.unpack_from('<'+fmt,buf,pos)[0]

def bounded(buf,pos,size):
    if pos < 0 or size < 0 or pos+size > len(buf): raise ValueError('Out-of-bounds data')
    return buf[pos:pos+size]

class Table:
    def __init__(self,b,p):
        self.b,self.p=b,p
        vt=p-value(b,p,'i'); vs=value(b,vt,'H'); obj=value(b,vt+2,'H')
        if vs < 4 or vs%2: raise ValueError('Invalid vtable')
        bounded(b,p,obj); bounded(b,vt,vs)
        self.slots=[value(b,vt+4+i*2,'H') for i in range((vs-4)//2)]
        if any(s and (s<4 or s>=obj) for s in self.slots): raise ValueError('Invalid field')
    @classmethod
    def root(cls,b,p=0): return cls(b,p+value(b,p,'I'))
    def field(self,i): return self.p+self.slots[i] if i<len(self.slots) and self.slots[i] else None
    def scalar(self,i,fmt,default=0):
        p=self.field(i); return default if p is None else value(self.b,p,fmt)
    def vector(self,i,width):
        p=self.field(i)
        if p is None: return 0,0
        v=p+value(self.b,p,'I'); n=value(self.b,v,'I')
        bounded(self.b,v+4,n*width)
        return v+4,n
    def integers(self,i):
        p,n=self.vector(i,8); return [value(self.b,p+8*k,'Q') for k in range(n)]
    def tables(self,i):
        p,n=self.vector(i,4)
        return [Table(self.b,p+4*k+value(self.b,p+4*k,'I')) for k in range(n)]
    def strings(self,i):
        p,n=self.vector(i,4); result=[]
        for k in range(n):
            s=p+4*k+value(self.b,p+4*k,'I'); size=value(self.b,s,'I')
            result.append(bounded(self.b,s+4,size).decode('utf-8'))
        return result

def fnv(text):
    h=0xCBF29CE484222645
    for x in text.encode(): h=((h^x)*0x100000001B3)&0xffffffffffffffff
    return h

def romfs_index(b):
    h=struct.unpack('<10Q',bounded(b,0,80))
    dm=bounded(b,h[3],h[4]); fm=bounded(b,h[7],h[8]); out={}
    def directory(d):
        parts=[]; seen=set()
        while d:
            if d in seen: raise ValueError('Cyclic directory')
            seen.add(d)
            parts.append(bounded(dm,d+24,value(dm,d+20,'I')).decode())
            d=value(dm,d,'I')
        return '/'.join(reversed(parts))
    p=0
    while p<len(fm):
        parent,_,off,size,_,nl=struct.unpack('<IIQQII',bounded(fm,p,32))
        name=bounded(fm,p+32,nl).decode(); d=directory(parent)
        path=f'{d}/{name}' if d else name
        if h[9]+off+size>len(b): raise ValueError('RomFS file exceeds image')
        out[path]=(h[9]+off,size); p+=32+((nl+3)&~3)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('romfs'); ap.add_argument('out')
    ap.add_argument('--pack-pattern',default=r'script.*lua|\.blua',help='Case-insensitive pack-name regex; defaults to Lua scripts')
    ap.add_argument('--list-only',action='store_true',help='List matching pack names and sizes without reading or extracting members')
    ap.add_argument('--max-pack-bytes',type=int,default=64*1024*1024,help='Skip selected packs above this size')
    args=ap.parse_args(); out=Path(args.out).resolve()
    pattern=re.compile(args.pack_pattern,re.I)
    if not 0 < args.max_pack_bytes <= 64*1024*1024: raise ValueError('Invalid pack budget')
    if not out.is_relative_to(Path(__file__).resolve().parents[2]/'build'):
        raise ValueError('Outputs must stay in experimental build/')
    out.mkdir(parents=True,exist_ok=True)
    records=[]
    with open(args.romfs,'rb') as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as b:
        files=romfs_index(b)
        fd=Table.root(bounded(b,*files['arc/data.trpfd']))
        names,info=fd.strings(1),fd.tables(3)
        if len(names)!=len(info): raise ValueError('Pack counts disagree')
        if args.list_only:
            packs=[dict(index=i,pack=name,packed_bytes=info[i].scalar(0,'Q'))
                   for i,name in enumerate(names) if pattern.search(name)]
            (out/'packs.json').write_text(json.dumps(packs,indent=2),encoding='utf-8')
            print(json.dumps(dict(packs=len(packs),packed_bytes=sum(p['packed_bytes'] for p in packs),file=str(out/'packs.json'))))
            return
        fs_off,fs_size=files['arc/data.trpfs']
        if bounded(b,fs_off,8)!=b'ONEPACK\0': raise ValueError('Archive magic differs')
        root=value(b,fs_off+8,'Q')
        if root>=fs_size: raise ValueError('Archive root exceeds file')
        fs=Table.root(bounded(b,fs_off+root,fs_size-root))
        hashes,offsets=fs.integers(0),fs.integers(1)
        if len(hashes)!=len(offsets) or len(set(hashes))!=len(hashes): raise ValueError('Archive index mismatch')
        lookup=dict(zip(hashes,offsets)); total=0
        for i,name in enumerate(names):
            if not pattern.search(name): continue
            po=lookup[fnv(name)]; size=info[i].scalar(0,'Q')
            if po+size>fs_size: raise ValueError('Pack size invalid')
            if size>args.max_pack_bytes: continue
            pk=Table.root(bounded(b,fs_off+po,size))
            members,entries=pk.integers(0),pk.tables(1)
            if len(members)!=len(entries): raise ValueError('Member counts disagree')
            for hash_,e in zip(members,entries):
                start,packed=e.vector(len(e.slots)-1,1)
                blob=bounded(e.b,start,packed); total+=packed
                if total>128*1024*1024: raise ValueError('Extraction budget exceeded')
                comp=e.scalar(1,'b',-1); unpacked=e.scalar(3,'Q')
                path=out/f'{i}-{hash_:016x}.bin'
                if path.exists() and path.read_bytes()!=blob: raise ValueError('Refusing to overwrite different extracted member')
                path.write_bytes(blob)
                records.append(dict(pack=name,hash=f'{hash_:016x}',compression=comp,
                                    packed=packed,unpacked=unpacked,path=str(path),
                                    sha256=hashlib.sha256(blob).hexdigest(),
                                    lua_header=blob.startswith(b'\x1bLua'),romfs_offset=fs_off+po+start))
    (out/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps(dict(members=len(records),stored=sum(r['compression']==-1 for r in records),
                         lua=sum(r['lua_header'] for r in records),packed_bytes=total)))

if __name__=='__main__': main()
