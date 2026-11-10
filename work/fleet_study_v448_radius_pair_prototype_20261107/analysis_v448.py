"""Read-only V448 pilot analysis. No solver imports or work at import time."""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,math,statistics,time,traceback
P=Path(__file__).resolve().parent
PRIMARY=('RADIUS','RADIUS_PAIR_LAZY','RADIUS_AWA','NO_BOUND')
AUX=('RADIUS_PAIR_EAGER','ROUTE')
METHODS=PRIMARY+AUX
CANDIDATE='RADIUS_PAIR_LAZY'
BASELINES=('RADIUS','RADIUS_AWA','NO_BOUND')
MAP={'RADIUS':('ROUTE','radius'),'RADIUS_PAIR_LAZY':('LAZY_ASTAR','radius'),
     'RADIUS_AWA':('AWA_ROUTE','radius'),'NO_BOUND':('NO_BOUND','exact'),
     'RADIUS_PAIR_EAGER':('PAIR_EAGER','radius'),'ROUTE':('ROUTE','exact')}
BUDGETS=(100,500,1000)
INPUT_SHA='b459e02e4173e07787b47e905de193842fc05e4f7c4738315de044a588b7afa1'
TIMERS=('elapsed_seconds','setup_seconds','initial_seconds','search_seconds','root_bound_seconds','overrun_seconds')
COUNTERS=('expanded','expanded_phase0','expanded_phase1','generated','pruned','dominated','peak_frontier',
          'base_calls','phase1_base_calls','full_calls','cutoff_calls','gate_calls','radius_calls',
          'skip_exact_quota','skip_radius_union_saturation','skip_alpha_union','skip_urel',
          'closure_cache_size','fa_cache_size','gamma_cache_size')

