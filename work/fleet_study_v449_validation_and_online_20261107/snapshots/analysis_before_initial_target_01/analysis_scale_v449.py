"""Read-only V449 confirmation analysis; no numerical solver imports or execution."""
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
import argparse, csv, hashlib, json, math, statistics, time, traceback
P=Path(__file__).resolve().parent
METHODS=('RADIUS','RADIUS_PAIR_EAGER','RADIUS_PAIR_LAZY','RADIUS_AWA','RADIUS_PAIR_AWA','RADIUS_PAIR_AWA_GATED','NO_BOUND','DP_ADAPTER','ROUTE')
MAP=dict(zip(METHODS,(('ROUTE','radius'),('PAIR_EAGER','radius'),('LAZY_ASTAR','radius'),('AWA_ROUTE','radius'),('AWA_PAIR','radius'),('AWA_GATED','radius'),('NO_BOUND','exact'),('TOPOLOGICAL_DP','none'),('ROUTE','exact'))))
BUDGETS=(100,500,1000)
TARGETS=(0,5,10)
INPUT_SHA='ce0a0e3118603f9585ef9f8b6a8ea119e428b5dc5a1b071835c6efafbe4f8f95'
MANIFEST_SHA='db11af7fa52192252baacc67938dcb06e6f1daf0dbdcf5b204f957a04343cd84'
TIMERS=('elapsed_seconds','setup_seconds','initial_seconds','search_seconds','root_bound_seconds','overrun_seconds')
WORK=('expanded','expanded_phase0','expanded_phase1','generated','pruned','dominated','stale_pops','joint_checks_at_pop','joint_pruned_at_pop','partial_expansions','base_calls','phase1_base_calls','full_calls','cutoff_calls','gate_calls','radius_calls','skip_exact_quota','skip_radius_union_saturation','skip_alpha_union','skip_urel','lazy_generation_bypasses','lazy_pop_bypasses','lazy_reinsertions','closure_queries','closure_cache_hits','dijkstra_runs','edge_relaxations','cache_clears')
PROXIES=('peak_frontier','closure_cache_size','fa_cache_size','gamma_cache_size','structural_labels','accepted_updates')
RAW_NAMES=('PROTOCOL.json','INPUTS.json','ATTEMPTS.jsonl','ORACLES.jsonl','MEASUREMENTS.jsonl','CASE_COMPLETE.jsonl','SUMMARY.json','PROCESS_COMPLETE.json','FAILURES.jsonl','FAILURE.json','REJECTED_RESULTS.jsonl')
def require(ok,why):
    if not ok:raise AssertionError(why)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def optional(p):return load(p) if p.exists() else None
