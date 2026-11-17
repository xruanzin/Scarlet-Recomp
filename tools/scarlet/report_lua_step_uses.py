"""Print direct constant uses and nearby Lua instructions, not a semantic claim."""
import argparse
from pathlib import Path
from inspect_lua_steps import Chunk, instruction

ap = argparse.ArgumentParser()
ap.add_argument('script', type=Path)
args = ap.parse_args()
c = Chunk(args.script.read_bytes())
by_path = {p['path']: p for p in c.protos}
for p in c.protos:
    keys = {k['index'] for k in p['constants'] if k['tag'] == 19 and k['bits'] == '111111111111a13f'}
    if not keys:
        continue
    print(f"PROTO {p['path']} start={p['start']:#x} code={len(p['code'])} params={p['params']} source={p['source']}")
    print('CONSTANTS', [(k['index'],hex(k['offset'])) for k in p['constants'] if k['index'] in keys])
    parent_path, child = p['path'].rsplit('.',1)
    parent = by_path[parent_path]
    for pc,w in enumerate(parent['code']):
        ins = instruction(w,pc)
        if ins['op'] == 'CLOSURE' and ins['bx'] == int(child):
            print('PARENT_BINDING', parent_path, pc)
            for j in range(max(0,pc-4),min(len(parent['code']),pc+7)):
                x=instruction(parent['code'][j],j)
                kidx = x['bx'] if x['op']=='LOADK' else x['c'] if x['op'] in ('GETTABUP','GETFIELD') else x['b'] if x['op'] in ('SETTABUP','SETFIELD') else None
                hint = parent['constants'][kidx]['value'] if kidx is not None and kidx<len(parent['constants']) else ''
                print(' ',j,x['op'],'a',x['a'],'b',x['b'],'c',x['c'],'k',x['k'],'bx',x['bx'],repr(hint))
    code = [instruction(w,i) for i,w in enumerate(p['code'])]
    uses = []
    for i,x in enumerate(code):
        if ((x['op'] == 'LOADK' and x['bx'] in keys) or
            (x['op'] in ('ADDK','SUBK','MULK','MODK','POWK','DIVK','IDIVK','BANDK','BORK','BXORK') and x['c'] in keys) or
            (x['op'] == 'EQK' and x['b'] in keys) or
            (x['op'] in ('SETTABUP','SETTABLE','SETI','SETFIELD') and x['k'] and x['c'] in keys)):
            uses.append(i)
    wanted = sorted({j for i in uses for j in range(max(0,i-8),min(len(code),i+13))})
    print('DIRECT_USE_PCS', uses)
    prev = -2
    for j in wanted:
        if j != prev+1: print('...')
        x=code[j]
        hints=[]
        for field in ('b','c','bx'):
            idx=x[field]
            if idx<len(p['constants']):
                k=p['constants'][idx]
                hints.append(f'{field}:K{idx}={k["value"]!r}')
        print(f"{j:05d} {x['op']:12} a={x['a']} b={x['b']} c={x['c']} k={x['k']} bx={x['bx']} ; {' '.join(hints)}")
        prev=j
