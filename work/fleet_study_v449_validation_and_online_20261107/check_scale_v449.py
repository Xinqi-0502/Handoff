"""V449 adapter correctness and evidence gate; numerical work only by explicit CLI."""
from pathlib import Path
import argparse,json,time,traceback
from scale_sources_v449 import P,V447,V448,METHODS,MAP,sha,load,dump,append,require,validate_sources,load_modules,run_search
import dp_adapter_v449 as adapter
MICRO=V447/'instances/micro_01/INPUTS.json'

def check_result(sp,dp,spec,row,opt,wall_ms):
    require(row['H2']>=opt,'Below exact optimum')
    require(row['remaining_bound'] is None or row['remaining_bound']<=opt,'Bad lower certificate')
    gap=None if row['remaining_bound'] is None else row['H2']-row['remaining_bound']
    require(row['certified_gap']==gap and row['certified_optimal']==(gap==0),'Certificate identity')
    require(not row['certified_optimal'] or row['H2']==opt,'False proof')
    require(abs(row['setup_seconds']+row['initial_seconds']+row['search_seconds']-row['elapsed_seconds'])<=1e-7,'Timer partition')
    require(row['expanded']==row['expanded_phase0']+row['expanded_phase1'],'Phase counts')
    last_time=-1;last_H2=None;checks=0
    for x in row['trace']:
        require(last_time<=x['seconds']<=row['elapsed_seconds']+1e-7,'Trace time')
        require(last_H2 is None or x['H2']<last_H2,'Strict incumbent improvements')
        require(sp.ref.replay_plan(spec,x['plan'],sp.Watchdog(15))==x['H2'],'Independent reference trace replay')
        require(dp.replay_plan(spec,x['plan'],max_seconds=15)==x['H2'],'Frozen DP action replay')
        last_time=x['seconds'];last_H2=x['H2'];checks+=1
    require(last_H2==row['H2'],'Final trace')
    if row['arm']=='TOPOLOGICAL_DP':
        require(row['stats']['proposed_bound_used'] is False and row['stats']['incumbent_pruning_used'] is False,'DP algorithm changed')
        require(row['remaining_bound']==(row['H2'] if row['certified_optimal'] else spec['t0']),'DP conservative certificate')
        require(row['stats']['partial_expansions'] in (0,1),'DP partial expansion count')
        require(row['root_bound_seconds']==0,'No hidden proposed-bound computation')
    literal={str(ms):min((x['H2'] for x in row['trace'] if x['seconds']<=ms/1000),default=None) for ms in (100,500,1000)}
    if wall_ms is not None:
        literal['actual_cap']=min((x['H2'] for x in row['trace'] if x['seconds']<=wall_ms/1000),default=None)
        require(abs(row['overrun_seconds']-max(0,row['elapsed_seconds']-wall_ms/1000))<=1e-7,'Overrun accounting')
    return checks,literal

def run_checks(args):
    sources=validate_sources();all_cases=load(MICRO)
    require(0<=args.start<args.stop<=24 and args.stop-args.start<=4,'Use 1..4 micro cases per fresh batch')
    run=(args.run if args.run.is_absolute() else P/args.run).resolve()
    require(P in run.parents and not run.exists(),'Fresh V449 check output')
    run.mkdir(parents=True);started=time.perf_counter();active=None
    try:
        require(sha(MICRO)==load(P/'Scale_Source_Manifest.json')['inputs']['micro'],'Micro input changed')
        sp,dp,helper=load_modules();specs=all_cases[args.start:args.stop]
        dump(run/'INPUTS.json',specs)
        dump(run/'PROTOCOL.json',dict(sources=sources,micro_sha256=sha(MICRO),start=args.start,stop=args.stop,
            methods=METHODS,dp_timecaps_ms=[0.001,1,1000],same_initial_required=True,
            no_performance_inference=True,oracle_self_comparison_not_independence=True))
        for s in specs:
            active=s['case'];case_started=time.perf_counter()
            oracle=sp.ref.ReferenceOracle(s,sp.Watchdog(30));opt=oracle.suffix(oracle.initial())
            refdp=dp.solve(s,max_seconds=15)
            require(refdp['status']=='PASS' and refdp['optimum_H2']==opt,'Independent exhaustive vs original structural DP')
            append(run/'ORACLES.jsonl',dict(case=active,optimum_H2=opt,exhaustive_states=len(oracle.memo),
                original_structural_dp=refdp,validation_scope='Separate exhaustive timed-prefix algorithm versus DP; DP adapter/oracle share source'))
            initials=[];initialplans=[];nsolves=ntrace=0
            for method in METHODS:
                require(time.perf_counter()-case_started<90,'Case correctness watchdog')
                row=adapter.solve(s,dp,wall_ms=None) if method=='DP_ADAPTER' else run_search(sp,s,method,sp.Watchdog(15),wall_ms=None)
                require(row['H2']==opt and row['certified_optimal'],'Unlimited optimum mismatch')
                n,literal=check_result(sp,dp,s,row,opt,None);ntrace+=n;nsolves+=1
                initials.append(row['trace'][0]['H2']);initialplans.append(tuple(row['trace'][0]['plan']))
                append(run/'CHECKS.jsonl',dict(case=active,method=method,kind='unlimited',trace_replays=n,literal=literal,result=row))
            require(len(set(initials))==1 and len(set(initialplans))==1,'Common greedy value/plan mismatch')
            for cap in (0.001,1,1000):
                row=adapter.solve(s,dp,wall_ms=cap)
                n,literal=check_result(sp,dp,s,row,opt,cap);ntrace+=n;nsolves+=1
                require(row['trace'][0]['H2']==initials[0] and tuple(row['trace'][0]['plan'])==initialplans[0],'Timed DP initialization mismatch')
                append(run/'CHECKS.jsonl',dict(case=active,method='DP_ADAPTER',kind='timecap',wall_ms=cap,trace_replays=n,literal=literal,result=row))
            append(run/'CASE_COMPLETE.jsonl',dict(case=active,status='PASS',solution_checks=nsolves,trace_replays=ntrace,
                same_initial_value=initials[0],same_initial_plan=list(initialplans[0]),exact_optimum=opt))
            print(json.dumps(dict(case=active,status='PASS')),flush=True)
        require(validate_sources()==sources,'Source changed')
        result=dict(status='PASS',cases=len(specs),start=args.start,stop=args.stop,sources=sources,seconds=time.perf_counter()-started)
        dump(run/'SUMMARY.json',result);dump(run/'PROCESS_COMPLETE.json',result)
    except BaseException as exc:
        failure=dict(status='FAIL',case=active,error=repr(exc),traceback=traceback.format_exc())
        dump(run/'FAILURE.json',failure);dump(run/'PROCESS_COMPLETE.json',failure);raise

