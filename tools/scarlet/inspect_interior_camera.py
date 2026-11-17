"""Inspect the recorded Scarlet 4.0.0 camera-interpolation candidates.

Read-only. Does NOT modify packed Lua, enable any game patch or claim the
controller's runtime identity from an unrelated identifier in a scene file.
Uses the decoded original main.blua from the user's private analysis build.
"""
import argparse
import hashlib
import json
from pathlib import Path

from inspect_lua_steps import Chunk, instruction

EXPECTED_SHA256 = 'c1a4f4e2625912cf0b739a642a79ba3357df0557a544b92da22a6cb139de2815'
INTERPOLATOR = '0.30688'
POSSIBLE_CAMERA_CALLER = '0.17567'
FIXED_STEP_SCHEDULER = '0.17747'


def describe(path: Path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f'Unexpected Scarlet Lua identity: {digest}')
    parsed = Chunk(data)
    by_name = {p['path']: p for p in parsed.protos}
    required = (INTERPOLATOR, POSSIBLE_CAMERA_CALLER, FIXED_STEP_SCHEDULER)
    if any(name not in by_name for name in required):
        raise ValueError('Recorded camera/step prototypes not present')
    interp = by_name[INTERPOLATOR]
    opcodes = [instruction(word, i)['op'] for i, word in enumerate(interp['code'])]
    # Recorded disassembly: four parameters, a repeat loop, and per-axis
    # (target-current)*blend+current. These are guards, not a proof of owner.
    evidence = {2: 'LT', 10: 'SUB', 12: 'MUL', 15: 'ADD',
                19: 'SUB', 21: 'MUL', 24: 'ADD',
                28: 'SUB', 30: 'MUL', 33: 'ADD', 38: 'RETURN1'}
    if interp['params'] != 4 or any(
            i >= len(opcodes) or opcodes[i] != op for i, op in evidence.items()):
        raise ValueError('Interpolation prototype changed; stop before any patch')
    candidate = by_name[POSSIBLE_CAMERA_CALLER]
    scheduler = by_name[FIXED_STEP_SCHEDULER]
    fixed = [k for k in scheduler['constants']
             if k['tag'] == 19 and k['bits'] == '111111111111a13f']
    if len(fixed) != 1:
        raise ValueError('Recorded fixed-step scheduler constant changed')
    return {
        'file': str(path),
        'sha256': digest,
        'interpolator': {
            'prototype': INTERPOLATOR,
            'start': hex(interp['start']),
            'parameters': interp['params'],
            'code_words': len(interp['code']),
            'guarded_ops': evidence,
            'interpretation': 'integer-step 3D lerp candidate; actual caller still needs confirmation',
        },
        'possible_camera_caller': {
            'prototype': POSSIBLE_CAMERA_CALLER,
            'start': hex(candidate['start']),
            'source_debug_name': candidate['source'],
        },
        'fixed_step_scheduler': {
            'prototype': FIXED_STEP_SCHEDULER,
            'step_constant_offset': hex(fixed[0]['offset']),
            'step_seconds': fixed[0]['value'],
        },
        'status': 'read_only; no game patch; no proof of 60 FPS indoor gameplay',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded_main_blua', type=Path)
    args = parser.parse_args()
    print(json.dumps(describe(args.decoded_main_blua), indent=2))


if __name__ == '__main__':
    main()
