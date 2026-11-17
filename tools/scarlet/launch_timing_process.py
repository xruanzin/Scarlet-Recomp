"""Launch a diagnostic child with real file handles, not parent-owned pipes."""
import argparse
import json
import os
import subprocess
import time
from owned_process import OwnedProcess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--exe', required=True)
p.add_argument('--game', required=True)
p.add_argument('--run', required=True)
p.add_argument('--fps', type=int, choices=(30,60), required=True)
p.add_argument('--seconds', type=int, default=60)
p.add_argument('--save-source')
a = p.parse_args()
run = Path(a.run).resolve()
root = Path(__file__).resolve().parents[2]
if not run.is_relative_to(root / 'build'):
    raise SystemExit('Diagnostic outputs must stay inside experimental build/')
if not 10 <= a.seconds <= 600: raise SystemExit('seconds must be 10..600')
(run / 'build' / 'frames').mkdir(parents=True, exist_ok=True)
data = Path(os.environ['LARECOMP_DATA_ROOT']).resolve()
if not data.is_relative_to(run):
    raise SystemExit('Diagnostic data must stay inside its private run directory')
(data / 'build' / 'frames').mkdir(parents=True, exist_ok=True)
with (run / 'stdout.log').open('wb', buffering=0) as out, (run / 'stderr.log').open('wb', buffering=0) as err:
    proc = OwnedProcess([a.exe, '--play', a.game],run,out,err)
    manifest = dict(pid=proc.pid, run=str(run), fps=a.fps, cwd=str(run), exe=str(Path(a.exe).resolve()),
                    data=str(data), runtime_cwd=str(data), source=a.game, save_source=a.save_source,
                    ownership='job-object', seconds=a.seconds,
                    input_script=os.environ.get('LARECOMP_INPUT'), shots=os.environ.get('LARECOMP_SHOT_AT'),
                    position_frames=os.environ.get('SCARLET_POSITION_TRACE'))
    (run / 'run.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest),flush=True)
    started=time.monotonic()
    try:
        while proc.accounting()['active_processes'] and time.monotonic()-started < a.seconds:
            time.sleep(0.25)
        timed_out=bool(proc.accounting()['active_processes'])
        if timed_out: proc.stop()
        proc.wait_empty()
        manifest.update(exit_code=proc.poll(), timed_out=timed_out, job=proc.accounting(),
                        observed_process_ids=sorted(proc.children),
                        elapsed=time.monotonic()-started)
    finally:
        try:
            manifest['observed_process_ids'] = sorted(proc.children)
            if proc.accounting()['active_processes']:
                proc.stop()
            proc.wait_empty()
            manifest['teardown_complete'] = True
            manifest.update(job=proc.accounting(), exit_code=proc.poll(),
                            elapsed=time.monotonic()-started,
                            timed_out=locals().get('timed_out', False))
        finally:
            proc.close()
            manifest['job_closed']=True
            (run / 'result.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest),flush=True)
