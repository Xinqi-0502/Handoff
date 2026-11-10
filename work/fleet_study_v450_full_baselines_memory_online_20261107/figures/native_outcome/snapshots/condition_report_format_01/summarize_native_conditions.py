"""Deferred stdlib-only full-factorial native condition summary. Never selects winning cells."""
from __future__ import annotations
import argparse,collections,hashlib,itertools,json,shutil,traceback
from pathlib import Path
from plot_native_outcome_v450 import (ROOT,CAND,BASE,BUDGETS,EPS,FILES,evidence,points,
    require,load,dump,csvread,csvwrite,num,flag,unique,sha,equal)
CELLS=tuple(itertools.product((0,24),(0,10),(0,2)))

def summarize(analysis):
    casepoints,overall=points(analysis)
    cases=csvread(analysis/"Case_Budget_Results.csv")
    calls=csvread(analysis/"Calls.csv")
    pairs=csvread(analysis/"Pair_Cases.csv")
    allseeds={r["seed"] for r in cases}
    require(len(allseeds)==8,"Expected eight mothers")
    matches=[];summary=[]
    maincalls=[r for r in calls if r["arm"] in (CAND,BASE)]
    require(len(maincalls)==64*2*3*3,"Policy calls coverage")
    require(len({(r["case"],r["arm"],r["budget_ms"],r["rep"]) for r in maincalls})==1152,"Duplicate policy call")
    for ms in BUDGETS:
        for c in [r for r in cases if r["arm"]==CAND and int(r["budget_ms"])==ms]:
            b=unique(cases,case=c["case"],arm=BASE,budget_ms=ms)
            paired=unique(pairs,case=c["case"],budget_ms=ms,left=CAND,right=BASE)
            identities={}
            for arm,case in ((CAND,c),(BASE,b)):
                rr=[r for r in maincalls if r["case"]==c["case"] and r["arm"]==arm and int(r["budget_ms"])==ms]
                require(len(rr)==3 and {int(r["rep"]) for r in rr}=={0,1,2},"Repeated policy identity")
                identities[arm]=[(unique(rr,rep=rep)["signature"],int(unique(rr,rep=rep)["activation_tick"])) for rep in range(3)]
                require((len(set(identities[arm]))==1)==flag(case,"direct_same_plan_and_activation"),"Within-arm stability mismatch")
            both=flag(c,"direct_same_plan_and_activation") and flag(b,"direct_same_plan_and_activation")
            require(flag(paired,"direct_pair")==bool(both and flag(paired,"actual_pair_known")),"Audit direct subset definition")
            matched=sum(x==y for x,y in zip(identities[CAND],identities[BASE]))
            same_distribution=collections.Counter(identities[CAND])==collections.Counter(identities[BASE])
            matches.append(dict(case=c["case"],seed=c["seed"],offset=int(c["offset"]),people=int(c["people"]),
                slow=int(c["slow"]),budget_ms=ms,candidate=CAND,baseline=BASE,
                candidate_within_arm_stable=flag(c,"direct_same_plan_and_activation"),
                baseline_within_arm_stable=flag(b,"direct_same_plan_and_activation"),both_within_arm_stable=both,
                audit_known_direct_subset=flag(paired,"direct_pair"),
                aligned_policy_rep_pairs=3,cross_arm_same_plan_activation_rep_pairs=matched,
                cross_arm_all3_aligned_match=(matched==3),
                cross_arm_execution_distribution_equal=same_distribution,
                stable_cross_arm_same_execution=both and identities[CAND][0]==identities[BASE][0]))
    for offset,people,slow in CELLS:
        for ms in BUDGETS:
            group=[r for r in matches if (r["offset"],r["people"],r["slow"],r["budget_ms"])==(offset,people,slow,ms)]
            require(len(group)==8 and {r["seed"] for r in group}==allseeds,"Every cell must contain all eight mothers")
            ids={r["case"] for r in group}
            for metric in ("customer_flow_J","truck_handoff_wait"):
                gg=[r for r in casepoints if r["budget_ms"]==ms and r["metric"]==metric and r["case"] in ids]
                require(len(gg)==8,"Condition metric coverage")
                known=[r for r in gg if r["known"]]
                count=lambda key:sum(r["result"]==key for r in gg)
                delta_sum=sum(r["paired_change_seconds"] for r in gg) if len(known)==8 else None
                summary.append(dict(offset=offset,people=people,slow=slow,budget_ms=ms,metric=metric,
                    candidate=CAND,baseline=BASE,planned_cases=8,independent_mothers=8,known_pairs=len(known),
                    wins=count("W"),ties=count("T"),losses=count("L"),unknown_pairs=count("U"),
                    full8_paired_change_seconds_sum=delta_sum,full8_mean_paired_change_seconds=delta_sum/8 if delta_sum is not None else None,
                    candidate_within_arm_stable_cases=sum(r["candidate_within_arm_stable"] for r in group),
                    baseline_within_arm_stable_cases=sum(r["baseline_within_arm_stable"] for r in group),
                    both_within_arm_stable_cases=sum(r["both_within_arm_stable"] for r in group),
                    audit_known_direct_subset_cases=sum(r["audit_known_direct_subset"] for r in group),
                    aligned_policy_rep_pairs=24,
                    cross_arm_same_plan_activation_rep_pairs=sum(r["cross_arm_same_plan_activation_rep_pairs"] for r in group),
                    cross_arm_all3_aligned_match_cases=sum(r["cross_arm_all3_aligned_match"] for r in group),
                    cross_arm_execution_distribution_equal_cases=sum(r["cross_arm_execution_distribution_equal"] for r in group),
                    stable_cross_arm_same_execution_cases=sum(r["stable_cross_arm_same_execution"] for r in group)))
    require(len(summary)==48 and len(matches)==192,"Fixed 8 cells x 3 budgets x 2 outcomes")
    for total in overall:
        ss=[r for r in summary if r["budget_ms"]==total["budget_ms"] and r["metric"]==total["metric"]]
        require(sum(r["wins"] for r in ss)==total["wins"] and sum(r["ties"] for r in ss)==total["ties"] and
                sum(r["losses"] for r in ss)==total["losses"] and sum(r["unknown_pairs"] for r in ss)==total["unknown_pairs"],"Condition counts do not reconcile")
        if all(r["full8_paired_change_seconds_sum"] is not None for r in ss):
            require(equal(sum(r["full8_paired_change_seconds_sum"] for r in ss)/64,total["full64_mean_change_seconds"]),"Cell means do not reconcile to overall mean")
        else:require(total["full64_mean_change_seconds"] is None,"Unknown global mean was filled")
    return casepoints,matches,summary

