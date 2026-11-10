"""Own-process lifecycle check only. Never starts SUMO or any numerical solver."""
from pathlib import Path
import argparse,ctypes,hashlib,importlib.util,json,os,subprocess,sys,time,traceback
from ctypes import wintypes as W
ROOT=Path(__file__).resolve().parent
HELPER=ROOT/'run_public_validation.py'
EXPECTED='c50fcb484be5261a6e710371fbe745af1c0cbabd548ff57994febc6bd8acb451'
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def load():
    if hashlib.sha256(HELPER.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Frozen helper mismatch')
    spec=importlib.util.spec_from_file_location('owned_helper',HELPER);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def child(folder,grandchild=False):
    folder=Path(folder);dump(folder/('grandchild_pid.json' if grandchild else 'child_pid.json'),{'pid':os.getpid()})
    if not grandchild:
        p=subprocess.Popen([sys.executable,'-B','-X','utf8',__file__,'--grandchild',str(folder)],cwd=folder,creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(30)
def worker(folder,mode):
    folder=Path(folder);dump(folder/'Worker_Progress.json',{'stage':'entered','time':time.time()});helper=load()
    dump(folder/'Worker_Progress.json',{'stage':'helper_loaded','time':time.time()})
    args=[str(Path(os.environ['SystemRoot'])/'System32'/'cmd.exe'),'/d','/c','exit','0'] if mode=='normal' else [sys.executable,'-B','-X','utf8',str(ROOT/'lifecycle_dummy.py'),str(folder)]
    with (folder/'stdout.txt').open('w',encoding='utf-8') as so,(folder/'stderr.txt').open('w',encoding='utf-8') as se:
        try:
            code=helper.owned_windows_process(args,folder,so,se,20 if mode=='timeout' else 45)
            if code!=0:raise ValueError(('child exit',code))
            if mode!='normal':raise AssertionError('Sleeping child unexpectedly completed')
            dump(folder/'Worker_Result.json',{'status':'PASS','normal_returncode':code})
        except subprocess.TimeoutExpired:
            if mode!='timeout':raise
            dump(folder/'Worker_Result.json',{'status':'PASS','expected_timeout':True})
def main(out):
    out=Path(out).resolve()
    if out.exists() or (ROOT/'lifecycle_checks').resolve() not in out.parents:raise ValueError('Fresh E lifecycle_checks descendant required')
    out.mkdir(parents=True);load()
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.WaitForSingleObject.restype=W.DWORD
    k.TerminateProcess.argtypes=[W.HANDLE,W.UINT];k.TerminateProcess.restype=W.BOOL
    k.CloseHandle.argtypes=[W.HANDLE];k.CloseHandle.restype=W.BOOL
    rows=[]
    try:
        for mode in ('normal','timeout','parent_killed'):
            folder=out/mode;folder.mkdir();handles=[];owner=None
            try:
                with (folder/'worker_stdout.txt').open('w',encoding='utf-8') as so,(folder/'worker_stderr.txt').open('w',encoding='utf-8') as se:
                    owner=subprocess.Popen([sys.executable,'-B','-X','utf8',__file__,'--worker',str(folder),'--mode',mode],cwd=folder,stdout=so,stderr=se,creationflags=subprocess.CREATE_NO_WINDOW)
                    pids=[]
                    if mode!='normal':
                        deadline=time.monotonic()+30
                        for name in ('child_pid.json','grandchild_pid.json'):
                            path=folder/name
                            while not path.exists():
                                if time.monotonic()>deadline or owner.poll() is not None:raise TimeoutError(('Owned child not ready',name,owner.poll()))
                                time.sleep(.02)
                            pid=json.loads(path.read_text())['pid']
                            h=k.OpenProcess(0x00100000|0x1000|0x0001,False,pid)
                            if not h:raise ctypes.WinError(ctypes.get_last_error())
                            handles.append(h);pids.append(pid)
                        if mode=='parent_killed':owner.kill()
                    owner.wait(timeout=60)
                    if mode!='parent_killed' and owner.returncode!=0:raise ValueError(('worker failure',mode,owner.returncode))
                    if mode!='parent_killed':
                        result=json.loads((folder/'Worker_Result.json').read_text());assert result['status']=='PASS'
                    waits=[k.WaitForSingleObject(h,5000) for h in handles]
                    if any(z!=0 for z in waits):raise AssertionError(('Owned descendants survived',mode,waits))
                    rows.append({'mode':mode,'status':'PASS','owner_pid':owner.pid,'owner_returncode':owner.returncode,'owned_descendant_pids':pids,'termination_wait_results':waits})
            finally:
                if owner is not None and owner.poll() is None:owner.kill();owner.wait(timeout=5)
                for h in handles:
                    if k.WaitForSingleObject(h,0)!=0:k.TerminateProcess(h,1);k.WaitForSingleObject(h,5000)
                    k.CloseHandle(h)
        dump(out/'Summary.json',{'status':'PASS','helper_sha256':EXPECTED,'cases':rows,'no_sumo_or_solver_started':True,'scope':'normal return, owned job timeout, abrupt owned parent death including its child and grandchild; no enumeration'})
        dump(out/'PROCESS_COMPLETE.json',{'status':'PASS','cases':len(rows)})
        print(json.dumps({'status':'PASS','cases':len(rows),'out':str(out)}))
    except BaseException as e:
        dump(out/'Failure.json',{'error':repr(e),'traceback':traceback.format_exc(),'completed':rows})
        dump(out/'PROCESS_COMPLETE.json',{'status':'FAIL','cases':len(rows)});raise
if __name__=='__main__':
    os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',PYTHONDONTWRITEBYTECODE='1')
    p=argparse.ArgumentParser();p.add_argument('--worker');p.add_argument('--mode');p.add_argument('--child');p.add_argument('--grandchild');p.add_argument('--out');a=p.parse_args()
    if a.child:child(a.child)
    elif a.grandchild:child(a.grandchild,True)
    elif a.worker:worker(a.worker,a.mode)
    elif a.out:main(a.out)
    else:p.error('Specify explicit operation')
