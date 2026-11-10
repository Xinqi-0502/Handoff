"""V449 seven-method scale benchmark driver. Prepared only until gates/launch."""
from pathlib import Path
import argparse,gc,hashlib,json,os,sys,time,traceback
from scale_sources_v449 import P,V448,METHODS,MAP,sha,load,dump,append,require,validate_sources,load_modules
from check_scale_v449 import validate_gate
import dp_adapter_v449 as adapter

def schedule(case_index):
    result=[]
    for rep in range(3):
        offset=(3*case_index+rep)%7
        result.extend(dict(method=m,repeat=rep,position_within_repeat=j) for j,m in enumerate(METHODS[offset:]+METHODS[:offset]))
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('split',choices=('cost','main'));ap.add_argument('--start',type=int,required=True)
    ap.add_argument('--stop',type=int,required=True);ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--gate',type=Path,required=True)
    args=ap.parse_args()
    run=(args.run if args.run.is_absolute() else P/args.run).resolve()
    require(P in run.parents and not run.exists(),'Fresh V449 benchmark output required')
    require(args.start%4==0 and args.stop%4==0 and 0<args.stop-args.start<=8,'Complete mothers, one or two per block')
    run.mkdir(parents=True);started=time.perf_counter();active={};ok=hard=exact=complete_cases=0
    os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',PYTHONDONTWRITEBYTECODE='1')
    try:
        sources=validate_sources();gate_path=args.gate if args.gate.is_absolute() else P/args.gate
        gate=validate_gate(gate_path);sp,dp,helper=load_modules()
        inp=P/'instances'/('scale_'+args.split+'_01')/'INPUTS.json'
        require(sha(inp)==load(P/'Scale_Source_Manifest.json')['inputs'][args.split],'Frozen benchmark inputs')
        all_cases=load(inp);require(len(all_cases)==(32 if args.split=='cost' else 400),'Frozen input count')
        require(0<=args.start<args.stop<=len(all_cases),'Case range')
        specs=all_cases[args.start:args.stop];require(len({len(s['old']) for s in specs})==1,'Single scale per block')
        dump(run/'INPUTS.json',specs)
        gate_file=gate_path/'GATE.json' if gate_path.is_dir() else gate_path
        dump(run/'PROTOCOL.json',dict(mode=args.split,sources=sources,input_file_sha256=sha(inp),
            start=args.start,stop=args.stop,methods=METHODS,method_map={m:dict(policy=MAP[m][0],basis=MAP[m][1]) for m in METHODS},
            repeats=3,wall_ms=1000,watchdog_seconds=15,oracle_seconds=15,expected_attempts=21*len(specs),
            independent_mothers=len({s['seed'] for s in specs}),related_scenarios=len(specs),
            order='rotation (3*global_case_index+repeat)%7; maximum position-count imbalance one',
            gate_path=str(gate_file),gate_sha256=sha(gate_file),full_micro24_pass=True,
            frozen_V448_solver_unchanged=True,oracle_not_used_as_incumbent=True,
            oracle_independent_of_DP_ADAPTER=False,
            DP_validation='Small separate full timed-prefix exhaustive algorithm plus frozen reference replay; oracle DP shares source',
            initial_rule='all old items greedily by (service completion,item id,node), then a handoff/delivery,b handoff',
            fresh_context_per_call=True,all_setup_initial_queries_trace_certificate_charged=True,
            checkpoint_snapshots=False,profile=False,actual_RAM_measured=False,
            scope='100-mother confirmation inputs for local synthetic H2 model; no whole-fleet SUMO claim'))
        for ci,s in enumerate(specs,args.start):
            active=dict(case=s['case'],stage='validation_oracle')
            before=time.perf_counter();oracle=dp.solve(s,max_seconds=15,max_cache_entries=100000)
            oracle.update(case=s['case'],outside_measured_solves=True,wall_seconds=time.perf_counter()-before,
                independent_of_DP_ADAPTER=False,not_passed_into_benchmark=True)
            append(run/'ORACLES.jsonl',oracle)
            require(oracle['status'] in ('PASS','CENSORED'),'Oracle status')
            opt=oracle['optimum_H2'] if oracle['status']=='PASS' else None
            if opt is not None:
                require(sp.ref.replay_plan(s,oracle['plan'],sp.Watchdog(15))==opt,'Oracle separate reference replay')
                exact+=1
            initials=[];initialplans=[];certified=[]
            for position,slot in enumerate(schedule(ci)):
                method=slot['method'];policy,basis=MAP[method]
                key=dict(case=s['case'],seed=s['seed'],m=len(s['old']),Q=s['Q'],signal=s['signal'],
                    capacity_regime=s['capacity_regime'],method=method,arm=method,policy=policy,bound_basis=basis,
                    repeat=slot['repeat'],position_within_repeat=slot['position_within_repeat'],position_within_case=position,
                    mode=args.split,cohort='three_repeat',input_sha256=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest())
                active.update(stage='solve',method=method,repeat=slot['repeat']);append(run/'ATTEMPTS.jsonl',dict(**key,status='STARTED'))
                gc.collect();before=time.perf_counter()
                try:
                    row=adapter.solve(s,dp,wall_ms=1000,hard_seconds=15) if method=='DP_ADAPTER' else sp.solve_method(s,method,sp.Watchdog(15),wall_ms=1000,profile=False,audit=False,checkpoints=())
                except (sp.ref.PilotTimeout,dp.OracleLimit) as exc:
                    result=dict(**key,outcome='HARD_TIMEOUT',status='HARD_TIMEOUT',seconds=time.perf_counter()-before,
                        wall_budget_ms=1000,hard_limit_seconds=15,error=repr(exc),incumbent_not_recovered=True,not_counted_as_solved=True)
                    append(run/'FAILURES.jsonl',result);append(run/'MEASUREMENTS.jsonl',result)
                    append(run/'ATTEMPTS.jsonl',dict(**key,status='HARD_TIMEOUT'));hard+=1;continue
                active['stage']='verification'
                try:
                    require(row['arm']==policy and row['method']==method and row['bound_basis']==basis,'Method mapping')
                    row=helper.valid_result(sp,dp,s,row,opt)
                    gap=None if row['remaining_bound'] is None else row['H2']-row['remaining_bound']
                    require(row['certified_gap']==gap and row['certified_optimal']==(gap==0),'Certificate identity')
                    if method=='DP_ADAPTER':
                        for x in row['trace']:
                            require(sp.ref.replay_plan(s,x['plan'],sp.Watchdog(15))==x['H2'],'DP trace separate-source replay')
                        row['verification']='FROZEN_REFERENCE_TRACE_REPLAY_AND_SHARED_DP_ORACLE' if opt is not None else 'FROZEN_REFERENCE_TRACE_REPLAY_ONLY'
                        row['oracle_independent_of_this_method']=False
                    else:row['oracle_independent_of_this_method']=True
                except BaseException as exc:
                    append(run/'REJECTED_RESULTS.jsonl',dict(key=key,result=row,error=repr(exc)));raise
                row.update(key);row['outcome']='OK'
                initials.append(row['trace'][0]['H2']);initialplans.append(tuple(row['trace'][0]['plan']))
                if row['certified_optimal']:certified.append(row['H2'])
                append(run/'MEASUREMENTS.jsonl',row);append(run/'ATTEMPTS.jsonl',dict(**key,status='COMPLETE'));ok+=1
            require(len(set(initials))<=1 and len(set(initialplans))<=1,'Common greedy identity across all seven methods')
            require(len(set(certified))<=1,'Contradictory optimal certificates')
            complete_cases+=1
            append(run/'CASE_COMPLETE.jsonl',dict(case=s['case'],oracle_exact=opt is not None,completed_attempts=21))
            print(json.dumps(dict(case=s['case'],complete_cases=complete_cases,total_cases=len(specs),ok=ok,hard=hard)),flush=True)
        require(ok+hard==21*len(specs),'Call matrix incomplete')
        require(validate_sources()==sources and sha(inp)==load(P/'Scale_Source_Manifest.json')['inputs'][args.split],'Sources or inputs changed')
        summary=dict(status='PASS_WITH_CENSORING' if hard else 'PASS',mode=args.split,records=ok,hard_timeouts=hard,
            cases=complete_cases,expected_attempts=21*len(specs),exact_oracles=exact,seconds=time.perf_counter()-started)
        dump(run/'SUMMARY.json',summary);dump(run/'PROCESS_COMPLETE.json',summary)
    except BaseException as exc:
        failure=dict(status='FAIL',active=active,error=repr(exc),traceback=traceback.format_exc(),records=ok,
            hard_timeouts=hard,complete_cases=complete_cases,seconds=time.perf_counter()-started)
        dump(run/'FAILURE.json',failure);dump(run/'PROCESS_COMPLETE.json',failure);raise
if __name__=='__main__':main()