def require(value,detail):
    if not value: raise AssertionError(detail)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def optional(p): return load(p) if p.exists() else None
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()] if p.exists() else []
def dump(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def med(xs): return statistics.median(xs) if xs and all(x is not None for x in xs) else None
def ratio(a,b): return None if a is None or b is None or b==0 else a/b
def near(a,b): return a is not None and b is not None and math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7)
def csvwrite(p,rows):
    if not rows: p.write_text('',encoding='utf-8'); return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader()
        for r in rows: w.writerow({k:json.dumps(v,allow_nan=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})

def schedule(index):
    slots=[]
    for rep in range(3):
        off=(index+rep)%4
        slots += [(m,rep,'primary',j) for j,m in enumerate(PRIMARY[off:]+PRIMARY[:off])]
    slots += [(m,0,'auxiliary',j) for j,m in enumerate(AUX if index%2==0 else tuple(reversed(AUX)))]
    return slots

def call_record(raw,spec,index,slot,position,opt):
    method,rep,cohort,within=slot
    ident=dict(case=spec['case'],seed=spec['seed'],m=len(spec['old']),Q=spec['Q'],
        capacity_regime=spec['capacity_regime'],signal=spec['signal'],method=method,arm=method,
        policy=MAP[method][0],bound_basis=MAP[method][1],repeat=rep,cohort=cohort,
        position_within_repeat=within,position_within_case=position,mode='pilot',
        input_sha256=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest())
    r=dict(ident,outcome='MISSING',oracle_H2=opt,t0=spec['t0'],end_H2=None,end_certified=None,
        on_time_certified=None,late_certificate=None,initialization_overrun=None,
        first_optimal_seconds=None,first_optimal_within_wall=None,initial_optimal=None,
        H2_within_wall=None,regret_within_wall=None,certified_gap=None,remaining_bound=None,
        hard_timeout_seconds=None)
    r.update({k:None for k in TIMERS+COUNTERS})
    for ms in BUDGETS: r.update({f'H2_{ms}ms':None,f'regret_{ms}ms':None})
    if raw is None: return r
    for k,v in ident.items(): require(raw.get(k)==v,('identity',spec['case'],method,rep,k,raw.get(k),v))
    require(raw.get('wall_budget_ms')==1000,'wall budget')
    r['outcome']=raw['outcome']
    if raw['outcome']=='HARD_TIMEOUT':
        require(raw['hard_limit_seconds']==15 and raw['incumbent_not_recovered'] is True,'hard censor schema')
        r['hard_timeout_seconds']=raw['seconds']
        return r
    require(raw['outcome']=='OK','unexpected outcome')
    require(raw['timing_interpretable'] is True and raw['stats']['detailed_profile_enabled'] is False,'instrumented data')
    require(raw['oracle_H2']==opt and raw['t0']==spec['t0'],'oracle/clock mismatch')
    require(raw['verification']==('TWO_PLAN_REPLAYS_AND_ORACLE' if opt is not None else 'TWO_PLAN_REPLAYS_ONLY'),'replay label')
    trace=raw['trace']; require(bool(trace),'empty trace')
    previous_time=-1; previous_value=None
    for x in trace:
        require(math.isfinite(x['seconds']) and x['seconds']>=previous_time>=-1,'trace time')
        require(previous_value is None or x['H2']<previous_value,'trace improvement')
        require(x['seconds']<=raw['elapsed_seconds']+1e-7,'trace after end')
        require(opt is None or x['H2']>=opt,'trace below oracle')
        previous_time=x['seconds']; previous_value=x['H2']
    require(trace[-1]['H2']==raw['H2'],'final trace value')
    require(near(sum(raw[k] for k in ('setup_seconds','initial_seconds','search_seconds')),raw['elapsed_seconds']),'timer partition')
    require(0<=raw['root_bound_seconds']<=raw['search_seconds'],'nested root timer')
    require(near(raw['overrun_seconds'],max(0,raw['elapsed_seconds']-1)),'overrun')
    require(raw['expanded']==raw['expanded_phase0']+raw['expanded_phase1'],'phase counts')
    require(opt is None or raw['remaining_bound'] is None or raw['remaining_bound']<=opt,'lower certificate')
    require(not raw['certified_optimal'] or opt is None or raw['H2']==opt,'optimal certificate')
    require(raw['certified_gap'] is None or raw['certified_gap']>=0,'negative gap')
    expected_gap=None if raw['remaining_bound'] is None else raw['H2']-raw['remaining_bound']
    require(raw['certified_gap']==expected_gap,'certificate gap identity')
    require(raw['certified_optimal']==(expected_gap==0),'certificate flag identity')
    on_time=raw['certified_optimal'] and raw['elapsed_seconds']<=1
    require(raw['certified_within_wall_conservative']==on_time,'literal proof cutoff')
    evaluations={x['ms']:x for x in raw['evaluation_at_ms']}
    require(set(evaluations)==set(BUDGETS) and len(raw['evaluation_at_ms'])==3,'evaluation grid')
    for ms in BUDGETS:
        value=min((x['H2'] for x in trace if x['seconds']<=ms/1000),default=None)
        regret=None if value is None or opt is None else value-opt
        require(evaluations[ms]==dict(ms=ms,H2=value,feasible=value is not None,regret=regret),'literal evaluation')
        r[f'H2_{ms}ms']=value; r[f'regret_{ms}ms']=regret
    require(raw['H2_within_wall']==r['H2_1000ms'] and raw['regret_within_wall']==r['regret_1000ms'],'wall evaluation')
    first=next((x['seconds'] for x in trace if x['H2']==opt),None) if opt is not None else None
    require(raw['first_optimal_seconds']==first,'first target')
    r.update(end_H2=raw['H2'],end_certified=raw['certified_optimal'],on_time_certified=on_time,
        late_certificate=raw['certified_optimal'] and not on_time,initialization_overrun=raw['initialization_overrun'],
        first_optimal_seconds=first,first_optimal_within_wall=None if opt is None else first is not None and first<=1,
        initial_optimal=None if opt is None else trace[0]['H2']==opt,H2_within_wall=r['H2_1000ms'],
        regret_within_wall=r['regret_1000ms'],certified_gap=raw['certified_gap'],remaining_bound=raw['remaining_bound'])
    for k in TIMERS+COUNTERS: r[k]=raw.get(k,raw['stats'].get(k))
    return r

def read_block(folder,specs,start,source_pins):
    issues=[]; protocol=optional(folder/'PROTOCOL.json')
    rows=lines(folder/'MEASUREMENTS.jsonl'); oracles=lines(folder/'ORACLES.jsonl')
    cases={s['case']:s for s in specs}; source=folder.as_posix()
    if protocol is None:
        issues.append('PROTOCOL missing')
        require(not rows and not oracles,'raw results without protocol')
    else:
        expected=dict(mode='pilot',sources=source_pins,input_file_sha256=INPUT_SHA,start=start,stop=start+8,
            methods=list(METHODS),primary=list(PRIMARY),aux=list(AUX),primary_repeats=3,aux_repeats=1,
            wall_ms=1000,hard_seconds=15,oracle_seconds=15,independent_mothers=2,paired_scenarios=8,
            expected_attempts=112,gate_verified_micro_cases=24,oracle_not_used_as_incumbent=True,
            all_initial_planning_and_bounds_charged=True,profile=False,checkpoints=[],fresh_context_per_call=True,
            preserve_censoring_and_failures=True,method_map={m:dict(policy=MAP[m][0],basis=MAP[m][1]) for m in METHODS})
        for k,v in expected.items(): require(protocol.get(k)==v,('protocol',source,k))
        require(optional(folder/'INPUTS.json')==specs,'selected inputs mismatch')
    oraclemap={}
    for o in oracles:
        require(o['case'] in cases and o['case'] not in oraclemap,'oracle duplicate/unknown')
        require(o['status'] in ('PASS','CENSORED') and o['outside_measured_solves'] is True,'oracle status')
        require(o['proposed_bound_used'] is False and o['incumbent_pruning_used'] is False,'oracle independence')
        require((o['optimum_H2'] is not None)==(o['status']=='PASS'),'oracle censor identity')
        oraclemap[o['case']]=o
    expectedkeys={(s['case'],m,rep) for i,s in enumerate(specs,start) for m,rep,_,_ in schedule(i)}
    rawmap={}
    for r in rows:
        key=(r['case'],r['method'],r['repeat'])
        require(key in expectedkeys and key not in rawmap,'duplicate/unplanned measurement')
        require(r['case'] in oraclemap,'measurement before oracle record')
        rawmap[key]=r
    attempts=lines(folder/'ATTEMPTS.jsonl'); attemptmap={}
    for a in attempts:
        key=(a['case'],a['method'],a['repeat'])
        require(key in expectedkeys and a['status'] in ('STARTED','COMPLETE','HARD_TIMEOUT'),'attempt key/status')
        attemptmap.setdefault(key,[]).append(a['status'])
    for key,r in rawmap.items():
        terminal='COMPLETE' if r['outcome']=='OK' else 'HARD_TIMEOUT'
        require(attemptmap.get(key)==['STARTED',terminal],'attempt journal mismatch')
    if set(attemptmap)!=set(rawmap): issues.append('started or missing attempt has no returned measurement')
    completed=lines(folder/'CASE_COMPLETE.jsonl'); completedmap={}
    for c in completed:
        require(c['case'] in cases and c['case'] not in completedmap,'case completion key')
        require(c['completed_attempts']==14 and c['case'] in oraclemap,'case completion count')
        require(c['oracle_exact']==(oraclemap[c['case']]['status']=='PASS'),'case oracle flag')
        require(sum(k[0]==c['case'] for k in rawmap)==14,'case completion raw coverage')
        completedmap[c['case']]=c
    summary=optional(folder/'SUMMARY.json'); complete=optional(folder/'PROCESS_COMPLETE.json')
    hard=sum(r['outcome']=='HARD_TIMEOUT' for r in rows); ok=len(rows)-hard
    if len(rows)!=112: issues.append('measurement matrix incomplete')
    if len(oraclemap)!=8: issues.append('oracle coverage incomplete')
    if len(completedmap)!=8: issues.append('case completion coverage incomplete')
    if summary is None or complete is None or summary!=complete: issues.append('matching summary/completion absent')
    else:
        expected=dict(status='PASS_WITH_CENSORING' if hard else 'PASS',mode='pilot',records=ok,
            hard_timeouts=hard,cases=8,expected_attempts=112,exact_oracles=sum(o['status']=='PASS' for o in oracles))
        for k,v in expected.items():
            if summary.get(k)!=v: issues.append('summary mismatch: '+k)
    if lines(folder/'FAILURES.jsonl')!=[r for r in rows if r['outcome']=='HARD_TIMEOUT']:
        issues.append('hard-timeout failure ledger does not match measurements')
    for name in ('FAILURE.json','REJECTED_RESULTS.jsonl'):
        if (folder/name).exists(): issues.append('preserved fatal/rejected evidence: '+name)
    calls=[]
    for i,s in enumerate(specs,start):
        opt=oraclemap.get(s['case'],{}).get('optimum_H2')
        for pos,slot in enumerate(schedule(i)):
            r=call_record(rawmap.get((s['case'],slot[0],slot[1])),s,i,slot,pos,opt)
            r['source_run']=source; calls.append(r)
    return calls,dict(run=source,full_source_complete=not issues,issues=issues,ok=ok,hard_timeouts=hard,
        missing=112-len(rows),complete_cases=len(completedmap),exact_oracles=sum(o['status']=='PASS' for o in oracles),
        source_summary=summary,process_complete=complete,preserved_failures=lines(folder/'FAILURES.jsonl'),
        rejected_results=lines(folder/'REJECTED_RESULTS.jsonl'),fatal=optional(folder/'FAILURE.json'))

def case_tables(calls,specs):
    cases=[]; quality=[]
    for s in specs:
        for method in METHODS:
            rs=[r for r in calls if r['case']==s['case'] and r['method']==method]
            n=3 if method in PRIMARY else 1
            require(len(rs)==n,'planned repeat matrix')
            meta={k:rs[0][k] for k in ('case','seed','m','Q','capacity_regime','signal','method','cohort','oracle_H2','t0')}
            c=dict(meta,aggregation='median_of_three_complete_values' if n==3 else 'single_auxiliary_observation',
                planned_repeats=n,ok=sum(r['outcome']=='OK' for r in rs),
                hard_timeouts=sum(r['outcome']=='HARD_TIMEOUT' for r in rs),missing=sum(r['outcome']=='MISSING' for r in rs),
                on_time_certificates=sum(r['on_time_certified'] is True for r in rs),
                late_certificates=sum(r['late_certificate'] is True for r in rs),
                end_certificates=sum(r['end_certified'] is True for r in rs),
                all_repeats_on_time_certified=all(r['on_time_certified'] is True for r in rs),
                initialization_overruns=sum(r['initialization_overrun'] is True for r in rs),
                first_optimal_known_repeats=sum(r['first_optimal_seconds'] is not None for r in rs),
                first_optimal_within_wall_repeats=sum(r['first_optimal_within_wall'] is True for r in rs),
                initial_optimal_repeats=None if meta['oracle_H2'] is None else sum(r['initial_optimal'] is True for r in rs))
            for k in TIMERS+COUNTERS+('end_H2','certified_gap','first_optimal_seconds'):
                c[k]=med([r[k] for r in rs])
            cases.append(c)
            for ms in BUDGETS:
                values=[r[f'H2_{ms}ms'] for r in rs]; value=med(values); opt=meta['oracle_H2']
                regret=None if value is None or opt is None else value-opt
                duration=None if opt is None else opt-meta['t0']
                quality.append(dict(meta,budget_ms=ms,planned_repeats=n,repeat_H2=values,
                    available_repeats=sum(v is not None for v in values),all_repeats_feasible=all(v is not None for v in values),
                    H2=value,regret=regret,relative_regret=ratio(regret,duration),
                    relative_regret_denominator=duration,zero_duration_denominator=duration==0 if duration is not None else None,
                    all_repeats_known_optimal=None if opt is None else all(v==opt for v in values)))
    return cases,quality

def pair_tables(cases,quality,specs):
    cm={(r['case'],r['method']):r for r in cases}; qm={(r['case'],r['method'],r['budget_ms']):r for r in quality}
    pairs=[]; qp=[]
    for s in specs:
        a=cm[s['case'],CANDIDATE]
        for baseline in BASELINES:
            b=cm[s['case'],baseline]
            meta={k:a[k] for k in ('case','seed','m','Q','capacity_regime','signal','oracle_H2','t0')}
            ac=a['all_repeats_on_time_certified']; bc=b['all_repeats_on_time_certified']; eligible=ac and bc
            status='BOTH_THREE_ON_TIME' if eligible else 'CANDIDATE_ONLY' if ac else 'BASELINE_ONLY' if bc else 'NEITHER'
            av=a['elapsed_seconds'] if eligible else None; bv=b['elapsed_seconds'] if eligible else None
            pairs.append(dict(meta,candidate=CANDIDATE,baseline=baseline,pair_status=status,time_eligible=eligible,
                candidate_on_time_repeats=a['on_time_certificates'],baseline_on_time_repeats=b['on_time_certificates'],
                candidate_late_repeats=a['late_certificates'],baseline_late_repeats=b['late_certificates'],
                candidate_elapsed_median=av,baseline_elapsed_median=bv,candidate_over_baseline_ratio=ratio(av,bv),
                elapsed_difference=None if not eligible else av-bv,zero_baseline_denominator=bv==0 if eligible else None,
                time_outcome='UNKNOWN' if not eligible else 'WIN' if av<bv else 'LOSS' if av>bv else 'TIE',
                candidate_expanded_median=a['expanded'],baseline_expanded_median=b['expanded'],
                candidate_final_H2_median=a['end_H2'],baseline_final_H2_median=b['end_H2']))
            for ms in BUDGETS:
                aa=qm[s['case'],CANDIDATE,ms]; bb=qm[s['case'],baseline,ms]
                cv,bv=aa['H2'],bb['H2']; known=cv is not None and bv is not None
                delta=bv-cv if known else None
                denom=None if meta['oracle_H2'] is None else meta['oracle_H2']-meta['t0']
                qp.append(dict(meta,candidate=CANDIDATE,baseline=baseline,budget_ms=ms,
                    candidate_H2_median=cv,baseline_H2_median=bv,candidate_available_repeats=aa['available_repeats'],
                    baseline_available_repeats=bb['available_repeats'],quality_eligible=known,
                    outcome='UNKNOWN' if not known else 'WIN' if cv<bv else 'LOSS' if cv>bv else 'TIE',
                    availability='BOTH_THREE' if known else 'CANDIDATE_ONLY_THREE' if cv is not None else 'BASELINE_ONLY_THREE' if bv is not None else 'NEITHER_THREE',
                    baseline_minus_candidate_H2=delta,relative_improvement=ratio(delta,denom),
                    relative_improvement_denominator=denom,zero_duration_denominator=denom==0 if denom is not None else None))
    return pairs,qp

def strata(specs):
    yield 'ALL','ALL',{s['case'] for s in specs}
    for field in ('m','capacity_regime','signal','seed'):
        values=sorted({len(s['old']) if field=='m' else s[field] for s in specs},key=str)
        for value in values:
            yield field,str(value),{s['case'] for s in specs if (len(s['old']) if field=='m' else s[field])==value}
    for m,cap,signal in sorted({(len(s['old']),s['capacity_regime'],s['signal']) for s in specs},key=str):
        yield 'm_capacity_signal',f'{m}|{cap}|{signal}',{s['case'] for s in specs if (len(s['old']),s['capacity_regime'],s['signal'])==(m,cap,signal)}

def aggregate(cases,quality,pairs,qp,specs):
    coverage=[]; times=[]; qualities=[]
    for field,value,ids in strata(specs):
        base=dict(stratum=field,value=value,scenarios=len(ids),independent_mothers=len({s['seed'] for s in specs if s['case'] in ids}))
        for method in METHODS:
            rs=[r for r in cases if r['case'] in ids and r['method']==method]
            coverage.append(dict(base,method=method,cohort=rs[0]['cohort'],planned_calls=sum(r['planned_repeats'] for r in rs),
                ok=sum(r['ok'] for r in rs),hard_timeouts=sum(r['hard_timeouts'] for r in rs),missing=sum(r['missing'] for r in rs),
                all_repeats_on_time_cases=sum(r['all_repeats_on_time_certified'] for r in rs),
                on_time_certificate_calls=sum(r['on_time_certificates'] for r in rs),late_certificate_calls=sum(r['late_certificates'] for r in rs),
                end_certificate_calls=sum(r['end_certificates'] for r in rs),initialization_overrun_calls=sum(r['initialization_overruns'] for r in rs),
                actual_RAM_measured=False))
        for baseline in BASELINES:
            rs=[r for r in pairs if r['case'] in ids and r['baseline']==baseline]
            eligible=[r for r in rs if r['time_eligible']]; counts=Counter(r['pair_status'] for r in rs)
            ratios=[r['candidate_over_baseline_ratio'] for r in eligible if r['candidate_over_baseline_ratio'] is not None]
            sa=sum(r['candidate_elapsed_median'] for r in eligible); sb=sum(r['baseline_elapsed_median'] for r in eligible)
            times.append(dict(base,candidate=CANDIDATE,baseline=baseline,eligible_cases=len(eligible),
                both_three_on_time=counts['BOTH_THREE_ON_TIME'],candidate_only=counts['CANDIDATE_ONLY'],
                baseline_only=counts['BASELINE_ONLY'],neither=counts['NEITHER'],
                faster=sum(r['time_outcome']=='WIN' for r in eligible),equal=sum(r['time_outcome']=='TIE' for r in eligible),
                slower=sum(r['time_outcome']=='LOSS' for r in eligible),ratio_n=len(ratios),median_case_ratio=med(ratios),
                sum_candidate_case_medians=sa if eligible else None,sum_baseline_case_medians=sb if eligible else None,
                ratio_of_summed_case_medians=ratio(sa,sb) if eligible else None))
            for ms in BUDGETS:
                rr=[r for r in qp if r['case'] in ids and r['baseline']==baseline and r['budget_ms']==ms]
                cc=Counter(r['outcome'] for r in rr); aa=Counter(r['availability'] for r in rr)
                gains=[r['relative_improvement'] for r in rr if r['relative_improvement'] is not None]
                qualities.append(dict(base,candidate=CANDIDATE,baseline=baseline,budget_ms=ms,
                    wins=cc['WIN'],ties=cc['TIE'],losses=cc['LOSS'],unknown=cc['UNKNOWN'],
                    both_three=aa['BOTH_THREE'],candidate_only_three=aa['CANDIDATE_ONLY_THREE'],
                    baseline_only_three=aa['BASELINE_ONLY_THREE'],neither_three=aa['NEITHER_THREE'],
                    relative_improvement_n=len(gains),median_relative_improvement=med(gains)))
    return coverage,times,qualities

def render(summary,times,qualities):
    text=['# V448 exploratory pilot analysis','',
        f"Data completeness: **{summary['status']}**. {summary['ok_calls']} OK, {summary['hard_timeout_calls']} hard-timeout and {summary['missing_calls']} missing calls out of 448 planned calls.",
        'The design has 8 independent mother instances and 32 related capacity/signal scenarios. Three repeats are technical timing repeats, not independent instances.',
        'Primary methods have three repeats per scenario; RADIUS_PAIR_EAGER and old exact ROUTE have one diagnostic observation each and are tabulated separately. All primary NO_BOUND observations are retained.',
        '', '## Strict paired completion time', '',
        'A scenario enters a time comparison only when both methods obtained an optimality certificate in all three repeats with total elapsed time at most 1 second. The table uses each case median; other pair states remain in the denominator. These are selected completed-pair costs, not unconditional speed.', '',
        '| Baseline | Eligible / 32 | Candidate only | Baseline only | Neither | Faster / tied / slower | Ratio of sums |',
        '|---|---:|---:|---:|---:|---|---:|']
    for r in times:
        if r['stratum']=='ALL':
            x=r['ratio_of_summed_case_medians']; x='NA' if x is None else f'{x:.6f}'
            text.append(f"| {r['baseline']} | {r['eligible_cases']} / 32 | {r['candidate_only']} | {r['baseline_only']} | {r['neither']} | {r['faster']} / {r['equal']} / {r['slower']} | {x} |")
    text += ['', '## Literal equal-budget quality', '',
        'H2 at each cutoff uses only improvements timestamped by that cutoff. The case comparison uses a median only when all three repeats have a feasible incumbent; missing observations remain UNKNOWN, not a loss or an infinite imputation. Lower H2 is better. The raw per-repeat values and availability are retained.', '',
        '| Baseline | Budget ms | Win / tie / loss / unknown (32) |', '|---|---:|---|']
    for r in qualities:
        if r['stratum']=='ALL': text.append(f"| {r['baseline']} | {r['budget_ms']} | {r['wins']} / {r['ties']} / {r['losses']} / {r['unknown']} |")
    text += ['', '## Interpretation limits', '',
        'A late final improvement or late proof never receives credit at the 1-second cutoff. First known-optimum hit is distinct from proof of optimality. Unknown oracle optima leave regret and first-target fields missing; zero duration denominators produce NA ratios.',
        'Hard timeouts have no recovered incumbent and no solver component timers. Their external call seconds are kept separately. Failed or partial sources remain visible and prevent a COMPLETE status. No case or failed attempt is silently discarded.',
        'Setup + initial + search partition total elapsed. Root-bound time is nested inside search and must not be added again. This unprofiled pilot does not record detailed quota/Gamma CPU time.',
        'Actual process RAM and Python allocation bytes were not measured. peak_frontier counts heap entries, possibly including stale entries; cache sizes count final entries. Neither is a memory-byte measurement or evidence of reduced actual memory.',
        'This is an exploratory synthetic FIFO-model pilot, not a large-sample confirmation, SUMO execution, or real customer-benefit study. No significance tests or win-based filtering are used.', '']
    return '\n'.join(text)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runs-json',type=Path,default=P/'records/explicit_selected_pilot_run_paths.json')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args(); out=(args.out if args.out.is_absolute() else P/args.out).resolve()
    require(P/'analysis' in out.parents and not out.exists(),'Use a fresh V448 analysis descendant')
    out.mkdir(parents=True,exist_ok=False); started=time.perf_counter()
    try:
        selection=args.runs_json if args.runs_json.is_absolute() else P/args.runs_json
        selected=load(selection); selected=selected['runs'] if isinstance(selected,dict) else selected
        folders=[(Path(s) if Path(s).is_absolute() else P/s).resolve() for s in selected]
        require(len(folders)==4 and len(set(folders))==4 and all(P in f.parents for f in folders),'Select four distinct V448 runs in m6/8/10/12 order')
        inp=P/'instances/pilot_01/INPUTS.json'; require(sha(inp)==INPUT_SHA,'Frozen input hash')
        specs=load(inp); require(len(specs)==32 and len({s['seed'] for s in specs})==8,'Frozen input coverage')
        frozen=load(P/'Pilot_Freeze_Manifest.json'); require(frozen['input_sha256']==INPUT_SHA,'Manifest input')
        calls=[]; statuses=[]; hashes={str(inp):sha(inp),str(selection):sha(selection),str(Path(__file__)):sha(Path(__file__))}
        hashes[str(P/'Pilot_Freeze_Manifest.json')]=sha(P/'Pilot_Freeze_Manifest.json')
        for block,folder in enumerate(folders):
            rr,ss=read_block(folder,specs[8*block:8*block+8],8*block,frozen['sources']); calls+=rr; statuses.append(ss)
            if folder.exists():
                for f in sorted(folder.glob('*.json*')):
                    if f.is_file(): hashes[str(f)]=sha(f)
        require(len(calls)==448,'Full planned matrix')
        cases,quality=case_tables(calls,specs); pairs,qp=pair_tables(cases,quality,specs)
        coverage,times,qualities=aggregate(cases,quality,pairs,qp,specs)
        outputs={'All_Calls.csv':calls,'Primary_Case_Summary.csv':[r for r in cases if r['cohort']=='primary'],
            'Auxiliary_Single_Observation_Cases.csv':[r for r in cases if r['cohort']=='auxiliary'],
            'Primary_Budget_Quality.csv':[r for r in quality if r['cohort']=='primary'],
            'Auxiliary_Single_Observation_Quality.csv':[r for r in quality if r['cohort']=='auxiliary'],
            'Paired_On_Time_Certificate_Time.csv':pairs,'Paired_Budget_Quality.csv':qp,
            'Method_Coverage_Strata.csv':coverage,'Paired_Time_Strata.csv':times,'Paired_Quality_Strata.csv':qualities}
        for name,rows in outputs.items(): csvwrite(out/name,rows)
        summary=dict(status='COMPLETE' if all(s['full_source_complete'] for s in statuses) else 'PROVISIONAL_INCOMPLETE_OR_FAILED_SOURCES',
            planned_scenarios=32,independent_mothers=8,planned_calls=448,
            ok_calls=sum(r['outcome']=='OK' for r in calls),hard_timeout_calls=sum(r['outcome']=='HARD_TIMEOUT' for r in calls),
            missing_calls=sum(r['outcome']=='MISSING' for r in calls),actual_RAM_measured=False,
            primary_time_policy='Both methods: all three repeats certified by literal 1-second total elapsed cutoff',
            primary_quality_policy='All 32 scenarios; all-three-available median, UNKNOWN otherwise; raw values retained',
            source_complete_blocks=sum(s['full_source_complete'] for s in statuses),
            aggregate_time=[r for r in times if r['stratum']=='ALL'],aggregate_quality=[r for r in qualities if r['stratum']=='ALL'])
        dump(out/'Summary.json',summary); dump(out/'Source_Status.json',statuses)
        (out/'Summary.md').write_text(render(summary,times,qualities),encoding='utf-8')
        dump(out/'Analysis_Manifest.json',dict(raw_file_sha256=hashes,selected_runs=[str(x) for x in folders],
            measurement_source_pins=frozen['sources'],script_sha256=sha(Path(__file__)),input_sha256=INPUT_SHA,
            numerical_sources_imported=False,solver_or_oracle_run=False,raw_sources_modified=False))
        dump(out/'ANALYSIS_COMPLETE.json',dict(status=summary['status'],analysis_execution='PASS',seconds=time.perf_counter()-started))
        print(json.dumps(summary,allow_nan=False))
    except BaseException as exc:
        dump(out/'FAILURE.json',dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc()))
        raise

if __name__=='__main__': main()
