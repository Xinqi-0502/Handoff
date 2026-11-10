"""Independent raw V449 audit, prepared only. Never imports analysis or solver.
Requires --execute, 52 complete selected blocks and a completed official analysis.
Recomputes all 36 pairs, literal quality, first-good and proof from raw traces.
"""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import combinations
import argparse,csv,hashlib,json,math,statistics,traceback
ROOT=Path(__file__).resolve().parents[1]
METHODS=('RADIUS','RADIUS_PAIR_EAGER','RADIUS_PAIR_LAZY','RADIUS_AWA','RADIUS_PAIR_AWA','RADIUS_PAIR_AWA_GATED','NO_BOUND','DP_ADAPTER','ROUTE')
MAPPING=(('ROUTE','radius'),('PAIR_EAGER','radius'),('LAZY_ASTAR','radius'),('AWA_ROUTE','radius'),('AWA_PAIR','radius'),('AWA_GATED','radius'),('NO_BOUND','exact'),('TOPOLOGICAL_DP','none'),('ROUTE','exact'))
BUDGETS=(100,500,1000);TARGETS=(0,5,10)
INPUT_SHA='ce0a0e3118603f9585ef9f8b6a8ea119e428b5dc5a1b071835c6efafbe4f8f95'
MANIFEST_SHA='db11af7fa52192252baacc67938dcb06e6f1daf0dbdcf5b204f957a04343cd84'
FILES={}
def need(v,label):
    if not v:raise AssertionError(label)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    p=Path(p);FILES[str(p)]=sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def jsonl(p,required=True):
    p=Path(p)
    if not p.exists():
        need(not required,('missing file',str(p)));return []
    FILES[str(p)]=sha(p)
    return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,indent=2,allow_nan=False)
def csvout(p,rows):
    need(bool(rows),'empty output table')
    with Path(p).open('x',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def med(values):return statistics.median(values) if all(x is not None for x in values) else None
def ratio(a,b):return None if a is None or b is None or b==0 else a/b
def close(a,b):return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7)
def met(v,opt,t0,pct):
    # Equivalent duration-gap threshold, avoiding reliance on cached target floats.
    return opt is not None and 100*(v-opt)<=pct*(opt-t0)
def strata(s):
    m=len(s['old']);sig='signal' if s['signal'] else 'free';cap=s['capacity_regime']
    return ('ALL',f'm{m}',sig,f'capacity_{cap}',f'm{m}_{sig}',f'm{m}_{cap}',f'm{m}_{cap}_{sig}')
def read_csv(p):
    p=Path(p);FILES[str(p)]=sha(p)
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def equal_csv(raw,want,label):
    if want is None:need(raw=='',('expected NA',label,raw));return
    if isinstance(want,bool):need(raw.lower()==str(want).lower(),(label,raw,want));return
    if isinstance(want,(int,float)):
        need(raw!='' and close(float(raw),want),(label,raw,want));return
    need(raw==str(want),(label,raw,want))

