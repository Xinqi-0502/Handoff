"""Independent V450 raw-evidence audit. No solver or study-analysis imports.
Prepared during main timing; execute only after the root releases an analysis window.
"""
from pathlib import Path
import argparse,collections,csv,hashlib,json,math,statistics,traceback
ROOT=Path(__file__).resolve().parent.parent
P=ROOT/'static_comparison'
METHODS=('RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS')
CANDIDATE='HZ_AWA_RADIUS_PAIR_GATED'
BASELINES=('HZ_AWA_RADIUS','ANA_RADIUS','RADIUS_PAIR_AWA_GATED')
ARMS=dict(zip(METHODS,('AWA_GATED','HZ_AWA','HZ_AWA_PAIR_GATED','ANA')))
DEADLINES=(100,500,1000)
FRACTIONS=(0.,.05,.10)
EVIDENCE={}

def require(ok,detail):
    if not ok:raise AssertionError(detail)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def text(p):
    p=Path(p).resolve();content=p.read_bytes();EVIDENCE[str(p)]=hashlib.sha256(content).hexdigest()
    return content.decode('utf-8-sig')
def load(p):return json.loads(text(p))
def jsonlines(p):return [json.loads(x) for x in text(p).splitlines() if x.strip()]
def save(p,data):Path(p).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csvsave(p,rows):
    if not rows:return
    with Path(p).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def spec_hash(s):return hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
def median(values):return statistics.median(values)
def change(a,b):return None if b==0 else 100*(a/b-1)
def close(a,b):return abs(a-b)<=1e-6

def verify_sources():
    manifest=load(P/'Frozen_Source_Manifest.json')
    require(manifest['status']=='FROZEN' and manifest['methods']==list(METHODS),'Frozen methods')
    require(manifest['wall_ms']==1000 and manifest['main_repeats']==3,'Frozen budget/repeats')
    require(manifest['main_cases']==256 and manifest['main_mothers']==64,'Frozen design size')
    for p,h in manifest['files'].items():
        actual=sha(p);require(actual==h,('Frozen source drift',p));EVIDENCE[str(Path(p).resolve())]=actual
    gate=load(manifest['gate']);require(gate['status']=='PASS','Core gate status')
    for p,h in gate['sources'].items():require(sha(p)==h,('Gate source drift',p))
    for p,h in gate['evidence_sha256'].items():require(sha(p)==h,('Core gate evidence drift',p))
    inputs=load(P/'inputs/main/INPUTS.json')
    require(sha(P/'inputs/main/INPUTS.json')==manifest['inputs']['main'],'Main input hash')
    require(len(inputs)==256 and len({s['case'] for s in inputs})==256 and len({s['seed'] for s in inputs})==64,'Independent mother design')
    mothers=collections.defaultdict(list)
    for s in inputs:mothers[s['seed']].append(s)
    for seed,ss in mothers.items():
        require(len(ss)==4 and len({len(s['old']) for s in ss})==1,'Four related variants per mother')
        require(len({(s['capacity_regime'],s['signal']) for s in ss})==4,'Capacity-signal factorial design')
        require(len({s['t0'] for s in ss})==1 and len({s['A'] for s in ss})==1,'Clock and supplier ETA controls')
    require(collections.Counter(len(ss[0]['old']) for ss in mothers.values())=={6:16,8:16,10:16,12:16},'Mothers per scale')
    return manifest,inputs

