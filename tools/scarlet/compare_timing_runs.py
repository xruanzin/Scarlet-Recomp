"""Compare supplied game-clock time to host time; never certify gameplay speed."""
import argparse
import json
import re
from pathlib import Path

def fields(line):
    return dict(re.findall(r'(\w+)=([^\s]+)', line))

def summarize(run):
    manifest = json.loads((run / 'result.json').read_text(encoding='utf-8'))
    rows = []
    readers = {}
    for line in (run / 'stderr.log').read_text(encoding='utf-8', errors='replace').splitlines():
        row = fields(line)
        if '[scarlet-frame]' in line and 'wall_ns' in row:
            rows.append(row)
        if '[scarlet-timing-read]' in line:
            key = (row['caller'], row['index'])
            readers.setdefault(key, []).append(int(row['step_ns']))
    intervals = []
    for previous, current in zip(rows, rows[1:]):
        wall = int(current['wall_ns']) - int(previous['wall_ns'])
        supplied = int(current['clock1_supplied_ns']) - int(previous['clock1_supplied_ns'])
        steps = int(current['clock1_supplied_steps']) - int(previous['clock1_supplied_steps'])
        if wall <= 0 or supplied < 0 or steps < 0:
            raise ValueError('Non-monotonic counters or process reset in log')
        intervals.append(dict(wall_s=wall / 1e9, supplied_s=supplied / 1e9,
                              ratio=supplied / wall, steps=steps,
                              accepted_fps=float(current['present_accepted_fps']),
                              mean_ms=float(current['mean_ms'])))
    # A long startup/pipeline stall is a different scenario, not steady gameplay.
    steady = [r for r in intervals if r['wall_s'] <= 1.5 and r['accepted_fps'] >= manifest['fps'] * .85]
    def totals(items):
        wall = sum(r['wall_s'] for r in items)
        supplied = sum(r['supplied_s'] for r in items)
        return dict(intervals=len(items), wall_s=wall, supplied_s=supplied,
                    supplied_wall_ratio=supplied / wall if wall else None,
                    supplied_steps=sum(r['steps'] for r in items))
    return dict(run=str(run), target_fps=manifest['fps'], job=manifest.get('job'),
                all_intervals=totals(intervals), near_target_intervals=totals(steady),
                intervals=intervals,
                readers=[dict(caller=c, index=int(i), min_ns=min(v), max_ns=max(v), samples=len(v))
                         for (c,i),v in sorted(readers.items())],
                gameplay_speed='unvalidated',
                limitation='Counts time supplied to clock 1; does not measure completed simulation, displacement, animations or script steps.')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+', type=Path)
    a = p.parse_args()
    print(json.dumps([summarize(run) for run in a.runs], indent=2))
