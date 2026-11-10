"""V448 frozen exploratory radius/PAIR pilot. No numerical work on import."""
from pathlib import Path
import argparse,gc,hashlib,importlib.util,json,os,sys,time,traceback
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
PARENT=P.parent/"fleet_study_v447_random_high_load_20261107"
PRIMARY=("RADIUS","RADIUS_PAIR_LAZY","RADIUS_AWA","NO_BOUND")
AUX=("RADIUS_PAIR_EAGER","ROUTE")
METHODS=PRIMARY+AUX
INPUT_SHA256="b459e02e4173e07787b47e905de193842fc05e4f7c4738315de044a588b7afa1"
INPUT_PATH=P/"instances"/"pilot_01"/"INPUTS.json"
DP_PATH=PARENT/"independent_dp_v447.py"
DP_SHA256="8c59f8695dfa2347b0f8ac5c817aec93c0c41e07c0882d45f099abaf4d9c2431"

def dump(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def append(path,value):
    with path.open("a",encoding="utf-8") as handle:
        handle.write(json.dumps(value,allow_nan=False)+"\n")
        handle.flush()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(ok,detail):
    if not ok:raise AssertionError(detail)

def load_independent():
    require(sha(DP_PATH)==DP_SHA256,"Independent DP source changed")
    spec=importlib.util.spec_from_file_location("v448_pilot_independent_dp",DP_PATH)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def schedule(global_case_index):
    # Primary method positions balance exactly over each eight-case scale block.
    rows=[]
    for repeat in range(3):
        offset=(global_case_index+repeat)%len(PRIMARY)
        order=PRIMARY[offset:]+PRIMARY[:offset]
        rows.extend(dict(repeat=repeat,method=m,cohort="primary",
                         position_within_repeat=j) for j,m in enumerate(order))
    aux=AUX if global_case_index%2==0 else tuple(reversed(AUX))
    rows.extend(dict(repeat=0,method=m,cohort="auxiliary",
                     position_within_repeat=j) for j,m in enumerate(aux))
    return rows

def valid_result(sp,dp,spec,row,opt):
    # All verification is outside solver elapsed; oracle never enters solve args.
    actual=sp.ref.replay_plan(spec,row["plan"],sp.Watchdog(15))
    independent=dp.replay_plan(spec,row["plan"],max_seconds=15)
    require(actual==row["H2"]==independent,("invalid plan",actual,row["H2"],independent))
    if opt is not None:
        require(row["H2"]>=opt,("better than independent oracle",row["H2"],opt))
        require(row["remaining_bound"] is None or row["remaining_bound"]<=opt,
                ("invalid lower certificate",row["remaining_bound"],opt))
        require(not row["certified_optimal"] or row["H2"]==opt,
                ("false optimal certificate",row["H2"],opt))
    row["oracle_H2"]=opt
    row["t0"]=spec["t0"]
    row["H2_duration"]=row["H2"]-spec["t0"]
    row["oracle_duration"]=None if opt is None else opt-spec["t0"]
    row["verification"]="TWO_PLAN_REPLAYS_AND_ORACLE" if opt is not None else "TWO_PLAN_REPLAYS_ONLY"
    row["first_optimal_seconds"]=next((x["seconds"] for x in row["trace"] if x["H2"]==opt),None) if opt is not None else None
    row["first_optimal_expansion"]=next((x["expansion_index"] for x in row["trace"] if x["H2"]==opt),None) if opt is not None else None
    row["evaluation_at_ms"]=[]
    for ms in (100,500,1000):
        value=min((x["H2"] for x in row["trace"] if x["seconds"]<=ms/1000),default=None)
        row["evaluation_at_ms"].append(dict(ms=ms,H2=value,feasible=value is not None,
            regret=None if value is None or opt is None else value-opt))
    cutoff=row["evaluation_at_ms"][-1]
    row["H2_within_wall"]=cutoff["H2"]
    row["regret_within_wall"]=cutoff["regret"]
    row["certified_within_wall_conservative"]=(row["certified_optimal"] and row["elapsed_seconds"]<=1.0)
    require(abs(row["setup_seconds"]+row["initial_seconds"]+row["search_seconds"]-row["elapsed_seconds"])<=1e-7,"Timer sum")
    require(0<=row["root_bound_seconds"]<=row["search_seconds"],"Root timer nesting")
    require(row["expanded"]==row["expanded_phase0"]+row["expanded_phase1"],"Phase counts")
    return row

def oracle(sp,dp,spec,run):
    started=time.perf_counter()
    answer=dp.solve(spec,max_seconds=15,max_cache_entries=100000)
    answer.update(case=spec["case"],outside_measured_solves=True,wall_seconds=time.perf_counter()-started)
    append(run/"ORACLES.jsonl",answer)
    require(answer["status"] in ("PASS","CENSORED"),("unexpected oracle status",answer))
    if answer["status"]=="PASS":
        value=answer["optimum_H2"]
        require(sp.ref.replay_plan(spec,answer["plan"],sp.Watchdog(15))==value,"Oracle reference replay")
        require(dp.replay_plan(spec,answer["plan"],max_seconds=15)==value,"Oracle independent replay")
        return value
    # A censored best feasible plan is never substituted for an exact optimum.
    return None

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("pilot",))
    parser.add_argument("--inputs",type=Path,default=INPUT_PATH)
    parser.add_argument("--run",type=Path,required=True)
    parser.add_argument("--gate",type=Path,required=True)
    parser.add_argument("--start",type=int,default=0)
    parser.add_argument("--stop",type=int,default=8)
    parser.add_argument("--wall-ms",type=float,default=1000)
    parser.add_argument("--hard-seconds",type=float,default=15)
    parser.add_argument("--oracle-seconds",type=float,default=15)
    parser.add_argument("--repeats",type=int,default=3)
    args=parser.parse_args()
    require(args.start in (0,8,16,24) and args.stop==args.start+8,"Use the frozen complete eight-case scale blocks")
    require((args.wall_ms,args.hard_seconds,args.oracle_seconds,args.repeats)==(1000,15,15,3),
            "Pilot budgets and primary repeats are frozen; no tuning flags")
    run=(args.run if args.run.is_absolute() else P/args.run).resolve()
    require(P in run.parents and not run.exists(),"Use a fresh V448 descendant output")
    run.mkdir(parents=True,exist_ok=False)
    os.environ.update(TEMP=r"E:\CodexResearch-xi\temp",TMP=r"E:\CodexResearch-xi\temp",
                      PYTHONDONTWRITEBYTECODE="1")
    started=time.perf_counter()
    active=dict(stage="gate",case=None,method=None,repeat=None)
    count=timeouts=oracles_exact=cases_done=0
    try:
        from micro_gate_v448 import current_sources,validate_gate
        gate=validate_gate(args.gate)
        source_hashes=current_sources()
        require(args.inputs.resolve()==INPUT_PATH.resolve() and sha(INPUT_PATH)==INPUT_SHA256,
                "Only the frozen new 32-scenario input is allowed")
        all_cases=json.loads(INPUT_PATH.read_text(encoding="utf-8-sig"))
        require(len(all_cases)==32 and len({s["seed"] for s in all_cases})==8,"Frozen input count")
        specs=all_cases[args.start:args.stop]
        require(len(specs)==8 and len({len(s["old"]) for s in specs})==1,"Frozen scale block")
        for s in specs:
            m=len(s["old"])
            require(m in (6,8,10,12) and s["seed"] in (9480000+1000*m+1,9480000+1000*m+2)
                    and s["split"]=="v448_radius_pilot","Unexpected seed/size/split")
        import selective_v448 as sp
        dp=load_independent()
        dump(run/"INPUTS.json",specs)
        protocol=dict(mode="pilot",scope="exploratory cost/mechanism; not large-sample confirmation",
            sources=source_hashes,input_file_sha256=INPUT_SHA256,start=args.start,stop=args.stop,
            methods=list(METHODS),primary=list(PRIMARY),aux=list(AUX),
            method_map={m:dict(policy=sp.METHOD_MAP[m][0],basis=sp.METHOD_MAP[m][1]) for m in METHODS},
            primary_repeats=3,aux_repeats=1,wall_ms=1000,hard_seconds=15,oracle_seconds=15,
            independent_mothers=2,paired_scenarios=8,expected_attempts=112,
            gate_path=str(args.gate.resolve()),gate_sha256=sha(args.gate.resolve()/"GATE.json") if args.gate.is_dir() else sha(args.gate.resolve()),
            gate_verified_micro_cases=24,oracle_not_used_as_incumbent=True,
            all_initial_planning_and_bounds_charged=True,profile=False,checkpoints=[],
            primary_order="cyclic (global_case_index+repeat)%4; auxiliaries alternate and run afterward",
            fresh_context_per_call=True,preserve_censoring_and_failures=True)
        dump(run/"PROTOCOL.json",protocol)
        for si,s in enumerate(specs):
            active.update(stage="oracle",case=s["case"],method=None,repeat=None)
            sp.ref.validate_instance(s)
            opt=oracle(sp,dp,s,run)
            oracles_exact+=int(opt is not None)
            initial_values=[];initial_plans=[];certified_values=[]
            for position,slot in enumerate(schedule(args.start+si)):
                method,rep=slot["method"],slot["repeat"]
                policy,basis=sp.METHOD_MAP[method]
                key=dict(case=s["case"],seed=s["seed"],m=len(s["old"]),Q=s["Q"],
                    capacity_regime=s["capacity_regime"],signal=s["signal"],arm=method,
                    method=method,policy=policy,bound_basis=basis,repeat=rep,
                    cohort=slot["cohort"],position_within_repeat=slot["position_within_repeat"],
                    position_within_case=position,mode="pilot",
                    input_sha256=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest())
                active.update(stage="solve",method=method,repeat=rep)
                append(run/"ATTEMPTS.jsonl",dict(**key,status="STARTED"))
                gc.collect()
                before=time.perf_counter()
                try:
                    row=sp.solve_method(s,method,sp.Watchdog(15),wall_ms=1000,
                                        profile=False,audit=False,checkpoints=())
                except sp.ref.PilotTimeout as exc:
                    failure=dict(**key,status="HARD_TIMEOUT",outcome="HARD_TIMEOUT",
                        seconds=time.perf_counter()-before,wall_budget_ms=1000,
                        hard_limit_seconds=15,error=str(exc),incumbent_not_recovered=True,
                        not_counted_as_solved=True)
                    append(run/"FAILURES.jsonl",failure)
                    append(run/"MEASUREMENTS.jsonl",failure)
                    append(run/"ATTEMPTS.jsonl",dict(**key,status="HARD_TIMEOUT"))
                    timeouts+=1
                    continue
                active["stage"]="verification"
                try:
                    require(row["arm"]==policy and row["bound_basis"]==basis and row["method"]==method,
                            "Method mapping mismatch")
                    row=valid_result(sp,dp,s,row,opt)
                except BaseException as exc:
                    append(run/"REJECTED_RESULTS.jsonl",dict(key=key,result=row,error=repr(exc)))
                    raise
                row.update(key)
                row["outcome"]="OK"
                initial_values.append(row["trace"][0]["H2"])
                initial_plans.append(tuple(row["trace"][0]["plan"]))
                if row["certified_optimal"]:certified_values.append(row["H2"])
                append(run/"MEASUREMENTS.jsonl",row)
                append(run/"ATTEMPTS.jsonl",dict(**key,status="COMPLETE"))
                count+=1
            require(len(set(initial_values))<=1 and len(set(initial_plans))<=1,
                    "Common initialization changed across methods")
            require(len(set(certified_values))<=1,"Contradictory certified optimum values")
            cases_done+=1
            append(run/"CASE_COMPLETE.jsonl",dict(case=s["case"],oracle_exact=opt is not None,
                   completed_attempts=14))
            print(json.dumps(dict(case=s["case"],cases_done=cases_done,cases_total=8,
                                  records=count,hard_timeouts=timeouts)),flush=True)
        require(count+timeouts==112,"Frozen block attempt count")
        require(current_sources()==source_hashes and sha(INPUT_PATH)==INPUT_SHA256,
                "Sources/inputs changed during batch")
        status="PASS_WITH_CENSORING" if timeouts else "PASS"
        summary=dict(status=status,mode="pilot",records=count,hard_timeouts=timeouts,
            cases=cases_done,expected_attempts=112,exact_oracles=oracles_exact,
            seconds=time.perf_counter()-started)
        dump(run/"SUMMARY.json",summary);dump(run/"PROCESS_COMPLETE.json",summary)
        print(json.dumps(summary),flush=True)
    except BaseException as exc:
        failure=dict(status="FAIL",mode="pilot",active=active,error=repr(exc),
            traceback=traceback.format_exc(),records=count,hard_timeouts=timeouts,
            complete_cases=cases_done,seconds=time.perf_counter()-started)
        dump(run/"FAILURE.json",failure);dump(run/"PROCESS_COMPLETE.json",failure)
        raise

if __name__=="__main__":
    main()