def validate_call(r,s,opt):
    require(r['arm']==ARMS[r['method']] and r['bound_basis']=='radius','Actual policy/basis')
    require(r['wall_budget_ms']==1000,'Actual solver wall budget')
    require(r['H2']>=s['t0'] and (opt is None or r['H2']>=opt),'Feasible value versus independent optimum')
    lb=r['remaining_bound'];gap=r['certified_gap']
    require(gap==(None if lb is None else r['H2']-lb),'Gap identity')
    require(lb is None or lb<=r['H2'],'Bound exceeds feasible value')
    require(lb is None or opt is None or lb<=opt,'Bound exceeds independent optimum')
    require(r['certified_optimal']==(gap==0),'Certificate flag')
    require(not r['certified_optimal'] or opt is None or r['H2']==opt,'False optimality certificate')
    for key in ('setup_seconds','initial_seconds','search_seconds','elapsed_seconds','root_bound_seconds'):
        require(math.isfinite(r[key]) and r[key]>=0,('Invalid timer',key))
    require(close(r['setup_seconds']+r['initial_seconds']+r['search_seconds'],r['elapsed_seconds']),'Timer partition')
    require(r['root_bound_seconds']<=r['search_seconds']+1e-6,'Nested root timing')
    require(close(r['overrun_seconds'],max(0,r['elapsed_seconds']-1)),'Overrun')
    require(r['expanded']==r['expanded_phase0']+r['expanded_phase1'],'Expansion accounting')
    trace=r['trace'];require(bool(trace),'Recovered solution has no trace')
    previous_time=-1;previous_value=math.inf
    for i,e in enumerate(trace):
        require(previous_time<=e['seconds']<=r['elapsed_seconds']+1e-6,'Trace times')
        require(e['H2']<previous_value and (opt is None or e['H2']>=opt),'Strict feasible improvements')
        k=e['expansion_index'];done=e['expansions_completed']
        require(0<=done<=k<=r['expanded'],'Trace expansion index')
        if i==0:require(k==done==0,'Initial trace index')
        elif r['method']=='ANA_RADIUS':require(e['event_kind']=='goal_pop' and k==done,'ANA goal-pop semantics')
        else:require(done==k-1,'Generated-goal semantics')
        previous_time=e['seconds'];previous_value=e['H2']
    require(trace[-1]['H2']==r['H2'] and trace[-1]['plan']==r['plan'],'Final plan/trace agreement')
    quality={ms:min((e['H2'] for e in trace if e['seconds']<=ms/1000),default=None) for ms in DEADLINES}
    require(quality=={ms:r['literal_quality'][str(ms)] for ms in DEADLINES},'Recorded literal quality')
    hits=[]
    for i,fraction in enumerate(FRACTIONS):
        target=None if opt is None else opt+fraction*(opt-s['t0'])
        event=next((e for e in trace if target is not None and e['H2']<=target),None)
        sec=None if event is None else event['seconds'];raw=r['first_quality_thresholds'][i]
        require(raw['fraction']==fraction and raw['target']==target and raw['seconds']==sec and raw['within_budget']==(sec is not None and sec<=1),'First quality threshold recomputation')
        hits.append(sec)
    return dict(raw=r,quality=quality,hits=hits,initial=(trace[0]['H2'],tuple(trace[0]['plan'])))

