"""Exercise re-exec-like ownership and inherited logs without launching the game."""
import pathlib
import sys
import tempfile
import time
from owned_process import OwnedProcess

def check(condition, message):
    if not condition:
        raise AssertionError(message)

root = pathlib.Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='job-test-', dir=root / 'build') as temp:
    path = pathlib.Path(temp)
    for terminate in (False, True):
        with (path / 'stdout.log').open('wb', buffering=0) as out, (path / 'stderr.log').open('wb', buffering=0) as err:
            child = "import time; print('descendant-log', flush=True); time.sleep(%s); print('descendant-done', flush=True)" % (30 if terminate else 3)
            parent = "import subprocess,sys; subprocess.Popen([sys.executable,'-c',%r]); print('parent-log',flush=True)" % child
            proc = OwnedProcess([sys.executable, '-c', parent], path, out, err)
            try:
                deadline = time.monotonic() + 10
                while proc.poll() is None and time.monotonic() < deadline:
                    time.sleep(.02)
                check(proc.poll() == 0, 'parent must exit independently')
                check(proc.accounting()['active_processes'] >= 1, 'descendant must remain owned')
                if terminate:
                    proc.stop()
                else:
                    proc.wait_empty()
                check(proc.accounting()['active_processes'] == 0, 'all descendants must exit before next test')
                check(proc.accounting()['total_processes'] >= 2, 'job must include parent and descendant (plus any venv launcher)')
            finally:
                proc.close()
        logs = (path / 'stdout.log').read_text()
        check('parent-log' in logs, 'parent log missing')
        if not terminate:
            check('descendant-done' in logs, 'log after parent exit missing')
print('PASS: natural descendant exit, inherited logs, and entire-job termination')
