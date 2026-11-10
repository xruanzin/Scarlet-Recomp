#!/usr/bin/env python3
"""Examine the original 1 MiB Scarlet 32x128x32 RGBA16F tiled sky volume.

Compare six Tegra GOB block-depth interpretations without restarting the game.
Spatial differences are only diagnostics, not proof of a correct layout.
No dependencies outside Python's standard library.
"""
import argparse
import math
import struct
from pathlib import Path
import zlib

W, H, D, PIXEL = 32, 128, 32, 8
SIZE = W * H * D * PIXEL
BH = 4  # original builder height, 16 GOBs = 128 rows

def offset(x, y, z, bd):
    xb = x * PIXEL
    goby = y >> 3
    localx = xb & 63
    localy = y & 7
    block_size = 512 << (BH + bd)
    blocks_y = (H + (8 << BH) - 1) // (8 << BH)
    return (((z >> bd) * blocks_y + (goby >> BH)) * ((W * PIXEL + 63) // 64) + (xb >> 6)) * block_size + \
        (((z & ((1 << bd) - 1)) << BH) | (goby & ((1 << BH) - 1))) * 512 + \
        ((localx >> 5) << 8) + ((localy >> 1) << 6) + \
        (((localx >> 4) & 1) << 5) + ((localy & 1) << 4) + (localx & 15)

def sample(raw, x, y, z, bd):
    return struct.unpack_from("<4e", raw, offset(x, y, z, bd))

def score(raw, bd):
    sums = [0.0, 0.0, 0.0]
    counts = [0, 0, 0]
    invalid = 0
    for z in range(D):
        for y in range(0, H, 4):
            for x in range(0, W, 4):
                a = sample(raw, x, y, z, bd)
                if not all(math.isfinite(v) for v in a):
                    invalid += 1
                    continue
                for idx, nxt in enumerate(((x,y,z+1), (x,y+4,z), (x+4,y,z))):
                    xx, yy, zz = nxt
                    if zz >= D or yy >= H or xx >= W: continue
                    b = sample(raw, xx, yy, zz, bd)
                    if not all(math.isfinite(v) for v in b): continue
                    sums[idx] += sum(min(abs(q-p), 64.0) for q,p in zip(a[:3], b[:3])) / 3
                    counts[idx] += 1
    return [s / max(1, n) for s,n in zip(sums, counts)], invalid

def chunk(name, payload):
    import binascii
    return struct.pack(">I",len(payload)) + name + payload + \
           struct.pack(">I",binascii.crc32(name+payload)&0xffffffff)

def make_png(raw, path):
    # Columns: block depths 0..5. Rows: z slices 0, 8, 16, 24.
    scale = 2
    width, height = 6 * W * scale, 4 * H * scale
    pixels = bytearray(width * height)
    choices = (0,8,16,24)
    src = sorted(v for z in choices for y in range(0,H,2) for x in range(0,W,2)
                 if math.isfinite(v := sample(raw,x,y,z,5)[0]))
    lo = src[len(src)//30] if src else 0
    hi = src[len(src)*29//30] if src else 1
    hi = max(hi,lo+1e-6)
    for bd in range(6):
        for row, z in enumerate(choices):
            for y in range(H):
                for x in range(W):
                    v = sample(raw,x,y,z,bd)[0]
                    gray = 0 if not math.isfinite(v) else max(0,min(255,round((v-lo)/(hi-lo)*255)))
                    for yi in range(scale):
                        base = (row*H*scale + y*scale + yi)*width + bd*W*scale + x*scale
                        pixels[base:base+scale] = bytes([gray])*scale
    scanlines = b"".join(b"\0"+bytes(pixels[i*width:(i+1)*width]) for i in range(height))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,0,0,0,0)) + \
          chunk(b"IDAT",zlib.compress(scanlines,6)) + chunk(b"IEND",b"")
    path.write_bytes(png)
    print(f"Montage: {path} (columns depth 0..5, rows slice 0/8/16/24)")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw", type=Path, help="sky_volume_tiled_rgba16f_32x128x32.bin")
    ap.add_argument("--png",type=Path,help="optional grayscale montage PNG")
    args = ap.parse_args()
    raw = args.raw.read_bytes()
    if len(raw) != SIZE: ap.error(f"Expected {SIZE:,} bytes, got {len(raw):,}")
    print("Sky volume 32x128x32 RGBA16F; smaller spatial differences = smoother")
    print("Block depth       deltaZ       deltaY       deltaX   invalid")
    for bd in range(6):
        (dz,dy,dx), bad = score(raw,bd)
        print(f"{bd:>11}   {dz:>10.5f}   {dy:>10.5f}   {dx:>10.5f}   {bad:>7}")
    print("Scores are clues, not definitive verification of the original guest layout.")
    if args.png: make_png(raw,args.png)

if __name__ == "__main__":
    main()