def collect(runs,allow_partial):
    manifest,all_inputs=verify_sources();selected={};groups=collections.defaultdict(list);oracles={};all_records=[]
    for item in runs:
        run=item.resolve();require(ROOT in run.parents,'Raw paths must be V450')
        done=load(run/'PROCESS_COMPLETE.json');require(done['status'] in ('PASS','PASS_WITH_CENSORING'),'Incomplete run rejected')
        protocol=load(run/'PROTOCOL.json');require(protocol['source_manifest']==manifest,'Run manifest mismatch')
        require(protocol['split']=='main' and protocol['methods']==list(METHODS) and protocol['repeats']==3,'Main method/repeat protocol')
        require(protocol['wall_ms']==1000 and protocol['hard_seconds']==15 and protocol['oracle_seconds']==15,'Budget protocol')
        require(protocol['oracle_outside_solver_and_not_supplied'] and protocol['common_initial_setup_included'],'Fairness declaration')
        start,stop=protocol['start'],protocol['stop'];require(0<=start<stop<=256 and start%4==stop%4==0,'Input slice')
        specs=load(run/'INPUTS.json');require(specs==all_inputs[start:stop],'Exact input slice')
        require(protocol['input_sha256']==manifest['inputs']['main'],'Input-source hash')
        require(protocol['expected_calls']==len(specs)*12,'Expected call count')
        for s in specs:
            require(s['case'] not in selected,'Overlapping selected run case');selected[s['case']]=s
        local={s['case']:s for s in specs}
        oo=jsonlines(run/'ORACLES.jsonl');require(len(oo)==len(specs) and {o['case'] for o in oo}==set(local),'Oracle coverage')
        for o in oo:
            rr=o['result'];require(rr['status'] in ('PASS','CENSORED'),'Unknown oracle status')
            oracles[o['case']]=rr['optimum_H2'] if rr['status']=='PASS' else None
        cc=jsonlines(run/'CASE_COMPLETE.jsonl')
        require([x['case'] for x in cc]==[s['case'] for s in specs],'CASE_COMPLETE unique ordered coverage')
        require(all(x['status']=='PASS' and x['oracle_H2']==oracles[x['case']] for x in cc),'CASE_COMPLETE status/oracle')
        records=jsonlines(run/'MEASUREMENTS.jsonl');want={(s['case'],method,rep) for s in specs for method in METHODS for rep in range(3)}
        keys=[(r['case'],r['method'],r['repeat']) for r in records]
        require(len(keys)==len(want) and set(keys)==want,'Exact method-repeat matrix including timeouts')
        success=hard=0
        for r in records:
            s=local[r['case']];ci=start+[x['case'] for x in specs].index(r['case']);rotation=(ci*3+r['repeat'])%4
            require(r['order']==(METHODS.index(r['method'])-rotation)%4,'Frozen rotation order')
            for key,value in (('seed',s['seed']),('m',len(s['old'])),('Q',s['Q']),('signal',s['signal']),('capacity_regime',s['capacity_regime']),('input_sha256',spec_hash(s))):
                require(r[key]==value,('Raw metadata mismatch',r['case'],key))
            require(r['status'] in ('OK','HARD_TIMEOUT'),'Unknown raw status')
            if r['status']=='OK':
                success+=1;require(r['oracle_H2']==oracles[s['case']],'Row oracle target')
                groups[(s['case'],r['method'])].append(validate_call(r,s,oracles[s['case']]))
            else:
                hard+=1;require(r['seconds']>=0 and 'H2' not in r and 'trace' not in r,'Unrecovered timeout must not acquire quality')
            all_records.append(r)
        attempts=jsonlines(run/'ATTEMPTS.jsonl');starts=collections.Counter((x['case'],x['method'],x['repeat']) for x in attempts if x['status']=='STARTED');ends=collections.Counter((x['case'],x['method'],x['repeat']) for x in attempts if x['status']=='COMPLETE')
        require(set(starts)==want and all(v==1 for v in starts.values()),'Attempt starts')
        require(set(ends)=={(r['case'],r['method'],r['repeat']) for r in records if r['status']=='OK'} and all(v==1 for v in ends.values()),'Attempt completions')
        require(len(attempts)==len(want)+success,'Unknown/duplicate attempt event')
        failures=jsonlines(run/'FAILURES.jsonl') if (run/'FAILURES.jsonl').exists() else []
        require(failures==[r for r in records if r['status']=='HARD_TIMEOUT'],'Hard-timeout records preserved')
        require(done['cases']==len(specs) and done['calls']==success and done['hard_timeouts']==hard,'Completion counts')
        require(done['status']==('PASS_WITH_CENSORING' if hard else 'PASS'),'Completion status consistency')
    require(allow_partial or len(selected)==256,'Final audit requires all256 scenarios')
    for case,s in selected.items():
        init={x['initial'] for method in METHODS for x in groups[(case,method)]}
        require(len(init)<=1,('Different initial plan/value across recovered calls',case))
    return selected,groups,oracles,all_records

