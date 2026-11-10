"""Small completed-CSV cross-check; no solver or main-analysis imports."""
from pathlib import Path
import csv,json,hashlib,math,statistics,collections
ROOT=Path(__file__).resolve().parent.parent
PRIMARY=ROOT/'static_comparison/analysis/main_01'
AUDIT=ROOT/'audit_code/results/main_01'
OUT=ROOT/'audit_code/results/crosscheck_01'
C='HZ_AWA_RADIUS_PAIR_GATED'
BASE=('HZ_AWA_RADIUS','ANA_RADIUS','RADIUS_PAIR_AWA_GATED')
inputs={}
def read(name,p):
    inputs[name]=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def equal(a,b):
    if a==b:return True
    try:return math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-9)
    except (ValueError,TypeError):return False
def check(a,b,label):
    if not equal(a,b):raise AssertionError((label,a,b))
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csvsave(p,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    OUT.mkdir(parents=True,exist_ok=False)
    p=read('primary_cases',PRIMARY/'Case_Medians.csv');a=read('audit_cases',AUDIT/'Independent_Case_Medians.csv')
    pd={(r['case'],r['method']):r for r in p};ad={(r['case'],r['method']):r for r in a};assert pd.keys()==ad.keys() and len(pd)==1024
    fields={x:x for x in ('seed','m','signal','capacity_regime','oracle_H2','quality_100','quality_500','quality_1000')}
    fields.update(repeats='returned_repeats',all_three_proved='all3_proved',expanded_end='expanded_median',elapsed_end='elapsed_median')
    for ms in (100,500,1000):fields[f'all_optimal_{ms}']=f'all3_optimal_{ms}'
    for k in range(3):fields[f'first_gap{k}']=f'first_seconds{k}';fields[f'initial_good_gap{k}']=f'initial_good{k}'
    comparisons=0
    for key in pd:
        for f,g in fields.items():check(pd[key][f],ad[key][g],(key,f));comparisons+=1
        check(pd[key]['proof_seconds'],ad[key]['elapsed_median'] if ad[key]['all3_proved']=='True' else '',(key,'proof_seconds'));comparisons+=1
    pairs=read('primary_pairs',PRIMARY/'Paired_Summary.csv');proof=read('audit_proof',AUDIT/'Directed_Proof_Pairs.csv');quality=read('audit_quality',AUDIT/'Directed_Literal_Quality_Pairs.csv');first=read('audit_first',AUDIT/'Initial_Strata_First_Good_Pairs.csv')
    pairchecks=0
    for base in BASE:
        r=next(r for r in pairs if {r['lhs'],r['rhs']}=={C,base});cp='lhs' if r['lhs']==C else 'rhs';bp='rhs' if cp=='lhs' else 'lhs'
        s=next(s for s in proof if s['stratum']=='all' and s['baseline']==base)
        for rf,sf in (('common_proved_cases','common_on_time_proved'),(cp+'_seconds','candidate_time_sum'),(bp+'_seconds','baseline_time_sum'),(cp+'_expansions','candidate_expanded_sum'),(bp+'_expansions','baseline_expanded_sum')):check(r[rf],s[sf],(base,rf));pairchecks+=1
        for ms in (100,500,1000):
            q=next(q for q in quality if q['stratum']=='all' and q['baseline']==base and q['deadline_ms']==str(ms))
            for rf,sf in ((f'quality_{ms}_paired','both_observed'),(f'quality_{ms}_{cp}_better','candidate_better'),(f'quality_{ms}_ties','ties'),(f'quality_{ms}_{bp}_better','baseline_better')):check(r[rf],q[sf],(base,rf));pairchecks+=1
        for k,frac in enumerate((0.,.05,.1)):
            f=next(f for f in first if f['stratum']=='all' and f['initial_group']=='all' and f['baseline']==base and float(f['fraction'])==frac)
            for rf,sf in ((f'gap{k}_common_reached','common_all3_reached'),(f'gap{k}_{cp}_seconds','candidate_seconds'),(f'gap{k}_{bp}_seconds','baseline_seconds')):check(r[rf],f[sf],(base,rf));pairchecks+=1
    mothers=collections.defaultdict(set)
    for r in a:mothers[r['seed']].add(r['case'])
    assert len(mothers)==64 and all(len(v)==4 for v in mothers.values())
    mr=[]
    for base in BASE:
        for seed,ids in mothers.items():
            allpairs=[(ad[(c,C)],ad[(c,base)]) for c in ids]
            good=[(x,y) for x,y in allpairs if x['all3_proved']=='True' and y['all3_proved']=='True']
            ct=sum(float(x['elapsed_median']) for x,y in good);bt=sum(float(y['elapsed_median']) for x,y in good)
            ce=sum(float(x['expanded_median']) for x,y in good);be=sum(float(y['expanded_median']) for x,y in good)
            mr.append(dict(seed=seed,m=int(allpairs[0][0]['m']),candidate=C,baseline=base,planned_variants=4,common_proved_variants=len(good),complete_mother=len(good)==4,candidate_seconds=ct,baseline_seconds=bt,time_change_percent=100*(ct/bt-1) if bt else None,candidate_expansions=ce,baseline_expansions=be,expansion_change_percent=100*(ce/be-1) if be else None))
    ms=[]
    for base in BASE:
        for scale in (None,6,8,10,12):
            subset=[r for r in mr if r['baseline']==base and (scale is None or r['m']==scale)];full=[r for r in subset if r['complete_mother']]
            ts=[r['time_change_percent'] for r in full];es=[r['expansion_change_percent'] for r in full]
            ms.append(dict(baseline=base,m='all' if scale is None else scale,planned_mothers=len(subset),complete_mothers=len(full),partial_mothers=len(subset)-len(full),faster=sum(t<0 for t in ts),ties=sum(t==0 for t in ts),slower=sum(t>0 for t in ts),median_time_change_percent=statistics.median(ts) if ts else None,fewer_expansion_mothers=sum(e<0 for e in es),equal_expansion_mothers=sum(e==0 for e in es),more_expansion_mothers=sum(e>0 for e in es)))
    csvsave(OUT/'Mother_Paired_Deltas.csv',mr);csvsave(OUT/'Mother_Consistency_Summary.csv',ms)
    result=dict(status='PASS',case_rows=1024,case_field_checks=comparisons,directed_pair_field_checks=pairchecks,independent_mothers=64,related_variants_per_mother=4,mother_comparison_scope='Four-variant common-proof sums; partial mothers retained and excluded from complete-mother consistency counts',inputs=inputs,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    save(OUT/'Crosscheck.json',result);save(OUT/'PROCESS_COMPLETE.json',dict(status='PASS'))
    print(json.dumps(dict(status='PASS',case_field_checks=comparisons,directed_pair_field_checks=pairchecks,mothers=ms),indent=2),flush=True)
if __name__=='__main__':main()