def jsonlines(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def validate_gate(path):
    path=Path(path);path=path/'GATE.json' if path.is_dir() else path
    gate=load(path);require(gate['status']=='PASS' and gate['sources']==validate_sources(),'V449 gate status/source')
    require(gate['micro_sha256']==sha(MICRO),'Gate micro identity')
    require(set(gate['case_ids'])=={s['case'] for s in load(MICRO)} and len(gate['case_ids'])==24,'Full micro coverage')
    for name,digest in gate['evidence_sha256'].items():require(sha(Path(name))==digest,('Gate evidence changed',name))
    require(load(path.parent/'PROCESS_COMPLETE.json')['status']=='PASS','Gate completion')
    return gate

def assemble(args):
    out=(args.out if args.out.is_absolute() else P/args.out).resolve()
    require(P in out.parents and not out.exists(),'Fresh gate output');out.mkdir(parents=True)
    try:
        sources=validate_sources();selection=args.runs_json if args.runs_json.is_absolute() else P/args.runs_json
        runs=load(selection);runs=runs['runs'] if isinstance(runs,dict) else runs
        folders=[(Path(x) if Path(x).is_absolute() else P/x).resolve() for x in runs]
        require(len(folders)==len(set(folders)),'Duplicate check runs');ids=[];hashes={str(selection):sha(selection)}
        micro=load(MICRO)
        for folder in folders:
            require(P in folder.parents and not (folder/'FAILURE.json').exists(),'Invalid/failed check run')
            done=load(folder/'PROCESS_COMPLETE.json');protocol=load(folder/'PROTOCOL.json')
            require(done['status']=='PASS' and done==load(folder/'SUMMARY.json'),'Check completion')
            require(protocol['sources']==sources and protocol['micro_sha256']==sha(MICRO),'Checked source/input')
            specs=micro[protocol['start']:protocol['stop']]
            require(load(folder/'INPUTS.json')==specs and len(specs)==done['cases'],'Checked input coverage')
            cases=jsonlines(folder/'CASE_COMPLETE.jsonl');records=jsonlines(folder/'CHECKS.jsonl');oracles=jsonlines(folder/'ORACLES.jsonl')
            require({x['case'] for x in cases}=={s['case'] for s in specs} and len(cases)==len(specs),'Case records')
            require({x['case'] for x in oracles}=={s['case'] for s in specs} and len(oracles)==len(specs),'Oracle records')
            require(len(records)==12*len(specs),'Check matrix size')
            for c in cases:
                require(c['status']=='PASS' and c['solution_checks']==12 and c['trace_replays']>=12,'Per-case checks')
                rr=[r for r in records if r['case']==c['case']]
                require({r['method'] for r in rr if r['kind']=='unlimited'}==set(METHODS) and sum(r['kind']=='unlimited' for r in rr)==9,'All nine unlimited methods')
                require({r.get('wall_ms') for r in rr if r['kind']=='timecap'}=={0.001,1,1000} and sum(r['kind']=='timecap' for r in rr)==3,'DP deadline checks')
                ids.append(c['case'])
            for f in folder.glob('*.json*'):hashes[str(f)]=sha(f)
        require(len(ids)==24 and len(set(ids))==24 and set(ids)=={s['case'] for s in micro},'Exactly all 24 micro cases')
        gate=dict(status='PASS',sources=sources,micro_sha256=sha(MICRO),case_ids=ids,evidence_sha256=hashes,
            scope='Adapter initial parity, exhaustive optimum, trace replay, timecap/certificate/timers; frozen V448 gate remains required')
        dump(out/'GATE.json',gate);dump(out/'PROCESS_COMPLETE.json',dict(status='PASS',cases=24,gate_sha256=sha(out/'GATE.json')))
    except BaseException as exc:
        failure=dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc());dump(out/'FAILURE.json',failure);dump(out/'PROCESS_COMPLETE.json',failure);raise

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True)
    c=sub.add_parser('check');c.add_argument('--start',type=int,required=True);c.add_argument('--stop',type=int,required=True);c.add_argument('--run',type=Path,required=True)
    a=sub.add_parser('assemble');a.add_argument('--runs-json',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();run_checks(args) if args.mode=='check' else assemble(args)
if __name__=='__main__':main()
