"""Read-only binding investigation for Scarlet's candidate interior camera lerp.

Prints the exact root CLOSURE registration neighborhoods and hashed member
references, using the user's private decoded main.blua. A nearby hashed name
is a candidate binding, NOT proof of a runtime caller or camera ownership.
Never writes game files, save data, or bytecode.
"""
import argparse
import hashlib
import json
from pathlib import Path

from inspect_lua_steps import Chunk, instruction
from inspect_interior_camera import EXPECTED_SHA256, INTERPOLATOR, POSSIBLE_CAMERA_CALLER, FIXED_STEP_SCHEDULER

CAMERA_NAMESPACE = 'CD9AE7C27B00EB066'
INTERPOLATION_MEMBER = 'SF667EA15F51B1676'
TARGET_PATHS = (INTERPOLATOR, POSSIBLE_CAMERA_CALLER, FIXED_STEP_SCHEDULER)

KEY_OPERANDS = {
    'LOADK': 'bx', 'GETTABUP': 'c', 'SETTABUP': 'b',
    'GETFIELD': 'c', 'SETFIELD': 'b', 'EQK': 'b',
}


def constant_at(proto, ins):
    op = ins['op']
    index = None
    if op in KEY_OPERANDS:
        index = ins[KEY_OPERANDS[op]]
    elif op == 'SELF' and ins['k']:
        index = ins['c']
    elif op in ('SETTABLE', 'SETI') and ins['k']:
        index = ins['c']
    if index is None or index >= len(proto['constants']):
        return None
    return proto['constants'][index]['value']


def excerpt(proto, center, before=10, after=12):
    result = []
    for pc in range(max(0, center - before), min(len(proto['code']), center + after + 1)):
        ins = instruction(proto['code'][pc], pc)
        item = dict(pc=pc, op=ins['op'], a=ins['a'], b=ins['b'],
                    c=ins['c'], k=ins['k'], bx=ins['bx'])
        value = constant_at(proto, ins)
        if value is not None:
            item['constant'] = value
        if ins['op'] == 'CLOSURE':
            item['child_path'] = proto['path'] + '.' + str(ins['bx'])
        result.append(item)
    return result


def report(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Decoded Lua SHA-256 differs; stop without guessing bindings')
    parsed = Chunk(data)
    by_name = {p['path']: p for p in parsed.protos}
    if any(name not in by_name for name in TARGET_PATHS):
        raise ValueError('Missing recorded prototype')
    root = by_name['0']
    roots = {}
    for name in TARGET_PATHS:
        # All three were recorded as immediate children of the root function.
        parts = name.split('.')
        if len(parts) != 2:
            raise ValueError('Not a direct root child: ' + name)
        number = int(parts[1])
        locations = [pc for pc, w in enumerate(root['code'])
                     if (ins := instruction(w, pc))['op'] == 'CLOSURE'
                     and ins['bx'] == number]
        roots[name] = [dict(closure_pc=pc, instructions=excerpt(root, pc, 14, 14))
                       for pc in locations[:5]]
        if len(locations) > 5:
            roots[name + '_omitted'] = len(locations) - 5

    # The hypothesized controller explicitly looks up a hashed member at pc31/32,
    # then CALLs four arguments at pc37. This is not yet an identity proof.
    controller = by_name[POSSIBLE_CAMERA_CALLER]
    checks = {
        31: ('GETTABUP', CAMERA_NAMESPACE),
        32: ('GETFIELD', INTERPOLATION_MEMBER),
        37: ('CALL', None),
    }
    for pc, (op, val) in checks.items():
        ins = instruction(controller['code'][pc], pc)
        if ins['op'] != op or (val is not None and constant_at(controller, ins) != val):
            raise ValueError('Candidate controller call site changed')
    call = instruction(controller['code'][37], 37)
    if call['b'] != 5:
        raise ValueError('Expected Lua CALL with four input arguments')

    # Targeted reverse-use scan: constants per prototype rather than scanning
    # raw bytes for strings (which would conflate code, data and other scripts).
    refs = []
    for proto in parsed.protos:
        matching = {k['index']: k['value'] for k in proto['constants']
                    if k['value'] in (CAMERA_NAMESPACE, INTERPOLATION_MEMBER)}
        if not matching:
            continue
        hits = []
        for pc, w in enumerate(proto['code']):
            ins = instruction(w, pc)
            val = constant_at(proto, ins)
            if val in (CAMERA_NAMESPACE, INTERPOLATION_MEMBER):
                hits.append(dict(pc=pc, opcode=ins['op'], member=val))
        if hits:
            refs.append(dict(proto=proto['path'],
                             namespace=any(k['value'] == CAMERA_NAMESPACE for k in proto['constants']),
                             member=any(k['value'] == INTERPOLATION_MEMBER for k in proto['constants']),
                             hits=hits[:12],
                             omitted_hits=max(0, len(hits) - 12)))
    refs.sort(key=lambda x: (not (x['namespace'] and x['member']), x['proto']))
    return {
        'status': 'read_only; static links are candidates, not live camera execution',
        'file_sha256': EXPECTED_SHA256,
        'requested_prototypes': list(TARGET_PATHS),
        'candidate_controller_call': {
            'proto': POSSIBLE_CAMERA_CALLER, 'namespace': CAMERA_NAMESPACE,
            'member': INTERPOLATION_MEMBER,
            'pc_namespace': 31, 'pc_member': 32, 'pc_call': 37,
            'four_arguments': True,
        },
        'root_closure_registration_windows': roots,
        'member_uses': refs[:40],
        'omitted_member_use_prototypes': max(0, len(refs) - 40),
        'limitations': [
            'Closures in the same root neighborhood are not automatically the member receiver.',
            'A registered member may be shared with other subsystems.',
            'No interior gameplay sample or post-physics view transform measured.',
            'No game patch or RomFS modification is performed.',
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('decoded_main_blua', type=Path)
    args = ap.parse_args()
    print(json.dumps(report(args.decoded_main_blua), indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