def report(rows):
    result=["# Complete factorial native-outcome summary","",
        "All eight predeclared offset x pedestrian x slow-vehicle cells and all three planning budgets are retained. Each cell contains the same eight independent mothers. These tables do not select favorable conditions or change the protocol.",
        "Changes are shared-quota-gated AWA minus the same AWA engine with RADIUS alone. The underlying case outcomes remain policy-frequency-weighted representative native replays, not three independent simulator repetitions.",
        "A cell mean is present only when all eight physical pairs are known; otherwise it is NA. W/T/L/U always sum to eight. No confidence intervals or inferential tests are introduced.",
        "| Offset | People | Slow | Budget ms | Mean J change (s) | J W/T/L/U | Mean handoff-wait change (s) | Wait W/T/L/U |",
        "|---:|---:|---:|---:|---:|---|---:|---|"]
    fmt=lambda v:"NA" if v is None else f"{v:+.6g}"
    for cell in CELLS:
        for ms in BUDGETS:
            rr=[r for r in rows if (r["offset"],r["people"],r["slow"])==cell and r["budget_ms"]==ms]
            j=next(r for r in rr if r["metric"]=="customer_flow_J");w=next(r for r in rr if r["metric"]=="truck_handoff_wait")
            counts=lambda x:"/".join(str(x[k]) for k in ("wins","ties","losses","unknown_pairs"))
            result.append(f"| {cell[0]} | {cell[1]} | {cell[2]} | {ms} | {fmt(j['full8_mean_paired_change_seconds'])} | {counts(j)} | {fmt(w['full8_mean_paired_change_seconds'])} | {counts(w)} |")
    result.extend(["",
        "Execution-identity counts are in All_Condition_Summary.csv and Execution_Identity_Per_Case.csv. Within-arm stable means all three policy repetitions chose the same signature AND activation tick within that arm. The audit's known direct subset requires both arms to be internally stable plus physical outcomes known; it does not require the two arms to execute the same plan.",
        "Cross-arm matched rep pairs compare the two arms' executed (signature, activation_tick) at the same technical repetition index (denominator 24 per cell). This index match is descriptive, not an independent native replication. Cross-arm execution-distribution equality compares the full three-entry multisets. Stable cross-arm same execution additionally requires both arms internally stable and their common execution identities equal. These counts never filter the outcome cohort.",
        "The actual customer-flow J differs from second-handoff time H2. Truck handoff waiting excludes two transfer services and differs from SUMO waitingTime. This is one frozen decision epoch in synthetic traffic, not a calibrated real-world or continuous-dispatch result."])
    return "\n\n".join(result)+"\n"

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analysis",type=Path,required=True);ap.add_argument("--summary-sha256",required=True)
    ap.add_argument("--out",type=Path,required=True);ap.add_argument("--execute",action="store_true");a=ap.parse_args()
    if not a.execute:raise SystemExit("Prepared only; do not aggregate while the native experiment runs.")
    prep=load(ROOT/"Condition_Preparation_Manifest.json")
    for p,h in prep["source_hashes"].items():require(sha(p)==h,"Prepared condition source drift")
    evidence(a.analysis,a.summary_sha256)
    out=a.out.resolve();require(out.drive.upper()=="E:","E-only output");out.mkdir(parents=True,exist_ok=False)
    try:
        source=out/"source_data";source.mkdir();pins={}
        for name in (*FILES,"Calls.csv","SUMMARY.json","PROCESS_COMPLETE.json","Audit_Source_Hashes.json"):
            shutil.copyfile(a.analysis/name,source/name);pins[name]={"original":str((a.analysis/name).resolve()),"sha256":sha(source/name)}
        casepoints,matches,rows=summarize(source)
        csvwrite(out/"Native_Per_Case_Points.csv",casepoints)
        csvwrite(out/"Execution_Identity_Per_Case.csv",matches)
        csvwrite(out/"All_Condition_Summary.csv",rows)
        (out/"All_Conditions.md").write_text(report(rows),encoding="utf-8")
        for name,item in pins.items():require(sha(a.analysis/name)==item["sha256"],"Audit tables changed")
        dump(out/"Output_Manifest.json",{"status":"PASS","cases":64,"mothers":8,"cells":8,"budgets_ms":list(BUDGETS),
            "summary_rows":48,"source_sha256":sha(__file__),"input_hashes":pins,
            "outputs":{p.name:sha(p) for p in out.iterdir() if p.is_file()},"numeric_measurements_or_simulator_runs":0})
        dump(out/"PROCESS_COMPLETE.json",{"status":"PASS","cases":64,"mothers":8,"all_cells":8,"summary_rows":48})
    except BaseException:
        dump(out/"FAILURE.json",{"status":"FAIL","error":traceback.format_exc()});raise
if __name__=="__main__":main()

