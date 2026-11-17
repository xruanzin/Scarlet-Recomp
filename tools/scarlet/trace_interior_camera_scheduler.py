"""Read-only Scarlet camera scheduler and controller call-chain inspection.

The analysis works on the user's private decoded Scarlet 4.0.0 main.blua.
It never writes bytecode or enables any runtime/gameplay patch. The reported
method registration proves a static call relationship, not which interior
camera instance runs in live gameplay.
"""
import argparse
import hashlib
import json
from pathlib import Path

from inspect_lua_steps import Chunk, instruction
from inspect_interior_camera import EXPECTED_SHA256
from trace_interior_camera_state import root_class_registrations, EXPECTED_CLASS

SCHEDULER_PATH = '0.17518'
CONTROLLER_PATH = '0.17567'
CONTROLLER_METHOD = 'FC0150FC2959FFA71'
SMOOTHING_INITIALIZER = '0.17566'
FIXED_SECONDS = 1.0 / 30.0


def identify_root_registration(root, path):
    index = int(path.split('.')[1])
    matches = []
    for pc, word in enumerate(root['code']):
        op = instruction(word, pc)
        if op['op'] != 'CLOSURE' or op['bx'] != index:
            continue
        # The generated Haxe binding pattern is:
        # GETUPVAL r68,LOADK r69=class,GETTABLE,LOADK r69='prototype',
        # GETTABLE,LOADK r69=member,CLOSURE r70,SETTABLE.
        before = [instruction(root['code'][i], i) for i in range(pc - 6, pc)]
        if [x['op'] for x in before] != [
                'GETUPVAL', 'LOADK', 'GETTABLE', 'LOADK',
                'GETTABLE', 'LOADK']:
            continue
        if pc + 1 >= len(root['code']) or instruction(root['code'][pc+1], pc+1)['op'] != 'SETTABLE':
            continue
        k_cls = before[1]['bx']
        k_proto = before[3]['bx']
        k_method = before[5]['bx']
        constants = root['constants']
        if any(k >= len(constants) for k in (k_cls, k_proto, k_method)):
            continue
        if constants[k_proto]['value'] != 'prototype':
            continue
        matches.append(dict(root_pc=pc,
                            class_hash=constants[k_cls]['value'],
                            method_hash=constants[k_method]['value']))
    if len(matches) != 1:
        raise ValueError(f'Expected one generated binding for {path}, found {len(matches)}')
    return matches[0]


def verify_scheduler(p):
    if len(p['code']) != 37 or p['params'] != 2:
        raise ValueError('Camera scheduler function shape differs')
    constants = [k for k in p['constants']
                 if k['tag'] == 19
                 and k['bits'] == '111111111111a13f']
    if len(constants) != 1 or constants[0]['offset'] != 0x7efc05:
        raise ValueError('Unexpected scheduler 1/30 constant or its offset')
    op = [instruction(w, i) for i, w in enumerate(p['code'])]
    # Last instructions from the original Codex disassembly: scheduler
    # delegates its dt and accumulated count to the camera method.
    expected = {
        32: ('SELF', 3, 0, None),
        33: ('MOVE', 5, 2, None),
        34: ('GETI', 6, 0, 22),
        35: ('CALL', 3, 4, 1),
    }
    for pc, (operation, a, b, c) in expected.items():
        x = op[pc]
        if x['op'] != operation or x['a'] != a or x['b'] != b or (
            c is not None and x['c'] != c
        ):
            raise ValueError(f'Camera scheduler delegation differs at PC {pc}')
    if not op[32]['k'] or p['constants'][op[32]['c']]['value'] != CONTROLLER_METHOD:
        raise ValueError('Scheduler calls a different method')
    return dict(
        one_thirtieth_constant=hex(constants[0]['offset']),
        fixed_step_s=FIXED_SECONDS,
        dispatch_pc=32,
        dispatch_member=CONTROLLER_METHOD,
        delta_argument='scheduler parameter 1 (register 1 via register 2)',
        integer_count_argument='scheduler self[22]',
        accumulator_field_candidates=[
            {'pc': x['pc'], 'op': x['op'], 'field': x['b'] if x['op'] == 'SETI' else x['c']}
            for x in op if x['op'] in ('GETI', 'SETI')
            and ((x['b'] if x['op'] == 'SETI' else x['c']) in (21, 22))
            and (x['op'] != 'GETI' or x['b'] == 0)
            and (x['op'] != 'SETI' or x['a'] == 0)
        ],
    )


def analyze(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError('Different Lua digest; do not infer an offset')
    protos = Chunk(data).protos
    lookup = {p['path']: p for p in protos}
    root = lookup['0']
    scheduler = verify_scheduler(lookup[SCHEDULER_PATH])
    registered = {
        name: identify_root_registration(root, name)
        for name in (SCHEDULER_PATH, SMOOTHING_INITIALIZER, CONTROLLER_PATH)
    }
    methods = root_class_registrations(root)
    if methods[CONTROLLER_PATH]['member'] != CONTROLLER_METHOD:
        raise ValueError('Camera class method identity changed')
    if registered[CONTROLLER_PATH]['class_hash'] != EXPECTED_CLASS:
        raise ValueError('Camera class identity changed')
    if not (registered[CONTROLLER_PATH]['class_hash'] ==
            registered[SMOOTHING_INITIALIZER]['class_hash']):
        raise ValueError('Camera setter and update no longer share a class')
    return dict(
        status='read_only; static scheduler call chain, not in-game validation',
        lua_sha256=digest,
        registrations=registered,
        scheduler=scheduler,
        controller_call={
            'path': CONTROLLER_PATH,
            'arguments': ['controller self', 'scheduler dt',
                          'scheduler self[22] count'],
        },
        scope_warning=(
            'DO NOT globally change the shared interpolator or all 1/30 '
            'constants. The fixed-step count may influence camera timing '
            'and other code; live indoor tracing is still required.'
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded_main_blua', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.decoded_main_blua), indent=2))


if __name__ == '__main__':
    main()
