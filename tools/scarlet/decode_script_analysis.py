"""Offline analysis only: decode the extracted Scarlet Lua members with ooz.

Loads the separately built GPL analysis helper; never linked into Scarlet runtime.
Inputs are copied game data under build, output is new *.blua analysis copies.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path

from inspect_lua_steps import Chunk


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest', type=Path)
    ap.add_argument('decoder', type=Path)
    a = ap.parse_args()
    decoder = ctypes.CDLL(str(a.decoder.resolve()))
    decoder.ooz_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                     ctypes.c_void_p, ctypes.c_size_t]
    decoder.ooz_decompress.restype = ctypes.c_int
    report = []
    for item in json.loads(a.manifest.read_text(encoding='utf-8-sig')):
        p = Path(item['path'])
        if p.resolve().parent != a.manifest.resolve().parent:
            raise ValueError('input outside analysis directory')
        raw = p.read_bytes()
        if len(raw) != item['packed'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('packed identity mismatch')
        size = item['unpacked']
        if item['compression'] != 3 or not 0 < size <= 128 * 1024 * 1024:
            raise ValueError('unsupported codec or unreasonable output size')
        src = ctypes.create_string_buffer(raw, len(raw) + 64)
        out = ctypes.create_string_buffer(size + 64)
        result = decoder.ooz_decompress(src, len(raw), out, size)
        if result != size:
            raise ValueError(f'{p}: decoder returned {result}, expected {size}')
        data = out.raw[:size]
        chunk = Chunk(data)  # full grammar/sentinel/length check before writing
        dest = p.with_suffix('.blua')
        if dest.exists() and dest.read_bytes() != data:
            raise ValueError('refusing to overwrite different analysis result')
        dest.write_bytes(data)
        report.append(dict(pack=item['pack'], file=str(dest), packed_sha256=item['sha256'],
                           decoded_sha256=hashlib.sha256(data).hexdigest(),
                           bytes_returned=result, bytes_parsed=chunk.pos,
                           prototypes=len(chunk.protos),
                           d130_constants=sum(k['tag'] == 19 and k['bits'] == '111111111111a13f'
                                              for p in chunk.protos for k in p['constants'])))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