def case_rows(specs,groups,oracles):
    result=[]
    for case,s in specs.items():
        opt=oracles[case]
        for method in METHODS:
            xs=sorted(groups[(case,method)],key=lambda x:x['raw']['repeat']);rr=[x['raw'] for x in xs];full=len(rr)==3
            initial=xs[0]['initial'][0] if xs else None
            c=dict(case=case,method=method,seed=s['seed'],m=len(s['old']),Q=s['Q'],capacity_regime=s['capacity_regime'],signal=s['signal'],t0=s['t0'],oracle_H2=opt,returned_repeats=len(rr),hard_repeats=3-len(rr),initial_H2=initial,initial_optimal=None if opt is None or initial is None else initial==opt,
                all3_proved=full and all(r['certified_optimal'] and r['elapsed_seconds']<=1 for r in rr),all3_soft_proved=full and all(r['certified_optimal'] for r in rr),late_proved_repeats=sum(r['certified_optimal'] and r['elapsed_seconds']>1 for r in rr),
                expanded_median=median([r['expanded'] for r in rr]) if full else None,elapsed_median=median([r['elapsed_seconds'] for r in rr]) if full else None,elapsed_min=min((r['elapsed_seconds'] for r in rr),default=None),elapsed_max=max((r['elapsed_seconds'] for r in rr),default=None),literal_wall_consumed_sum=sum(r['elapsed_seconds'] for r in rr),soft_overrun_repeats=sum(r['elapsed_seconds']>1 for r in rr))
            for ms in DEADLINES:
                values=[x['quality'][ms] for x in xs];observed=full and all(v is not None for v in values)
                q=median(values) if observed else None
                c[f'quality_{ms}']=q;c[f'quality_observed_{ms}']=observed
                c[f'all3_optimal_{ms}']=observed and opt is not None and all(v==opt for v in values)
                c[f'duration_gap_{ms}']=None if q is None or opt is None or opt==s['t0'] else (q-opt)/(opt-s['t0'])
            for k,fraction in enumerate(FRACTIONS):
                target=None if opt is None else opt+fraction*(opt-s['t0']);ts=[x['hits'][k] for x in xs]
                c[f'initial_good{k}']=None if target is None or initial is None else initial<=target
                c[f'all3_reached{k}']=full and all(t is not None and t<=1 for t in ts)
                c[f'first_seconds{k}']=median(ts) if c[f'all3_reached{k}'] else None
            result.append(c)
    return result

def strata(specs):
    rows=[('all','all',set(specs))]
    for field,func in (('m',lambda s:len(s['old'])),('capacity_regime',lambda s:s['capacity_regime']),('signal',lambda s:s['signal'])):
        for value in sorted({func(s) for s in specs.values()},key=str):rows.append((field,str(value),{c for c,s in specs.items() if func(s)==value}))
    for m in (6,8,10,12):
        for cap in sorted({s['capacity_regime'] for s in specs.values()}):
            for signal in sorted({s['signal'] for s in specs.values()},key=str):
                ids={c for c,s in specs.items() if len(s['old'])==m and s['capacity_regime']==cap and s['signal']==signal}
                if ids:rows.append(('m_capacity_signal',f'{m}|{cap}|{signal}',ids))
    return rows

