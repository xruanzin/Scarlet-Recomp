"""Focused Lua prototype listing with correctly typed constant annotations."""
import argparse
from pathlib import Path
from inspect_lua_steps import Chunk, instruction

ap=argparse.ArgumentParser()
ap.add_argument('script',type=Path)
ap.add_argument('prototypes',nargs='+')
a=ap.parse_args()
c=Chunk(a.script.read_bytes())
for p in c.protos:
    if p['path'] not in a.prototypes: continue
    print('PROTO',p['path'],'params',p['params'],'start',hex(p['start']))
    for k in p['constants']: print('K',k['index'],hex(k['offset']),repr(k['value']))
    for pc,w in enumerate(p['code']):
        x=instruction(w,pc)
        indices=[]
        if x['op']=='LOADK': indices=[x['bx']]
        elif x['op'] in ('GETTABUP','GETFIELD','ADDK','SUBK','MULK','MODK','POWK','DIVK','IDIVK','BANDK','BORK','BXORK'): indices=[x['c']]
        elif x['op'] in ('SETTABUP','SETFIELD'): indices=[x['b']]+([x['c']] if x['k'] else [])
        elif x['op'] in ('SELF','SETTABLE','SETI') and x['k']: indices=[x['c']]
        elif x['op']=='EQK': indices=[x['b']]
        note=' '.join(f'K{k}={p["constants"][k]["value"]!r}' for k in indices if k<len(p['constants']))
        print(f"{pc:05d} {x['op']:12} a={x['a']} b={x['b']} c={x['c']} k={x['k']} bx={x['bx']} {note}")
