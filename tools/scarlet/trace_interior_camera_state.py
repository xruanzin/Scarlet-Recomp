"""Trace Scarlet interior camera smoothing inputs from private Lua bytecode.

Read-only: resolves root class/method registrations for camera candidates,
checks the exact interpolator CALL dataflow and lists possible writes to
self[41] (smoothing strength) and self[42] (previous camera vector).
It does not identify live camera state, patch scripts, or alter save files.
"""
import argparse
import hashlib
import json
from pathlib import Path
from inspect_lua_steps import Chunk, instruction
from inspect_interior_camera import EXPECTED_SHA256, POSSIBLE_CAMERA_CALLER

EXPECTED_CLASS = 'CD00CF28AF6D6C9ED'
EXPECTED_MEMBER = 'FC0150FC2959FFA71'
INTERP_NAMESPACE = 'CD9AE7C27B00EB066'
INTERP_MEMBER = 'SF667EA15F51B1676'
TARGET_FIELDS = (41, 42)


def value(p, row):
    op = row['op']
    idx = row['bx'] if op == 'LOADK' else (
        row['c'] if op in ('GETTABUP', 'GETFIELD') or
        (op == 'SELF' and row['k']) else
        row['b'] if op in ('SETTABUP', 'SETFIELD', 'EQK') else None)
    if idx is None or idx >= len(p['constants']):
        return None
    return p['constants'][idx]['value']


def snippet(p, pc, before=4, after=3):
    rows = []
    for i in range(max(0, pc-before), min(len(p['code']), pc+after+1)):
        row = instruction(p['code'][i], i)
        entry = dict(pc=i, op=row['op'], a=row['a'], b=row['b'], c=row['c'])
        name = value(p, row)
        if name is not None:
            entry['constant'] = name
        rows.append(entry)
    return rows


def root_class_registrations(root):
    # Compiled class prototype methods: GETUPVAL, LOADK class, GETTABLE,
    # LOADK 'prototype', GETTABLE, LOADK method, CLOSURE, SETTABLE.
    result = {}
    for pc in range(6, len(root['code'])-1):
        row = instruction(root['code'][pc], pc)
        if row['op'] != 'CLOSURE':
            continue
        a = [instruction(root['code'][pc-off], pc-off) for off in range(1, 7)]
        nxt = instruction(root['code'][pc+1], pc+1)
        if not (a[0]['op'] == 'LOADK' and a[1]['op'] == 'GETTABLE' and
                a[2]['op'] == 'LOADK' and a[3]['op'] == 'GETTABLE' and
                a[4]['op'] == 'LOADK' and a[5]['op'] == 'GETUPVAL' and
                nxt['op'] == 'SETTABLE'):
            continue
        cls = value(root, a[4])
        if cls != EXPECTED_CLASS or value(root, a[2]) != 'prototype':
            continue
        if not (a[0]['a'] == nxt['b'] and row['a'] == nxt['c'] and
                a[1]['a'] == a[0]['a'] - 1 and
                a[3]['a'] == a[1]['a']):
            continue
        child = '0.' + str(row['bx'])
        result[child] = dict(closure_pc=pc, member=value(root, a[0]))
    return result


def analyze(path):
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Unrecognized decoded Lua: no inferred offsets allowed')
    protos = Chunk(payload).protos
    by_path = {p['path']: p for p in protos}
    root = by_path['0']
    bindings = root_class_registrations(root)
    if POSSIBLE_CAMERA_CALLER not in bindings or bindings[POSSIBLE_CAMERA_CALLER]['member'] != EXPECTED_MEMBER:
        raise ValueError('Controller method registration no longer matches')

    camera = by_path[POSSIBLE_CAMERA_CALLER]
    # PC 33..37: lerp(self[42], vector, self[41], argument #2).
    seq = [instruction(camera['code'][i], i) for i in range(31, 38)]
    expected = ['GETTABUP','GETFIELD','GETI','MOVE','GETI','MOVE','CALL']
    if [r['op'] for r in seq] != expected:
        raise ValueError('Controller lerp CALL instruction sequence differs')
    if (value(camera, seq[0]) != INTERP_NAMESPACE or
        value(camera, seq[1]) != INTERP_MEMBER or
        seq[2]['b'] != 0 or seq[2]['c'] != 42 or
        seq[3]['b'] != 4 or
        seq[4]['b'] != 0 or seq[4]['c'] != 41 or
        seq[5]['b'] != 2 or seq[6]['b'] != 5):
        raise ValueError('Controller camera lerp arguments changed')

    setters = []
    for child, info in sorted(bindings.items(), key=lambda it: int(it[0].split('.')[1])):
        p = by_path.get(child)
        if p is None:
            continue
        for pc, word in enumerate(p['code']):
            row = instruction(word, pc)
            if row['op'] == 'SETI' and row['b'] in TARGET_FIELDS and row['a'] == 0:
                setters.append(dict(method=info['member'], prototype=child,
                                    field=row['b'], pc=pc,
                                    code=snippet(p, pc)))
    references = []
    for p in protos:
        constants = {k['index'] for k in p['constants']
                     if k['value'] == EXPECTED_MEMBER}
        if not constants:
            continue
        for pc, word in enumerate(p['code']):
            row = instruction(word, pc)
            if (row['op'] == 'SELF' and row['k'] and row['c'] in constants or
                row['op'] == 'GETFIELD' and row['c'] in constants):
                references.append(dict(prototype=p['path'], pc=pc,
                                       opcode=row['op'], code=snippet(p, pc, 3, 5)))
                if len(references) >= 30:
                    break
        if len(references) >= 30:
            break
    return {
        'status': 'static-only; no gameplay hook; no script modification',
        'main_blua_sha256': EXPECTED_SHA256,
        'camera_class_hash': EXPECTED_CLASS,
        'camera_method': bindings[POSSIBLE_CAMERA_CALLER],
        'confirmed_call': {
            'method': f'{INTERP_NAMESPACE}.{INTERP_MEMBER}',
            'prototype': POSSIBLE_CAMERA_CALLER, 'pc': 37,
            'arguments': ['self[42] (current camera vector candidate)',
                          'local vector at register 4 (target candidate)',
                          'self[41] (smoothing alpha candidate)',
                          'method parameter 2 (integer step count candidate)'],
        },
        'class_methods_found': len(bindings),
        'self_fields_written': setters[:30],
        'self_fields_omitted': max(0, len(setters)-30),
        'other_calls_to_camera_method': references,
        'notes': [
            'These are Lua register dataflow candidates, not runtime values.',
            'Do not equate the fixed 1/30 scheduler in a different class with the count here without tracing call flow.',
            'A global change to the shared lerp affects other callers.',
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('decoded_main_blua', type=Path)
    args = ap.parse_args()
    print(json.dumps(analyze(args.decoded_main_blua),
                     indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
