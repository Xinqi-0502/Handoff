"""Serial memory jobs or strict explicit wrapper-gate assembly."""
from pathlib import Path
import argparse,json,time,traceback
from memory_common import *

def assemble(selected,out):
    runs=load(selected);runs=runs['runs'] if isinstance(runs,dict) else runs
    out=Path(out).resolve();require(P in out.parents,'Gate location');out.mkdir(parents=True,exist_ok=False)
    evidence={};allcases=[];manifest_hash=None;imports_hash=None;methods=list(PRIMARY+EXTERNAL)
    for raw in runs:
        run=Path(raw);summary=load(run/'PROCESS_COMPLETE.json');require(summary['status']=='PASS' and summary['stage']=='correctness','Wrapper check did not pass')
        if manifest_hash is None:manifest_hash=summary['manifest_sha256']
        require(summary['manifest_sha256']==manifest_hash,'Different manifests');allcases+=summary['case_ids']
        if imports_hash is None:imports_hash=summary['common_import_origins_sha256']
        require(imports_hash is not None and summary['common_import_origins_sha256']==imports_hash,'Common import set differs across wrapper cases')
        rows=[json.loads(x) for x in (run/'MEMORY.jsonl').read_text(encoding='utf-8-sig').splitlines() if x.strip()]
        for case in summary['case_ids']:
            subset=[r for r in rows if r['case']==case]
            require(len(subset)==len(methods) and sorted(r['method'] for r in subset)==sorted(methods),'Wrapper method matrix')
            require(all(r['status']=='OK' and r['validation']['status']=='PASS' and r['solver_result']['certified_optimal'] and r['repeat']==0 for r in subset),'Invalid wrapper row')
            require(all(r['post_solve']['counters_bytes']['PeakWorkingSetSize']>0 for r in subset),'Native endpoint unavailable')
        for name in ('PROTOCOL.json','ORACLES.jsonl','MEMORY.jsonl','CASE_COMPLETE.jsonl','SUMMARY.json','PROCESS_COMPLETE.json'):
            evidence[str(run/name)]=sha(run/name)
    expected=load(P/'freeze_01'/'MICRO.json');require(sorted(allcases)==sorted(s['case'] for s in expected) and len(set(allcases))==len(expected),'Exact declared micro coverage')
    current=P/'freeze_01'/'MANIFEST.json';verify_manifest(current);require(sha(current)==manifest_hash,'Current manifest mismatch')
    gate=dict(status='PASS',manifest_sha256=manifest_hash,evidence=evidence,case_ids=allcases,methods=methods,scope='Three predeclared m3/m4/m5 wrapper cases with independent exhaustive optimum and two replay implementations; frozen upstream 24-case algorithm gates remain separate')
    dump(out/'GATE.json',gate);dump(out/'PROCESS_COMPLETE.json',gate);print('PASS '+str(out))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--jobs',type=Path);ap.add_argument('--selected',type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    require(a.execute,'Explicit execution required')
    if a.selected:require(a.out is not None and a.jobs is None,'Assembly arguments');assemble(a.selected,a.out);return
    require(a.jobs is not None,'Jobs file required');config=load(a.jobs);jobs=config['jobs'];out=Path(config['run']).resolve();require(P in out.parents,'Coordinator location');out.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();done=[]
    try:
        import run_memory
        for job in jobs:
            run_memory.main(['--execute','--job',job]);done.append(job);dump(out/'PROGRESS.json',dict(completed=done))
        dump(out/'PROCESS_COMPLETE.json',dict(status='PASS',jobs=done,seconds=time.perf_counter()-start,meaning='All jobs returned normally; inspect each job PASS versus PASS_WITH_CENSORING'));print('ALL_JOBS_COMPLETE')
    except BaseException as exc:
        dump(out/'FAILURE.json',dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc(),completed=done,seconds=time.perf_counter()-start));raise
if __name__=='__main__':main()