def load_raw(selected):
    manifest=read(ROOT/'Scale_Source_Manifest.json')
    need(sha(ROOT/'Scale_Source_Manifest.json')==MANIFEST_SHA,'manifest SHA')
    pins=manifest['sources'];need(len(pins)==12,'12 measured sources')
    for name,h in pins.items():need(sha(name)==h,('source drift',name));FILES[name]=h
    inputs_path=ROOT/'instances/scale_main_01/INPUTS.json'
    need(sha(inputs_path)==INPUT_SHA,'input SHA');specs=read(inputs_path)
    need(len(specs)==400 and len({s['case'] for s in specs})==400 and len({s['seed'] for s in specs})==100,'400/100 design')
    need(Counter(len(s['old']) for s in specs)=={6:100,8:100,10:100,12:100},'size balance')
    for seed in {s['seed'] for s in specs}:
        subset=[s for s in specs if s['seed']==seed]
        need(len(subset)==4 and len({(s['capacity_regime'],s['signal']) for s in subset})==4,'paired variants')
    choose=read(selected);names=choose['runs'] if isinstance(choose,dict) else choose
    folders=[(Path(x) if Path(x).is_absolute() else ROOT/x).resolve() for x in names]
    need(len(folders)==len(set(folders))==52,'52 unique explicit blocks')
    # Completion preflight precedes reading measurement rows; do not audit a running batch.
    for f in folders:
        need(ROOT in f.parents,('outside root',f));pc=read(f/'PROCESS_COMPLETE.json')
        need(pc['status'] in ('PASS','PASS_WITH_CENSORING'),('not complete',f))
    data={};oracles={};covered=set();block_counts=[]
    for folder in folders:
        protocol=read(folder/'PROTOCOL.json');a,z=protocol['start'],protocol['stop'];indices=set(range(a,z))
        need(a%4==z%4==0 and z-a in (4,8) and 0<=a<z<=400 and not covered&indices,'disjoint whole-mother blocks')
        covered|=indices;block=specs[a:z]
        need(protocol['mode']=='main' and protocol['sources']==pins and protocol['input_file_sha256']==INPUT_SHA,'protocol/source identity')
        need(protocol['methods']==list(METHODS) and protocol['repeats']==3 and protocol['wall_ms']==1000,'method/budget')
        need(protocol['watchdog_seconds']==protocol['oracle_seconds']==15 and protocol['actual_RAM_measured'] is False,'caps/RAM scope')
        need(protocol['oracle_not_used_as_incumbent'] is True and protocol['oracle_independent_of_DP_ADAPTER'] is False,'oracle role')
        need(read(folder/'INPUTS.json')==block,'block input equality')
        gate_path=Path(protocol['gate_path']);need(sha(gate_path)==protocol['gate_sha256'],'gate hash')
        gate=read(gate_path);need(gate['status']=='PASS' and gate['sources']==pins and len(gate['case_ids'])==24,'micro gate')
        ids={s['case'] for s in block};obs=jsonl(folder/'ORACLES.jsonl')
        need(len(obs)==len(block),'oracle coverage')
        for o in obs:
            need(o['case'] in ids and o['case'] not in oracles,'unique oracle case')
            need(o['status'] in ('PASS','CENSORED') and o['outside_measured_solves'] is True and o['not_passed_into_benchmark'] is True,'oracle status')
            need(o['independent_of_DP_ADAPTER'] is False and not o['proposed_bound_used'] and not o['incumbent_pruning_used'],'oracle source relation')
            need((o['optimum_H2'] is not None)==o['certified_optimal']==(o['status']=='PASS'),'oracle exactness')
            oracles[o['case']]=o
        rows=jsonl(folder/'MEASUREMENTS.jsonl');needed={(s['case'],m,r) for s in block for m in METHODS for r in range(3)}
        keys=[(r['case'],r['method'],r['repeat']) for r in rows]
        need(len(keys)==len(set(keys))==len(needed) and set(keys)==needed,'complete 27 calls per case')
        journal=defaultdict(list)
        for x in jsonl(folder/'ATTEMPTS.jsonl'):journal[(x['case'],x['method'],x['repeat'])].append(x['status'])
        need(set(journal)==needed,'attempt matrix')
        hard=[]
        for r in rows:
            key=(r['case'],r['method'],r['repeat']);need(key not in data,'duplicate across blocks')
            need(r['outcome'] in ('OK','HARD_TIMEOUT'),'returned outcome')
            need(journal[key]==['STARTED','COMPLETE' if r['outcome']=='OK' else 'HARD_TIMEOUT'],'attempt status')
            if r['outcome']=='HARD_TIMEOUT':hard.append(r)
            data[key]=r
        need(jsonl(folder/'FAILURES.jsonl',False)==hard,'hard ledger')
        need(not (folder/'FAILURE.json').exists() and not (folder/'REJECTED_RESULTS.jsonl').exists(),'fatal/rejected source')
        cc=jsonl(folder/'CASE_COMPLETE.jsonl');need(len(cc)==len(block) and {x['case'] for x in cc}==ids,'case completion')
        need(all(x['completed_attempts']==27 and x['oracle_exact']==(oracles[x['case']]['status']=='PASS') for x in cc),'case completion counters')
        sm=read(folder/'SUMMARY.json');need(sm==read(folder/'PROCESS_COMPLETE.json'),'matching summary')
        need(sm['cases']==len(block) and sm['records']==len(rows)-len(hard) and sm['hard_timeouts']==len(hard) and sm['expected_attempts']==len(rows),'block counters')
        block_counts.append({'run':str(folder),'cases':len(block),'calls':len(rows),'hard':len(hard)})
    need(covered==set(range(400)) and len(data)==10800 and len(oracles)==400,'global matrix')
    return specs,data,oracles,block_counts

