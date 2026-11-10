"""Independent stdlib-only V450 memory audit. No measured-module imports or solving."""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, math, statistics, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MEM=ROOT/"memory"
METHODS=("RADIUS_PAIR_AWA_GATED","HZ_AWA_RADIUS","HZ_AWA_RADIUS_PAIR_GATED","ANA_RADIUS")
PAIRS=((METHODS[0],METHODS[1]),(METHODS[2],METHODS[1]),(METHODS[0],METHODS[3]),
       (METHODS[0],METHODS[2]),(METHODS[2],METHODS[3]))
METRICS=("PeakWorkingSetSize","PeakPagefileUsage","PrivateUsage")
PHASES=("pre_import","pre_solve","post_solve")
COUNTERS=("PeakWorkingSetSize","WorkingSetSize","PeakPagefileUsage","PagefileUsage","PrivateUsage")

def require(test,message):
    if not test:raise AssertionError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()
def close(a,b):
    if a is None or b is None:return a is b
    return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-8)
def dump(path,obj):Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def csvout(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
class Reader:
    def __init__(self):self.hashes={}
    def track(self,path):
        p=Path(path).resolve();h=sha(p);old=self.hashes.setdefault(str(p),h)
        require(old==h,("File changed during audit",str(p)));return p
    def read(self,path):return json.loads(self.track(path).read_text(encoding="utf-8-sig"))
    def lines(self,path):return [json.loads(s) for s in self.track(path).read_text(encoding="utf-8-sig").splitlines() if s.strip()]
    def csv(self,path):
        with self.track(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
    def unchanged(self):
        for p,h in self.hashes.items():require(sha(p)==h,("Evidence changed",p))

def arrive(spec,source,target,clock):
    """Independent O(n^2) label-setting scan, no imported network/cache/queue code."""
    n=spec["n_nodes"];distance=[math.inf]*n;distance[source]=clock;settled=set()
    while target not in settled:
        choices=[v for v in range(n) if v not in settled]
        require(choices,"Unreachable replay target")
        u=min(choices,key=lambda v:(distance[v],v))
        require(math.isfinite(distance[u]),"Unreachable replay target")
        settled.add(u)
        for start,end,travel,period,green,offset in spec["edges"]:
            if start!=u:continue
            leave=distance[u]
            if period:
                phase=(leave-offset)%period
                if phase>=green:leave+=period-phase
            distance[end]=min(distance[end],leave+travel)
    return distance[target]

def replay(spec,actions):
    remaining=set(range(len(spec["old"])));position=spec["start_node"];clock=spec["t0"]
    first=False;delivered=False;finished=False
    require(isinstance(actions,list),"Plan is not an action list")
    for action in actions:
        require(not finished,"Action after terminal handoff")
        cargo=sum(spec["old"][j]["weight"] for j in remaining)
        if action.startswith("old:"):
            j=int(action.split(":")[1]);require(j in remaining,"Old identity repeated or unknown")
            item=spec["old"][j];clock=arrive(spec,position,item["node"],clock)+item["service"]
            position=item["node"];remaining.remove(j)
        elif action=="handoff:a":
            require(not first and cargo+spec["wa"]<=spec["Q"],"First transfer infeasible")
            clock=max(arrive(spec,position,spec["hub"],clock),spec["A"])+spec["tau_a"]
            position=spec["hub"];first=True
        elif action=="deliver:a":
            require(first and not delivered,"New-a delivery infeasible")
            clock=arrive(spec,position,spec["a_node"],clock)+spec["a_service"]
            position=spec["a_node"];delivered=True
        elif action=="handoff:b":
            require(first and delivered and cargo+spec["wb"]<=spec["Q"],"Second transfer infeasible")
            clock=arrive(spec,position,spec["hub"],clock)+spec["tau_b"]
            position=spec["hub"];finished=True
        else:raise AssertionError(("Unknown replay action",action))
    require(finished,"Incomplete replay")
    return clock

def native(snapshot,pid):
    require(snapshot["status"]=="OK" and snapshot["pid"]==pid,"Native snapshot identity")
    require(snapshot["peak_reset_performed"] is False,"Lifetime peak reset claim")
    require(snapshot["pointer_bits"] in (32,64),"Pointer width")
    require(snapshot["counter_structure_bytes"]==8+9*(snapshot["pointer_bits"]//8),"Counter ABI")
    c=snapshot["counters_bytes"]
    require(all(isinstance(v,int) and not isinstance(v,bool) and v>=0 for v in c.values()),"Counter units")
    require(all(c[k]>0 for k in COUNTERS),"Missing/zero live counter endpoint")
    require(c["PeakWorkingSetSize"]>=c["WorkingSetSize"],"Working-set peak invariant")
    require(c["PeakPagefileUsage"]>=c["PagefileUsage"],"Commit peak invariant")
    require(isinstance(snapshot["page_fault_count"],int) and snapshot["page_fault_count"]>=0,"Page faults")
    return c

def check_solver(spec,row,opt):
    s=row["solver_result"];v=row["validation"]
    require(v["status"]=="PASS" and v["validation_location"]=="Parent only, after native measurement endpoint","Parent validation evidence")
    require(v["oracle_H2"]==opt and s["method"]==row["method"],"Solver/target identity")
    require(isinstance(s["H2"],int) and s["H2"]>=spec["t0"],"Objective domain")
    require(s["trace"],"Missing trace")
    prior_t=-1;prior_H=math.inf;replays=0
    for event in s["trace"]:
        require(math.isfinite(event["seconds"]) and prior_t<=event["seconds"]<=s["elapsed_seconds"]+1e-6,"Trace clock")
        require(event["H2"]<prior_H,"Non-improving incumbent trace")
        require(replay(spec,event["plan"])==event["H2"],"Independent action replay failed")
        require(0<=event["expansion_index"]<=s["expanded"],"Trace expansion range")
        prior_t=event["seconds"];prior_H=event["H2"];replays+=1
    require(s["H2"]==prior_H and s["plan"]==s["trace"][-1]["plan"],"Final/trace mismatch")
    require(s["trace"][0]["expansion_index"]==0 and v["initial_H2"]==s["trace"][0]["H2"],"Initial identity")
    lb=s["remaining_bound"];gap=s["certified_gap"]
    if lb is None:require(gap is None and not s["certified_optimal"],"Unknown certificate incorrectly used")
    else:
        require(math.isfinite(lb) and gap==s["H2"]-lb and gap>=0,"Certificate algebra")
        require(s["certified_optimal"]==(gap==0),"Certificate flag")
        if opt is not None:require(lb<=opt<=s["H2"],"Saved exact oracle/certificate inequality")
    if opt is not None:
        require(s["H2"]>=opt,"Solution beats saved exact optimum")
        if s["certified_optimal"]:require(s["H2"]==opt,"False certificate")
    for key in ("setup_seconds","initial_seconds","search_seconds","elapsed_seconds"):
        require(math.isfinite(s[key]) and s[key]>=0,("Timer",key))
    require(abs(s["setup_seconds"]+s["initial_seconds"]+s["search_seconds"]-s["elapsed_seconds"])<.02,"Timer decomposition")
    require(close(s["overrun_seconds"],max(0,s["elapsed_seconds"]-1)),"Soft-overrun identity")
    ontime=bool(s["certified_optimal"] and s["elapsed_seconds"]<=1)
    require(v["certified_by_1s"]==ontime,"On-time proof")
    quality={ms:min((e["H2"] for e in s["trace"] if e["seconds"]<=ms/1000),default=None) for ms in (100,500,1000)}
    require(all(v["literal_H2_at_ms"][str(ms)]==q for ms,q in quality.items()),"Literal deadline quality")
    flat=dict(H2_end=s["H2"],oracle_H2=opt,proof_by_1s=ontime,elapsed_seconds=s["elapsed_seconds"],
              soft_overrun_seconds=s["overrun_seconds"],expanded=s["expanded"],
              initial_H2=s["trace"][0]["H2"],initial_optimal=(s["trace"][0]["H2"]==opt) if opt is not None else None,
              certified_at_return=s["certified_optimal"],remaining_bound=lb,
              independent_replayed_trace_plans=replays)
    flat.update({"H2_"+str(ms)+"ms":q for ms,q in quality.items()})
    return flat,(s["trace"][0]["H2"],s["trace"][0]["plan"])

def inspect_worker(rd,run,index,spec,row,manifest_path,manifest,opt):
    method=row["method"];folder=run/f"{index:03d}_0_{method}"
    request=rd.read(folder/"REQUEST.json")
    allowed={"mode","worker_source_hashes","manifest","spec","spec_sha256","method","wall_ms","hard_seconds"}
    require(set(request)==allowed and request["mode"]=="solve","Hidden worker request fields")
    require(request["spec"]==spec and request["spec_sha256"]==digest(spec),"Worker input identity")
    require(request["method"]==method and request["wall_ms"]==1000 and request["hard_seconds"]==15,"Worker budget")
    require(Path(request["manifest"]).resolve()==manifest_path.resolve(),"Worker manifest path")
    localpins={p:h for p,h in manifest["sources"].items() if Path(p).parent==MEM}
    require(request["worker_source_hashes"]==localpins,"Worker local source closure")
    handles=rd.read(folder/"HANDLE_OBSERVATIONS.json")
    require(handles==row["handle_observations"] and len(handles)==2,"Owned process lifecycle")
    require(handles[0]["stage"]=="started" and handles[1]["stage"] in ("exited","terminated"),"Lifecycle order")
    pid=handles[0]["pid"];require(pid>0 and handles[1]["pid"]==pid,"Owned handle PID")
    for obs in handles:
        require(obs["status"] in ("OK","UNAVAILABLE"),"Optional handle snapshot status")
        if obs["status"]=="UNAVAILABLE":require("counters_bytes" not in obs,"Unavailable counters filled")
    flat=dict(case=spec["case"],seed=spec["seed"],m=len(spec["old"]),Q=spec["Q"],
              signal=spec["signal"],capacity_regime=spec["capacity_regime"],method=method,repeat=0,
              status=row["status"],pid=pid,worker_folder=str(folder),
              native_endpoint_available=False,proof_by_1s=None,oracle_H2=None,saved_oracle_H2=opt,
              post_exit_counter_status=handles[-1]["status"],parent_process_seconds=row["parent_process_seconds"])
    require(row["process_hard_seconds"]==60,"Process startup+solver watchdog")
    if row["status"]=="HARD_PROCESS_TIMEOUT":
        require(row["solver_result"] is None and row["native_memory"] is None and row["incumbent_not_recovered"],"Timeout padding")
        require(row["exit_code"] is None and handles[-1]["stage"]=="terminated","Hard process termination")
        if (folder/"STARTED.json").exists():
            started=rd.read(folder/"STARTED.json");require(started["pid"]==pid and started["request_sha256"]==sha(folder/"REQUEST.json"),"Partial start identity")
        return flat,None,None
    require(row["exit_code"]==0 and handles[-1]["stage"]=="exited","Completed worker exit")
    started=rd.read(folder/"STARTED.json");worker=rd.read(folder/"RESULT.json")
    require(started==dict(pid=pid,request_sha256=sha(folder/"REQUEST.json"),mode="solve"),"Fresh worker request/PID")
    require(all(row.get(k)==v for k,v in worker.items()),"Controller altered worker result")
    require(row["pid"]==pid and row["spec_sha256"]==digest(spec),"Native worker identity")
    require(row["memory_semantics"]==manifest["semantics"],"Changed memory semantics")
    require(row["oracle_or_replay_executed_in_worker"] is False and row["memory_profile_timing_not_primary_speed_evidence"] is True,"Measurement contamination")
    require(row["wall_ms"]==1000 and row["hard_seconds"]==15,"Returned budget")
    clocks=[];previous=None
    for phase in PHASES:
        snap=row[phase];c=native(snap,pid);clocks.append(snap["monotonic_seconds"])
        if previous:
            for metric in METRICS[:2]:require(c[metric]>=previous[metric],"Peak decreased")
        flat.update({phase+"_"+k:c[k] for k in COUNTERS});previous=c
    require(clocks==sorted(clocks),"Native endpoint order")
    for metric in METRICS[:2]:
        growth=row["post_solve"]["counters_bytes"][metric]-row["pre_solve"]["counters_bytes"][metric]
        require(growth==row["observed_peak_growth_after_baseline"][metric],"Peak-growth arithmetic")
        flat["observed_growth_"+metric]=growth
    after=rd.read(folder/"AFTER_REPORT_MEMORY.json")
    ac=native(after["native"],pid)
    require(after["native"]["monotonic_seconds"]>=clocks[-1],"After-report endpoint order")
    for metric in METRICS[:2]:require(ac[metric]>=previous[metric],"After-report peak decreased")
    flat["native_endpoint_available"]=True
    flat["external_solve_wall_seconds"]=row["external_solve_wall_seconds"]
    imports=row["common_import_origins"]
    require(imports==sorted(set(imports)),"Import origins not a stable unique set")
    require(str(Path(manifest["external_module"]).resolve()) in imports,"Full engine not commonly imported")
    initial=None
    if row["status"]=="OK":
        result,initial=check_solver(spec,row,opt);flat.update(result)
    else:
        require(row["status"]=="HARD_SOLVE_TIMEOUT" and row["solver_result"] is None and row["error"],"Unknown failed status")
        require("validation" not in row,"Censored solve padded as validated")
    return flat,initial,imports

def strata(specs):
    result=[("all","all",set(s["case"] for s in specs))]
    for field in ("m","Q","signal","capacity_regime"):
        values=sorted({str(len(s["old"]) if field=="m" else s[field]) for s in specs})
        for value in values:result.append((field,value,{s["case"] for s in specs if str(len(s["old"]) if field=="m" else s[field])==value}))
    for m,cap,sig in sorted({(len(s["old"]),s["capacity_regime"],s["signal"]) for s in specs}):
        result.append(("m_capacity_signal",f"{m}|{cap}|{sig}",{s["case"] for s in specs if (len(s["old"]),s["capacity_regime"],s["signal"])==(m,cap,sig)}))
    return result

def pair_tables(specs,rows):
    lookup={(r["case"],r["method"]):r for r in rows};cases=[];summary=[]
    for candidate,baseline in PAIRS:
        for spec in specs:
            c=lookup.get((spec["case"],candidate),{});b=lookup.get((spec["case"],baseline),{})
            pair=dict(case=spec["case"],seed=spec["seed"],m=len(spec["old"]),Q=spec["Q"],
                      signal=spec["signal"],capacity_regime=spec["capacity_regime"],candidate=candidate,baseline=baseline,
                      both_proved_by_1s=c.get("proof_by_1s") is True and b.get("proof_by_1s") is True)
            for metric in METRICS:
                cv=c.get("post_solve_"+metric);bv=b.get("post_solve_"+metric)
                pair[metric+"_candidate_bytes"]=cv;pair[metric+"_baseline_bytes"]=bv
                pair[metric+"_ratio"]=cv/bv if cv is not None and bv is not None and bv>0 else None
            cases.append(pair)
        for field,value,ids in strata(specs):
            planned=[p for p in cases if p["candidate"]==candidate and p["baseline"]==baseline and p["case"] in ids]
            for cohort in ("all_native","common_proof_by_1s"):
                eligible=[p for p in planned if cohort=="all_native" or p["both_proved_by_1s"]]
                for metric in METRICS:
                    valid=[p for p in eligible if p[metric+"_ratio"] is not None]
                    cs=sum(p[metric+"_candidate_bytes"] for p in valid) if valid else None
                    bs=sum(p[metric+"_baseline_bytes"] for p in valid) if valid else None
                    ratios=[p[metric+"_ratio"] for p in valid]
                    summary.append(dict(candidate=candidate,baseline=baseline,stratum=field,value=value,cohort=cohort,metric=metric,
                        planned_cases=len(planned),eligible_cases=len(eligible),paired_native_cases=len(valid),unknown_pairs=len(eligible)-len(valid),
                        candidate_bytes_sum=cs,baseline_bytes_sum=bs,ratio_of_sums=cs/bs if bs else None,
                        percent_change=100*(cs/bs-1) if bs else None,median_case_ratio=statistics.median(ratios) if ratios else None,
                        lower=sum(x<1 for x in ratios),equal=sum(x==1 for x in ratios),higher=sum(x>1 for x in ratios)))
    return cases,summary


def method_tables(specs,rows):
    result=[]
    for field,value,ids in strata(specs):
        for method in METHODS:
            rr=[r for r in rows if r["method"]==method and r["case"] in ids]
            endpoints=[r for r in rr if r["native_endpoint_available"]]
            item=dict(stratum=field,value=value,method=method,attempts=len(rr),native_endpoints=len(endpoints),
                valid_solve=sum(r["status"]=="OK" for r in rr),oracle_known=sum(r.get("oracle_H2") is not None for r in rr),
                saved_oracle_known=sum(r.get("saved_oracle_H2") is not None for r in rr),
                proof_by_1s=sum(r.get("proof_by_1s") is True for r in rr),
                literal_feasible_1s=sum(r.get("H2_1000ms") is not None for r in rr),
                literal_optimal_1s=sum(r.get("H2_1000ms") is not None and r.get("oracle_H2") is not None and r["H2_1000ms"]==r["oracle_H2"] for r in rr))
            for phase in PHASES:
                for metric in METRICS+("WorkingSetSize",):
                    values=[r[phase+"_"+metric] for r in endpoints]
                    item[phase+"_"+metric+"_median_bytes"]=statistics.median(values) if values else None
                    item[phase+"_"+metric+"_max_bytes"]=max(values) if values else None
            result.append(item)
    return result

def compare_primary(rd,path,rows,pairs,methods,manifest_hash):
    done=rd.read(path/"PROCESS_COMPLETE.json")
    require(done["status"]=="COMPLETE" and done["observations"]==128 and done["manifest_sha256"]==manifest_hash,"Primary analysis incomplete/different")
    for p,h in rd.read(path/"Source_and_Raw_Hashes.json").items():require(sha(rd.track(p))==h,"Primary recorded hash drift")
    obs=rd.csv(path/"Observations.csv");idx={(r["case"],r["method"]):r for r in obs}
    require(len(idx)==len(obs)==128,"Primary observation matrix")
    checks=0
    def parsed(raw,expected):
        if raw=="":return None
        if isinstance(expected,bool):return raw=="True" if raw in ("True","False") else raw
        if isinstance(expected,(int,float)):return float(raw)
        return raw
    for r in rows:
        other=idx[r["case"],r["method"]]
        for key in ("seed","m","Q","signal","capacity_regime","status","oracle_H2","proof_by_1s","H2_1000ms",
                    *(phase+"_"+metric for phase in PHASES for metric in COUNTERS)):
            expected=r.get(key);actual=parsed(other.get(key,""),expected)
            require(close(expected,actual) if isinstance(expected,(int,float)) and not isinstance(expected,bool) else expected==actual,("Observation mismatch",r["case"],r["method"],key));checks+=1
    for row in rd.csv(path/"Method_Summary.csv"):
        field="all" if row["scale"]=="all" else "m"
        matches=[r for r in methods if r["stratum"]==field and r["value"]==row["scale"] and r["method"]==row["method"]]
        require(len(matches)==1,"Primary method summary mapping")
        ours=matches[0]
        keys=("attempts","native_endpoints","valid_solve","oracle_known","proof_by_1s","literal_feasible_1s","literal_optimal_1s",
              *(phase+"_"+metric+"_"+stat+"_bytes" for phase in PHASES for metric in METRICS+("WorkingSetSize",) for stat in ("median","max")))
        for key in keys:
            require(close(ours[key],parsed(row[key],ours[key])),("Method summary mismatch",row["scale"],row["method"],key));checks+=1
    for name,cohort in (("Pair_Summary.csv","all_native"),("Pair_Summary_Proved_By_1s.csv","common_proof_by_1s")):
        for row in rd.csv(path/name):
            field="all" if row.get("scale","all")=="all" else "m";value=row.get("scale","all")
            matches=[r for r in pairs if r["candidate"]==row["candidate"] and r["baseline"]==row["baseline"]
                     and r["metric"]==row["metric"] and r["cohort"]==cohort and r["stratum"]==field and r["value"]==value]
            require(len(matches)==1,"Primary pair mapping")
            ours=matches[0]
            for key in ("paired_native_cases","candidate_bytes_sum","baseline_bytes_sum","ratio_of_sums","median_case_ratio","lower","equal","higher"):
                require(close(ours[key],parsed(row[key],ours[key])),("Pair summary mismatch",name,key));checks+=1
            if cohort=="common_proof_by_1s":require(int(row["common_on_time_proved_cases"])==ours["eligible_cases"],"Common proof denominator")
    return dict(status="PASS",field_checks=checks,primary_path=str(path))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--selected",type=Path,default=MEM/"freeze_01/main_selected.json")
    ap.add_argument("--out",type=Path,required=True);ap.add_argument("--compare",type=Path);ap.add_argument("--execute",action="store_true");a=ap.parse_args()
    if not a.execute:raise SystemExit("Prepared only. Wait for the serial window, then pass --execute.")
    out=a.out.resolve();require(out.drive.upper()=="E:","E-only output");out.mkdir(parents=True,exist_ok=False)
    rd=Reader();issues=[];rows=[];all_initial={};imports_set=set();replay_count=0
    try:
        manifest_path=MEM/"freeze_01/MANIFEST.json";m=rd.read(manifest_path);mh=sha(manifest_path)
        require(m["status"]=="FROZEN" and m["main_design"]==dict(methods=list(METHODS),repeats=1,calls=128),"Amended design")
        require(rd.read(MEM/"freeze_01/FREEZE_COMPLETE.json")["manifest_sha256"]==mh,"Freeze receipt")
        for section in ("sources","inputs","job_sha256","config_sha256"):
            for p,h in m[section].items():require(sha(rd.track(p))==h,("Frozen hash drift",p))
        for kind in ("external","safety"):
            gate=rd.read(m[kind+"_gate"]);require(sha(m[kind+"_gate"])==m[kind+"_gate_sha256"] and gate["status"]=="PASS","Required gate")
        config=rd.read(MEM/"freeze_01/main_jobs.json");jobs=[rd.read(p) for p in config["jobs"]]
        selected=rd.read(a.selected);selected=selected["runs"] if isinstance(selected,dict) else selected
        require(selected==[j["run"] for j in jobs] and len(selected)==32,"Exact frozen selected main runs")
        require(len({j["offset"] for j in jobs})==32 and sorted(j["offset"] for j in jobs)==list(range(32)),"Exact main offsets")
        specs=rd.read(MEM/"freeze_01/INPUTS.json");require(len(specs)==len({s["case"] for s in specs})==32,"32 distinct cases")
        require(len({s["seed"] for s in specs})==8,"Eight independent mothers")
        require(collections.Counter(len(s["old"]) for s in specs)=={6:8,8:8,10:8,12:8},"Scale allocation")
        for seed in {s["seed"] for s in specs}:
            group=[s for s in specs if s["seed"]==seed]
            require(len(group)==4 and len({(s["capacity_regime"],s["signal"]) for s in group})==4,"Four paired variants per mother")
        fullpath=next(p for p,h in m["inputs"].items() if h==m["parent_main_sha256"]);full=rd.read(fullpath)
        require(specs==[full[i] for base in (0,100,200,300) for i in range(base,base+8)],"Prospective subset identity")
        coordinator=rd.read(Path(config["run"])/"PROCESS_COMPLETE.json")
        require(coordinator["status"]=="PASS" and coordinator["jobs"]==config["jobs"],"Main coordinator incomplete")
        seen=set()
        for runstr,job,jobpath in zip(selected,jobs,config["jobs"]):
            run=Path(runstr);protocol=rd.read(run/"PROTOCOL.json")
            require(protocol==dict(job=job,job_sha256=sha(jobpath),manifest_sha256=mh,sources=m["sources"],semantics=m["semantics"],stage="main"),"Run protocol")
            require(job["methods"]==list(METHODS) and job["repeats"]==1 and job["count"]==1 and job["wall_ms"]==1000 and job["hard_seconds"]==15,"Run design/budget")
            for key in ("correctness_gate","cost_approval"):
                gate=rd.read(job[key]);require(gate["status"]=="PASS" and gate["manifest_sha256"]==mh,"Prerequisite gate/approval")
                for p,h in gate.get("evidence",{}).items():require(sha(rd.track(p))==h,"Gate evidence drift")
            spec=specs[job["offset"]];done=rd.read(run/"PROCESS_COMPLETE.json");summary=rd.read(run/"SUMMARY.json")
            require(done==summary and done["status"] in ("PASS","PASS_WITH_CENSORING"),"Run unsuccessful/incomplete")
            require(done["stage"]=="main" and done["cases"]==1 and done["attempts"]==4 and done["case_ids"]==[spec["case"]],"Completion coverage")
            require(done["manifest_sha256"]==mh and done["source_hashes"]==m["sources"],"Completion source identity")
            require(not (run/"FAILURE.json").exists(),"Run failure marker")
            raw=rd.lines(run/"MEMORY.jsonl");require(len(raw)==4 and {r["method"] for r in raw}==set(METHODS),"Complete method matrix")
            failures=rd.lines(run/"FAILURES.jsonl") if (run/"FAILURES.jsonl").exists() else []
            require(failures==[r for r in raw if r["status"]!="OK"],"Failed observations not retained")
            cc=rd.lines(run/"CASE_COMPLETE.jsonl")
            require(cc==[dict(case=spec["case"],attempts=4,status="PASS",censored=len(failures))],"Case completion")
            require(done["censored"]==len(failures),"Censor count")
            oo=rd.lines(run/"ORACLES.jsonl");require(len(oo)==1 and oo[0]["case"]==spec["case"] and not oo[0]["used_as_incumbent"] and oo[0]["location"]=="parent" and not oo[0]["small_exhaustive_checked"],"Saved independent oracle")
            oracle=oo[0]["result"];opt=oracle["optimum_H2"] if oracle["status"]=="PASS" else None
            if opt is not None:
                require(replay(spec,oracle["plan"])==opt,"Saved oracle plan replay");replay_count+=1
            rotation=job["offset"]%4;order=METHODS[rotation:]+METHODS[:rotation];run_origins=None
            for position,row in enumerate(raw):
                key=(row["case"],row["method"],row["repeat"]);require(key not in seen,"Duplicate observation");seen.add(key)
                require(row["case"]==spec["case"] and row["method"]==order[position] and row["repeat"]==0 and row["order_position"]==position,"Frozen rotation/order")
                require(row["stage"]=="main" and row["m"]==len(spec["old"]) and row["seed"]==spec["seed"] and row["Q"]==spec["Q"] and row["input_sha256"]==digest(spec),"Raw input metadata")
                flat,initial,origins=inspect_worker(rd,run,0,spec,row,manifest_path,m,opt)
                if initial is not None:
                    require(all_initial.setdefault(spec["case"],initial)==initial,"Common initial mismatch")
                    replay_count+=flat["independent_replayed_trace_plans"]
                if origins is not None:
                    oh=hashlib.sha256(json.dumps(origins).encode()).hexdigest();imports_set.add(oh)
                    if row["status"]=="OK" and run_origins is None:run_origins=oh
                    if row["status"]=="OK":require(run_origins==oh,"Within-case imports differ")
                rows.append(flat)
            require(done["common_import_origins_sha256"]==run_origins,"Summary import identity")
        expected={(s["case"],method,0) for s in specs for method in METHODS}
        require(seen==expected and len(rows)==128,"Complete 32x4x1 matrix")
        require(len(imports_set)==1,"Different pre-solve import bundles")
        pair_cases,pair_summary=pair_tables(specs,rows)
        methods=method_tables(specs,rows)
        comparison=compare_primary(rd,a.compare,rows,pair_summary,methods,mh) if a.compare else dict(status="NOT_REQUESTED")
        pidcounts=collections.Counter(r["pid"] for r in rows)
        result=dict(status="PASS",observations=128,cases=32,independent_mothers=8,methods=4,repeats=1,
            native_endpoints=sum(r["native_endpoint_available"] for r in rows),
            failed_or_censored=sum(r["status"]!="OK" for r in rows),unique_observed_pids=len(pidcounts),
            repeated_pid_values=[p for p,c in pidcounts.items() if c>1],
            fresh_lifecycle_records=128,independent_trace_and_saved_oracle_replays=replay_count,
            saved_oracle_scope="Optima are validated saved independent-DP results; no optimization rerun.",
            fresh_pid_scope="Each REQUEST/STARTED/owned-handle lifecycle is matched; Windows may legitimately reuse a PID after exit.",
            common_import_hash=next(iter(imports_set)),comparison=comparison,
            primary_peak_endpoint="Worker post_solve, before replay/serialization; lifetime peak, including any soft overrun.",
            peak_working_set="PeakWorkingSetSize: resident private and shared pages.",
            peak_private_commit="PeakPagefileUsage: peak process commit; not physical pagefile writes.",
            current_private_commit="PrivateUsage: current private commit, not a peak.",
            baseline_subtraction_not_algorithm_exclusive_RAM=True,pilot_or_micro_observations_pooled=False,
            measurement_source_changed=False,solver_or_SUMO_runs=0,manifest_sha256=mh,source_sha256=sha(__file__))
        csvout(out/"Independent_Observations.csv",rows);csvout(out/"Independent_Paired_Cases.csv",pair_cases)
        csvout(out/"Independent_Pair_Summary.csv",pair_summary)
        csvout(out/"Independent_Method_Summary.csv",methods)
        dump(out/"Independent_Memory_Audit.json",result)
        report=["# Independent V450 memory audit","",
            "PASS: 128 planned observations, 32 scenarios, eight independent mother instances; four methods and one fresh process per method/scenario.",
            "This audit imports only the standard library. It checks source/input/job hashes, the complete matrix, owned process lifecycle and native endpoints, controller validation evidence, saved exact-oracle inequalities, and an additional independent scan-based FIFO replay of every available incumbent plan. It performs no optimization or simulator run.",
            "Primary endpoints remain separate: PeakWorkingSetSize is the lifetime resident working-set peak (including shared pages); PeakPagefileUsage is peak process commit; PrivateUsage is current private commit. Baseline snapshots are retained. Their difference is not algorithm-exclusive RAM.",
            "All-native pairs and common-on-time-proof pairs have separate denominators in Independent_Pair_Summary.csv, including m, Q, capacity-regime, signal and joint strata. Censored solver results keep any genuine available native endpoint; missing endpoints remain null. Optional post-exit counters are never substituted for the post-solve primary endpoint.",
            "One process observation per method/case does not estimate process-repeat variability. Lifetime peaks include startup/import history and any soft overrun. Instrumented timing is not substituted for the separate timing study. Micro correctness and the four-scenario cost pilot are not pooled into this main cohort.",
            "Primary-analysis comparison: "+comparison["status"]+".",
            "Independent replay verifies saved plans; the saved exact-oracle status is checked, not independently re-proved by a new exhaustive search."]
        (out/"Independent_Memory_Audit.md").write_text("\n\n".join(report)+"\n",encoding="utf-8")
        rd.unchanged();dump(out/"Source_and_Raw_Hashes.json",rd.hashes)
        dump(out/"Output_Manifest.json",{"source_sha256":sha(__file__),"outputs":{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}})
        dump(out/"PROCESS_COMPLETE.json",{"status":"PASS","observations":128,"primary_comparison":comparison["status"]})
        print(json.dumps(result,indent=2))
    except BaseException as exc:
        dump(out/"FAILURE.json",dict(status="FAIL",error=repr(exc),traceback=traceback.format_exc(),
                                    retained_rows=len(rows),source_sha256=sha(__file__)))
        raise

if __name__=="__main__":main()


