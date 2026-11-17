#!/usr/bin/env python3
"""Native Scarlet button glyphs in the game's own NintendoExt font slot.

Builds a small glyph-only replacement font from the bundled, OFL-licensed
DejaVu Sans. No Switch assets, copyrighted game data, saved games, or RomFS
files are modified. Pure Python standard library; works offline on Windows.
The game must use NintendoExt PUA glyphs for this replacement to take effect.
"""
import argparse
import math
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


def icon_ring(cx, cy, outer, inner, n=40):
    a = [(round(cx+outer*math.cos(2*math.pi*i/n)),round(cy+outer*math.sin(2*math.pi*i/n))) for i in range(n)]
    b = [(round(cx+inner*math.cos(-2*math.pi*i/n)),round(cy+inner*math.sin(-2*math.pi*i/n))) for i in range(n)]
    return [a,b]

def icon_stroke(x1,y1,x2,y2,t=85):
    length = math.hypot(x2-x1,y2-y1)
    if not length: return []
    nx = -((y2-y1)/length)*(t/2)
    ny = ((x2-x1)/length)*(t/2)
    return [(round(x1+nx),round(y1+ny)),(round(x2+nx),round(y2+ny)),
            (round(x2-nx),round(y2-ny)),(round(x1-nx),round(y1-ny))]

def icon_letter(letter):
    L,R,T,B,M,C = 630,1400,1480,610,1035,1015
    strokes = {
        "A":[(L,B,C,T),(C,T,R,B),(730,950,1310,950)],
        "B":[(L,B,L,T),(L,T,1180,T),(1180,T,R,1300),(R,1300,1180,M),
             (1180,M,L,M),(1180,M,R,830),(R,830,1180,B),(1180,B,L,B)],
        "X":[(L,B,R,T),(L,T,R,B)],
        "Y":[(L,T,C,M),(R,T,C,M),(C,M,C,B)],
        "K":[(L,B,L,T),(L,M,R,T),(L,M,R,B)],
        "J":[(R,T,R,780),(R,780,1150,B),(1150,B,L,750)],
        "L":[(L,T,L,B),(L,B,R,B)],
        "I":[(L,T,R,T),(C,T,C,B),(L,B,R,B)],
    }
    return [icon_stroke(*coords) for coords in strokes.get(letter, strokes["K"])]

def icon_glyph(style, letter, upem):
    cx=cy=1024
    if style in ("xbox","steamdeck"):
        parts = icon_ring(cx,cy,820,745)+icon_letter(letter)
    elif style == "keyboard":
        parts = [[(260,260),(1790,260),(1790,1790),(260,1790)],
                 [(340,340),(340,1710),(1710,1710),(1710,340)]]+icon_letter(letter)
    elif letter == "×":
        parts = [icon_stroke(480,480,1550,1550,135),icon_stroke(480,1550,1550,480,135)]
    elif letter == "○":
        parts = icon_ring(cx,cy,680,570)
    elif letter == "□":
        parts = [[(365,365),(1683,365),(1683,1683),(365,1683)],
                 [(470,470),(470,1578),(1578,1578),(1578,470)]]
    elif letter == "△":
        parts = [[(1024,1770),(270,380),(1778,380)],
                 [(1024,1510),(1530,500),(510,500)]]
    else:
        raise ValueError("Unsupported native icon "+letter)
    contours = [[(round(x*upem/2048),round(y*upem/2048)) for x,y in poly] for poly in parts]
    points = [p for contour in contours for p in contour]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    data = struct.pack(">hhhhh",len(contours),min(xs),min(ys),max(xs),max(ys))
    end = -1
    for poly in contours:
        end += len(poly)
        data += b16(end)
    data += bytes(2)+bytes([1]*len(points)) # 0 instructions; all on-curve
    prev=0
    for px,py in points:
        data += struct.pack(">h",px-prev)
        prev=px
    prev=0
    for px,py in points:
        data += struct.pack(">h",py-prev)
        prev=py
    return data+bytes(-len(data)%2)

def native_base(repo):
    # Preserve every existing NintendoExt icon from a user's own dump; only
    # A/B/X/Y are added/replaced. DejaVu is a fallback if no dump was supplied.
    raw = repo/"fonts/nintendo_ext_003.bfttf"
    plain = repo/"fonts/nintendo_ext_003.ttf"
    if plain.is_file():
        data = plain.read_bytes()
        print("[scarlet-native-title] using user's unmodified NintendoExt TTF")
        return data
    if raw.is_file():
        blob = raw.read_bytes()
        key, magic = 0x49621806, 0x7f9a0218
        if len(blob) >= 12:
            w0,w1=struct.unpack_from("<II",blob)
            if (w0^key)==magic:
                size=w1^key
                decode=lambda w: (w^key).to_bytes(4,"big")
            else:
                swapped=int.from_bytes(key.to_bytes(4,"little"),"big")
                smagic=int.from_bytes(magic.to_bytes(4,"little"),"big")
                if (w0^swapped)==smagic:
                    size=int.from_bytes((w1^swapped).to_bytes(4,"little"),"big")
                    decode=lambda w: (w^swapped).to_bytes(4,"little")
                else:
                    size=0
            if 12<=len(blob) and 4<=size<=len(blob)-8:
                data=b"".join(decode(u32le) for (u32le,) in
                              struct.iter_unpack("<I",blob[8:8+((size+3)&~3)]))[:size]
                if data[:4] in (bytes((0,1,0,0)),b"true"):
                    print("[scarlet-native-title] using user's NintendoExt BFTTF")
                    return data
        print("[scarlet-native-title] invalid BFTTF; using bundled OFL font")
    print("[scarlet-native-title] no console NintendoExt dump; using bundled OFL font")
    return (repo/"third_party/fonts/DejaVu/DejaVuSans.ttf").read_bytes()

