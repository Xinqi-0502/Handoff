"""New-seed, paired comparison of the frozen main method and complete search engines."""
from pathlib import Path
import argparse, gc, hashlib, importlib.util, json, os, sys, time, traceback
P=Path(__file__).resolve().parent; ROOT=P.parent; W=ROOT.parent
V449=W/'fleet_study_v449_validation_and_online_20261107'
sys.path.insert(0,str(V449));sys.path.insert(0,str(ROOT/'baseline_replication'))
from scale_sources_v449 import load_modules,run_search
import published_search_v450 as pub
METHODS=('RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def append(p,v):
    with Path(p).open('a',encoding='utf-8') as f:f.write(json.dumps(v,allow_nan=False)+'\n');f.flush()
def check_sources():
    manifest=load(P/'Frozen_Source_Manifest.json')
    for p,h in manifest['files'].items():assert sha(p)==h,('Source drift',p)
    return manifest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('split',choices=('cost','main'));ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
    run=a.run.resolve();assert ROOT in run.parents and not run.exists();run.mkdir(parents=True)
    started=time.perf_counter();active={};rows=hard=completed=0
    try:
        os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',PYTHONDONTWRITEBYTECODE='1')
        manifest=check_sources(); gate=load(manifest['gate'])
        assert gate['status']=='PASS', 'Published-engine correctness gate required'
        inputpath=P/'inputs'/a.split/'INPUTS.json';specs=load(inputpath)
        assert sha(inputpath)==manifest['inputs'][a.split]
        stop=len(specs) if a.stop is None else a.stop
        assert 0<=a.start<stop<=len(specs) and a.start%4==stop%4==0
        specs=specs[a.start:stop];repeats=1 if a.split=='cost' else 3
        sp,dp,_=load_modules();pub.configure_domain(sp)
        save(run/'INPUTS.json',specs)
        save(run/'PROTOCOL.json',dict(status='RUNNING',source_manifest=manifest,split=a.split,start=a.start,stop=stop,methods=METHODS,repeats=repeats,wall_ms=1000,hard_seconds=15,oracle_seconds=15,expected_calls=len(specs)*repeats*len(METHODS),input_sha256=sha(inputpath),source_check_included_in_solver_time=False,common_initial_setup_included=True,gc_outside_solver=True,oracle_outside_solver_and_not_supplied=True,order='rotate by (global_case_index*repeats+repeat)%len(METHODS)',observations='new orders; technical repeats are not independent orders'))
        for ci,s in enumerate(specs,a.start):
            active=dict(case=s['case'],stage='oracle')
            oracle=dp.solve(s,max_seconds=15,max_cache_entries=100000)
            append(run/'ORACLES.jsonl',dict(case=s['case'],result=oracle))
            assert oracle['status'] in ('PASS','CENSORED')
            opt=oracle['optimum_H2'] if oracle['status']=='PASS' else None
            initials=[]
            for rep in range(repeats):
                k=(ci*repeats+rep)%len(METHODS)
                for pos,method in enumerate(METHODS[k:]+METHODS[:k]):
                    key=dict(case=s['case'],seed=s['seed'],m=len(s['old']),Q=s['Q'],signal=s['signal'],capacity_regime=s['capacity_regime'],method=method,repeat=rep,order=pos,input_sha256=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest())
                    active=dict(**key,stage='solve');append(run/'ATTEMPTS.jsonl',dict(**key,status='STARTED'))
                    gc.collect();before=time.perf_counter()
                    try:
                        if method==METHODS[0]:r=run_search(sp,s,method,sp.Watchdog(15),wall_ms=1000)
                        else:r=pub.solve(s,method,watchdog=sp.Watchdog(15),wall_ms=1000,hard_seconds=15,domain_module=sp)
                    except sp.ref.PilotTimeout as exc:
                        fail=dict(**key,status='HARD_TIMEOUT',error=repr(exc),seconds=time.perf_counter()-before)
                        append(run/'FAILURES.jsonl',fail);append(run/'MEASUREMENTS.jsonl',fail);hard+=1;continue
                    # All reference checking follows the measured solver. It is not fed back.
                    active['stage']='verification';last=-1;previous=None
                    for t in r['trace']:
                        assert last<=t['seconds']<=r['elapsed_seconds']+1e-6
                        assert previous is None or t['H2']<previous
                        assert sp.ref.replay_plan(s,t['plan'],sp.Watchdog(15))==t['H2']
                        assert dp.replay_plan(s,t['plan'],max_seconds=15)==t['H2']
                        if opt is not None:assert t['H2']>=opt
                        last=t['seconds'];previous=t['H2']
                    assert previous==r['H2'] and r['trace']
                    initial=(r['trace'][0]['H2'],tuple(r['trace'][0]['plan']));initials.append(initial)
                    lb=r['remaining_bound'];gap=None if lb is None else r['H2']-lb
                    assert r['certified_gap']==gap and r['certified_optimal']==(gap==0)
                    if opt is not None:
                        assert lb is None or lb<=opt
                        assert not r['certified_optimal'] or r['H2']==opt
                    r['literal_quality']={str(ms):min((t['H2'] for t in r['trace'] if t['seconds']<=ms/1000),default=None) for ms in (100,500,1000)}
                    r['first_quality_thresholds']=[]
                    for fraction in (0.,.05,.10):
                        target=None if opt is None else opt+fraction*(opt-s['t0'])
                        hit=next((t for t in r['trace'] if target is not None and t['H2']<=target),None)
                        r['first_quality_thresholds'].append(dict(fraction=fraction,target=target,seconds=None if hit is None else hit['seconds'],within_budget=hit is not None and hit['seconds']<=1))
                    r.update(key);r.update(status='OK',oracle_H2=opt,verification='REFERENCE_AND_DP_PLAN_REPLAY; independent structural oracle value when complete')
                    append(run/'MEASUREMENTS.jsonl',r);append(run/'ATTEMPTS.jsonl',dict(**key,status='COMPLETE'));rows+=1
            assert len(set(initials))<=1, 'Common initial plan differs'
            completed+=1;append(run/'CASE_COMPLETE.jsonl',dict(case=s['case'],status='PASS',oracle_H2=opt))
            print(json.dumps(dict(case=s['case'],completed_cases=completed,expected_cases=len(specs),rows=rows,hard=hard)),flush=True)
        assert rows+hard==len(specs)*repeats*len(METHODS)
        assert check_sources()==manifest
        summary=dict(status='PASS_WITH_CENSORING' if hard else 'PASS',cases=completed,calls=rows,hard_timeouts=hard,seconds=time.perf_counter()-started)
        save(run/'PROCESS_COMPLETE.json',summary);print(json.dumps(summary),flush=True)
    except BaseException as exc:
        fail=dict(status='FAIL',active=active,error=repr(exc),traceback=traceback.format_exc(),cases=completed,calls=rows,seconds=time.perf_counter()-started)
        save(run/'FAILURE.json',fail);save(run/'PROCESS_COMPLETE.json',fail);raise
if __name__=='__main__':main()