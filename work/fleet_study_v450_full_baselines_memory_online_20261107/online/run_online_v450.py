"""Gate-protected predeclared V450 single-epoch native online experiment.
Do not execute during another timed experiment. Run under thermal monitor and
job_host_online_v450, which owns the worker and every native SUMO descendant.
Policy timings all finish before native replay. No selected plan is outcome-filtered.
"""
from pathlib import Path
import argparse,json,math,traceback,itertools
import online_model_v450 as model
import published_online_v450 as published
import native_online_v450 as native
from check_online_v450 import read,put,sha,sources,validate_gate
PRIMARY=('HZ_AWA_RADIUS','HZ_AWA_PAIR_GATED')
AUX=('RADIUS','ROUTE','ANA_RADIUS')
BUDGETS=(.01,.05,.2)

def schedule():
    return tuple((arm,b) for b in BUDGETS for arm in PRIMARY)+tuple((arm,.05) for arm in AUX)
def main():
    p=argparse.ArgumentParser();p.add_argument('--definitions',type=Path,required=True)
    p.add_argument('--prefixes',type=Path,required=True);p.add_argument('--gate',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--native-gate',type=Path,required=True);p.add_argument('--pilot',action='store_true');p.add_argument('--native',action='store_true')
    a=p.parse_args();validate_gate(a.gate);definitions=read(a.definitions)
    ng=read(a.native_gate/'GATE.json');nc=read(a.native_gate/'PROCESS_COMPLETE.json')
    if (a.native_gate/'FAILURE.json').exists():raise ValueError('Failed native gate')
    assert nc['status']=='PASS' and nc['gate_sha256']==sha(a.native_gate/'GATE.json')
    assert ng['status']=='PASS' and ng['sources']==sources() and len(ng['checks'])==4
    assert all(x['status']=='PASS' for x in ng['checks'])
    completed=read(a.prefixes/'PROCESS_COMPLETE.json');prefixes=read(a.prefixes/'INPUTS.json')
    if (a.prefixes/'FAILURE.json').exists() or completed['status']!='PASS':raise ValueError('Incomplete or failed native prefixes')
    assert completed['input_sha256']==sha(a.prefixes/'INPUTS.json') and completed['sources']==sources()
    assert prefixes['source_inputs_sha256']==sha(a.definitions)
    assert tuple(definitions['mothers'])==tuple(range(4509001,4509009)) and len(definitions['cases'])==64
    rows=prefixes['cases'];wanted=definitions['pilot_cases'] if a.pilot else [s['case'] for s in definitions['cases']]
    assert [s['case'] for s in rows]==wanted and len(set(wanted))==len(wanted)==(2 if a.pilot else 64)
    base={s['case']:s for s in definitions['cases']}
    for s in rows:
        assert all(s[k]==v for k,v in base[s['case']].items())
        assert sum(s['c']['size'][j] for j in model.old.items(s['c'],'A'))==12
        assert sum(s['c']['size'][j] for j in model.old.items(s['c'],'B'))==12
    frozen=sources();a.out.mkdir(parents=True,exist_ok=False);records=[];physical=[];failures=[]
    protocol=dict(sources=frozen,definitions_sha256=sha(a.definitions),prefix_inputs_sha256=sha(a.prefixes/'INPUTS.json'),
        gate_sha256=sha(a.gate/'GATE.json'),native_gate_sha256=sha(a.native_gate/'GATE.json'),cases=wanted,mothers=len({s['seed'] for s in rows}),
        schedule=schedule(),repeats=3,pilot=a.pilot,native=a.native,objective='All old plus two new customer flow J',
        scope='One frozen decision epoch, not continuous rolling arrivals',
        activation='ceil(total measured planning seconds / 0.2) simulator steps after t=6; old vehicles held; release remains6',
        native_selection='Every distinct chosen plan per case/arm/budget retained; median latency among repetitions of that plan, lower middle then rep ID',
        native_deduplication='Exact case + plan signature + activation tick only',
        deadline_fallback='If no complete action incumbent by deadline, execute mandatory common initializer after full solver return and flag missed deadline',
        statistical_unit='8 mother instances in full cohort; 64 paired conditions; repetitions measure timing variation',
        unpublished_internal_weighted_arms_in_main=False)
    put(a.out/'PROTOCOL.json',protocol)
    try:
        with (a.out/'RESULTS.jsonl').open('x',encoding='utf8') as stream:
            jobs=schedule()
            for i,s in enumerate(rows):
                for rep in range(3):
                    shift=(i+rep)%len(jobs);order=jobs[shift:]+jobs[:shift]
                    for arm,budget in order:
                        r=published.solve(s,arm,budget) if arm in published.METHODS else model.solve(s,arm,budget)
                        plan=r['within_budget_plan'];fallback=plan is None
                        if fallback:plan=r['initial']['plan']
                        # Certification of initialization is only known if a final certificate or strict improvement supplies evidence.
                        initial_equal=abs(r['initial']['J']-r['J'])<=1e-7
                        initial_known_optimal=True if initial_equal and r['certified_forecast_optimal'] else False if not initial_equal else None
                        row=dict(case=s['case'],seed=s['seed'],rep=rep,budget_seconds=budget,**r,
                            executed_plan=plan,executed_signature=model.signature(plan),deadline_fallback=fallback,deadline_status='NO_PLAN_BY_DEADLINE' if fallback else 'PLAN_BY_DEADLINE',
                            activation_tick=model.old.EPOCH+math.ceil(r['elapsed_seconds']*model.old.HZ),
                            initial_known_forecast_optimal=initial_known_optimal)
                        records.append(row);stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');stream.flush()
        # Common feasible initializer, across all methods, budgets, and timing repetitions.
        for s in rows:
            starts={model.signature(r['initial']['plan']) for r in records if r['case']==s['case']}
            costs={round(r['initial']['J'],7) for r in records if r['case']==s['case']}
            assert len(starts)==len(costs)==1
        selected={};selections=[]
        for s in rows:
            for arm,budget in jobs:
                group=[r for r in records if r['case']==s['case'] and r['arm']==arm and r['budget_seconds']==budget]
                assert len(group)==3
                for sig in sorted({r['executed_signature'] for r in group}):
                    same=sorted((r for r in group if r['executed_signature']==sig),key=lambda r:(r['elapsed_seconds'],r['rep']))
                    chosen=same[(len(same)-1)//2]
                    key=(s['case'],sig,chosen['activation_tick'])
                    selected.setdefault(key,(s,chosen))
                    selections.append(dict(case=s['case'],arm=arm,budget_seconds=budget,signature=sig,
                        represented_reps=[r['rep'] for r in same],selected_rep=chosen['rep'],
                        planning_seconds=chosen['elapsed_seconds'],activation_tick=chosen['activation_tick'],
                        quantization_seconds=(chosen['activation_tick']-model.old.EPOCH)/model.old.HZ-chosen['elapsed_seconds'],
                        deadline_fallback=chosen['deadline_fallback']))
        put(a.out/'NATIVE_SELECTION.json',selections)
        if a.native:
            for i,(key,(s,r)) in enumerate(sorted(selected.items())):
                folder=a.out/f'native_{i:04d}_{s["case"]}_{key[1][:10]}_t{key[2]}'
                try:
                    audit=native.simulate(s,r['executed_plan'],folder,r['elapsed_seconds'])
                    physical.append(dict(case=s['case'],signature=key[1],activation_tick=key[2],folder=folder.name,**audit))
                except BaseException:
                    result=read(folder/'RESULT.json') if (folder/'RESULT.json').exists() else {}
                    failure=dict(case=s['case'],signature=key[1],activation_tick=key[2],folder=folder.name,
                        status='FAIL',completed=result.get('completed',{}),unfinished_customers=result.get('unfinished_customers'),
                        collision_ticks=result.get('collision_ticks'),teleports=result.get('teleports'),error=traceback.format_exc())
                    failures.append(failure);physical.append(failure)
                    put(folder/'NATIVE_FAILURE.json',failure)
        assert sources()==frozen
        put(a.out/'PHYSICAL.json',physical);put(a.out/'FAILURES.json',failures)
        put(a.out/'SUMMARY.json',dict(status='PASS' if not failures else 'FAIL',policy_rows=len(records),
            planned_policy_rows=len(rows)*27,cases=len(rows),mothers=len({s['seed'] for s in rows}),
            native_unique=len(selected),native_completed=len(physical),native_failures=len(failures),
            sources=frozen,all_initializers_equal=True,actual_RAM_measured=False))
        if failures:raise RuntimeError('Native failures preserved; do not claim completed full cohort')
        put(a.out/'PROCESS_COMPLETE.json',dict(status='PASS',summary_sha256=sha(a.out/'SUMMARY.json')))
    except BaseException:
        put(a.out/'FAILURE.json',dict(error=traceback.format_exc()));raise
if __name__=='__main__':main()
