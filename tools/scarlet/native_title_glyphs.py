#!/usr/bin/env python3
"""Native Scarlet button glyphs in the game's own NintendoExt font slot.

Builds a small glyph-only replacement font from the bundled, OFL-licensed
DejaVu Sans. No Switch assets, copyrighted game data, saved games, or RomFS
files are modified. Pure Python standard library; works offline on Windows.
The game must use NintendoExt PUA glyphs for this replacement to take effect.
"""
import argparse
import re
import struct
from pathlib import Path

def u16(b, o):
    return struct.unpack_from(">H", b, o)[0]

def u32(b, o):
    return struct.unpack_from(">I", b, o)[0]

def b16(x):
    return struct.pack(">H", x)

def b32(x):
    return struct.pack(">I", x)

def checksum(b):
    b += bytes(-len(b) % 4)
    return sum(struct.unpack(">" + "I" * (len(b) // 4), b)) & 0xffffffff

def font_tables(b):
    if b[:4] not in (bytes((0,1,0,0)), b"true"):
        raise ValueError("This is not a TrueType font")
    out = {}
    for i in range(u16(b, 4)):
        o = 12 + 16*i
        tag = b[o:o+4].decode("ascii")
        at, size = u32(b, o+8), u32(b, o+12)
        if at + size > len(b):
            raise ValueError("Invalid font table")
        out[tag] = b[at:at+size]
    return out

def cmap4(sub):
    count = u16(sub, 6)//2
    out = {}
    starts = 16+2*count
    deltas = starts+2*count
    ranges = deltas+2*count
    for i in range(count):
        first = u16(sub, starts+2*i)
        last = u16(sub, 14+2*i)
        delta = u16(sub, deltas+2*i)
        ro = u16(sub, ranges+2*i)
        for cp in range(first, last+1):
            if cp == 0xffff:
                continue
            if ro:
                pos = ranges+2*i+ro+2*(cp-first)
                gid = u16(sub, pos) if pos+2 <= len(sub) else 0
                if gid:
                    gid = (gid+delta) & 65535
            else:
                gid = (cp+delta) & 65535
            if gid:
                out[cp] = gid
    return out

def cmap12(sub):
    out = {}
    for i in range(u32(sub, 12)):
        a, b, gid = struct.unpack_from(">III", sub, 16+12*i)
        for cp in range(a, b+1):
            if gid + cp-a:
                out[cp] = gid+cp-a
    return out

def read_cmap(data):
    if u16(data, 0):
        raise ValueError("Unsupported cmap version")
    out = {}
    for kind, encoding in ((4, 1), (12, 10)):
        for i in range(u16(data, 2)):
            platform, enc, off = struct.unpack_from(">HHI", data, 4+8*i)
            if platform == 3 and enc == encoding and u16(data, off) == kind:
                sub = data[off:]
                out.update(cmap4(sub) if kind == 4 else cmap12(sub))
                break
    return out

def write_cmap4(m):
    segments = []
    for cp, gid in sorted(m.items()):
        if cp >= 0xffff or gid >= 65536:
            continue
        delta = (gid-cp) & 65535
        if segments and cp == segments[-1][1]+1 and delta == segments[-1][2]:
            segments[-1] = (segments[-1][0], cp, delta)
        else:
            segments.append((cp, cp, delta))
    segments.append((0xffff, 0xffff, 1))
    n = len(segments)
    level = 1 << (n.bit_length()-1)
    out = b16(4)+b16(16+8*n)+b16(0)+b16(2*n)+b16(2*level)+b16(level.bit_length()-1)+b16(2*n-2*level)
    out += b"".join(b16(end) for start, end, d in segments) + b16(0)
    out += b"".join(b16(start) for start, end, d in segments)
    out += b"".join(b16(d) for start, end, d in segments)
    out += bytes(2*n)
    if len(out) > 65535:
        raise ValueError("The BMP glyph table is too large")
    return out

def write_cmap12(m):
    groups = []
    for cp, gid in sorted(m.items()):
        if not gid:
            continue
        if groups and cp == groups[-1][1]+1 and gid == groups[-1][2]+cp-groups[-1][0]:
            groups[-1] = (groups[-1][0], cp, groups[-1][2])
        else:
            groups.append((cp, cp, gid))
    data = b"".join(struct.pack(">III", *g) for g in groups)
    return struct.pack(">HHIII", 12, 0, 16+len(data), 0, len(groups))+data

def create_cmap(mapping):
    f4, f12 = write_cmap4(mapping), write_cmap12(mapping)
    off = 4+8*3
    return (struct.pack(">HH",0,3)+struct.pack(">HHI",0,3,off)+
            struct.pack(">HHI",3,1,off)+struct.pack(">HHI",3,10,off+len(f4))+f4+f12)

def rebuild_font(original, tables):
    tables = dict(tables)
    h = bytearray(tables["head"])
    h[8:12] = bytes(4)
    tables["head"] = bytes(h)
    tags = sorted(tables)
    n = len(tags)
    power = 1 << (n.bit_length()-1)
    out = bytearray(original[:4]+struct.pack(">HHHH",n,16*power,power.bit_length()-1,16*(n-power)))
    entries = bytearray()
    payload = []
    off = 12 + 16*n
    head_off = None
    for tag in tags:
        data = tables[tag]
        if tag == "head":
            head_off = off
        entries += tag.encode("ascii")+struct.pack(">III",checksum(data),off,len(data))
        payload.append(data+bytes(-len(data)%4))
        off += (len(data)+3) & ~3
    out.extend(entries)
    for data in payload:
        out.extend(data)
    if head_off is None:
        raise ValueError("Missing font head")
    out[head_off+8:head_off+12] = b32((0xB1B0AFBA-checksum(bytes(out))) & 0xffffffff)
    return bytes(out)

def keyboard_names(ini):
    mapping = {"a":"K","b":"J","x":"L","y":"I"}
    if ini.exists():
        for line in ini.read_text(encoding="utf-8-sig",errors="replace").splitlines():
            m = re.match(r"^\s*bind_key_(a|b|x|y)\s*=\s*([^#;\s]+)",line,re.I)
            if m:
                v = m.group(2).upper()
                if len(v)==1 and v.isascii() and v.isalnum():
                    mapping[m.group(1).lower()] = v
    return "".join(mapping[x] for x in "abxy")

def build(repo, ini):
    font = (repo/"third_party/fonts/DejaVu/DejaVuSans.ttf").read_bytes()
    tables = font_tables(font)
    default = read_cmap(tables["cmap"])
    names = {"xbox":"ABXY","playstation":"×○□△","steamdeck":"ABXY","keyboard":keyboard_names(ini)}
    dest = repo/"fonts"
    dest.mkdir(exist_ok=True)
    for style, chars in names.items():
        cmap = dict(default)
        for i, char in enumerate(chars):
            glyph = default.get(ord(char))
            if not glyph:
                raise ValueError("The bundled font lacks glyph for "+repr(char))
            # Outline and filled PUA icons: Switch A/B/X/Y in NintendoExt.
            cmap[0xe0a0+i] = glyph
            cmap[0xe0e0+i] = glyph
        changed = dict(tables)
        changed["cmap"] = create_cmap(cmap)
        data = rebuild_font(font, changed)
        target = dest/("nintendo_ext_003_scarlet_"+style+".ttf")
        if not target.exists() or target.read_bytes()!=data:
            target.write_bytes(data)
        print("[scarlet-native-title] "+style+" glyphs="+repr(chars)+" "+str(target))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument("--settings",type=Path,default=Path("larecomp.ini"))
    args = parser.parse_args()
    build(args.repo.resolve(),args.settings.resolve())

if __name__=="__main__":
    main()
