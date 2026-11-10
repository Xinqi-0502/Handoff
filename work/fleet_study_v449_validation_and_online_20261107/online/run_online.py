"""Gate-protected V449 prediction-to-native replay; run only under thermal monitor.
Separate protocols: forecast24 caps complete forecasts, wall records literal
incumbents before an absolute deadline. Technical repeats are not new scenarios.
No external oracle is fed to the online policy or its initial witnesses.
"""
from pathlib import Path
import argparse,json,time,traceback
import online_model as model
import native_two_batch as native
from check_online import read,put,sha,sources,validate_gate


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--gate',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mode',choices=('forecast24','wall'),required=True)
    ap.add_argument('--wall-seconds',type=float,default=0.05);ap.add_argument('--repeats',type=int,default=3)
    ap.add_argument('--native',action='store_true',help='Replay each distinct selected plan once in native SUMO')
    a=ap.parse_args()
    if a.repeats<1 or a.wall_seconds<=0:raise ValueError('Positive limits required')
    validate_gate(a.gate,a.inputs);frozen=sources();inputs=read(a.inputs);rows=inputs['cases']
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.mkdir(exist_ok=False)
    put(a.out/'PROTOCOL.json',{'mode':a.mode,'wall_seconds':a.wall_seconds if a.mode=='wall' else None,
        'per_branch_forecast_cap':6 if a.mode=='forecast24' else None,'repeats':a.repeats,
        'native':a.native,'sources':frozen,'inputs_sha256':sha(a.inputs),'gate_sha256':sha(a.gate/'GATE.json'),
        'scenario_count':len(rows),'mothers':len({s['seed'] for s in rows}),
        'objective':'sum customer completion minus releases; all old plus a and b',
        'prediction_claim':'COARSE forecast objective only; no physical admissibility claim',
        'candidate_domain':'4 branches; both atomic orders same receiver/hub a then b; other route fixed',
        'deadline':'all setup/greedy/bounds/forecast charged; wall checked between complete expansions; use trace<=wall only',
        'arm_order':'cyclic by case index and technical repetition; native replay after ALL policy timing'})
    records=[];selected={};physical=[]
    try:
        with (a.out/'RESULTS.jsonl').open('x',encoding='utf8') as f:
            for i,s in enumerate(rows):
                for rep in range(a.repeats):
                    order=model.ARMS[(i+rep)%3:]+model.ARMS[:(i+rep)%3]
                    for arm in order:
                        r=model.solve(s,arm,per_branch_cap=6 if a.mode=='forecast24' else 10**9,
                                      wall_seconds=None if a.mode=='forecast24' else a.wall_seconds)
                        record={'case':s['case'],'seed':s['seed'],'rep':rep,'mode':a.mode,**r};records.append(record)
                        f.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n');f.flush()
                        plan=r['plan'] if a.mode=='forecast24' else r['within_budget_plan']
                        if plan is not None:selected[(s['case'],model.signature(plan))]=(s,plan)
        if a.native:
            for index,((case,sig),(s,plan)) in enumerate(sorted(selected.items())):
                dest=a.out/f'native_{index:03d}_{case}_{sig[:10]}'
                audit=native.simulate(s,plan,dest)
                matches=[{'arm':r['arm'],'rep':r['rep']} for r in records if r['case']==case and
                         (model.signature(r['plan'] if a.mode=='forecast24' else r['within_budget_plan']) if
                          (r['plan'] if a.mode=='forecast24' else r['within_budget_plan']) is not None else None)==sig]
                physical.append({'case':case,'signature':sig,'selected_by':matches,'folder':dest.name,**audit})
        assert sources()==frozen
        put(a.out/'PHYSICAL.json',physical)
        put(a.out/'SUMMARY.json',{'status':'PASS','policy_rows':len(records),'selected_unique_plans':len(selected),
            'native_replays':len(physical),'sources':frozen,'inputs_sha256':sha(a.inputs),
            'all_native_pass':all(x['status']=='PASS' for x in physical),'native_requested':a.native})
        put(a.out/'PROCESS_COMPLETE.json',{'status':'PASS','summary_sha256':sha(a.out/'SUMMARY.json')})
    except BaseException:
        put(a.out/'FAILURE.json',{'error':traceback.format_exc()});raise
if __name__=='__main__':main()