def lines(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()] if p.exists() else []
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def near(a,b):return a is not None and b is not None and math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7)
def median(xs):return statistics.median(xs) if xs and all(x is not None for x in xs) else None
def ratio(a,b):return None if a is None or b is None or b==0 else a/b
def outcome(a,b):return 'UNKNOWN' if a is None or b is None else ('WIN' if a<b else 'LOSS' if a>b else 'TIE')
def csvwrite(p,rows):
    if not rows:p.write_text('',encoding='utf-8');return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerows({k:json.dumps(v,allow_nan=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
def schedule(index):
    slots=[]
    for rep in range(3):
        off=(3*index+rep)%9
        slots.extend((m,rep,j) for j,m in enumerate(METHODS[off:]+METHODS[:off]))
    return slots

def call_record(raw,s,index,slot,position,opt):
    method,rep,j=slot
    ident=dict(case=s['case'],seed=s['seed'],m=len(s['old']),Q=s['Q'],signal=s['signal'],capacity_regime=s['capacity_regime'],method=method,arm=method,policy=MAP[method][0],bound_basis=MAP[method][1],repeat=rep,position_within_repeat=j,position_within_case=position,mode='main',cohort='three_repeat',input_sha256=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest())
    r=dict(ident,outcome='MISSING',oracle_H2=opt,t0=s['t0'],end_H2=None,remaining_bound=None,certified_gap=None,end_certified=None,on_time_certified=None,late_certificate=None,initialization_overrun=None,hard_timeout_seconds=None,initial_H2=None,initial_plan=None,oracle_independent_of_this_method=method!='DP_ADAPTER')
    r.update({k:None for k in TIMERS+WORK+PROXIES})
    for ms in BUDGETS:r.update({f'H2_{ms}ms':None,f'regret_{ms}ms':None})
    for pct in TARGETS:r.update({f'first_{pct}pct_seconds':None,f'first_{pct}pct_expansion':None,f'first_{pct}pct_on_time':None})
    if raw is None:return r
    for k,v in ident.items():require(raw.get(k)==v,('row identity',s['case'],method,rep,k,raw.get(k),v))
    require(raw.get('wall_budget_ms')==1000,'one-second budget');r['outcome']=raw['outcome']
    if raw['outcome']=='HARD_TIMEOUT':
        require(raw.get('status')=='HARD_TIMEOUT' and raw['hard_limit_seconds']==15 and raw['incumbent_not_recovered'] is True,'hard schema')
        require(raw['not_counted_as_solved'] is True and raw['seconds']>=0,'hard accounting')
        r['hard_timeout_seconds']=raw['seconds'];return r
    require(raw['outcome']=='OK' and raw['timing_interpretable'] is True and raw['stats']['detailed_profile_enabled'] is False,'returned mode')
    require(raw['oracle_H2']==opt and raw['t0']==s['t0'],'oracle/clock')
    if method=='DP_ADAPTER':
        verify='FROZEN_REFERENCE_TRACE_REPLAY_AND_SHARED_DP_ORACLE' if opt is not None else 'FROZEN_REFERENCE_TRACE_REPLAY_ONLY'
        require(raw['stats']['proposed_bound_used'] is False and raw['stats']['incumbent_pruning_used'] is False,'DP recurrence')
    else:verify='TWO_PLAN_REPLAYS_AND_ORACLE' if opt is not None else 'TWO_PLAN_REPLAYS_ONLY'
    require(raw['verification']==verify and raw['oracle_independent_of_this_method']==(method!='DP_ADAPTER'),'validation scope')
    trace=raw['trace'];require(bool(trace),'empty incumbent trace');last_t=-1;last_value=None;last_k=-1
    for x in trace:
        require(math.isfinite(x['seconds']) and last_t<=x['seconds']<=raw['elapsed_seconds']+1e-7,'trace clock')
        require(last_value is None or x['H2']<last_value,'non-improving incumbent trace')
        require(last_k<=x['expansion_index']<=raw['expanded']+raw.get('partial_expansions',0),'trace expansion index')
        require(opt is None or x['H2']>=opt,'incumbent below oracle')
        last_t=x['seconds'];last_value=x['H2'];last_k=x['expansion_index']
    require(trace[-1]['H2']==raw['H2'] and trace[-1]['plan']==raw['plan'],'final incumbent trace')
    require(near(sum(raw[k] for k in ('setup_seconds','initial_seconds','search_seconds')),raw['elapsed_seconds']),'timer partition')
    require(all(math.isfinite(raw[k]) and raw[k]>=0 for k in TIMERS),'negative/nonfinite timer')
    require(raw['root_bound_seconds']<=raw['search_seconds']+1e-7,'nested root timer')
    require(near(raw['overrun_seconds'],max(0,raw['elapsed_seconds']-1)),'overrun identity')
    require(raw['expanded']==raw['expanded_phase0']+raw['expanded_phase1'],'phase expansion partition')
    lower=raw['remaining_bound'];gap=None if lower is None else raw['H2']-lower
    require(raw['certified_gap']==gap and (gap is None or gap>=0),'gap identity')
    require(raw['certified_optimal']==(gap==0),'certificate identity')
    require(opt is None or lower is None or lower<=opt,'certificate above oracle')
    require(not raw['certified_optimal'] or opt is None or raw['H2']==opt,'false optimal certificate')
    on_time=raw['certified_optimal'] and raw['elapsed_seconds']<=1
    require(raw['certified_within_wall_conservative']==on_time,'on-time proof')
    evaluations={x['ms']:x for x in raw['evaluation_at_ms']}
    require(set(evaluations)==set(BUDGETS) and len(raw['evaluation_at_ms'])==3,'quality grid')
    for ms in BUDGETS:
        value=min((x['H2'] for x in trace if x['seconds']<=ms/1000),default=None)
        regret=None if value is None or opt is None else value-opt
        require(evaluations[ms]==dict(ms=ms,H2=value,feasible=value is not None,regret=regret),'literal quality')
        r[f'H2_{ms}ms']=value;r[f'regret_{ms}ms']=regret
    require(raw['H2_within_wall']==r['H2_1000ms'] and raw['regret_within_wall']==r['regret_1000ms'],'wall quality')
    require(len(raw['first_quality_thresholds'])==3,'first-good grid')
    for pct,stored in zip(TARGETS,raw['first_quality_thresholds']):
        fraction=pct/100;target=None if opt is None else opt+fraction*(opt-s['t0'])
        hit=next((x for x in trace if target is not None and x['H2']<=target),None)
        seconds=None if hit is None else hit['seconds'];ki=None if hit is None else hit['expansion_index']
        timely=None if opt is None else hit is not None and seconds<=1
        require(stored==dict(relative_gap=fraction,target_H2=target,seconds=seconds,expansion_index=ki,reached_within_wall=timely),'post-hoc threshold trace')
        r[f'first_{pct}pct_seconds']=seconds;r[f'first_{pct}pct_expansion']=ki;r[f'first_{pct}pct_on_time']=timely
    require(raw['first_optimal_seconds']==r['first_0pct_seconds'] and raw['first_optimal_expansion']==r['first_0pct_expansion'],'first optimum trace')
    r.update(end_H2=raw['H2'],remaining_bound=lower,certified_gap=gap,end_certified=raw['certified_optimal'],on_time_certified=on_time,late_certificate=raw['certified_optimal'] and not on_time,initialization_overrun=raw['initialization_overrun'],initial_H2=trace[0]['H2'],initial_plan=trace[0]['plan'])
    for k in TIMERS+WORK+PROXIES:r[k]=raw.get(k,raw['stats'].get(k))
    return r

def read_block(folder,all_specs,pins,raw_hashes):
    protocol=load(folder/'PROTOCOL.json');start=protocol['start'];stop=protocol['stop']
    require(start%4==stop%4==0 and 0<=start<stop<=400 and stop-start in (4,8),'block range')
    specs=all_specs[start:stop];n=len(specs);expected_calls=n*27
    require(len({len(s['old']) for s in specs})==1,'mixed scale block')
    expected=dict(mode='main',sources=pins,input_file_sha256=INPUT_SHA,start=start,stop=stop,methods=list(METHODS),method_map={m:dict(policy=MAP[m][0],basis=MAP[m][1]) for m in METHODS},repeats=3,wall_ms=1000,watchdog_seconds=15,oracle_seconds=15,expected_attempts=expected_calls,independent_mothers=len({s['seed'] for s in specs}),related_scenarios=n,full_micro24_pass=True,frozen_V448_solver_unchanged=True,oracle_not_used_as_incumbent=True,oracle_independent_of_DP_ADAPTER=False,fresh_context_per_call=True,all_setup_initial_queries_trace_certificate_charged=True,checkpoint_snapshots=False,profile=False,actual_RAM_measured=False)
    for k,v in expected.items():require(protocol.get(k)==v,('protocol',str(folder),k))
    require(load(folder/'INPUTS.json')==specs,'frozen block input')
    gatepath=Path(protocol['gate_path']);require(sha(gatepath)==protocol['gate_sha256'],'gate hash')
    gate=load(gatepath);require(gate['status']=='PASS' and gate['sources']==pins and len(gate['case_ids'])==24,'micro gate scope')
    raw_hashes[str(gatepath)]=sha(gatepath)
    for name in RAW_NAMES:
        path=folder/name
        if path.exists():raw_hashes[str(path)]=sha(path)
    issues=[];oracles=lines(folder/'ORACLES.jsonl');rows=lines(folder/'MEASUREMENTS.jsonl')
    ids={s['case'] for s in specs};oraclemap={};rawmap={}
    for o in oracles:
        require(o['case'] in ids and o['case'] not in oraclemap,'oracle duplicate/unplanned')
        require(o['status'] in ('PASS','CENSORED') and o['outside_measured_solves'] is True,'oracle status')
        require(o['independent_of_DP_ADAPTER'] is False and o['not_passed_into_benchmark'] is True,'oracle separation')
        require(o['proposed_bound_used'] is False and o['incumbent_pruning_used'] is False,'oracle recurrence')
        require((o['optimum_H2'] is not None)==(o['status']=='PASS') and o['certified_optimal']==(o['status']=='PASS'),'oracle exactness')
        oraclemap[o['case']]=o
    keys={(s['case'],m,rep) for s in specs for m in METHODS for rep in range(3)}
    for r in rows:
        key=(r['case'],r['method'],r['repeat'])
        require(key in keys and key not in rawmap and r['case'] in oraclemap,'measurement duplicate/unplanned/oracle absent')
        rawmap[key]=r
    amap=defaultdict(list)
    for a in lines(folder/'ATTEMPTS.jsonl'):
        key=(a['case'],a['method'],a['repeat'])
        require(key in keys and a['status'] in ('STARTED','COMPLETE','HARD_TIMEOUT'),'attempt identity')
        amap[key].append(a['status'])
    for key,r in rawmap.items():require(amap[key]==['STARTED','COMPLETE' if r['outcome']=='OK' else 'HARD_TIMEOUT'],'attempt completion')
    if set(amap)!=set(rawmap):issues.append('started/missing attempt without returned row')
    completed={}
    for c in lines(folder/'CASE_COMPLETE.jsonl'):
        require(c['case'] in ids and c['case'] not in completed,'case completion duplicate')
        require(c['completed_attempts']==27 and c['case'] in oraclemap,'case completion count')
        require(c['oracle_exact']==(oraclemap[c['case']]['status']=='PASS'),'case oracle flag')
        require(sum(k[0]==c['case'] for k in rawmap)==27,'case completion raw coverage')
        completed[c['case']]=c
    hardrows=[r for r in rows if r['outcome']=='HARD_TIMEOUT'];hard=len(hardrows);ok=len(rows)-hard
    if len(rows)!=expected_calls:issues.append('incomplete measurement matrix')
    if len(oraclemap)!=n:issues.append('incomplete oracle coverage')
    if len(completed)!=n:issues.append('incomplete case completion coverage')
    sm=optional(folder/'SUMMARY.json');pc=optional(folder/'PROCESS_COMPLETE.json')
    if sm is None or pc is None or sm!=pc:issues.append('matching summary/completion absent')
    else:
        se=dict(status='PASS_WITH_CENSORING' if hard else 'PASS',mode='main',records=ok,hard_timeouts=hard,cases=n,expected_attempts=expected_calls,exact_oracles=sum(o['status']=='PASS' for o in oracles))
        for k,v in se.items():
            if sm.get(k)!=v:issues.append('summary mismatch: '+k)
    if lines(folder/'FAILURES.jsonl')!=hardrows:issues.append('hard failure ledger mismatch')
    for name in ('FAILURE.json','REJECTED_RESULTS.jsonl'):
        if (folder/name).exists():issues.append('preserved failure: '+name)
    calls=[]
    for i,s in enumerate(specs,start):
        opt=oraclemap.get(s['case'],{}).get('optimum_H2');casecalls=[]
        for position,slot in enumerate(schedule(i)):
            r=call_record(rawmap.get((s['case'],slot[0],slot[1])),s,i,slot,position,opt)
            r['source_run']=str(folder);casecalls.append(r)
        returned=[r for r in casecalls if r['outcome']=='OK']
        require(len({r['initial_H2'] for r in returned})<=1 and len({tuple(r['initial_plan']) for r in returned})<=1,'common initialization')
        require(len({r['end_H2'] for r in returned if r['end_certified']})<=1,'conflicting optimal certificates')
        calls.extend(casecalls)
    return calls,oracles,dict(run=str(folder),start=start,stop=stop,full_source_complete=not issues,issues=issues,ok=ok,hard_timeouts=hard,missing=expected_calls-len(rows),complete_cases=len(completed),exact_oracles=sum(o['status']=='PASS' for o in oracles),summary=sm,process_complete=pc,preserved_failures=lines(folder/'FAILURES.jsonl'),fatal=optional(folder/'FAILURE.json'))

def make_case_tables(calls):
    groups=defaultdict(list)
    for r in calls:groups[(r['case'],r['method'])].append(r)
    case_rows=[];quality=[];targets=[]
    for rs in groups.values():
        require(len(rs)==3 and {r['repeat'] for r in rs}=={0,1,2},'three planned repeats')
        meta={k:rs[0][k] for k in ('case','seed','m','Q','capacity_regime','signal','method','oracle_H2','t0')}
        c=dict(meta,planned_repeats=3,ok=sum(r['outcome']=='OK' for r in rs),hard_timeouts=sum(r['outcome']=='HARD_TIMEOUT' for r in rs),missing=sum(r['outcome']=='MISSING' for r in rs),on_time_certificates=sum(r['on_time_certified'] is True for r in rs),end_certificates=sum(r['end_certified'] is True for r in rs),late_certificates=sum(r['late_certificate'] is True for r in rs),initialization_overruns=sum(r['initialization_overrun'] is True for r in rs),all3_on_time_certified=all(r['on_time_certified'] is True for r in rs))
        for k in TIMERS+WORK+PROXIES+('end_H2','certified_gap','remaining_bound'):c[k]=median([r[k] for r in rs])
        case_rows.append(c)
        for ms in BUDGETS:
            values=[r[f'H2_{ms}ms'] for r in rs];value=median(values);opt=meta['oracle_H2']
            regret=None if value is None or opt is None else value-opt
            quality.append(dict(meta,ms=ms,available_repeats=sum(v is not None for v in values),all3_feasible=all(v is not None for v in values),H2_median=value,H2_repeat_values=values,regret_median=regret,relative_regret=ratio(regret,None if opt is None else opt-meta['t0']),all3_optimal=None if opt is None else all(v==opt for v in values),median_optimal=None if value is None or opt is None else value==opt))
        for pct in TARGETS:
            seconds=[r[f'first_{pct}pct_seconds'] for r in rs]
            targets.append(dict(meta,target_pct=pct,target_H2=None if meta['oracle_H2'] is None else meta['oracle_H2']+pct/100*(meta['oracle_H2']-meta['t0']),hit_repeats=sum(x is not None for x in seconds),on_time_hit_repeats=sum(r[f'first_{pct}pct_on_time'] is True for r in rs),all3_reached_on_time=all(r[f'first_{pct}pct_on_time'] is True for r in rs),seconds_median=median(seconds),expansion_median=median([r[f'first_{pct}pct_expansion'] for r in rs])))
    return case_rows,quality,targets

def strata(r):
    sig='signal' if r['signal'] else 'free';cap=r['capacity_regime'];m=r['m']
    return ('ALL',f'm{m}',sig,f'capacity_{cap}',f'm{m}_{sig}',f'm{m}_{cap}',f'm{m}_{cap}_{sig}')
def describe(values,prefix):
    xs=[v for v in values if v is not None]
    return {prefix+'_n':len(xs),prefix+'_sum':sum(xs) if xs else None,prefix+'_median':median(xs),prefix+'_min':min(xs) if xs else None,prefix+'_max':max(xs) if xs else None}

def grouped_summaries(case_rows,quality,targets):
    result={};groups=defaultdict(list)
    for r in case_rows:
        for st in strata(r):groups[(st,r['method'])].append(r)
    work=[]
    for (st,m),rs in groups.items():
        d=dict(stratum=st,method=m,scenarios=len(rs),independent_mothers=len({r['seed'] for r in rs}),planned_calls=3*len(rs),ok=sum(r['ok'] for r in rs),hard_timeouts=sum(r['hard_timeouts'] for r in rs),missing=sum(r['missing'] for r in rs),all3_on_time_certified=sum(r['all3_on_time_certified'] for r in rs),on_time_certificates=sum(r['on_time_certificates'] for r in rs),late_certificates=sum(r['late_certificates'] for r in rs),initialization_overruns=sum(r['initialization_overruns'] for r in rs))
        for k in TIMERS+WORK+PROXIES:d.update(describe([r[k] for r in rs],k))
        work.append(d)
    result['work_and_proof']=work
    for name,rows,axis in (('quality',quality,'ms'),('first_good',targets,'target_pct')):
        groups=defaultdict(list)
        for r in rows:
            for st in strata(r):groups[(st,r['method'],r[axis])].append(r)
        out=[]
        for (st,m,level),rs in groups.items():
            d=dict(stratum=st,method=m,scenarios=len(rs),independent_mothers=len({r['seed'] for r in rs}),**{axis:level})
            if name=='quality':
                d.update(all3_feasible=sum(r['all3_feasible'] for r in rs),unknown_cases=sum(r['H2_median'] is None for r in rs),known_oracle_cases=sum(r['oracle_H2'] is not None for r in rs),all3_optimal=sum(r['all3_optimal'] is True for r in rs),median_optimal=sum(r['median_optimal'] is True for r in rs))
                for k in ('H2_median','regret_median','relative_regret'):d.update(describe([r[k] for r in rs],k))
            else:
                eligible=[r for r in rs if r['all3_reached_on_time']]
                d.update(known_oracle_cases=sum(r['oracle_H2'] is not None for r in rs),all3_reached_on_time=len(eligible))
                d.update(describe([r['seconds_median'] for r in eligible],'eligible_seconds'))
                d.update(describe([r['expansion_median'] for r in eligible],'eligible_expansions'))
            out.append(d)
        result[name]=out
    return result

def pair_tables(case_rows,quality,targets):
    cq={(r['case'],r['method'],r['ms']):r for r in quality};ct={(r['case'],r['method'],r['target_pct']):r for r in targets}
    cm={(r['case'],r['method']):r for r in case_rows}
    metas={r['case']:{k:r[k] for k in ('case','seed','m','Q','capacity_regime','signal')} for r in case_rows}
    qp=[];tp=[]
    for cid,meta in metas.items():
        for left,right in combinations(METHODS,2):
            pair=dict(meta,left=left,right=right)
            for ms in BUDGETS:
                a=cq[(cid,left,ms)];b=cq[(cid,right,ms)];av=a['H2_median'];bv=b['H2_median']
                qp.append(dict(pair,ms=ms,left_H2=av,right_H2=bv,outcome=outcome(av,bv),left_all3_feasible=a['all3_feasible'],right_all3_feasible=b['all3_feasible'],H2_difference=None if av is None or bv is None else av-bv))
            for target in ('proof',)+TARGETS:
                if target=='proof':
                    a=cm[(cid,left)];b=cm[(cid,right)];ae=a['all3_on_time_certified'];be=b['all3_on_time_certified']
                    av=a['elapsed_seconds'];bv=b['elapsed_seconds'];ak=a['expanded'];bk=b['expanded']
                else:
                    a=ct[(cid,left,target)];b=ct[(cid,right,target)];ae=a['all3_reached_on_time'];be=b['all3_reached_on_time']
                    av=a['seconds_median'];bv=b['seconds_median'];ak=a['expansion_median'];bk=b['expansion_median']
                common=ae and be
                tp.append(dict(pair,target=str(target),left_all3_eligible=ae,right_all3_eligible=be,common=common,left_seconds=av if common else None,right_seconds=bv if common else None,left_to_right_ratio=ratio(av,bv) if common else None,time_outcome=outcome(av,bv) if common else 'INELIGIBLE',left_expansions=ak if common else None,right_expansions=bk if common else None))
    gs=defaultdict(list)
    for r in qp:
        for st in strata(r):gs[(st,r['left'],r['right'],r['ms'])].append(r)
    qs=[]
    for (st,a,b,ms),rs in gs.items():
        counts=Counter(r['outcome'] for r in rs)
        qs.append(dict(stratum=st,left=a,right=b,ms=ms,scenarios=len(rs),independent_mothers=len({r['seed'] for r in rs}),wins=counts['WIN'],ties=counts['TIE'],losses=counts['LOSS'],unknown=counts['UNKNOWN'],left_only_feasible=sum(r['left_all3_feasible'] and not r['right_all3_feasible'] for r in rs),right_only_feasible=sum(r['right_all3_feasible'] and not r['left_all3_feasible'] for r in rs),neither_feasible=sum(not r['left_all3_feasible'] and not r['right_all3_feasible'] for r in rs),**describe([r['H2_difference'] for r in rs],'paired_H2_difference')))
    gs=defaultdict(list)
    for r in tp:
        for st in strata(r):gs[(st,r['left'],r['right'],r['target'])].append(r)
    ts=[]
    for (st,a,b,target),rs in gs.items():
        eligible=[r for r in rs if r['common']];lefts=[r['left_seconds'] for r in eligible];rights=[r['right_seconds'] for r in eligible]
        counts=Counter(r['time_outcome'] for r in eligible)
        ts.append(dict(stratum=st,left=a,right=b,target=target,scenarios=len(rs),independent_mothers=len({r['seed'] for r in rs}),both_all3_on_time=len(eligible),left_only=sum(r['left_all3_eligible'] and not r['right_all3_eligible'] for r in rs),right_only=sum(r['right_all3_eligible'] and not r['left_all3_eligible'] for r in rs),neither=sum(not r['left_all3_eligible'] and not r['right_all3_eligible'] for r in rs),common_mothers=len({r['seed'] for r in eligible}),left_seconds_sum=sum(lefts) if eligible else None,right_seconds_sum=sum(rights) if eligible else None,ratio_of_sums=ratio(sum(lefts),sum(rights)) if eligible else None,median_case_ratio=median([r['left_to_right_ratio'] for r in eligible if r['left_to_right_ratio'] is not None]),ratio_defined_cases=sum(r['left_to_right_ratio'] is not None for r in eligible),earlier=counts['WIN'],same=counts['TIE'],later=counts['LOSS']))
    return qp,tp,qs,ts

def report(out,summary,groups):
    q={(r['method'],r['ms']):r for r in groups['quality'] if r['stratum']=='ALL'}
    w={r['method']:r for r in groups['work_and_proof'] if r['stratum']=='ALL'}
    text=['# V449 frozen nine-method confirmation analysis','',f"Source status: **{summary['status']}**. {summary['ok']} returned calls, {summary['hard_timeouts']} hard timeouts and {summary['missing']} missing calls out of 10,800 planned calls.",
        'The design contains 100 independent random mother networks and 400 related capacity/signal scenarios. Each method has three technical repeats. No single universal winner is selected.','',
        'Early feasible quality is the primary view. The table counts scenarios with all three incumbents available at the literal deadline, and all three equal to the known optimum. Missing data and unknown optima are not converted to success.','',
        '| Method | 100 ms feasible / optimal | 500 ms feasible / optimal | 1000 ms feasible / optimal | All 3 proofs within 1 s |','|---|---:|---:|---:|---:|']
    for m in METHODS:
        cells=[f"{q[m,ms]['all3_feasible']}/400 / {q[m,ms]['all3_optimal']}/400" for ms in BUDGETS]
        text.append('| '+m+' | '+' | '.join(cells)+f" | {w[m]['all3_on_time_certified']}/400 |")
    text += ['', 'Pair_Quality_Summary.csv reports all 36 method pairs at 100/500/1000 ms, including wins, ties, losses, unknown cases and asymmetric availability. Case_Quality.csv preserves every case and all repeat values. Quality comparisons use the median only when all three values exist.',
        '', 'Pair_Time_Summary.csv separates proof time from first 0%, 5% and 10% relative-duration-gap targets. Each time comparison uses only scenarios where BOTH methods achieved the specified event within one second in ALL THREE repeats; the remaining left-only, right-only and neither counts stay visible. Targets use opt + fraction*(opt - t0), derived after search. Ratios use paired case medians, never pooled calls. Zero denominators are NA.',
        '', 'Late improvements and certificates remain in end-of-run records but receive no credit at earlier cutoffs. Hard timeouts have no recovered incumbent; their duration is not treated as solver elapsed or proof time. Returned soft-overrun values are retained separately. Incomplete source blocks make the report provisional.',
        '', 'Case_Work_And_Proof.csv and Work_And_Proof_Summary.csv distinguish elapsed/setup/initial/search/root timing, phase-specific completed expansions, joint rejection counts and available work counters. Root timing is nested within search; it must not be added again. Detailed profiling was disabled, so absent internal DP/closure counters are NA.',
        '', 'No process RAM or Python allocation bytes were measured. Peak heap entries (including stale labels), closure/cache entries, and DP structural-label counts are storage proxies with different meanings. The DP closure caches full arrival vectors; search closures cache scalar queries. These counts do not establish an actual memory saving.',
        '', 'DP_ADAPTER is this study\'s standard complete topological DP implementation. Its reference oracle shares recurrence/network source; it is not independently validated by that same source. Separate small exhaustive checks and frozen-reference plan replay provide the cross-checks. Lazy A* and weighted anytime A* are published search-policy adaptations to this local model, not reproductions of a complete published freight dispatcher. The joint bound is supplied by this study.',
        '', 'This confirmation concerns synthetic local two-handoff H2 optimization. It supplies no whole-fleet SUMO or real-world delivery benefit by itself. Signal/capacity variants are paired conditions, not additional independent mother networks. No p-values or extrapolated success probabilities are reported.',
        '', 'Source_Status.json and Provenance.json retain explicit selection, source/raw hashes, incomplete/failure evidence and accounting. All measured sources and input files are read only.']
    (out/'Analysis_Report.md').write_text('\n'.join(text)+'\n',encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selected',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();out=(args.out if args.out.is_absolute() else P/args.out).resolve()
    require((P/'analysis').resolve() in out.parents and not out.exists(),'Fresh output below V449/analysis required')
    out.mkdir(parents=True);started=time.perf_counter();raw_hashes={}
    try:
        source_manifest=P/'Scale_Source_Manifest.json';require(sha(source_manifest)==MANIFEST_SHA,'frozen source manifest')
        manifest=load(source_manifest);pins=manifest['sources'];require(len(pins)==12,'source count')
        for path,value in pins.items():require(sha(Path(path))==value,('frozen source drift',path))
        inp=P/'instances/scale_main_01/INPUTS.json';require(sha(inp)==INPUT_SHA==manifest['inputs']['main'],'main input hash')
        specs=load(inp);require(len(specs)==400 and len({s['case'] for s in specs})==400 and len({s['seed'] for s in specs})==100,'main units')
        require(Counter(len(s['old']) for s in specs)=={6:100,8:100,10:100,12:100},'scale counts')
        for seed in {s['seed'] for s in specs}:
            rs=[s for s in specs if s['seed']==seed]
            require(len(rs)==4 and len({(s['capacity_regime'],s['signal']) for s in rs})==4,'paired mother conditions')
        selected=args.selected if args.selected.is_absolute() else P/args.selected
        data=load(selected);data=data['runs'] if isinstance(data,dict) else data
        folders=[(Path(x) if Path(x).is_absolute() else P/Path(x)).resolve() for x in data]
        require(len(folders)==len(set(folders)) and folders,'explicit unique run selection')
        calls=[];oracles=[];statuses=[];covered=set()
        for folder in folders:
            require(P.resolve() in folder.parents,'selected source outside V449')
            block,obs,status=read_block(folder,specs,pins,raw_hashes)
            indices=set(range(status['start'],status['stop']));require(not covered&indices,'overlapping source ranges')
            covered|=indices;calls.extend(block);oracles.extend(obs);statuses.append(status)
        require(covered==set(range(400)),'explicit selection must cover all 400 frozen scenarios')
        require(len(calls)==10800,'planned call matrix')
        cases,quality,targets=make_case_tables(calls);groups=grouped_summaries(cases,quality,targets)
        qp,tp,qs,ts=pair_tables(cases,quality,targets)
        for filename,rows in (('Calls.csv',calls),('Case_Work_And_Proof.csv',cases),('Case_Quality.csv',quality),('Case_First_Good.csv',targets),('Work_And_Proof_Summary.csv',groups['work_and_proof']),('Quality_Summary.csv',groups['quality']),('First_Good_Summary.csv',groups['first_good']),('Pair_Quality_Cases.csv',qp),('Pair_Time_Cases.csv',tp),('Pair_Quality_Summary.csv',qs),('Pair_Time_Summary.csv',ts)):
            csvwrite(out/filename,rows)
        counts=Counter(r['outcome'] for r in calls)
        summary=dict(status='COMPLETE' if all(s['full_source_complete'] for s in statuses) else 'PROVISIONAL_INCOMPLETE_SOURCE',planned_calls=10800,ok=counts['OK'],hard_timeouts=counts['HARD_TIMEOUT'],missing=counts['MISSING'],independent_mothers=100,related_scenarios=400,methods=list(METHODS),technical_repeats=3,exact_oracle_cases=sum(o['status']=='PASS' for o in oracles),source_blocks=len(statuses),primary_view='literal early quality; first-good and proof separately',actual_RAM_measured=False,ratio_scope='both methods all three repeats meet event by 1s',all36_pairs_retained=True,analysis_seconds=time.perf_counter()-started)
        dump(out/'Summary.json',summary);dump(out/'Source_Status.json',statuses)
        dump(out/'Provenance.json',dict(analysis_source=str(Path(__file__).resolve()),analysis_sha256=sha(Path(__file__)),selected_path=str(selected),selected_sha256=sha(selected),selected_runs=[str(x) for x in folders],input_path=str(inp),input_sha256=sha(inp),source_manifest_sha256=sha(source_manifest),frozen_sources=pins,raw_sha256=raw_hashes))
        report(out,summary,groups)
        for path,value in pins.items():require(sha(Path(path))==value,('source drift during analysis',path))
        for path,value in raw_hashes.items():require(sha(Path(path))==value,('raw changed during analysis',path))
        require(sha(inp)==INPUT_SHA,'input changed during analysis')
        dump(out/'PROCESS_COMPLETE.json',summary);print(json.dumps(summary),flush=True)
    except BaseException as exc:
        failure=dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc(),seconds=time.perf_counter()-started,raw_hashes_read=raw_hashes)
        dump(out/'FAILURE.json',failure);dump(out/'PROCESS_COMPLETE.json',failure);raise
if __name__=='__main__':main()
