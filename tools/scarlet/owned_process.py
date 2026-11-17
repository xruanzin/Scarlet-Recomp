"""Windows diagnostic process tree owned by a kill-on-close Job Object.

Create suspended, assign ownership, then resume: even constructor re-execs
cannot escape ownership. Never attaches to an existing process.
"""
import ctypes as C
from ctypes import wintypes as W
import msvcrt
import os
import subprocess
import time

K = C.WinDLL('kernel32', use_last_error=True)
SIZE_T = C.c_size_t
class IO_COUNTERS(C.Structure):
    _fields_ = [(n, C.c_ulonglong) for n in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
class BASIC_LIMIT(C.Structure):
    _fields_ = [('process_time', C.c_longlong), ('job_time', C.c_longlong),
                ('flags', W.DWORD), ('min_ws', SIZE_T), ('max_ws', SIZE_T),
                ('active', W.DWORD), ('affinity', SIZE_T), ('priority', W.DWORD), ('scheduling', W.DWORD)]
class EXTENDED_LIMIT(C.Structure):
    _fields_ = [('basic', BASIC_LIMIT), ('io', IO_COUNTERS),
                ('process_memory', SIZE_T), ('job_memory', SIZE_T),
                ('peak_process', SIZE_T), ('peak_job', SIZE_T)]
class STARTUP(C.Structure):
    _fields_ = [('cb',W.DWORD), ('reserved',W.LPWSTR), ('desktop',W.LPWSTR), ('title',W.LPWSTR),
                ('x',W.DWORD), ('y',W.DWORD), ('cx',W.DWORD), ('cy',W.DWORD),
                ('chars_x',W.DWORD), ('chars_y',W.DWORD), ('fill',W.DWORD), ('flags',W.DWORD),
                ('show',W.WORD), ('reserved_size',W.WORD), ('reserved_ptr',C.c_void_p),
                ('stdin',W.HANDLE), ('stdout',W.HANDLE), ('stderr',W.HANDLE)]
class PROCESS(C.Structure):
    _fields_ = [('process',W.HANDLE), ('thread',W.HANDLE), ('pid',W.DWORD), ('tid',W.DWORD)]

class ACCOUNTING(C.Structure):
    _fields_ = [(n, C.c_longlong) for n in ('user_time', 'kernel_time', 'period_user', 'period_kernel')] + [
        (n, W.DWORD) for n in ('page_faults', 'total_processes', 'active_processes', 'terminated_processes')]

class PROCESS_IDS(C.Structure):
    _fields_ = [('assigned', W.DWORD), ('count', W.DWORD), ('ids', SIZE_T * 256)]

def api(name, restype, *args):
    f = getattr(K,name); f.restype=restype; f.argtypes=args; return f
create_job = api('CreateJobObjectW', W.HANDLE, C.c_void_p, W.LPCWSTR)
set_job = api('SetInformationJobObject', W.BOOL, W.HANDLE, C.c_int, C.c_void_p, W.DWORD)
query_job = api('QueryInformationJobObject', W.BOOL, W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p)
assign = api('AssignProcessToJobObject', W.BOOL, W.HANDLE, W.HANDLE)
create_process = api('CreateProcessW', W.BOOL, W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p,
                     W.BOOL,W.DWORD,C.c_void_p,W.LPCWSTR,C.POINTER(STARTUP),C.POINTER(PROCESS))
resume = api('ResumeThread',W.DWORD,W.HANDLE)
close = api('CloseHandle',W.BOOL,W.HANDLE)
terminate = api('TerminateJobObject',W.BOOL,W.HANDLE,W.UINT)
terminate_process = api('TerminateProcess',W.BOOL,W.HANDLE,W.UINT)
wait = api('WaitForSingleObject',W.DWORD,W.HANDLE,W.DWORD)
exit_code = api('GetExitCodeProcess',W.BOOL,W.HANDLE,C.POINTER(W.DWORD))
open_process = api('OpenProcess',W.HANDLE,W.DWORD,W.BOOL,W.DWORD)

class OwnedProcess:
    def __init__(self, argv, cwd, stdout, stderr):
        self.job = create_job(None,None)
        self.info = PROCESS()
        self.children = {}
        if not self.job: raise C.WinError(C.get_last_error())
        limits = EXTENDED_LIMIT(); limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE
        try:
            if not set_job(self.job,9,C.byref(limits),C.sizeof(limits)):
                raise C.WinError(C.get_last_error())
            with open(os.devnull,'rb') as null:
                files = [null,stdout,stderr]
                handles = [msvcrt.get_osfhandle(f.fileno()) for f in files]
                for h in handles: os.set_handle_inheritable(h,True)
                si=STARTUP(); si.cb=C.sizeof(si); si.flags=0x101; si.show=0
                si.stdin,si.stdout,si.stderr=handles
                try:
                    cmd=C.create_unicode_buffer(subprocess.list2cmdline(argv))
                    if not create_process(str(argv[0]),cmd,None,None,True,4,None,str(cwd),C.byref(si),C.byref(self.info)):
                        raise C.WinError(C.get_last_error())
                finally:
                    for h in handles: os.set_handle_inheritable(h,False)
            if not assign(self.job,self.info.process):
                raise C.WinError(C.get_last_error())
            if resume(self.info.thread) == 0xffffffff:
                raise C.WinError(C.get_last_error())
            close(self.info.thread); self.info.thread=None
        except BaseException:
            if self.info.process: terminate_process(self.info.process,1)
            self.close()
            raise

    @property
    def pid(self): return self.info.pid

    def poll(self):
        result=wait(self.info.process,0)
        if result == 258: return None
        if result != 0: raise C.WinError(C.get_last_error())
        code=W.DWORD()
        if not exit_code(self.info.process,C.byref(code)): raise C.WinError(C.get_last_error())
        return code.value

    def stop(self):
        self.capture_children()
        if self.job and not terminate(self.job,124): raise C.WinError(C.get_last_error())
        self.wait_empty()

    def capture_children(self):
        ids = PROCESS_IDS()
        if not query_job(self.job, 3, C.byref(ids), C.sizeof(ids), None):
            raise C.WinError(C.get_last_error())
        for pid in ids.ids[:ids.count]:
            if pid not in self.children:
                handle = open_process(0x100000, False, pid)  # SYNCHRONIZE only
                if handle:
                    self.children[pid] = handle

    def accounting(self):
        self.capture_children()
        info = ACCOUNTING()
        if not query_job(self.job, 1, C.byref(info), C.sizeof(info), None):
            raise C.WinError(C.get_last_error())
        return dict(total_processes=info.total_processes, active_processes=info.active_processes,
                    terminated_processes=info.terminated_processes)

    def wait_empty(self, timeout=60):
        deadline = time.monotonic() + timeout
        while self.accounting()['active_processes']:
            if time.monotonic() >= deadline:
                raise TimeoutError('Diagnostic Job still has active processes; do not start another run')
            time.sleep(0.025)
        # Job accounting reaches zero before process teardown releases inherited
        # file handles. Wait for the process objects too, including re-execs.
        for handle in self.children.values():
            remaining = max(0, int((deadline - time.monotonic()) * 1000))
            if wait(handle, remaining) != 0:
                raise TimeoutError('Diagnostic descendant teardown is incomplete')

    def close(self):
        if self.job: close(self.job); self.job=None
        for handle in self.children.values(): close(handle)
        self.children.clear()
        if self.info.thread: close(self.info.thread); self.info.thread=None
        if self.info.process: close(self.info.process); self.info.process=None