def normalize(specs,data,oracles):
    calls={}
    for index,s in enumerate(specs):
        opt=oracles[s['case']]['optimum_H2'];initials=[];plans=[];ends=[]
        for mi,method in enumerate(METHODS):
            for rep in range(3):
                r=data[(s['case'],method,rep)];policy,basis=MAPPING[mi]
                offset=(3*index+rep)%9;order=METHODS[offset:]+METHODS[:offset];j=order.index(method)
                expected={'case':s['case'],'seed':s['seed'],'m':len(s['old']),'Q':s['Q'],'signal':s['signal'],'capacity_regime':s['capacity_regime'],'method':method,'arm':method,'policy':policy,'bound_basis':basis,'repeat':rep,'position_within_repeat':j,'position_within_case':9*rep+j,'mode':'main','cohort':'three_repeat','wall_budget_ms':1000,'input_sha256':hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()}
                for k,v in expected.items():need(r.get(k)==v,('identity',s['case'],method,rep,k))
                n={'status':r['outcome'],'quality':{ms:None for ms in BUDGETS},'proof':False,'elapsed':None,'expanded':None,'targets':{p:None for p in TARGETS},'initial':None,'initial_time':None,'initial_targets':{p:None for p in TARGETS},'partial':None,'dp_counts':{}}
                if r['outcome']=='HARD_TIMEOUT':
                    need(r['incumbent_not_recovered'] is True and r['not_counted_as_solved'] is True and r['hard_limit_seconds']==15,'hard timeout accounting')
                    calls[(s['case'],method,rep)]=n;continue
                need(r['timing_interpretable'] is True and r['stats']['detailed_profile_enabled'] is False,'no profiling timing')
                need(r['oracle_H2']==opt and r['t0']==s['t0'] and r['oracle_independent_of_this_method']==(method!='DP_ADAPTER'),'oracle metadata')
                t=r['elapsed_seconds'];trace=r['trace'];need(bool(trace),'incumbent trace')
                need(all(math.isfinite(r[k]) and r[k]>=0 for k in ('elapsed_seconds','setup_seconds','initial_seconds','search_seconds','root_bound_seconds','overrun_seconds')),'timers finite/nonnegative')
                need(close(r['setup_seconds']+r['initial_seconds']+r['search_seconds'],t) and r['root_bound_seconds']<=r['search_seconds']+1e-7,'timing partition')
                need(close(r['overrun_seconds'],max(0,t-1)),'overrun')
                last=(-1,None,-1)
                for e in trace:
                    need(last[0]<=e['seconds']<=t+1e-7 and (last[1] is None or e['H2']<last[1]),'trace time/improvement')
                    need(last[2]<=e['expansion_index']<=r['expanded']+r.get('partial_expansions',0),'complete/partial expansion index')
                    need(opt is None or e['H2']>=opt,'feasible value below oracle')
                    last=e['seconds'],e['H2'],e['expansion_index']
                need(trace[-1]['H2']==r['H2'] and trace[-1]['plan']==r['plan'],'final trace')
                lower=r['remaining_bound'];gap=None if lower is None else r['H2']-lower
                need(r['certified_gap']==gap and (gap is None or gap>=0) and r['certified_optimal']==(gap==0),'certificate identity')
                need(opt is None or lower is None or lower<=opt,'LB above known optimum')
                need(not r['certified_optimal'] or opt is None or r['H2']==opt,'false certificate')
                need(r['expanded']==r['expanded_phase0']+r['expanded_phase1'],'completed phase expansion accounting')
                proof=r['certified_optimal'] and t<=1;need(r['certified_within_wall_conservative']==proof,'proof deadline')
                vals={ms:min((e['H2'] for e in trace if e['seconds']<=ms/1000),default=None) for ms in BUDGETS}
                need(r['H2_within_wall']==vals[1000],'literal wall incumbent')
                evals={x['ms']:x for x in r['evaluation_at_ms']};need(set(evals)==set(BUDGETS),'literal evaluation grid')
                for ms,v in vals.items():need(evals[ms]['H2']==v and evals[ms]['feasible']==(v is not None) and evals[ms]['regret']==(None if v is None or opt is None else v-opt),'cached literal evaluation')
                targets={}
                for pct in TARGETS:
                    e=next((e for e in trace if met(e['H2'],opt,s['t0'],pct)),None)
                    targets[pct]=None if e is None else (e['seconds'],e['expansion_index'])
                initials.append(trace[0]['H2']);plans.append(json.dumps(trace[0]['plan'],sort_keys=True))
                if r['certified_optimal']:ends.append(r['H2'])
                n.update(quality=vals,proof=proof,elapsed=t,expanded=r['expanded'],targets=targets,initial=trace[0]['H2'],initial_time=trace[0]['seconds'],initial_targets={p:None if opt is None else met(trace[0]['H2'],opt,s['t0'],p) for p in TARGETS},partial=r.get('partial_expansions',0))
                if method=='DP_ADAPTER':
                    need(r['stats']['proposed_bound_used'] is False and r['stats']['incumbent_pruning_used'] is False,'DP scope')
                    n['dp_counts']={k:r.get(k,r['stats'].get(k)) for k in ('expanded','expanded_phase0','expanded_phase1','partial_expansions','generated','structural_labels','accepted_updates','closure_queries','closure_cache_hits','dijkstra_runs','edge_relaxations','cache_clears','closure_cache_size')}
                calls[(s['case'],method,rep)]=n
        need(len(set(initials))<=1 and len(set(plans))<=1,'common initial across all returned calls')
        need(len(set(ends))<=1,'conflicting exact certificates')
    return calls

