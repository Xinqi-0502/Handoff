"""Small native-counter and owned-process checks; never imports a solver."""
from pathlib import Path
import argparse,os,subprocess,sys,time,traceback
from memory_common import P,sha,load,dump,require
from native_memory import observe_exit,pid_exited
from owned_process import owned_windows_process

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--execute',action='store_true');a=ap.parse_args(argv)
    require(a.execute,'Explicit execution required');out=a.run.resolve();require(P in out.parents,'Output must be under memory');out.mkdir(parents=True,exist_ok=False)
    os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',PYTHONDONTWRITEBYTECODE='1');sys.dont_write_bytecode=True
    names=('native_memory.py','owned_process.py','memory_common.py','memory_worker.py','check_memory_safety.py');pins={str(P/n):sha(P/n) for n in names}
    start=time.perf_counter();rows=[];dump(out/'PROTOCOL.json',dict(scope='16-MiB native counters, successful exit callback and owned timeout cleanup only; no solver',sources=pins,prior_helper_provenance=load(P/'Helper_Provenance.json')))
    try:
        for mode in ('counter','success','linger'):
            folder=out/mode;folder.mkdir();request=folder/'REQUEST.json';dump(request,dict(mode=mode,worker_source_hashes=pins));observations=[]
            def observer(stage,pid,handle):
                row=observe_exit(stage,pid,handle);observations.append(row);dump(folder/'HANDLE_OBSERVATIONS.json',observations)
            timeout=40 if mode=='linger' else 30;timed_out=False;code=None;begin=time.perf_counter()
            with (folder/'stdout.log').open('wb') as stdout,(folder/'stderr.log').open('wb') as stderr:
                try:code=owned_windows_process([sys.executable,'-B','-X','utf8',str(P/'memory_worker.py'),'--request',str(request),'--execute'],P,stdout,stderr,timeout,observer=observer)
                except subprocess.TimeoutExpired:timed_out=True
            require(any(r['stage']=='started' for r in observations),'Missing initial owned-process observation')
            if mode=='linger':
                require(timed_out,'Timeout test did not time out');desc=load(folder/'DESCENDANT.json')
                # Only read known owned PIDs; never terminate by name/PID.
                deadline=time.perf_counter()+3
                while time.perf_counter()<deadline and not all(pid_exited(desc[k]) for k in ('worker_pid','descendant_pid')):time.sleep(.05)
                require(all(pid_exited(desc[k]) for k in ('worker_pid','descendant_pid')),'Owned Job descendant remained alive')
                require(any(r['stage']=='terminated' for r in observations),'Termination observer missing')
            else:
                require(not timed_out and code==0,'Normal worker failed');result=load(folder/'RESULT.json');require(result['status']=='PASS','Native self-check failed')
                require(any(r['stage']=='exited' for r in observations),'Exit observer missing')
            rows.append(dict(test=mode,status='PASS',exit_code=code,intentional_timeout=timed_out,seconds=time.perf_counter()-begin,observations=observations))
        require(all(sha(path)==h for path,h in pins.items()),'Source changed during checks')
        result=dict(status='PASS',scope='Counter/lifecycle plumbing only; not a solver or memory-performance gate',sources=pins,tests=rows,seconds=time.perf_counter()-start)
        dump(out/'SUMMARY.json',result);dump(out/'PROCESS_COMPLETE.json',result);print('PASS '+str(out),flush=True);return 0
    except BaseException as exc:
        result=dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc(),tests=rows,seconds=time.perf_counter()-start);dump(out/'FAILURE.json',result);dump(out/'PROCESS_COMPLETE.json',result);raise
if __name__=='__main__':raise SystemExit(main())

