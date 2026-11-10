"""Recompute paired descriptive results from raw V450 records, without solver imports."""
from pathlib import Path
import argparse,collections,csv,hashlib,json,statistics,itertools
P=Path(__file__).resolve().parent
METHODS=('RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS')
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def med(x):return statistics.median(x)
def csvsave(p,rows):
    if rows:
        with p.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--runs',type=Path,nargs='+',required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert not a.out.exists();a.out.mkdir(parents=True)
    group=collections.defaultdict(list);raw=0;source={};failed=[];expected_cases=set();spec_by_case={};attempt_keys=set()
    for run in a.runs:
        status=json.loads((run/'PROCESS_COMPLETE.json').read_text())
        assert status['status'] in ('PASS','PASS_WITH_CENSORING'),(run,status)
        protocol=json.loads((run/'PROTOCOL.json').read_text())
        assert protocol['split']=='main' and protocol['repeats']==3 and protocol['wall_ms']==1000
        assert tuple(protocol['methods'])==METHODS
        for fp,h in protocol['source_manifest']['files'].items():assert hashlib.sha256(Path(fp).read_bytes()).hexdigest()==h,('Source drift',fp)
        ip=P/'inputs'/'main'/'INPUTS.json'
        assert hashlib.sha256(ip.read_bytes()).hexdigest()==protocol['input_sha256']
        local=json.loads((run/'INPUTS.json').read_text());global_inputs=json.loads(ip.read_text())
        assert local==global_inputs[protocol['start']:protocol['stop']]
        assert not expected_cases&{s['case'] for s in local},'Overlapping input cases across runs'
        completed=jl(run/'CASE_COMPLETE.jsonl')
        assert [x['case'] for x in completed]==[s['case'] for s in local] and all(x['status']=='PASS' for x in completed)
        spec_by_case.update({s['case']:s for s in local})
        p=run/'MEASUREMENTS.jsonl';source[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        current=jl(p);wanted={(s['case'],m,r) for s in local for m in METHODS for r in range(3)}
        observed=[(r['case'],r['method'],r['repeat']) for r in current]
        assert len(observed)==len(set(observed)) and set(observed)==wanted
        assert not attempt_keys&set(observed);attempt_keys.update(observed)
        assert protocol['expected_calls']==len(current)==status['calls']+status['hard_timeouts']
        for s in json.loads((run/'INPUTS.json').read_text()):expected_cases.add(s['case'])
        for r in jl(p):
            raw+=1
            if r['status']!='OK':failed.append(r);continue
            group[(r['case'],r['method'])].append(r)
    entries=[];d={}
    for (case,method),rr in sorted(group.items()):
        assert len({r['repeat'] for r in rr})==len(rr),'Duplicate measurement'
        oracle={r['oracle_H2'] for r in rr};assert len(oracle)==1
        opt=oracle.pop();proof=[r['certified_optimal'] and r['elapsed_seconds']<=1 for r in rr]
        c=dict(case=case,method=method,seed=rr[0]['seed'],m=rr[0]['m'],signal=rr[0]['signal'],capacity_regime=rr[0]['capacity_regime'],repeats=len(rr),oracle_H2=opt,all_three_proved=len(rr)==3 and all(proof),proof_seconds=med(r['elapsed_seconds'] for r in rr) if len(rr)==3 and all(proof) else None,expanded_end=med(r['expanded'] for r in rr),elapsed_end=med(r['elapsed_seconds'] for r in rr))
        for ms in (100,500,1000):
            vals=[min((t['H2'] for t in r['trace'] if t['seconds']<=ms/1000),default=None) for r in rr]
            assert vals==[r['literal_quality'][str(ms)] for r in rr]
            c[f'quality_{ms}']=med(vals) if len(vals)==3 and all(v is not None for v in vals) else None
            c[f'all_optimal_{ms}']=len(vals)==3 and opt is not None and all(v==opt for v in vals)
        for k,fraction in enumerate((0.,.05,.1)):
            ts=[r['first_quality_thresholds'][k]['seconds'] for r in rr]
            c[f'first_gap{k}']=med(ts) if len(ts)==3 and all(t is not None and t<=1 for t in ts) else None
            target=None if opt is None else opt+fraction*(opt-spec_by_case[case]['t0'])
            assert all(r['first_quality_thresholds'][k]['target']==target for r in rr)
            c[f'initial_good_gap{k}']=target is not None and all(r['trace'][0]['H2']<=target for r in rr)
        entries.append(c);d[(case,method)]=c
    summaries=[]
    for method in METHODS:
        rr=[x for x in entries if x['method']==method];proof=[x for x in rr if x['all_three_proved']]
        s=dict(method=method,expected_cases=len(expected_cases),available_cases=len(rr),available_calls=sum(x['repeats'] for x in rr),all_three_proved=len(proof),sum_case_median_proof_seconds=sum(x['proof_seconds'] for x in proof),sum_expanded_end=sum(x['expanded_end'] for x in rr))
        for ms in (100,500,1000):s[f'all_three_optimal_{ms}']=sum(x[f'all_optimal_{ms}'] for x in rr)
        for k in (0,1,2):
            s[f'all_three_gap{k}_reached']=sum(x[f'first_gap{k}'] is not None for x in rr)
            s[f'initial_good_gap{k}_cases']=sum(x[f'initial_good_gap{k}'] for x in rr)
        summaries.append(s)
    pairs=[]
    for lhs,rhs in itertools.combinations(METHODS,2):
        matches=[(d[(c,lhs)],d[(c,rhs)]) for c in expected_cases if (c,lhs) in d and (c,rhs) in d]
        complete=[(x,y) for x,y in matches if x['all_three_proved'] and y['all_three_proved']]
        st=sum(x['proof_seconds'] for x,y in complete);bt=sum(y['proof_seconds'] for x,y in complete)
        se=sum(x['expanded_end'] for x,y in complete);be=sum(y['expanded_end'] for x,y in complete)
        row=dict(lhs=lhs,rhs=rhs,expected_cases=len(expected_cases),paired_cases=len(matches),common_proved_cases=len(complete),lhs_seconds=st,rhs_seconds=bt,lhs_time_change_percent=None if bt==0 else 100*(st/bt-1),lhs_expansions=se,rhs_expansions=be,lhs_expansion_change_percent=None if be==0 else 100*(se/be-1),lhs_faster=sum(x['proof_seconds']<y['proof_seconds'] for x,y in complete),rhs_faster=sum(x['proof_seconds']>y['proof_seconds'] for x,y in complete))
        for ms in (100,500,1000):
            q=[(x[f'quality_{ms}'],y[f'quality_{ms}']) for x,y in matches if x[f'quality_{ms}'] is not None and y[f'quality_{ms}'] is not None]
            row[f'quality_{ms}_paired']=len(q);row[f'quality_{ms}_lhs_better']=sum(x<y for x,y in q);row[f'quality_{ms}_ties']=sum(x==y for x,y in q);row[f'quality_{ms}_rhs_better']=sum(x>y for x,y in q)
        for k in (0,1,2):
            q=[(x[f'first_gap{k}'],y[f'first_gap{k}']) for x,y in matches if x[f'first_gap{k}'] is not None and y[f'first_gap{k}'] is not None]
            aa=sum(x for x,y in q);bb=sum(y for x,y in q)
            row[f'gap{k}_common_reached']=len(q);row[f'gap{k}_lhs_seconds']=aa;row[f'gap{k}_rhs_seconds']=bb;row[f'gap{k}_lhs_change_percent']=None if bb==0 else 100*(aa/bb-1)
        pairs.append(row)
    csvsave(a.out/'Case_Medians.csv',entries);csvsave(a.out/'Method_Summary.csv',summaries);csvsave(a.out/'Paired_Summary.csv',pairs)
    save(a.out/'Analysis.json',dict(status='PASS',raw_calls=raw,expected_cases=len(expected_cases),independent_mothers=len({x['seed'] for x in spec_by_case.values()}),failures=failed,methods=summaries,pairs=pairs,sources=source,limitations=['Technical repetitions are not independent orders.','Time/expansion ratios use identical all-three-on-time proved subsets.','End-of-run counts on interrupted searches are not full-search counts.','The complete published search algorithms are adapted to H2, not full freight-paper systems.','Memory is assessed separately.']))
    save(a.out/'PROCESS_COMPLETE.json',dict(status='PASS',raw_calls=raw,case_rows=len(entries),expected_cases=len(expected_cases)))
    print(json.dumps(dict(status='PASS',raw_calls=raw,expected_cases=len(expected_cases))),flush=True)
if __name__=='__main__':main()