def aggregate(specs,calls,oracles):
    cases={};case_rows=[];dp_rows=[];first_rows=[]
    for s in specs:
        opt=oracles[s['case']]['optimum_H2']
        for method in METHODS:
            rr=[calls[s['case'],method,r] for r in range(3)]
            q={ms:[x['quality'][ms] for x in rr] for ms in BUDGETS}
            target={p:[x['targets'][p] for x in rr] for p in TARGETS}
            initial={p:None if opt is None else all(x['initial_targets'][p] is True for x in rr) for p in TARGETS}
            events={'proof':{'eligible':all(x['proof'] for x in rr),'seconds':med([x['elapsed'] for x in rr]),'expanded':med([x['expanded'] for x in rr]),'initial':initial[0]}}
            for p in TARGETS:events[str(p)]={'eligible':all(x is not None and x[0]<=1 for x in target[p]),'seconds':med([None if x is None else x[0] for x in target[p]]),'expanded':med([None if x is None else x[1] for x in target[p]]),'initial':initial[p]}
            c={'quality':{ms:med(v) for ms,v in q.items()},'all3_optimal':{ms:opt is not None and all(v==opt for v in values) for ms,values in q.items()},'events':events,'ok':sum(x['status']=='OK' for x in rr),'hard':sum(x['status']=='HARD_TIMEOUT' for x in rr),'initial':initial}
            cases[s['case'],method]=c
            for ms in BUDGETS:case_rows.append({'case':s['case'],'seed':s['seed'],'m':len(s['old']),'method':method,'ms':ms,'known_optimum':opt,'all3_feasible':c['quality'][ms] is not None,'all3_optimal':None if opt is None else c['all3_optimal'][ms],'H2_median':c['quality'][ms],'all3_proof':events['proof']['eligible'],'initial_optimal_all3':initial[0]})
            for pct in TARGETS:
                event=events[str(pct)]
                first_rows.append({'case':s['case'],'method':method,'target_pct':pct,'all3_reached_on_time':event['eligible'],'all3_initial_meets_target':event['initial'],'seconds_median':event['seconds'],'expansion_median':event['expanded']})
            if method=='DP_ADAPTER':
                row={'case':s['case'],'seed':s['seed'],'m':len(s['old']),'method':method,'ok_repeats':c['ok'],'on_time_proof_all3':events['proof']['eligible']}
                for k in ('expanded','expanded_phase0','expanded_phase1','partial_expansions','generated','structural_labels','accepted_updates','closure_queries','closure_cache_hits','dijkstra_runs','edge_relaxations','cache_clears','closure_cache_size'):row[k]=med([x['dp_counts'].get(k) for x in rr])
                dp_rows.append(row)
    groups=defaultdict(list)
    for s in specs:
        for st in strata(s):groups[st].append(s)
    coverage=[];times=[];qualitypairs=[]
    for st,ss in groups.items():
        for method in METHODS:
            cc=[cases[s['case'],method] for s in ss]
            for ms in BUDGETS:
                coverage.append({'stratum':st,'method':method,'ms':ms,'scenarios':len(ss),'mothers':len({s['seed'] for s in ss}),'known_oracles':sum(oracles[s['case']]['optimum_H2'] is not None for s in ss),'all3_feasible':sum(c['quality'][ms] is not None for c in cc),'all3_optimal':sum(c['all3_optimal'][ms] for c in cc),'all3_proof':sum(c['events']['proof']['eligible'] for c in cc),'hard_calls':sum(c['hard'] for c in cc),'initial_optimal_all3':sum(c['initial'][0] is True for c in cc)})
        for left,right in combinations(METHODS,2):
            for ms in BUDGETS:
                w=t=l=u=0
                for s in ss:
                    a=cases[s['case'],left]['quality'][ms];b=cases[s['case'],right]['quality'][ms]
                    if a is None or b is None:u+=1
                    elif a<b:w+=1
                    elif a>b:l+=1
                    else:t+=1
                qualitypairs.append({'stratum':st,'left':left,'right':right,'ms':ms,'scenarios':len(ss),'wins':w,'ties':t,'losses':l,'unknown':u})
            for target in ('proof','0','5','10'):
                common=[];leftonly=rightonly=neither=0
                for s in ss:
                    a=cases[s['case'],left]['events'][target];b=cases[s['case'],right]['events'][target]
                    if a['eligible'] and b['eligible']:common.append((s,a,b))
                    elif a['eligible']:leftonly+=1
                    elif b['eligible']:rightonly+=1
                    else:neither+=1
                av=[x[1]['seconds'] for x in common];bv=[x[2]['seconds'] for x in common]
                ex=[x for x in common if x[1]['expanded'] is not None and x[2]['expanded'] is not None]
                aa=sum(av) if common else None;bb=sum(bv) if common else None
                ae=sum(x[1]['expanded'] for x in ex) if ex else None;be=sum(x[2]['expanded'] for x in ex) if ex else None
                times.append({'stratum':st,'left':left,'right':right,'target':target,'scenarios':len(ss),'both_all3_on_time':len(common),'left_only':leftonly,'right_only':rightonly,'neither':neither,'common_mothers':len({x[0]['seed'] for x in common}),'left_seconds_sum':aa,'right_seconds_sum':bb,'ratio_of_sums':ratio(aa,bb),'expansion_pairs':len(ex),'left_expansion_sum':ae,'right_expansion_sum':be,'ratio_of_expansion_sums':ratio(ae,be),'left_initial_target_all3_in_common':sum(x[1]['initial'] is True for x in common),'right_initial_target_all3_in_common':sum(x[2]['initial'] is True for x in common),'both_initial_target_all3_in_common':sum(x[1]['initial'] is True and x[2]['initial'] is True for x in common),'earlier':sum(a<b for a,b in zip(av,bv)),'same':sum(a==b for a,b in zip(av,bv)),'later':sum(a>b for a,b in zip(av,bv))})
    return case_rows,coverage,qualitypairs,times,dp_rows,first_rows