def summarize(specs,rows):
    d={(x['case'],x['method']):x for x in rows};method_rows=[];proof_rows=[];quality_rows=[];first_rows=[]
    for field,value,ids in strata(specs):
        for method in METHODS:
            xs=[d[(c,method)] for c in ids]
            r=dict(stratum=field,value=value,method=method,cases=len(ids),mothers=len({specs[c]['seed'] for c in ids}),returned_calls=sum(x['returned_repeats'] for x in xs),hard_calls=sum(x['hard_repeats'] for x in xs),oracle_known_cases=sum(x['oracle_H2'] is not None for x in xs),initial_optimal_cases=sum(x['initial_optimal'] is True for x in xs),initial_unknown_cases=sum(x['initial_optimal'] is None for x in xs),all3_proved=sum(x['all3_proved'] for x in xs),all3_soft_proved=sum(x['all3_soft_proved'] for x in xs),late_proved_calls=sum(x['late_proved_repeats'] for x in xs),literal_returned_wall_consumption=sum(x['literal_wall_consumed_sum'] for x in xs))
            for ms in DEADLINES:
                r[f'quality_observed_{ms}']=sum(x[f'quality_observed_{ms}'] for x in xs);r[f'all3_optimal_{ms}']=sum(x[f'all3_optimal_{ms}'] for x in xs)
            for k in range(3):
                r[f'initial_good{k}']=sum(x[f'initial_good{k}'] is True for x in xs);r[f'all3_reached{k}']=sum(x[f'all3_reached{k}'] for x in xs);r[f'noninitial_all3_reached{k}']=sum(x[f'initial_good{k}'] is False and x[f'all3_reached{k}'] for x in xs)
            method_rows.append(r)
        for baseline in BASELINES:
            pairs=[(d[(c,CANDIDATE)],d[(c,baseline)]) for c in ids];joint=[(x,y) for x,y in pairs if x['all3_proved'] and y['all3_proved']]
            ce=sum(x['expanded_median'] for x,y in joint);be=sum(y['expanded_median'] for x,y in joint);ct=sum(x['elapsed_median'] for x,y in joint);bt=sum(y['elapsed_median'] for x,y in joint)
            p=dict(stratum=field,value=value,candidate=CANDIDATE,baseline=baseline,all_cases=len(ids),common_on_time_proved=len(joint),candidate_expanded_sum=ce,baseline_expanded_sum=be,expansion_change_percent=change(ce,be),candidate_time_sum=ct,baseline_time_sum=bt,time_change_percent=change(ct,bt),zero_baseline_expansion_cases=sum(y['expanded_median']==0 for x,y in joint),candidate_faster_medians=sum(x['elapsed_median']<y['elapsed_median'] for x,y in joint),tied_medians=sum(x['elapsed_median']==y['elapsed_median'] for x,y in joint),baseline_faster_medians=sum(x['elapsed_median']>y['elapsed_median'] for x,y in joint),candidate_all3_faster=sum(x['elapsed_max']<y['elapsed_min'] for x,y in joint),baseline_all3_faster=sum(y['elapsed_max']<x['elapsed_min'] for x,y in joint))
            p['timing_ranges_overlap']=len(joint)-p['candidate_all3_faster']-p['baseline_all3_faster'];proof_rows.append(p)
            for ms in DEADLINES:
                both=[(x,y) for x,y in pairs if x[f'quality_observed_{ms}'] and y[f'quality_observed_{ms}']]
                q=dict(stratum=field,value=value,candidate=CANDIDATE,baseline=baseline,deadline_ms=ms,all_cases=len(ids),both_observed=len(both),candidate_only=sum(x[f'quality_observed_{ms}'] and not y[f'quality_observed_{ms}'] for x,y in pairs),baseline_only=sum(y[f'quality_observed_{ms}'] and not x[f'quality_observed_{ms}'] for x,y in pairs),neither=sum(not x[f'quality_observed_{ms}'] and not y[f'quality_observed_{ms}'] for x,y in pairs),candidate_better=sum(x[f'quality_{ms}']<y[f'quality_{ms}'] for x,y in both),ties=sum(x[f'quality_{ms}']==y[f'quality_{ms}'] for x,y in both),baseline_better=sum(x[f'quality_{ms}']>y[f'quality_{ms}'] for x,y in both),both_initial_optimal=sum(x['initial_optimal'] is True and y['initial_optimal'] is True for x,y in both))
                quality_rows.append(q)
            for k,fraction in enumerate(FRACTIONS):
                for initial_group in ('all','initial_good','initial_not_good'):
                    subset=[(x,y) for x,y in pairs if initial_group=='all' or (x[f'initial_good{k}'] is True and y[f'initial_good{k}'] is True if initial_group=='initial_good' else x[f'initial_good{k}'] is False and y[f'initial_good{k}'] is False)]
                    good=[(x,y) for x,y in subset if x[f'all3_reached{k}'] and y[f'all3_reached{k}']];ct=sum(x[f'first_seconds{k}'] for x,y in good);bt=sum(y[f'first_seconds{k}'] for x,y in good)
                    first_rows.append(dict(stratum=field,value=value,candidate=CANDIDATE,baseline=baseline,fraction=fraction,initial_group=initial_group,group_cases=len(subset),common_all3_reached=len(good),candidate_seconds=ct,baseline_seconds=bt,time_change_percent=change(ct,bt)))
    return method_rows,proof_rows,quality_rows,first_rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runs',type=Path,nargs='+',required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--allow-partial',action='store_true');a=parser.parse_args()
    out=a.out.resolve();require(ROOT in out.parents and not out.exists(),'Fresh E/V450 audit output');out.mkdir(parents=True)
    try:
        specs,groups,oracles,raw=collect(a.runs,a.allow_partial);rows=case_rows(specs,groups,oracles);methods,proof,quality,first=summarize(specs,rows)
        csvsave(out/'Independent_Case_Medians.csv',rows);csvsave(out/'Independent_Method_Summary.csv',methods);csvsave(out/'Directed_Proof_Pairs.csv',proof);csvsave(out/'Directed_Literal_Quality_Pairs.csv',quality);csvsave(out/'Initial_Strata_First_Good_Pairs.csv',first)
        facts=dict(status='PASS',final_complete=len(specs)==256,scenarios=len(specs),independent_mothers=len({s['seed'] for s in specs.values()}),raw_calls=len(raw),returned_calls=sum(r['status']=='OK' for r in raw),hard_timeouts=sum(r['status']=='HARD_TIMEOUT' for r in raw),hard_timeout_seconds=sum(r['seconds'] for r in raw if r['status']=='HARD_TIMEOUT'),oracle_exact_cases=sum(v is not None for v in oracles.values()),source_imports='Python standard library only; no solver or study-analysis imports',source_evidence=EVIDENCE,limitations=['Trace/certificate/provenance audit, not a fresh route replay or new optimum solve.','Paired proof ratios require all3 technical repeats of both arms proved within1s.','Literal quality excludes events after the deadline.','Unknown oracle is never replaced by a solver self-certificate.','Initial-good attainment is reported separately from search improvement.','The256 scenarios comprise64 independent mothers and4 related variants each.','No confidence interval, p-value or significance claim.'])
        save(out/'Independent_Audit.json',facts)
        notes=['# Independent raw audit','',f"Status: PASS. Final complete: {facts['final_complete']}. {len(specs)} scenarios, {facts['independent_mothers']} independent mothers, {len(raw)} calls; {facts['hard_timeouts']} hard timeouts retained.",'','Candidate is HZ_AWA_RADIUS_PAIR_GATED. Negative change means less than the named baseline. The first table uses the identical common all-three-on-time proof subset.','','| Baseline | Common cases | Expansion change % | Total median-time change % |','|---|---:|---:|---:|']
        for r in proof:
            if r['stratum']=='all':notes.append(f"| {r['baseline']} | {r['common_on_time_proved']} | {r['expansion_change_percent']} | {r['time_change_percent']} |")
        notes+=['','Sources, missingness, initialization strata, literal-deadline comparisons and all size/capacity/signal strata are in the adjacent JSON/CSV files. End-of-run consumption is not a solved-search speed metric. Complete published search policies are adapted to this H2 model, not full freight-paper benchmark reproductions.']
        (out/'Independent_Audit.md').write_text('\n'.join(notes)+'\n',encoding='utf-8')
        outputs={str(p):sha(p) for p in out.iterdir() if p.is_file()};save(out/'Manifest.json',dict(source_sha256=sha(__file__),arguments=dict(runs=[str(p.resolve()) for p in a.runs],allow_partial=a.allow_partial),outputs=outputs));save(out/'PROCESS_COMPLETE.json',dict(status='PASS',final_complete=facts['final_complete'],raw_calls=len(raw)))
        print(json.dumps({k:facts[k] for k in ('status','final_complete','scenarios','independent_mothers','raw_calls','hard_timeouts')}),flush=True)
    except BaseException as exc:
        save(out/'FAILURE.json',dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc()));save(out/'PROCESS_COMPLETE.json',dict(status='FAIL'));raise
if __name__=='__main__':main()
