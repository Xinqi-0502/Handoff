"""Read-only raw-result audit; imports no solver, predictor, SUMO or production audit."""
from pathlib import Path
import collections,csv,gzip,hashlib,json,statistics,xml.etree.ElementTree as ET
B=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
ARMS=('RADIUS','PAIR','OR_OPT')
HASHES={}
def read(p):
    p=Path(p);HASHES[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def signature(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,indent=2,allow_nan=False)
def csvwrite(p,rows):
    with Path(p).open('x',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def close(a,b):assert abs(a-b)<1e-6,(a,b)
SITES={'HW':('WC',22),'HE':('EC',22),'TW':('WC',30),'TE':('EC',30),'ME':('CE',59),'MW':('CW',59)}
for side in 'WE':
    for br in 'UD':
        for tag,num,pos in [('u','0',28),('v','0',73),('x','1',27)]:SITES[side+br+tag]=(side+br+num,pos)

def audit_native(folder,record,snapshot):
    inp=read(folder/'INPUT.json');raw=read(folder/'RESULT.json');audit=read(folder/'AUDIT.json')
    assert inp['snapshot']==snapshot and signature(inp['plan'])==record['signature']
    assert not raw['error'] and raw['collision_ticks']==raw['teleports']==0 and audit['status']=='PASS'
    c=snapshot['c'];w=snapshot['wave2'];plan=inp['plan'];E=6.;Hz=5
    held={v:{j for j in c['old'] if j[0].upper()==v} for v in c['actors']};truck={'a','b'}
    done={};trans={};beg={};released=[];arrival=None;intervals=[]
    for tick,kind,v,j,*rest in raw['events']:
        if kind=='arrive' and v=='T':
            assert arrival is None;arrival=tick
        if kind=='beginX':assert j not in beg;beg[j]=tick
        if kind=='transfer':
            assert v==plan['receiver'] and j in truck and j not in held[v]
            assert j=='a' and not trans or j=='b' and set(trans)=={'a'} and 'a' in done
            assert tick-beg[j]==10
            load=sum(w['orders'][k]['weight'] if k in ('a','b') else c['size'][k] for k in held[v])
            assert load+w['orders'][j]['weight']<=({'A':6,'B':5}[v])
            truck.remove(j);held[v].add(j);trans[j]=tick
            intervals.extend([(beg[j],tick,v,plan['hub']),(beg[j],tick,'T','T'+plan['hub'][-1])])
        if kind=='delivery':
            assert j in held[v] and j not in done
            held[v].remove(j);done[j]=tick
            site=w['orders'][j]['dest'] if j in ('a','b') else c['old'][j]
            intervals.append((tick-20,tick,v,site))
        if kind=='truck_release':released.append(tick)
    assert set(done)==set(c['old'])|{'a','b'} and done==raw['completed']==record['completed']
    assert not truck and not any(held.values()) and released==[trans['b']]
    assert arrival is not None and arrival<=beg['a']<trans['a']<=beg['b']<trans['b']
    intervals.append((arrival,trans['b'],'T','T'+plan['hub'][-1]))
    total=hashlib.sha256();prefix=hashlib.sha256();n=0
    with gzip.open(folder/'trace.jsonl.gz','rb') as f:
        for line in f:
            n+=1;total.update(line);fr=json.loads(line);assert fr['tick']==n
            if n<=30:prefix.update(line);assert 'T' not in fr['vehicles']
            for lo,hi,v,site in intervals:
                if lo<=n<=hi:
                    x=fr['vehicles'].get(v);edge,pos=SITES[site]
                    assert x is not None and x[0]==edge and abs(x[1]-pos)<1.6 and x[2]==0 and x[3]&1,(folder,n,v,site,x)
    HASHES[str(folder/'trace.jsonl.gz')]=sha(folder/'trace.jsonl.gz')
    assert total.hexdigest()==raw['trace_hash']==audit['trace_sha256']==record['trace_sha256']
    assert prefix.hexdigest()==raw['prefix']==snapshot['prefix']
    assert sha(folder/'old_batch.rou.xml')==snapshot['xml']==inp['initial_xml_hash']
    HASHES[str(folder/'old_batch.rou.xml')]=sha(folder/'old_batch.rou.xml')
    trips=ET.parse(folder/'trips.xml').getroot().findall('tripinfo')
    expected=set(c['actors'])|{'bg','T'}|({'slow0','slow1'} if c['slow'] else set())
    assert {x.get('id') for x in trips}==expected and all(float(x.get('arrival'))>0 for x in trips)
    HASHES[str(folder/'trips.xml')]=sha(folder/'trips.xml')
    old=sum(t/Hz for j,t in done.items() if j not in ('a','b'))
    a=done['a']/Hz-E;b=done['b']/Hz-E;J=old+a+b
    close(J,record['J_customer_seconds']);close(J,audit['J_customer_seconds'])
    close(trans['b']/Hz,record['last_handoff_seconds']);close(released[0]/Hz,record['truck_release_seconds'])
    return dict(actual_J=J,old_flow=old,new_a_flow=a,new_b_flow=b,truck_arrival=arrival/Hz,
        first_handoff=trans['a']/Hz,last_handoff=trans['b']/Hz,truck_release=released[0]/Hz,
        truck_wait_excluding_transfer=(trans['b']-arrival)/Hz-4,truck_dwell=(trans['b']-arrival)/Hz,
        initial_wait=(beg['a']-arrival)/Hz,between_transfer_wait=(beg['b']-trans['a'])/Hz,
        receiver=plan['receiver'],hub=plan['hub'],trace_frames=n)

inputs=read(B/'INPUTS_01.json');snapshots={x['case']:x for x in inputs['cases']}
gate=read(B/'gates/check_01/GATE.json');gc=read(B/'gates/check_01/PROCESS_COMPLETE.json')
assert gate['status']==gc['status']=='PASS' and gc['gate_sha256']==sha(B/'gates/check_01/GATE.json')
assert gate['inputs_sha256']==sha(B/'INPUTS_01.json')
for p,h in gate['sources'].items():assert sha(p)==h;HASHES[p]=h
opt={x['case']:x['optimum_J'] for x in gate['checks']}
all_tables={};aggregates={};rawfiles=[]
for tag in ('forecast24_native_01','wall50ms_native_01'):
    run=B/'runs'/tag;mode='forecast24' if tag.startswith('forecast') else 'wall50ms'
    pc=read(run/'PROCESS_COMPLETE.json');summary=read(run/'SUMMARY.json');protocol=read(run/'PROTOCOL.json')
    assert pc['status']==summary['status']=='PASS' and pc['summary_sha256']==sha(run/'SUMMARY.json')
    assert protocol['sources']==summary['sources']==gate['sources']
    assert protocol['inputs_sha256']==summary['inputs_sha256']==sha(B/'INPUTS_01.json')
    host=read(B/'runs'/('host_'+tag)/'PROCESS_COMPLETE.json')
    monitor=read(B/'runs'/('monitor_'+tag)/'PROCESS_COMPLETE.json')
    assert host['status']==monitor['Status']=='PASS'
    path=run/'RESULTS.jsonl';HASHES[str(path)]=sha(path)
    rows=[json.loads(x) for x in path.read_text(encoding='utf8').splitlines()]
    assert len(rows)==36 and {(x['case'],x['arm'],x['rep']) for x in rows}=={(c,a,r) for c in snapshots for a in ARMS for r in range(3)}
    physical=read(run/'PHYSICAL.json');pm={};native_rows=[]
    for p in physical:
        key=(p['case'],p['signature']);assert key not in pm
        metrics=audit_native(run/p['folder'],p,snapshots[p['case']]);pm[key]=metrics
        native_rows.append({'mode':mode,'case':p['case'],'signature':p['signature'],**metrics})
    expected_links=collections.defaultdict(list)
    for r in rows:
        assert signature(r['plan'])==r['signature'] and r['counts']['full_forecasts']==sum(r['per_branch_forecasts'].values())
        assert len(r['per_branch_forecasts'])==4
        if mode=='forecast24':assert all(1<=v<=6 for v in r['per_branch_forecasts'].values()) and r['counts']['full_forecasts']<=24
        else:close(r['deadline_seconds'],.05)
        assert r['J']>=opt[r['case']]-1e-6
        prev=float('inf');prevtime=-1
        for ev in r['trace']:
            assert ev['seconds']>=prevtime and ev['J']<=prev+1e-8 and signature(ev['plan'])==ev['signature']
            prev,prevtime=ev['J'],ev['seconds']
        eligible=[e for e in r['trace'] if mode=='forecast24' or e['seconds']<=.05]
        if eligible:
            close(r['within_budget_J'],eligible[-1]['J']);assert r['within_budget_plan']==eligible[-1]['plan']
            expected_links[(r['case'],signature(r['within_budget_plan']))].append((r['arm'],r['rep']))
        else:assert r['within_budget_J'] is None and r['within_budget_plan'] is None
        assert r['certified_forecast_optimal_by_deadline']==(r['certified_forecast_optimal'] and (mode=='forecast24' or r['elapsed_seconds']<=.05))
        close(r['overrun_seconds'],0 if mode=='forecast24' else max(0,r['elapsed_seconds']-.05))
        if r['certified_forecast_optimal']:close(r['J'],opt[r['case']])
    assert set(expected_links)==set(pm)
    for p in physical:assert sorted(expected_links[(p['case'],p['signature'])])==sorted((x['arm'],x['rep']) for x in p['selected_by'])
    table=[]
    for case in sorted(snapshots):
        starts={signature(r['initial']['plan']) for r in rows if r['case']==case};assert len(starts)==1
        for arm in ARMS:
            rr=[r for r in rows if r['case']==case and r['arm']==arm]
            assert len({r['signature'] for r in rr})==len({r['J'] for r in rr})==1
            assert all(r['counts']==rr[0]['counts'] for r in rr)
            assert all(r['within_budget_plan']==r['plan'] for r in rr)
            r=rr[0];m=pm[(case,r['signature'])]
            target=[next((e['seconds'] for e in z['trace'] if abs(e['J']-opt[case])<1e-6),None) for z in rr]
            table.append({'mode':mode,'case':case,'seed':snapshots[case]['seed'],'offset':snapshots[case]['offset'],'slow':snapshots[case]['slow'],'arm':arm,
                'initial_J':r['initial']['J'],'forecast_J':r['J'],'oracle_forecast_J':opt[case],
                'within_deadline_J':r['within_budget_J'],'median_ms':statistics.median(z['elapsed_seconds'] for z in rr)*1000,
                'min_ms':min(z['elapsed_seconds'] for z in rr)*1000,'max_ms':max(z['elapsed_seconds'] for z in rr)*1000,
                'max_overrun_ms':max(z['overrun_seconds'] for z in rr)*1000,
                'proof_repeats':sum(z['certified_forecast_optimal'] for z in rr),
                'proof_by_deadline_repeats':sum(z['certified_forecast_optimal_by_deadline'] for z in rr),
                'first_optimum_median_ms':statistics.median(target)*1000 if all(t is not None for t in target) else None,
                **r['counts'],**m})
    sums={a:{'sum_case_median_ms':sum(r['median_ms'] for r in table if r['arm']==a),'expanded':sum(r['expanded'] for r in table if r['arm']==a),'forecasts':sum(r['full_forecasts'] for r in table if r['arm']==a),'actual_J_sum':sum(r['actual_J'] for r in table if r['arm']==a),'forecast_J_sum':sum(r['forecast_J'] for r in table if r['arm']==a),'pair_calls':sum(r['pair_calls'] for r in table if r['arm']==a),'pair_stronger':sum(r['pair_stronger'] for r in table if r['arm']==a),'pair_only_pruned':sum(r['pair_only_pruned'] for r in table if r['arm']==a)} for a in ARMS}
    pairs=[]
    for base in ('RADIUS','OR_OPT'):
        cand=[x for x in table if x['arm']=='PAIR'];other=[x for x in table if x['arm']==base]
        count=lambda field:[sum(x[field]<y[field]-1e-7 for x,y in zip(cand,other)),sum(abs(x[field]-y[field])<=1e-7 for x,y in zip(cand,other)),sum(x[field]>y[field]+1e-7 for x,y in zip(cand,other))]
        pairs.append({'candidate':'PAIR','baseline':base,'cases':4,'time_sum_ratio':sums['PAIR']['sum_case_median_ms']/sums[base]['sum_case_median_ms'],'actual_J_sum_ratio':sums['PAIR']['actual_J_sum']/sums[base]['actual_J_sum'],'forecast_J_WTL':count('forecast_J'),'actual_J_WTL':count('actual_J'),'median_time_WTL':count('median_ms')})
    aggregates[mode]={'rows':len(rows),'native_plans':len(physical),'case_count':4,'mother_count':1,'sum_one_deterministic_solve_per_case':sums,'pairs':pairs,'all_literal_results_available':True,'max_elapsed_ms':max(x['elapsed_seconds'] for x in rows)*1000}
    csvwrite(OUT/(mode+'_cases.csv'),table);csvwrite(OUT/(mode+'_native_events.csv'),native_rows);all_tables[mode]=table
write(OUT/'Independent_Aggregates.json',aggregates)
write(OUT/'Audit_Source_Hashes.json',HASHES)
print(json.dumps(aggregates,indent=2))