def crosscheck(official,case_rows,coverage,qualitypairs,times,dp_rows,first_rows):
    status=read(official/'PROCESS_COMPLETE.json');need(status['status']=='COMPLETE','official analysis not complete')
    check_count=0
    def compare(table,keys,rows,columns=None):
        nonlocal check_count
        values=read_csv(official/table);index={tuple(r[k] for k in keys):r for r in values}
        need(len(index)==len(values),'duplicate CSV keys')
        for r in rows:
            key=tuple(str(r[k]) for k in keys);need(key in index,('CSV row absent',table,key))
            for k in columns or r.keys():
                if k in keys:continue
                need(k in index[key],('CSV column absent',table,k));equal_csv(index[key][k],r[k],(table,key,k));check_count+=1
    compare('Case_Quality.csv',('case','method','ms'),case_rows,('all3_feasible','all3_optimal','H2_median'))
    compare('Case_First_Good.csv',('case','method','target_pct'),first_rows)
    case_proofs=[{'case':r['case'],'method':r['method'],'all3_on_time_certified':r['all3_proof']} for r in case_rows if r['ms']==1000]
    compare('Case_Work_And_Proof.csv',('case','method'),case_proofs)
    compare('Quality_Summary.csv',('stratum','method','ms'),coverage,('scenarios','all3_feasible','all3_optimal'))
    proof_rows=[{'stratum':r['stratum'],'method':r['method'],'all3_on_time_certified':r['all3_proof']} for r in coverage if r['ms']==1000]
    compare('Work_And_Proof_Summary.csv',('stratum','method'),proof_rows)
    compare('Pair_Quality_Summary.csv',('stratum','left','right','ms'),qualitypairs)
    compare('Pair_Time_Summary.csv',('stratum','left','right','target'),times)
    compare('Case_Work_And_Proof.csv',('case','method'),dp_rows,('expanded','expanded_phase0','expanded_phase1','partial_expansions','generated','structural_labels','accepted_updates','closure_queries','closure_cache_hits','dijkstra_runs','edge_relaxations','cache_clears','closure_cache_size'))
    return check_count

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true')
    ap.add_argument('--selected',type=Path,required=True);ap.add_argument('--analysis',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if not a.execute:ap.error('Prepared only; --execute requires the parent completion notification')
    out=a.out.resolve();need(ROOT/'analysis' in out.parents and not out.exists(),'fresh E V449/analysis output');out.mkdir(parents=True)
    try:
        specs,data,oracles,blocks=load_raw(a.selected);calls=normalize(specs,data,oracles)
        cr,cov,qp,tm,dp,first=aggregate(specs,calls,oracles)
        comparisons=crosscheck(a.analysis,cr,cov,qp,tm,dp,first)
        for name,rows in (('Case_Quality.csv',cr),('Independent_Coverage.csv',cov),('Independent_Pair_Quality.csv',qp),('Independent_Pair_Time.csv',tm),('Independent_DP_Counts.csv',dp),('Independent_First_Good_Cases.csv',first)):csvout(out/name,rows)
        for p,h in FILES.items():need(sha(p)==h,('source/raw drift during audit',p))
        status={'status':'PASS','independent_raw_recomputation':True,'audit_script_sha256':sha(Path(__file__)),'official_csv_field_checks':comparisons,'planned_calls':10800,'cases':400,'mothers':100,'methods':9,'pairs':36,'selected_blocks':52,'exact_oracles':sum(o['status']=='PASS' for o in oracles.values()),'hard_timeout_calls':sum(x['status']=='HARD_TIMEOUT' for x in calls.values()),'actual_RAM_measured':False,'oracle_independent_of_DP_ADAPTER':False,'scope':'Independent arithmetic/source audit, not an independent rerun of search or oracle; no SUMO claim'}
        save(out/'Block_Coverage.json',blocks);save(out/'Audit_Source_Hashes.json',FILES);save(out/'SUMMARY.json',status)
        save(out/'PROCESS_COMPLETE.json',status);print(json.dumps(status))
    except BaseException:
        save(out/'FAILURE.json',{'error':traceback.format_exc(),'input_hashes_read':FILES});raise
if __name__=='__main__':main()

