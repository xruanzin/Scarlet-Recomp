"""Read-only class/method binding evidence from a strictly parsed Lua chunk."""
import argparse
from pathlib import Path
from inspect_lua_steps import Chunk, instruction

ap = argparse.ArgumentParser()
ap.add_argument('script', type=Path)
ap.add_argument('names', nargs='+')
a = ap.parse_args()
c = Chunk(a.script.read_bytes())
ps = {p['path']: p for p in c.protos}

def show(p, lo, hi):
    for pc in range(max(0,lo),min(len(p['code']),hi)):
        x = instruction(p['code'][pc],pc)
        inds = ([x['bx']] if x['op']=='LOADK' else [x['c']] if x['op'] in ('GETTABUP','GETFIELD') else [x['b']] if x['op'] in ('SETFIELD','SETTABUP') else [x['c']] if x['op']=='SELF' and x['k'] else [])
        print(pc,x['op'],x['a'],x['b'],x['c'],x['k'],x['bx'],[p['constants'][i]['value'] for i in inds if i<len(p['constants'])])

for p in c.protos:
    keys={k['index'] for k in p['constants'] if isinstance(k['value'],str) and k['value'] in a.names}
    if not keys: continue
    print('\nPROTO',p['path'],'params',p['params'],'start',hex(p['start']),'source',p['source'],'lines',p['lines'])
    print('STRINGS',[k['value'] for k in p['constants'] if isinstance(k['value'],str)][:250])
    if '.' in p['path']:
        par,idx=p['path'].rsplit('.',1)
        pp=ps[par]
        for pc,w in enumerate(pp['code']):
            x=instruction(w,pc)
            if x['op']=='CLOSURE' and x['bx']==int(idx):
                print('BINDING',par); show(pp,pc-9,pc+3)
    for pc,w in enumerate(p['code']):
        x=instruction(w,pc)
        idx=x['bx'] if x['op']=='LOADK' else x['c'] if x['op'] in ('GETTABUP','GETFIELD') or x['op']=='SELF' and x['k'] else x['b'] if x['op'] in ('SETFIELD','SETTABUP') else None
        if idx in keys:
            print('XREF',p['constants'][idx]['value']); show(p,pc-5,pc+14)
