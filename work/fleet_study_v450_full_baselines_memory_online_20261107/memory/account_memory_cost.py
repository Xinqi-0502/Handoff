"""Account for actual memory cost pilot; never imports/runs a solver."""
from pathlib import Path
import argparse,hashlib,json,statistics
P=Path(__file__).resolve().parent
MAIN=('RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def rows(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def require(x,m):
    if not x:raise AssertionError(m)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--approve-under-minutes',type=float,default=45);a=ap.parse_args()
    out=a.out.resolve();require(P in out.parents and not out.exists(),'Fresh E output required');out.mkdir(parents=True)
    manifest=P/'freeze_01/MANIFEST.json';m=load(manifest)
    for f,h in m['sources'].items():require(sha(f)==h,'Source changed')
    selected=load(P/'freeze_01/pilot_selected.json');allrows=[];residuals=[];evidence={};total=0;perrun=[]
    for s in selected:
        run=Path(s);done=load(run/'PROCESS_COMPLETE.json');rr=rows(run/'MEMORY.jsonl')
        require(done['status'] in ('PASS','PASS_WITH_CENSORING') and done['stage']=='pilot','Pilot did not complete')
        require(done['manifest_sha256']==sha(manifest) and len(rr)==done['attempts']==9,'Pilot identity/count')
        require({r['method'] for r in rr}==set(m['primary_methods']) and all(r['repeat']==0 for r in rr),'Pilot method matrix')
        processes=sum(r['parent_process_seconds'] for r in rr);residual=max(0,done['seconds']-processes);residuals.append(residual);total+=done['seconds'];allrows+=rr
        perrun.append(dict(run=str(run),m=rr[0]['m'],seconds=done['seconds'],process_seconds=processes,parent_validation_and_loading_residual_seconds=residual,censored=done['censored']))
        for name in ('PROTOCOL.json','MEMORY.jsonl','ORACLES.jsonl','CASE_COMPLETE.jsonl','SUMMARY.json','PROCESS_COMPLETE.json'):evidence[str(run/name)]=sha(run/name)
    require(len(allrows)==36 and len({r['case'] for r in allrows})==4,'Full prespecified pilot')
    wrapper=[]
    for s in load(P/'freeze_01/correctness_selected.json'):
        run=Path(s);wrapper+=rows(run/'MEMORY.jsonl');evidence[str(run/'MEMORY.jsonl')]=sha(run/'MEMORY.jsonl')
    require(len(wrapper)==12,'Wrapper completeness')
    observed=wrapper+allrows;valid=[r for r in observed if r['status']=='OK']
    overhead=[max(0,r['parent_process_seconds']-r['solver_result']['elapsed_seconds']) for r in valid]
    soft_overrun=max((r['solver_result']['overrun_seconds'] for r in valid if r['method'] in MAIN),default=0)
    # Operational arithmetic, not a probabilistic bound or a promise for future calls.
    estimate=128*(max(overhead)+1+soft_overrun)+32*max(residuals)
    bymethod=[]
    for method in m['primary_methods']:
        rr=[r for r in allrows if r['method']==method];times=[r['parent_process_seconds'] for r in rr]
        bymethod.append(dict(method=method,calls=len(rr),censored=sum(r['status']!='OK' for r in rr),process_seconds_sum=sum(times),process_seconds_median=statistics.median(times),process_seconds_max=max(times)))
    record=dict(status='ACCOUNTED',manifest_sha256=sha(manifest),calls=36,per_run=perrun,per_method=bymethod,pilot_run_seconds_sum=total,
        maximum_observed_process_non_solver_seconds=max(overhead),maximum_observed_main_method_soft_overrun_seconds=soft_overrun,maximum_observed_case_parent_residual_seconds=max(residuals),
        planned_main_cases=32,planned_main_calls=128,main_arithmetic_estimate_seconds=estimate,
        estimate_rule='128*(maximum observed process wall minus solver elapsed + 1s soft budget + observed main-method overrun) + 32*maximum pilot case residual; based on observed wrapper/pilot costs, not a guaranteed upper bound',
        no_selection_by_memory_or_quality=True,all_censored_records_retained=True,evidence=evidence)
    dump(out/'Cost_Run_Accounting.json',record)
    note=['# Native-memory cost accounting','',f"Actual completed cost pilot: 36 calls; summed case-run duration {total:.3f} s. Main workload remains 128 calls over 32 paired scenarios.",'',f"The prespecified arithmetic projection is {estimate/60:.2f} minutes. This uses the slowest observed non-solver process overhead plus the common 1 s budget, observed main-method overrun and parent case residual. It is not a future-runtime guarantee.",'','| Method | Calls | Censored | Sum process seconds | Median | Maximum |','|---|---:|---:|---:|---:|---:|']
    for r in bymethod:note.append(f"| {r['method']} | {r['calls']} | {r['censored']} | {r['process_seconds_sum']:.3f} | {r['process_seconds_median']:.3f} | {r['process_seconds_max']:.3f} |")
    note+=['','Cost was inspected to check execution feasibility. No method/input/budget was selected or changed from memory/quality wins. Solver durations here are from separate memory runs and are not formal speed evidence.']
    (out/'Cost_Run_Accounting.md').write_text('\n'.join(note)+'\n',encoding='utf-8')
    approval=P/'Cost_Approval_01.json';require(not approval.exists(),'Preserve existing cost approval')
    if estimate<=a.approve_under_minutes*60:
        evidence[str(out/'Cost_Run_Accounting.json')]=sha(out/'Cost_Run_Accounting.json')
        dump(approval,dict(status='PASS',manifest_sha256=sha(manifest),evidence=evidence,authorization='Parent explicitly authorized frozen 128-call main after pilot, with notification before proceeding if arithmetic cost exceeds 45 minutes',projected_seconds=estimate,methods=list(MAIN),cases=32,calls=128))
        record['main_authorized_by_existing_instruction']=True
    else:record['main_authorized_by_existing_instruction']=False
    dump(out/'PROCESS_COMPLETE.json',dict(status='PASS',projection_seconds=estimate,approval_written=approval.exists()));print(json.dumps({k:record[k] for k in ('calls','pilot_run_seconds_sum','main_arithmetic_estimate_seconds','main_authorized_by_existing_instruction')}))
if __name__=='__main__':main()
