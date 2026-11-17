"""Read-only Lua 5.4 constant/prototype evidence for Scarlet script timing.

Format reference: https://www.lua.org/source/5.4/lundump.c.html and
https://www.lua.org/source/5.4/lopcodes.h.html. Does not patch any script.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

OPS = ('MOVE LOADI LOADF LOADK LOADKX LOADFALSE LFALSESKIP LOADTRUE LOADNIL '
       'GETUPVAL SETUPVAL GETTABUP GETTABLE GETI GETFIELD SETTABUP SETTABLE SETI '
       'SETFIELD NEWTABLE SELF ADDI ADDK SUBK MULK MODK POWK DIVK IDIVK BANDK '
       'BORK BXORK SHRI SHLI ADD SUB MUL MOD POW DIV IDIV BAND BOR BXOR SHL SHR '
       'MMBIN MMBINI MMBINK UNM BNOT NOT LEN CONCAT CLOSE TBC JMP EQ LT LE EQK '
       'EQI LTI LEI GTI GEI TEST TESTSET CALL TAILCALL RETURN RETURN0 RETURN1 '
       'FORLOOP FORPREP TFORPREP TFORCALL TFORLOOP SETLIST CLOSURE VARARG VARARGPREP EXTRAARG').split()


class Chunk:
    def __init__(self, data):
        self.data, self.pos, self.protos = data, 0, []
        if self.take(6) != b'\x1bLua\x54\x00':
            raise ValueError('expected Lua 5.4 format 0')
        if self.take(6) != b'\x19\x93\r\n\x1a\n' or self.take(3) != b'\x04\x08\x08':
            raise ValueError('unexpected Lua signature or scalar sizes')
        if struct.unpack('<q', self.take(8))[0] != 0x5678:
            raise ValueError('unexpected integer sentinel/endianness')
        if struct.unpack('<d', self.take(8))[0] != 370.5:
            raise ValueError('unexpected float sentinel')
        self.main_upvalues = self.take(1)[0]
        self.function('0', 0)
        if self.pos != len(data):
            raise ValueError(f'trailing bytes: parsed {self.pos} of {len(data)}')

    def take(self, count):
        if count < 0 or count > len(self.data) - self.pos:
            raise ValueError(f'truncated Lua chunk at {self.pos:#x}, length {count}')
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result

    def varint(self):
        value = 0
        for _ in range(10):
            b = self.take(1)[0]
            value = (value << 7) | (b & 127)
            if value > 0x7fffffffffffffff:
                raise ValueError('oversized Lua varint')
            if b & 128:
                return value
        raise ValueError('unterminated Lua varint')

    def string(self):
        length = self.varint()
        return self.take(length - 1).decode('utf-8', 'backslashreplace') if length else None

    def function(self, path, depth):
        if depth > 200:
            raise ValueError('prototype nesting exceeds inspection bound')
        start = self.pos
        source = self.string()
        lines = [self.varint(), self.varint()]
        params, vararg, stack = self.take(3)
        count = self.varint()
        code_offset = self.pos
        code = list(struct.unpack(f'<{count}I', self.take(count * 4)))
        consts = []
        for index in range(self.varint()):
            tag = self.take(1)[0]
            offset = self.pos
            value, bits = None, None
            if tag in (4, 20):
                value = self.string()
            elif tag in (3, 19):
                raw = self.take(8)
                value = struct.unpack('<q' if tag == 3 else '<d', raw)[0]
                bits = raw.hex()
                if isinstance(value, float) and not math.isfinite(value):
                    value = str(value)
            elif tag in (0, 1, 17):
                value = {0: None, 1: False, 17: True}[tag]
            else:
                raise ValueError(f'unknown constant tag {tag:#x} at {offset-1:#x}')
            consts.append(dict(index=index, tag=tag, offset=offset, value=value, bits=bits))
        nup = self.varint()
        self.take(nup * 3)
        proto = dict(path=path, start=start, source=source, lines=lines,
                     params=params, vararg=vararg, stack=stack, code_offset=code_offset,
                     code=code, constants=consts, upvalues=nup)
        self.protos.append(proto)
        proto['children'] = self.varint()
        for i in range(proto['children']):
            self.function(f'{path}.{i}', depth + 1)
        self.take(self.varint())  # relative line info
        for _ in range(self.varint()):
            self.varint(), self.varint()
        for _ in range(self.varint()):
            self.string(), self.varint(), self.varint()
        for _ in range(self.varint()):
            self.string()
        proto['end'] = self.pos


def instruction(word, pc):
    op = word & 127
    return dict(pc=pc, word=f'{word:08x}', op=OPS[op] if op < len(OPS) else f'UNKNOWN_{op}',
                a=(word >> 7) & 255, k=(word >> 15) & 1, b=(word >> 16) & 255,
                c=word >> 24, bx=word >> 15, ax=word >> 7)


def report(path):
    data = path.read_bytes()
    c = Chunk(data)
    found = []
    for p in c.protos:
        matches = [k for k in p['constants'] if k['tag'] == 19 and k['bits'] == '111111111111a13f']
        if matches:
            found.append(dict(path=p['path'], start=p['start'], end=p['end'],
                              code_offset=p['code_offset'], constants=p['constants'],
                              matches=matches, instructions=[instruction(w,i) for i,w in enumerate(p['code'])]))
    return dict(file=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                parsed=c.pos, prototypes=len(c.protos), matches=found,
                note='Numeric constant identity is not proof of movement semantics; no modifications made.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('scripts', nargs='+', type=Path)
    args = ap.parse_args()
    print(json.dumps([report(p) for p in args.scripts], indent=2, ensure_ascii=True))
