"""One fresh owned worker per observation. Explicit execution required."""
from pathlib import Path
import argparse,gc,json,os,subprocess,sys,time,traceback
from memory_common import P,PRIMARY,EXTERNAL,load,dump,sha,require,verify_manifest,load_bundle,solve_selected,memory_semantics
from native_memory import snapshot,counter_self_check

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--request',type=Path,required=True);ap.add_argument('--execute',action='store_true');args=ap.parse_args()
    require(args.execute,'Explicit --execute required');request=load(args.request);out=args.request.resolve().parent
    require(P in out.parents,'Worker output must be under memory directory')
    require(not (out/'RESULT.json').exists(),'Worker result must be new')
    os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',PYTHONDONTWRITEBYTECODE='1');sys.dont_write_bytecode=True
    started=time.perf_counter();dump(out/'STARTED.json',dict(pid=os.getpid(),request_sha256=sha(args.request),mode=request['mode']))
    try:
        for path,h in request['worker_source_hashes'].items():require(sha(path)==h,'Worker source changed')
        mode=request['mode']
        if mode=='counter':dump(out/'RESULT.json',counter_self_check());return 0
        if mode=='success':dump(out/'RESULT.json',dict(status='PASS',pid=os.getpid(),native=snapshot()));return 0
        if mode=='nonzero':dump(out/'RESULT.json',dict(status='INTENTIONAL_NONZERO',pid=os.getpid()));return 7
        if mode=='linger':
            child=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(120)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=0x08000000)
            dump(out/'DESCENDANT.json',dict(worker_pid=os.getpid(),descendant_pid=child.pid,scope='Created by this worker inside the inherited owned Job; no breakaway flag'))
            time.sleep(120);return 0
        require(mode=='solve','Unknown worker mode')
        manifest=verify_manifest(request['manifest']);spec=request['spec'];method=request['method']
        require(set(request)=={'mode','worker_source_hashes','manifest','spec','spec_sha256','method','wall_ms','hard_seconds'},'No oracle/hidden request fields')
        require(method in PRIMARY+EXTERNAL and request['hard_seconds']==15,'Method/watchdog')
        require(sha(args.request)==load(out/'STARTED.json')['request_sha256'],'Request identity')
        require(request['spec_sha256']==__import__('hashlib').sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),'Input identity')
        before_import=snapshot();bundle=load_bundle(manifest);imports_finished=time.perf_counter()
        gc.collect();pre=snapshot();row=None;error=None;outcome='OK';solve_begin=time.perf_counter()
        try:row=solve_selected(bundle,spec,method,request['wall_ms'],request['hard_seconds'])
        except (bundle[1].ref.PilotTimeout,bundle[2].OracleLimit) as exc:outcome='HARD_SOLVE_TIMEOUT';error=repr(exc)
        solve_returned=time.perf_counter()
        # This endpoint precedes validation, JSON serialization and all parent work.
        post=snapshot()
        for key in ('PeakWorkingSetSize','PeakPagefileUsage'):
            require(post['counters_bytes'][key]>=pre['counters_bytes'][key],'Peak reset/inconsistent read')
        result=dict(status=outcome,method=method,case=spec['case'],seed=spec['seed'],m=len(spec['old']),spec_sha256=request['spec_sha256'],
            wall_ms=request['wall_ms'],hard_seconds=15,pid=os.getpid(),memory_semantics=memory_semantics(),
            pre_import=before_import,pre_solve=pre,post_solve=post,
            observed_peak_growth_after_baseline={k:post['counters_bytes'][k]-pre['counters_bytes'][k] for k in ('PeakWorkingSetSize','PeakPagefileUsage')},
            common_import_origins=bundle[-1],bootstrap_seconds=imports_finished-started,external_solve_wall_seconds=solve_returned-solve_begin,
            solver_result=row,error=error,memory_profile_timing_not_primary_speed_evidence=True,oracle_or_replay_executed_in_worker=False)
        dump(out/'RESULT.json',result)
        dump(out/'AFTER_REPORT_MEMORY.json',dict(status='OK',scope='Lifetime high-water after result serialization, before final shutdown',native=snapshot()))
        return 0
    except BaseException as exc:
        dump(out/'FAILURE.json',dict(status='FAIL',pid=os.getpid(),error=repr(exc),traceback=traceback.format_exc(),seconds=time.perf_counter()-started));raise
if __name__=='__main__':raise SystemExit(main())
