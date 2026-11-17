"""Summarize observed native position reads, without guessing player identity."""
import argparse
import json
import math
import re
from pathlib import Path
from compare_timing_runs import fields

def summarize(path):
    run_path = path.parent / 'run.json'
    run = json.loads(run_path.read_text(encoding='utf-8')) if run_path.exists() else {}
    hold = re.search(r'(\d+):STICK_UP:(\d+)', run.get('input_script') or '')
    core_bounds = None
    if hold:
        start, duration = map(int, hold.groups())
        # Leave acceleration/deceleration outside the comparison. Input and
        # submission counters can differ slightly; use only the central 60%.
        core_bounds = (start + duration//5, start + duration*4//5)
    groups = {}
    truncated = False
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if '[scarlet-position]' not in line:
            continue
        row = fields(line)
        if 'truncated' in row:
            truncated = True
            continue
        xyz = tuple(float(row[k]) for k in ('x', 'y', 'z'))
        if not all(math.isfinite(v) for v in xyz):
            raise ValueError('Non-finite coordinate in trace')
        key = (row['kind'], row['subject'])
        group = groups.setdefault(key, {})
        # First sample for this subject per submitted frame. Multiple wrappers
        # or Lua queries can return the same transform in a single frame.
        group.setdefault(int(row['frame']), dict(xyz=xyz, wall_ns=int(row['wall_ns'])))
    report = []
    for (kind, subject), frames in groups.items():
        ordered = sorted(frames)
        first, last = frames[ordered[0]], frames[ordered[-1]]
        elapsed = (last['wall_ns'] - first['wall_ns']) / 1e9
        distance = math.dist(first['xyz'], last['xyz'])
        steps = [math.dist(frames[a]['xyz'], frames[b]['xyz']) for a,b in zip(ordered, ordered[1:])]
        moving = [i for i,d in enumerate(steps) if d >= 1e-5]
        motion = None
        if moving:
            start, end = ordered[moving[0]], ordered[moving[-1] + 1]
            duration = (frames[end]['wall_ns'] - frames[start]['wall_ns']) / 1e9
            motion = dict(first_frame=start, last_frame=end, wall_s=duration,
                          path_length=sum(steps[moving[0]:moving[-1]+1]),
                          mean_speed=sum(steps[moving[0]:moving[-1]+1]) / duration if duration > 0 else None)
        core = None
        if core_bounds:
            inside = [f for f in ordered if core_bounds[0] <= f <= core_bounds[1]]
            if len(inside) >= 2:
                duration = (frames[inside[-1]]['wall_ns'] - frames[inside[0]]['wall_ns']) / 1e9
                pairs = [(frames[a]['xyz'], frames[b]['xyz']) for a,b in zip(inside, inside[1:])]
                ground = sum(math.hypot(b[0]-a[0], b[2]-a[2]) for a,b in pairs)
                spatial = sum(math.dist(a,b) for a,b in pairs)
                core = dict(first_frame=inside[0], last_frame=inside[-1], wall_s=duration,
                            horizontal_path=ground, spatial_path=spatial,
                            horizontal_speed=ground/duration if duration>0 else None,
                            spatial_speed=spatial/duration if duration>0 else None)
        report.append(dict(kind=kind, subject=subject, frames=len(ordered),
                           first_frame=ordered[0], last_frame=ordered[-1],
                           first=first['xyz'], last=last['xyz'], elapsed_s=elapsed,
                           displacement=distance, path_length=sum(steps), motion=motion, motion_core=core,
                           stationary_transitions=sum(d < 1e-6 for d in steps)))
    return dict(log=str(path), truncated=truncated,
                subjects=sorted(report, key=lambda r:r['displacement'], reverse=True),
                limitation='Native getter values and setter requests are distinct. Player identity must be established from controlled input and starting position; do not equate every moving object with the player.')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs', nargs='+', type=Path)
    args = p.parse_args()
    print(json.dumps([summarize(path) for path in args.logs], indent=2))
