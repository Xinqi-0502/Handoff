"""Windows native process memory counters. No native call at module import."""
import ctypes as C
from ctypes import wintypes as W
import os,time

class PROCESS_MEMORY_COUNTERS_EX(C.Structure):
    _fields_=[('cb',W.DWORD),('PageFaultCount',W.DWORD)]+[(name,C.c_size_t) for name in (
        'PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
        'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]

def require(ok,why):
    if not ok:raise AssertionError(why)

def snapshot(handle=None):
    if os.name!='nt':raise RuntimeError('Native Windows counters required')
    require(C.sizeof(PROCESS_MEMORY_COUNTERS_EX)==8+9*C.sizeof(C.c_size_t),'Counter ABI size')
    k=C.WinDLL('kernel32',use_last_error=True);p=C.WinDLL('psapi',use_last_error=True)
    k.GetCurrentProcess.argtypes=[];k.GetCurrentProcess.restype=W.HANDLE
    p.GetProcessMemoryInfo.argtypes=[W.HANDLE,C.POINTER(PROCESS_MEMORY_COUNTERS_EX),W.DWORD]
    p.GetProcessMemoryInfo.restype=W.BOOL
    counters=PROCESS_MEMORY_COUNTERS_EX();counters.cb=C.sizeof(counters)
    if not p.GetProcessMemoryInfo(k.GetCurrentProcess() if handle is None else handle,C.byref(counters),C.sizeof(counters)):
        raise C.WinError(C.get_last_error())
    values={name:int(getattr(counters,name)) for name,_ in counters._fields_ if name!='cb'}
    require(values['PeakWorkingSetSize']>=values['WorkingSetSize'],'Working-set high-water invariant')
    require(values['PeakPagefileUsage']>=values['PagefileUsage'],'Commit high-water invariant')
    return dict(status='OK',pid=os.getpid() if handle is None else None,monotonic_seconds=time.perf_counter(),
        counters_bytes={k:v for k,v in values.items() if k!='PageFaultCount'},page_fault_count=values['PageFaultCount'],
        counter_structure_bytes=C.sizeof(counters),pointer_bits=8*C.sizeof(C.c_void_p),
        semantics='Working set includes resident private and shared pages. PagefileUsage/PrivateUsage are process commit, not actual bytes written to a paging file.',
        peak_reset_performed=False)

def observe_exit(stage,pid,handle):
    try:
        row=snapshot(handle);row['pid']=pid
        # Some Windows versions do not expose useful counters after termination.
        if stage in ('exited','terminated') and row['counters_bytes']['PeakWorkingSetSize']==0:
            return dict(status='UNAVAILABLE',stage=stage,pid=pid,reason='Zero post-exit peak; not interpreted as zero memory')
        row['stage']=stage;return row
    except OSError as exc:
        return dict(status='UNAVAILABLE',stage=stage,pid=pid,error=repr(exc))

def pid_exited(pid):
    """Read-only liveness check; never terminates a process by PID/name."""
    if os.name!='nt':raise RuntimeError('Windows required')
    k=C.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.WaitForSingleObject.restype=W.DWORD
    k.CloseHandle.argtypes=[W.HANDLE];k.CloseHandle.restype=W.BOOL
    handle=k.OpenProcess(0x00100000|0x1000,False,int(pid))
    if not handle:
        error=C.get_last_error()
        if error==87:return True
        raise C.WinError(error)
    try:
        result=k.WaitForSingleObject(handle,0)
        if result==0:return True
        if result==258:return False
        raise C.WinError(C.get_last_error())
    finally:k.CloseHandle(handle)

def counter_self_check():
    """Dedicated 16-MiB committed allocation, page touch and release. Not a solver."""
    k=C.WinDLL('kernel32',use_last_error=True)
    k.VirtualAlloc.argtypes=[C.c_void_p,C.c_size_t,W.DWORD,W.DWORD];k.VirtualAlloc.restype=C.c_void_p
    k.VirtualFree.argtypes=[C.c_void_p,C.c_size_t,W.DWORD];k.VirtualFree.restype=W.BOOL
    size=16*1024*1024;before=snapshot();address=k.VirtualAlloc(None,size,0x3000,0x04)
    if not address:raise C.WinError(C.get_last_error())
    try:
        for offset in range(0,size,4096):C.c_ubyte.from_address(address+offset).value=0xA5
        allocated=snapshot()
        delta=allocated['counters_bytes']['PrivateUsage']-before['counters_bytes']['PrivateUsage']
        require(delta>=size-1024*1024,'Native commit counter did not register the dedicated allocation (1-MiB allowance for unrelated process housekeeping)')
        require(allocated['counters_bytes']['WorkingSetSize']>0,'No resident working set')
    finally:
        if not k.VirtualFree(address,0,0x8000):raise C.WinError(C.get_last_error())
    released=snapshot()
    for field in ('PeakWorkingSetSize','PeakPagefileUsage'):
        require(before['counters_bytes'][field]<=allocated['counters_bytes'][field]<=released['counters_bytes'][field],'Lifetime peak unexpectedly reset')
    return dict(status='PASS',allocation_bytes=size,private_commit_growth_bytes=delta,before=before,allocated=allocated,released=released,
        resident_delta_not_required='OS trimming can change current working set; commit growth and peak invariants are checked',
        no_claim_of_peak_reset=True)
