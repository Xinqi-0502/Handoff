"""Independent raw-output audit; never invokes SUMO or the validation executor."""
from pathlib import Path
import argparse,csv,hashlib,json,math,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def check(x,msg):
    if not x:raise AssertionError(msg)
def near(a,b):return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-8)
def observed(day,station):
    rows=[]
    for line in (ROOT/'upstream/data'/f'obstimes_{day}_{station}.txt').read_text().splitlines():
        h,m,s=map(int,line.split(':'));rows.append(3600*h+60*m+s)
    return rows
def audit_run(folder,p,declared):
    day,tau=declared['day'],declared['tau'];obs={k:observed(day,k) for k in (1,2,3,4,7,8)};n=len(obs[1])
    check(all(len(z)==n for z in obs.values()),'Raw observation lengths')
    manifest=load(folder/'Input_Manifest.json')
    for name,h in manifest['files'].items():check(sha(folder/name)==h,('Input hash',folder,name))
    check(sha(folder.parent/'network.net.xml')==manifest['network_sha256'],'Network hash')
    seen={k:{} for k in (1,2,3,4)}
    for _,e in ET.iterparse(folder/'instant.xml',events=('end',)):
        if e.attrib.get('state')=='enter':
            k=int(e.attrib['id'][3:]);i=int(e.attrib['vehID'])
            check(k in seen and 0<=i<n and i not in seen[k],'Unique known detector event')
            seen[k][i]=float(e.attrib['time'])
        e.clear()
    check(all(set(z)==set(range(n)) for z in seen.values()),'Complete detector population')
    trips=ET.parse(folder/'tripinfo.xml').getroot().findall('tripinfo')
    check(len(trips)==n and len({z.attrib['id'] for z in trips})==n,'Trip population')
    check(all(float(z.attrib['arrival'])>=0 for z in trips),'Full arrivals')
    last=ET.parse(folder/'summary.xml').getroot()[-1].attrib
    for key in ('running','waiting','collisions','teleports','discarded'):check(float(last[key])==0,('Terminal summary',key,last[key]))
    check(int(last['inserted'])==n and int(last['arrived'])==n,'Summary conservation')
    rows=[];all_errors={}
    for a,b in p['segments']:
        errors=[]
        for i in range(n):
            actual=obs[b][i]-obs[a][i];simulated=seen[b][i]-seen[a][i]
            check(simulated>0,'Positive simulated segment time')
            if actual>0:errors.append(simulated-actual)
        count=len(errors)
        rows.append(dict(day=day,tau=tau,segment=f'{a}-{b}',n_total=n,n=count,n_excluded=n-count,
            rmse_seconds=math.sqrt(sum(e*e for e in errors)/count),
            mae_seconds=sum(abs(e) for e in errors)/count,bias_seconds=sum(errors)/count))
        all_errors[f'{a}-{b}']=errors
    for actual,expected in zip(rows,declared['segment_metrics']):
        for key in ('segment','n_total','n','n_excluded'):check(actual[key]==expected[key],('Metric identity',key))
        for key in ('rmse_seconds','mae_seconds','bias_seconds'):check(near(actual[key],expected[key]),('Metric arithmetic',key))
    mean_rmse=sum(z['rmse_seconds'] for z in rows)/len(rows)
    check(near(mean_rmse,declared['mean_segment_rmse_seconds']),'Mean segment RMSE')
    with (folder/'Matched_Travel_Times.csv').open(newline='',encoding='utf-8') as f:csvrows=list(csv.DictReader(f))
    check(len(csvrows)==n*len(p['segments']),'Matched CSV complete population')
    keys=set()
    for z in csvrows:
        i=int(z['ordinal_row_index']);a,b=map(int,z['segment'].split('-'));key=(i,a,b)
        check(key not in keys,'Duplicate matched CSV key');keys.add(key)
        check(int(z['source_start_seconds'])==obs[a][i] and int(z['source_end_seconds'])==obs[b][i],'Raw timestamp CSV identity')
        actual=obs[b][i]-obs[a][i];simulated=seen[b][i]-seen[a][i]
        check(near(z['observed_seconds'],actual) and near(z['simulated_seconds'],simulated),'Matched time CSV')
        check((z['score_eligible']=='True')==(actual>0),'Eligibility identity')
        if actual>0:check(near(z['error_seconds'],simulated-actual),'CSV error')
        else:check(z['error_seconds']=='','Excluded error not fabricated')
    return rows,dict(day=day,tau=tau,vehicles=n,mean_segment_rmse_seconds=mean_rmse,
        max_depart_delay_seconds=max(float(z.attrib['departDelay']) for z in trips),
        mean_depart_delay_seconds=sum(float(z.attrib['departDelay']) for z in trips)/n,
        last_summary=last,all_vehicles_arrived=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    run=a.run.resolve();out=a.out.resolve()
    check((ROOT/'runs').resolve() in run.parents,'Known run descendant')
    check((ROOT/'analysis').resolve() in out.parents and not out.exists(),'Fresh analysis output')
    complete=load(run/'PROCESS_COMPLETE.json');check(complete['status']=='PASS','Only completed PASS attempts use this full audit; retain failures separately')
    s=load(run/'Summary.json');p=load(ROOT/'Frozen_Protocol_v2.json')
    check(s['script_sha256']==sha(ROOT/'run_public_validation_v2.py'),'Frozen v2 source')
    check(s['protocol_sha256']==sha(ROOT/'Frozen_Protocol_v2.json'),'Frozen v2 protocol')
    for name,h in load(run/'Output_Manifest.json')['files'].items():check(sha(run/name)==h,('Raw output hash',name))
    rows=[];records=[];input_by_day={}
    for r in s['all_run_metrics']:
        folder=run/f"day{r['day']}_tau{r['tau']:.1f}"
        rr,recomputed=audit_run(folder,p,r);rows.extend(rr);records.append(recomputed)
        route=ET.parse(folder/'routes.rou.xml').getroot()
        check(float(route.find('vType').attrib['tau'])==r['tau'],'Candidate tau')
        cargo=[z.attrib for z in route.findall('vehicle')]
        controls=dict(cargo=cargo,boundary=sha(folder/'boundary.vss.xml'),detectors=sha(folder/'detectors.add.xml'),config=sha(folder/'scenario.sumocfg'),
            vtype={k:v for k,v in route.find('vType').attrib.items() if k!='tau'})
        if r['day'] in input_by_day:check(controls==input_by_day[r['day']],'Within-day controls identical except tau')
        input_by_day[r['day']]=controls
    train=[r for r in records if r['day']==p['train_day']]
    check(sorted(r['tau'] for r in train)==sorted(p['tau_candidates']),'Exactly prespecified train candidates')
    chosen=min(train,key=lambda r:(r['mean_segment_rmse_seconds'],r['tau']!=p['baseline_tau'],r['tau']))
    check(chosen['tau']==s['selected_tau'],'Train-only selection')
    selection=load(run/'Selection_Before_Heldout.json')
    check(selection['selected_tau']==chosen['tau'] and selection['selection_uses_day1_only'],'Selection record')
    check(sha(run/'Selection_Before_Heldout.json')==s['selection_before_heldout_sha256'],'Selection hash')
    held=[r for r in records if r['day']==p['heldout_day']]
    check(sorted(r['tau'] for r in held)==sorted({p['baseline_tau'],chosen['tau']}),'Only baseline/winner on held-out day')
    baseline=next(r for r in held if r['tau']==p['baseline_tau']);winner=next(r for r in held if r['tau']==chosen['tau'])
    delta=winner['mean_segment_rmse_seconds']-baseline['mean_segment_rmse_seconds']
    check(near(delta,s['heldout_mean_segment_rmse_delta_seconds']),'Held-out delta')
    check(s['sumo_runs']==len(records)<=5 and s['no_day2_parameter_tuning'] and not s['delivery_network_calibrated'],'Scope/run count')
    out.mkdir(parents=True)
    with (out/'Independent_Segment_Metrics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result=dict(status='PASS',scope='Independent recomputation from raw detector XML and original ordinal observations; not independent empirical dataset',
        source_run=str(run),source_sha256=sha(ROOT/'run_public_validation_v2.py'),audit_script_sha256=sha(__file__),
        records=records,selected_tau=chosen['tau'],heldout_mean_segment_rmse_delta_seconds=delta,
        heldout_rmse_relative_change_percent=None if baseline['mean_segment_rmse_seconds']==0 else 100*delta/baseline['mean_segment_rmse_seconds'],
        no_delivery_network_calibration=True,within_day_controls_identical_except_tau=True,
        failure_attempt_preserved=str(ROOT/'analysis/public_01_failure/Failure_Audit.md'))
    dump(out/'Independent_Audit.json',result)
    def table(items):
        lines=['| Day | Tau (s) | Segment | Eligible / total | Excluded | RMSE (s) | MAE (s) | Bias (s) |',
               '|---:|---:|:---:|---:|---:|---:|---:|---:|']
        for z in items:lines.append(f"| {z['day']} | {z['tau']:.1f} | {z['segment']} | {z['n']} / {z['n_total']} | {z['n_excluded']} | {z['rmse_seconds']:.6f} | {z['mae_seconds']:.6f} | {z['bias_seconds']:.6f} |")
        return '\n'.join(lines)
    training='; '.join(f"tau={z['tau']:.1f}: {z['mean_segment_rmse_seconds']:.6f} s" for z in sorted(train,key=lambda x:x['tau']))
    text=f"""# Independent public-data validation audit

The revised public-data workflow completed {len(records)} traffic runs. Raw detector XML, original ordinal observation rows, complete trip populations, recorded metric arithmetic and output hashes independently matched the saved results. This PASS means workflow and arithmetic consistency, not a universal traffic-calibration acceptance criterion.

Day-1 mean-of-segment-RMSE scores were {training}. The frozen minimum-score rule selected tau={chosen['tau']:.1f} s. The baseline is the official tutorial runner's initial tau=1.5 s, not a claim about the simulator's factory default. No held-out day selected tau.

On day 2 the baseline mean segment RMSE was {baseline['mean_segment_rmse_seconds']:.6f} s and the selected candidate was {winner['mean_segment_rmse_seconds']:.6f} s. The signed change (selected minus baseline) was {delta:.6f} s. A negative value is improvement; a zero or positive value is retained. These are observed-boundary, ordinal-matching errors from a small three-candidate screen; they do not identify globally optimal parameters.

{table(rows)}

All {records[0]['vehicles']} day-1 and {held[0]['vehicles']} day-2 demand vehicles were retained and arrived in each corresponding run. The end summaries reported no collisions, teleports, discarded vehicles or remaining vehicles. Scoring excludes only nonpositive raw differences separately for each segment. Day-1 denominators are 2298/2297/2295; day-2 denominators are 2293/2289/2292. The complete matched CSVs retain excluded raw rows without fabricated errors. The raw files contain no explicit vehicle IDs; simulated IDs support bookkeeping and do not establish actual observed identity.

Within each day, demand records, boundary speed inputs, network, detector configuration, seed and simulation settings were identical across candidates, with tau the only vehicle-parameter change. Day-specific measured inflow and downstream speed boundaries are conditioning inputs. The held-out measurements are therefore not an unconstrained forecast of a new city network.

The original attempt ended with 119 unfinished day-1 tau=1.2 vehicles and remains a failed/censored artifact. The single approved amendment extended the same final drain allowance from 900 to 7200 seconds for every candidate/day, using completeness evidence before any error-driven selection. No further horizon tuning was performed. Actual historical traffic runs include that failed attempt in addition to the {len(records)} completed revised runs.

This is a separate San Pablo Dam tutorial adaptation. It does not calibrate the delivery network, traffic signals, parcel demand, robots or elevator behavior. Its errors and any transfer failure remain part of the evidence.

Sources: [raw summary]({run/'Summary.json'}), [frozen v2 protocol]({ROOT/'Frozen_Protocol_v2.json'}), [selection before held-out runs]({run/'Selection_Before_Heldout.json'}), [retained first failure]({ROOT/'analysis/public_01_failure/Failure_Audit.md'}), [official tutorial](https://eclipse.dev/sumo/docs/Tutorials/Calibration/San_Pablo_Dam.html). Independent_Segment_Metrics.csv and Independent_Audit.json contain the unrounded recalculations.
"""
    (out/'Independent_Validation_Report.md').write_text(text,encoding='utf-8')
    dump(out/'Manifest.json',{'files':{x.name:sha(x) for x in out.iterdir() if x.is_file()},'raw_output_manifest_sha256':sha(run/'Output_Manifest.json'),'audit_script_sha256':sha(__file__)})
    dump(out/'PROCESS_COMPLETE.json',{'status':'PASS','traffic_runs_audited':len(records),'no_simulation_executed_by_auditor':True})
    print(json.dumps(dict(status='PASS',selected_tau=chosen['tau'],heldout_delta_seconds=delta,out=str(out))))
if __name__=='__main__':main()