def append_icons(tbls, style, chars):
    # Keep the original cmap and ALL non-face icons. Append four new vector
    # glyphs to the source TrueType font, then route the eight face codepoints
    # (outline and filled) to those native symbols.
    n=u16(tbls["maxp"],4)
    head=bytearray(tbls["head"])
    loc_format=struct.unpack_from(">h",head,50)[0]
    loca=tbls["loca"]
    offsets=[u32(loca,4*i) if loc_format else 2*u16(loca,2*i) for i in range(n+1)]
    glyf=bytearray(tbls["glyf"][:offsets[-1]])
    newoffsets=list(offsets)
    upem=u16(head,18)
    for letter in chars:
        glyf.extend(icon_glyph(style,letter,upem))
        glyf.extend(bytes(-len(glyf)%4))
        newoffsets.append(len(glyf))
    new=dict(tbls)
    head[50:52]=b16(1)
    new["head"]=bytes(head)
    new["glyf"]=bytes(glyf)
    new["loca"]=b"".join(b32(v) for v in newoffsets)
    mx=bytearray(tbls["maxp"])
    mx[4:6]=b16(n+4)
    if len(mx)>=10 and u32(mx,0)==0x00010000:
        # The new Xbox B has 10 contours and the circles have 80 points.
        # Older console icon fonts can advertise fewer than this in maxp.
        mx[6:8]=b16(max(u16(mx,6),128))
        mx[8:10]=b16(max(u16(mx,8),12))
    new["maxp"]=bytes(mx)
    hh=bytearray(tbls["hhea"])
    nm=u16(hh,34)
    hh[10:12]=b16(max(u16(hh,10),upem))
    hh[34:36]=b16(n+4)
    new["hhea"]=bytes(hh)
    hmtx=tbls["hmtx"]
    lastadvance=u16(hmtx,4*(nm-1))
    metrics=bytearray()
    for i in range(n):
        adv,lsb=struct.unpack_from(">Hh",hmtx,4*i) if i<nm else (
            lastadvance,struct.unpack_from(">h",hmtx,4*nm+2*(i-nm))[0])
        metrics.extend(struct.pack(">Hh",adv,lsb))
    for letter in chars:
        metrics.extend(struct.pack(">Hh",upem,0))
    new["hmtx"]=bytes(metrics)
    post=tbls.get("post")
    if post and u32(post,0)==0x00020000:
        new["post"]=bytes((0,3,0,0))+post[4:32]
    return new,n

def build(repo, ini):
    font = native_base(repo)
    tbls = font_tables(font)
    default = read_cmap(tbls["cmap"])
    names = {"xbox":"ABXY","playstation":"×○□△","steamdeck":"ABXY","keyboard":keyboard_names(ini)}
    dest = repo/"fonts"
    dest.mkdir(exist_ok=True)
    for style, chars in names.items():
        changed, first_new_id = append_icons(tbls,style,chars)
        cmap = dict(default)
        for i in range(4):
            cmap[0xe0a0+i] = first_new_id+i
            cmap[0xe0e0+i] = first_new_id+i
        changed["cmap"] = create_cmap(cmap)
        data = rebuild_font(font,changed)
        # Catch damaged TTF layouts before the game ever receives the font.
        parsed = font_tables(data)
        verified = read_cmap(parsed["cmap"])
        if any(verified.get(0xe0a0+i)!=first_new_id+i or
               verified.get(0xe0e0+i)!=first_new_id+i for i in range(4)):
            raise ValueError("Native button font validation failed for "+style)
        if u16(parsed["maxp"],4)!=first_new_id+4:
            raise ValueError("Native glyph count is invalid for "+style)
        target = dest/("nintendo_ext_003_scarlet_"+style+".ttf")
        if not target.exists() or target.read_bytes()!=data:
            target.write_bytes(data)
        print("[scarlet-native-title] "+style+" native glyphs="+repr(chars)+" "+str(target))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument("--settings",type=Path,default=Path("larecomp.ini"))
    args = parser.parse_args()
    build(args.repo.resolve(),args.settings.resolve())

if __name__=="__main__":
    main()
