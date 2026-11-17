"""Focused read-only evidence for movement scheduler and downstream count uses."""
from pathlib import Path
from inspect_lua_steps import Chunk, instruction
names=set('FC0150FC2959FFA71 F19F6CA8D7CAC788A F11CDEDD901912D4B F1E368E897D1BE717 FE8266E5DA7D6F49A FEE379E06C95CAE5F FBAE95341D487C6BF FDDEE52FCC5CCE074 FAB14B4709E63A2F4 F0F68DB6A2102DE2F FC40AE968BAA5C94A'.split())
c=Chunk(Path('build/scarlet-script-analysis/21977-be21e65463b9a98f.blua').read_bytes())
names.update(('FEB6685558281F194','SCAD25230630F7BCB','F2D2358C8818745D2'))
names.update(('S9487238A2BCBB744','SF667EA15F51B1676','FD3CF58695CBD5774'))
root=c.protos[0]
bindings={}
for pc,w in enumerate(root['code']):
    x=instruction(w,pc)
    if x['op']!='CLOSURE': continue
    prev=[instruction(root['code'][i],i) for i in range(max(0,pc-9),pc)]
    ss=[root['constants'][i['bx']]['value'] for i in prev if i['op']=='LOADK']
    bindings['0.'+str(x['bx'])]=ss
for p in c.protos:
    b=bindings.get(p['path'],[])
    if not b or b[-1] not in names: continue
    child=int(p['path'].split('.')[1])
    if not (17500<=child<=18250 or 30600<=child<=30720): continue
    print('\nPROTO',p['path'],hex(p['start']),'params',p['params'],'lines',p['lines'],'BIND',b)
    print('K',[(k['index'],k['value']) for k in p['constants']])
    # all count-taking downstream definitions, but only brief base virtual summaries
    if b[-1]=='FC0150FC2959FFA71' and p['path'] not in ('0.17520','0.17536','0.17567','0.18186'): continue
    for pc,w in enumerate(p['code']):
        x=instruction(w,pc)
        print(pc,x['op'],x['a'],x['b'],x['c'],x['k'],x['bx'])
