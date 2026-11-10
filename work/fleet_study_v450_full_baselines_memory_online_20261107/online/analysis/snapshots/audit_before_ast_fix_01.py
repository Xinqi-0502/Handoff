"""Independent saved online evidence audit: standard library only; no solver/SUMO imports.
Execution requires --execute and explicit run/gate/prefix paths. Failed native
representatives stay in denominators. Never renormalize over surviving plans.
"""
from pathlib import Path
import argparse,collections,csv,gzip,hashlib,itertools,json,math,statistics,traceback,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
PRIMARY=('HZ_AWA_RADIUS','HZ_AWA_PAIR_GATED');AUX=('RADIUS','ROUTE','ANA_RADIUS')
SCHEDULE=tuple((a,ms) for ms in (10,50,200) for a in PRIMARY)+tuple((a,50) for a in AUX)
SITES={'HW':('WC',22),'HE':('EC',22),'TW':('WC',30),'TE':('EC',30),'ME':('CE',59),'MW':('CW',59)}
for side,branch,(tag,num,pos) in itertools.product('WE','UD',(('u','0',28),('v','0',73),('x','1',27)):
    SITES[side+branch+tag]=(side+branch+num,pos)
EPS=1e-6

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def close(x,y):assert x is not None and y is not None and abs(x-y)<=EPS,(x,y)
def sign(x):return -1 if x<-EPS else 1 if x>EPS else 0
def mean(xs):return statistics.mean(xs) if xs else None
def median(xs):return statistics.median(xs) if xs else None
def dump(path,obj):
    with Path(path).open('x',encoding='utf8') as f:json.dump(obj,f,indent=2,ensure_ascii=False,allow_nan=False)
def csvwrite(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('x',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

class Reader:
    def __init__(self):self.hashes={};self.metadata={}
    def track(self,path):
        p=Path(path).resolve();h=sha(p);st=p.stat();meta=(st.st_size,st.st_mtime_ns)
        if str(p) in self.hashes:assert self.hashes[str(p)]==h and self.metadata[str(p)]==meta
        self.hashes[str(p)]=h;self.metadata[str(p)]=meta
        return p
    def read(self,path):return json.loads(self.track(path).read_text(encoding='utf-8-sig'))
    def lines(self,path):return [json.loads(s) for s in self.track(path).read_text(encoding='utf-8-sig').splitlines() if s]
    def unchanged(self):
        for name,meta in self.metadata.items():
            p=Path(name);st=p.stat();assert (st.st_size,st.st_mtime_ns)==meta,('Evidence changed',name)
            if p.suffix!='.gz':assert sha(p)==self.hashes[name],('Evidence hash changed',name)

def load_gate(rd,path):
    path=Path(path);assert not (path/'FAILURE.json').exists()
    g=rd.read(path/'GATE.json');p=rd.read(path/'PROCESS_COMPLETE.json')
    assert g['status']==p['status']=='PASS' and p['gate_sha256']==sha(path/'GATE.json')
    return g

def validate_plan(snapshot,plan,matrix):
    c=snapshot['c'];v=plan['receiver'];h=plan['hub'];actors=c['actors'];w=snapshot['wave2']
    assert v in actors and h in ('HE','HW') and set(plan['route'])==set(actors)
    jobs={a:tuple(j for j in c['old'] if j[0].upper()==a) for a in actors}
    for a in actors:
        seq=plan['route'][a];assert seq[0]==jobs[a][0]
        assert sorted(seq)==sorted(jobs[a]+(('Xa','a','Xb','b') if a==v else ()))
        owned=set(jobs[a][1:]);picked=set();old_done=0
        for j in seq[1:]:
            if j in ('Xa','Xb'):
                k=j[1];assert a==v and k not in picked
                assert (k=='a' and old_done>=1) or (k=='b' and 'a' in picked)
                load=sum(w['orders'][o]['weight'] if o in ('a','b') else c['size'][o] for o in owned)
                assert load+w['orders'][k]['weight']<=snapshot['capacity'][a]
                owned.add(k);picked.add(k)
            else:
                assert j in owned;owned.remove(j);old_done+=j not in ('a','b')
        assert not owned
        if a!=v:
            todo=list(jobs[a][1:]);fixed=[jobs[a][0]];at=c['old'][fixed[0]]
            while todo:
                j=min(todo,key=lambda j:(matrix[at][c['old'][j]][0],j));fixed.append(j);todo.remove(j);at=c['old'][j]
            assert seq==fixed

def policy_record(r,s,matrix):
    budget=r['budget_seconds'];assert budget in (.01,.05,.2) and r['rep'] in range(3)
    close(r['deadline_seconds'],budget);assert r['elapsed_seconds']>=0
    prev=math.inf;stamp=-1.
    for e in r['trace']:
        assert stamp<=e['seconds']<=r['elapsed_seconds']+EPS and e['J']<=prev+EPS
        assert digest(e['plan'])==e['signature'];validate_plan(s,e['plan'],matrix)
        if 'cost' in e:close(e['cost'],e['J'])
        prev=e['J'];stamp=e['seconds']
    assert r['trace'];close(r['trace'][-1]['J'],r['J'])
    validate_plan(s,r['plan'],matrix);assert digest(r['plan'])==r['signature']
    close(r['trace'][0]['J'],r['initial']['J']);assert r['trace'][0]['plan']==r['initial']['plan']
    close(r['trace'][0]['seconds'],r['initial']['seconds'])
    ontime=[e for e in r['trace'] if e['seconds']<=budget]
    if ontime:
        close(r['within_budget_J'],ontime[-1]['J']);assert r['within_budget_plan']==ontime[-1]['plan']
    else:assert r['within_budget_J'] is None and r['within_budget_plan'] is None
    fallback=not ontime;assert r['deadline_fallback']==fallback
    assert r['deadline_status']==('NO_PLAN_BY_DEADLINE' if fallback else 'PLAN_BY_DEADLINE')
    expected=r['initial']['plan'] if fallback else ontime[-1]['plan']
    assert r['executed_plan']==expected and r['executed_signature']==digest(expected)
    assert r['activation_tick']==30+math.ceil(r['elapsed_seconds']*5)
    close(r['overrun_seconds'],max(0.,r['elapsed_seconds']-budget))
    assert r['certified_forecast_optimal_by_deadline']==(r['certified_forecast_optimal'] and r['elapsed_seconds']<=budget)
    lower=r['lower_bound']
    if lower is not None:assert lower<=r['J']+EPS
    if r['certified_forecast_optimal']:close(lower,r['J'])
    initial=True if abs(r['initial']['J']-r['J'])<=1e-7 and r['certified_forecast_optimal'] else False if abs(r['initial']['J']-r['J'])>1e-7 else None
    assert r['initial_known_forecast_optimal'] is initial
    if 'per_branch_forecasts' in r:assert sum(r['per_branch_forecasts'].values())==r['counts']['full_forecasts']
    if r['arm'] in ('HZ_AWA_RADIUS','HZ_AWA_PAIR_GATED','ANA_RADIUS'):
        raw=r['published']['raw_engine'];close(raw['objective_value'],r['J'])
        assert raw['certified_optimal']==r['certified_forecast_optimal']
        if lower is None:assert raw['lower_bound'] is None
        else:close(raw['lower_bound'],lower)
        if raw['certified_gap'] is not None:close(raw['certified_gap'],r['J']-lower)
        assert r['published']['custom_pair_hook']==(r['arm']=='HZ_AWA_PAIR_GATED')
    return dict(case=r['case'],seed=r['seed'],arm=r['arm'],budget_ms=round(budget*1000),rep=r['rep'],
        final_forecast_J=r['J'],within_budget_forecast_J=r['within_budget_J'],executed_forecast_J=r['initial']['J'] if fallback else r['within_budget_J'],
        deadline_fallback=fallback,elapsed_ms=r['elapsed_seconds']*1000,overrun_ms=r['overrun_seconds']*1000,
        activation_tick=r['activation_tick'],quantization_ms=((r['activation_tick']-30)/5-r['elapsed_seconds'])*1000,
        initial_known_optimal=initial,proof_by_deadline=r['certified_forecast_optimal_by_deadline'],signature=r['executed_signature'],
        **{k:r['counts'].get(k) for k in ('expanded','generated','full_forecasts','extra_pruned','pair_only_pruned','pair_calls','pair_skip_upper','pair_events','pair_loop_queries')})

def audit_native(rd,folder,record,snapshot,network,matrix):
    inp=rd.read(folder/'INPUT.json');raw=rd.read(folder/'RESULT.json');audit=rd.read(folder/'AUDIT.json')
    assert record['status']==audit['status']=='PASS' and not raw['error']
    assert raw['collision_ticks']==raw['teleports']==0
    assert inp['snapshot']==snapshot and digest(inp['plan'])==record['signature']
    validate_plan(snapshot,inp['plan'],matrix)
    close(inp['planning_seconds'],raw['planning_seconds']);activation=inp['activation_tick']
    assert activation==record['activation_tick']==raw['activation_tick']==30+math.ceil(inp['planning_seconds']*5)
    close(inp['quantization_seconds'],(activation-30)/5-inp['planning_seconds'])
    assert -EPS<=inp['quantization_seconds']<.2+EPS
    c=snapshot['c'];w=snapshot['wave2'];plan=inp['plan'];v=plan['receiver'];h=plan['hub']
    held={a:set(j for j in c['old'] if j[0].upper()==a) for a in c['actors']};supplier=set();done={};owners={}
    trans={};beg={};released=[];releases=[];activations=[];arrival=None;intervals=[];service_order={a:[] for a in c['actors']}
    last_tick=-1
    for tick,tag,who,j,*rest in raw['events']:
        assert isinstance(tick,int) and tick>=last_tick;last_tick=tick
        if tag=='release':
            assert tick==30 and who=='T' and j in ('a','b') and j not in supplier;supplier.add(j);releases.append(j)
        elif tag=='plan_activation':activations.append(tick)
        elif tag=='arrive' and who=='T':
            assert arrival is None and tick>=activation;arrival=tick
        elif tag=='beginX':
            assert who==v and j in supplier and j not in beg and tick>=activation;beg[j]=tick
        elif tag=='transfer':
            assert who==v and j in supplier and j not in held[v] and tick-beg[j]==10
            assert (j=='a' and not trans) or (j=='b' and set(trans)=={'a'} and 'a' in done)
            load=sum(w['orders'][o]['weight'] if o in ('a','b') else c['size'][o] for o in held[v])
            assert load+w['orders'][j]['weight']<=snapshot['capacity'][v]
            supplier.remove(j);held[v].add(j);trans[j]=tick;service_order[v].append('X'+j)
            intervals.extend(((beg[j],tick,v,h),(beg[j],tick,'T','T'+h[-1])))
        elif tag=='delivery':
            assert who in held and j in held[who] and j not in done
            held[who].remove(j);done[j]=tick;owners[j]=who;service_order[who].append(j)
            site=w['orders'][j]['dest'] if j in ('a','b') else c['old'][j]
            intervals.append((tick-20,tick,who,site))
        elif tag=='truck_release':assert who=='T' and j=='b';released.append(tick)
        for a,cargo in held.items():
            assert sum(w['orders'][o]['weight'] if o in ('a','b') else c['size'][o] for o in cargo)<=snapshot['capacity'][a]
    assert sorted(releases)==['a','b'] and activations==[activation]
    assert done==raw['completed']==record['completed']==audit['completed']
    assert set(done)==set(c['old'])|{'a','b'} and not supplier and not any(held.values())
    assert service_order==plan['route'] and released==[trans['b']]
    assert arrival is not None and arrival<=beg['a']<trans['a']<=beg['b']<trans['b']
    intervals.append((arrival,trans['b'],'T','T'+h[-1]))
    for a in c['actors']:
        first=next(j for j in c['old'] if j[0].upper()==a);assert done[first]==30
        intervals.append((30,activation,a,c['old'][first]))
    net=ET.parse(rd.track(network)).getroot()
    lengths={e.get('id'):float(e.find('lane').get('length')) for e in net.findall('edge')}
    links={(e.get('from'),e.get('to')):int(e.get('linkIndex')) for e in net.findall('connection') if e.get('tl')=='C'}
    assert inp['net']==sha(network)
    total=hashlib.sha256();prefix=hashlib.sha256();n=0;red={a:0 for a in c['actors']+['T']};near=set();near_ticks=crossing=0
    first_moving=None;first_left=None
    with gzip.open(rd.track(folder/'trace.jsonl.gz'),'rb') as stream:
        for line in stream:
            n+=1;fr=json.loads(line);assert fr['tick']==n
            canonical=(json.dumps(fr,sort_keys=True,separators=(',',':'))+'\n').encode()
            assert line in (canonical,canonical[:-1]+b'\r\n');total.update(canonical)
            if n<=30:prefix.update(canonical)
            if n<=activation:assert 'T' not in fr['vehicles']
            for lo,hi,a,site in intervals:
                if lo<=n<=hi:
                    row=fr['vehicles'].get(a);edge,pos=SITES[site]
                    assert row and row[0]==edge and abs(row[1]-pos)<1.6 and row[2]==0 and row[3]&1,(folder,n,a,site,row)
            if n>trans['b'] and 'T' in fr['vehicles']:
                row=fr['vehicles']['T'];edge,pos=SITES['T'+h[-1]]
                if first_moving is None and row[2]>0:first_moving=n/5
                if first_left is None and (row[0]!=edge or abs(row[1]-pos)>=1.6):first_left=n/5
            if n<=activation:continue
            crossing+=any(row[0]==':C_c0' for row in fr['people'].values())
            for a in red:
                row=fr['vehicles'].get(a)
                if row is None:continue
                link=links.get((row[0],fr.get('next_edges',{}).get(a)))
                if link is not None and 0<=lengths[row[0]]-row[1]<=45 and not row[3]&1 and row[2]<.1 and fr['signal'][link] in 'rRyY':red[a]+=1
                for person,pr in fr['people'].items():
                    if math.dist(row[4:6],pr[1:3])<=15:near.add((a,person));near_ticks+=1
    assert total.hexdigest()==raw['trace_hash']==audit['trace_sha256']==record['trace_sha256']
    assert prefix.hexdigest()==raw['prefix']==snapshot['prefix']
    assert sha(rd.track(folder/'old_batch.rou.xml'))==snapshot['xml']==inp['initial_xml_hash']
    trips=ET.parse(rd.track(folder/'trips.xml')).getroot();vehicles={x.get('id'):x.attrib for x in trips.findall('tripinfo')}
    expected=set(c['actors'])|{'bg','T'}|({'slow0','slow1'} if c['slow'] else set())
    assert set(vehicles)==expected and all(float(x['arrival'])>0 for x in vehicles.values())
    people=trips.findall('personinfo');assert len(people)==snapshot['people']
    assert len({x.get('id') for x in people})==len(people)
    for person in people:
        walks=person.findall('walk');assert walks and all(float(z.get('arrival','-1'))>0 for z in walks)
    collision=ET.parse(rd.track(folder/'collisions.xml')).getroot();assert not collision.findall('.//collision')
    exposure=audit['observed_exposure'];assert exposure['red_signal_stopped_ticks']==red
    assert exposure['ped_near_vehicle_pair_ticks']==near_ticks and exposure['ped_near_vehicle_pairs']==[list(x) for x in sorted(near)]
    assert exposure['crosswalk_occupied_ticks_after_activation']==crossing
    old=sum(t for j,t in done.items() if j not in ('a','b'))/5;a_flow=done['a']/5-6;b_flow=done['b']/5-6;J=old+a_flow+b_flow
    for obj in (audit,record):
        close(obj['J_customer_seconds'],J);close(obj['old_flow_seconds'],old)
        close(obj['new_flow_seconds']['a'],a_flow);close(obj['new_flow_seconds']['b'],b_flow)
        close(obj['truck_release_seconds'],trans['b']/5);close(obj['last_handoff_seconds'],trans['b']/5)
        close(obj['truck_dwell_seconds'],(trans['b']-arrival)/5)
        close(obj['truck_wait_excluding_transfer_seconds'],(trans['b']-arrival)/5-4)
        assert obj['unfinished_customers']==[]
    customers=[dict(case=snapshot['case'],signature=record['signature'],activation_tick=activation,
        customer=j,vehicle=owners[j],release_seconds=6 if j in ('a','b') else 0,
        completion_seconds=t/5,flow_seconds=t/5-(6 if j in ('a','b') else 0)) for j,t in sorted(done.items())]
    return dict(status='PASS',actual_J=J,old_flow=old,new_a_flow=a_flow,new_b_flow=b_flow,
        truck_arrival_seconds=arrival/5,first_handoff_seconds=trans['a']/5,last_handoff_seconds=trans['b']/5,
        truck_release_command_seconds=trans['b']/5,truck_first_moving_seconds=first_moving,truck_first_left_hub_seconds=first_left,
        truck_wait_excluding_transfer=(trans['b']-arrival)/5-4,truck_dwell=(trans['b']-arrival)/5,
        completed_customers=len(done),unfinished_customers=0,trace_frames=n,
        red_signal_stopped_ticks=sum(red.values()),ped_near_vehicle_pair_ticks=near_ticks,
        crosswalk_occupied_ticks_after_activation=crossing,
        fleet_trip_timeLoss=sum(float(vehicles[a]['timeLoss']) for a in c['actors']),
        truck_trip_timeLoss=float(vehicles['T']['timeLoss']),receiver=v,hub=h),customers

def aggregate_cases(snapshots,records,selections,physical):
    table=[];links=[];pm={(p['case'],p['signature'],p['activation_tick']):p for p in physical}
    for case,s in snapshots.items():
        for arm,ms in SCHEDULE:
            rr=[r for r in records if r['case']==case and r['arm']==arm and round(r['budget_seconds']*1000)==ms]
            ss=[q for q in selections if q['case']==case and q['arm']==arm and round(q['budget_seconds']*1000)==ms]
            assert len(rr)==3 and sorted(rep for q in ss for rep in q['represented_reps'])==[0,1,2]
            mapped=[]
            for q in ss:
                ph=pm.get((case,q['signature'],q['activation_tick']))
                chosen=next(r for r in rr if r['rep']==q['selected_rep'])
                assert q['planning_seconds']==chosen['elapsed_seconds'] and q['signature']==chosen['executed_signature']
                pred=chosen['initial']['J'] if chosen['deadline_fallback'] else chosen['within_budget_J']
                links.append(dict(case=case,seed=s['seed'],offset=s['offset'],people=s['people'],slow=s['slow'],arm=arm,budget_ms=ms,
                    signature=q['signature'],activation_tick=q['activation_tick'],selected_rep=q['selected_rep'],
                    represented_reps=','.join(map(str,q['represented_reps'])),frequency_weight=len(q['represented_reps'])/3,
                    forecast_J=pred,planning_seconds=q['planning_seconds'],quantization_seconds=q['quantization_seconds'],
                    native_status=ph['status'] if ph else 'MISSING',actual_J=ph.get('actual_J') if ph else None))
                mapped.append((len(q['represented_reps'])/3,ph))
            complete=all(p is not None and p['status']=='PASS' for _,p in mapped)
            weighted=lambda name:sum(w*p[name] for w,p in mapped) if complete else None
            within=[r['within_budget_J'] for r in rr]
            direct=len({(r['executed_signature'],r['activation_tick']) for r in rr})==1
            vals=[p['actual_J'] for _,p in mapped if p is not None and p['status']=='PASS']
            row=dict(case=case,seed=s['seed'],offset=s['offset'],people=s['people'],slow=s['slow'],arm=arm,budget_ms=ms,
                policy_repetitions=3,plan_by_deadline_repetitions=sum(v is not None for v in within),fallback_repetitions=sum(r['deadline_fallback'] for r in rr),
                proof_by_deadline_repetitions=sum(r['certified_forecast_optimal_by_deadline'] for r in rr),
                initial_optimal_known_true=sum(r['initial_known_forecast_optimal'] is True for r in rr),
                initial_optimal_known_false=sum(r['initial_known_forecast_optimal'] is False for r in rr),
                initial_optimal_unknown=sum(r['initial_known_forecast_optimal'] is None for r in rr),
                within_forecast_J_mean=mean(within) if all(x is not None for x in within) else None,
                within_forecast_J_median=median(within) if all(x is not None for x in within) else None,
                executed_forecast_J_mean=mean([r['initial']['J'] if r['deadline_fallback'] else r['within_budget_J'] for r in rr]),
                median_elapsed_ms=median([r['elapsed_seconds']*1000 for r in rr]),max_overrun_ms=max(r['overrun_seconds']*1000 for r in rr),
                retained_plan_count=len(ss),failed_or_missing_plan_count=sum(p is None or p['status']!='PASS' for _,p in mapped),
                complete_representative_replays=complete,direct_same_plan_and_activation=direct,
                representative_actual_J_min=min(vals) if complete else None,representative_actual_J_max=max(vals) if complete else None,
                policy_frequency_weighted_representative_replay_J=weighted('actual_J'),
                weighted_old_flow=weighted('old_flow'),weighted_new_a_flow=weighted('new_a_flow'),weighted_new_b_flow=weighted('new_b_flow'),
                weighted_truck_wait=weighted('truck_wait_excluding_transfer'),weighted_truck_dwell=weighted('truck_dwell'),
                weighted_red_stop_ticks=weighted('red_signal_stopped_ticks'),weighted_ped_proximity_ticks=weighted('ped_near_vehicle_pair_ticks'))
            for k in ('expanded','generated','pair_calls','pair_skip_upper','pair_events','pair_loop_queries','extra_pruned','full_forecasts'):
                values=[r['counts'].get(k) for r in rr];row['median_'+k]=median(values) if all(v is not None for v in values) else None
            table.append(row)
    return table,links

def pair_tables(cases):
    pairs=[];by={(r['case'],r['budget_ms'],r['arm']):r for r in cases}
    for case,ms in sorted({(r['case'],r['budget_ms']) for r in cases}):
        arms=[a for a,b in SCHEDULE if b==ms]
        for a,b in itertools.combinations(arms,2):
            if b=='HZ_AWA_PAIR_GATED':a,b=b,a
            x,y=by[case,ms,a],by[case,ms,b]
            actual=x['policy_frequency_weighted_representative_replay_J'];other=y['policy_frequency_weighted_representative_replay_J']
            known=actual is not None and other is not None;fx,fy=x['executed_forecast_J_mean'],y['executed_forecast_J_mean']
            rows=dict(case=case,seed=x['seed'],offset=x['offset'],people=x['people'],slow=x['slow'],budget_ms=ms,left=a,right=b,
                actual_pair_known=known,direct_pair=known and x['direct_same_plan_and_activation'] and y['direct_same_plan_and_activation'],
                left_actual_J=actual,right_actual_J=other,actual_delta=actual-other if known else None,
                left_forecast_J=fx,right_forecast_J=fy,forecast_delta=fx-fy,
                strict_direction_reversal=known and sign(actual-other)*sign(fx-fy)==-1,
                left_fallback_repetitions=x['fallback_repetitions'],right_fallback_repetitions=y['fallback_repetitions'],
                left_median_elapsed_ms=x['median_elapsed_ms'],right_median_elapsed_ms=y['median_elapsed_ms'],
                time_delta_ms=x['median_elapsed_ms']-y['median_elapsed_ms'],
                both_all3_proved_by_deadline=x['proof_by_deadline_repetitions']==y['proof_by_deadline_repetitions']==3)
            for col in ('weighted_old_flow','weighted_new_a_flow','weighted_new_b_flow','weighted_truck_wait','weighted_truck_dwell'):
                rows[col+'_delta']=x[col]-y[col] if known else None
            wf=x['within_forecast_J_mean'];wy=y['within_forecast_J_mean']
            rows['literal_forecast_pair_known']=wf is not None and wy is not None
            rows['literal_forecast_delta']=wf-wy if wf is not None and wy is not None else None
            pairs.append(rows)
    summaries=[];mothers=[]
    strata=[('ALL',lambda r:True)]
    strata.extend((f'{field}={value}',lambda r,f=field,v=value:r[f]==v) for field,values in [('offset',(0,24)),('people',(0,10)),('slow',(0,2))] for value in values)
    for ms,a,b in sorted({(r['budget_ms'],r['left'],r['right']) for r in pairs}):
        group=[r for r in pairs if (r['budget_ms'],r['left'],r['right'])==(ms,a,b)]
        for seed in sorted({r['seed'] for r in group}):
            rr=[r for r in group if r['seed']==seed];good=[r for r in rr if r['actual_pair_known']]
            mothers.append(dict(seed=seed,budget_ms=ms,left=a,right=b,planned_conditions=len(rr),known_conditions=len(good),
                complete_mother=len(good)==len(rr),mean_actual_delta=mean([r['actual_delta'] for r in good]) if len(good)==len(rr) else None,
                mean_forecast_delta=mean([r['forecast_delta'] for r in rr]),
                actual_wins=sum(sign(r['actual_delta'])<0 for r in good),actual_ties=sum(sign(r['actual_delta'])==0 for r in good),actual_losses=sum(sign(r['actual_delta'])>0 for r in good)))
        for stratum,pred in strata:
            rr=[r for r in group if pred(r)]
            if not rr:continue
            good=[r for r in rr if r['actual_pair_known']];direct=[r for r in good if r['direct_pair']]
            proof=[r for r in rr if r['both_all3_proved_by_deadline']]
            lx=sum(r['left_actual_J'] for r in good);ry=sum(r['right_actual_J'] for r in good)
            summaries.append(dict(stratum=stratum,budget_ms=ms,left=a,right=b,planned_scenarios=len(rr),mothers=len({r['seed'] for r in rr}),
                actual_known_pairs=len(good),actual_unknown_pairs=len(rr)-len(good),left_actual_sum=lx if good else None,right_actual_sum=ry if good else None,
                actual_sum_ratio=lx/ry if good and ry else None,mean_actual_delta=mean([r['actual_delta'] for r in good]),
                actual_wins=sum(sign(r['actual_delta'])<0 for r in good),actual_ties=sum(sign(r['actual_delta'])==0 for r in good),actual_losses=sum(sign(r['actual_delta'])>0 for r in good),
                forecast_wins=sum(sign(r['forecast_delta'])<0 for r in rr),forecast_ties=sum(sign(r['forecast_delta'])==0 for r in rr),forecast_losses=sum(sign(r['forecast_delta'])>0 for r in rr),
                strict_direction_reversals=sum(r['strict_direction_reversal'] for r in good),
                direct_same_plan_activation_pairs=len(direct),direct_mean_actual_delta=mean([r['actual_delta'] for r in direct]),
                direct_wins=sum(sign(r['actual_delta'])<0 for r in direct),direct_ties=sum(sign(r['actual_delta'])==0 for r in direct),direct_losses=sum(sign(r['actual_delta'])>0 for r in direct),
                both_all3_proof_pairs=len(proof),proof_left_sum_case_median_ms=sum(r['left_median_elapsed_ms'] for r in proof),
                proof_right_sum_case_median_ms=sum(r['right_median_elapsed_ms'] for r in proof),
                allcase_left_sum_case_median_ms=sum(r['left_median_elapsed_ms'] for r in rr),allcase_right_sum_case_median_ms=sum(r['right_median_elapsed_ms'] for r in rr)))
    return pairs,summaries,mothers

def main():
    ap=argparse.ArgumentParser()
    for key in ('definitions','prefixes','gate','native-gate','run','host','monitor','out'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    if not a.execute:raise SystemExit('Prepared only; --execute is required to inspect result evidence')
    a.out.mkdir(parents=True,exist_ok=False);rd=Reader()
    try:
        defs=rd.read(a.definitions);pref=rd.read(a.prefixes/'INPUTS.json');pr=rd.read(a.prefixes/'PROCESS_COMPLETE.json')
        protocol=rd.read(a.run/'PROTOCOL.json');summary=rd.read(a.run/'SUMMARY.json');gate=load_gate(rd,a.gate);ng=load_gate(rd,a.native_gate)
        expected=defs['pilot_cases'] if protocol['pilot'] else [s['case'] for s in defs['cases']]
        assert protocol['cases']==expected and len(expected)==(2 if protocol['pilot'] else 64)
        assert len(defs['cases'])==64 and defs['mothers']==list(range(4509001,4509009))
        assert protocol['definitions_sha256']==sha(a.definitions)==pref['source_inputs_sha256']
        assert protocol['prefix_inputs_sha256']==pr['input_sha256']==sha(a.prefixes/'INPUTS.json')
        assert pr['status']=='PASS' and not (a.prefixes/'FAILURE.json').exists()
        assert protocol['gate_sha256']==sha(a.gate/'GATE.json') and protocol['native_gate_sha256']==sha(a.native_gate/'GATE.json')
        assert protocol['sources']==summary['sources']==pr['sources']==gate['sources']==ng['sources']
        for path,h in protocol['sources'].items():assert sha(rd.track(path))==h
        assert protocol['schedule']==[[arm,ms/1000] for arm,ms in SCHEDULE] and protocol['repeats']==3
        snapshots={s['case']:s for s in pref['cases']};assert list(snapshots)==expected
        for s in pref['cases']:
            original=next(x for x in defs['cases'] if x['case']==s['case']);assert all(s[k]==v for k,v in original.items())
        host=rd.read(a.host/'PROCESS_COMPLETE.json') if (a.host/'PROCESS_COMPLETE.json').exists() else None
        monitor=rd.read(a.monitor/'PROCESS_COMPLETE.json') if (a.monitor/'PROCESS_COMPLETE.json').exists() else None
        raw=rd.lines(a.run/'RESULTS.jsonl')
        wanted={(c,arm,ms,rep) for c in expected for arm,ms in SCHEDULE for rep in range(3)}
        keys=[(r['case'],r['arm'],round(r['budget_seconds']*1000),r['rep']) for r in raw]
        assert len(keys)==len(set(keys)) and set(keys)==wanted
        matrixpath=next(Path(p) for p in protocol['sources'] if p.endswith('turn2_legs.json'));matrix=rd.read(matrixpath)['matrix']
        calls=[policy_record(r,snapshots[r['case']],matrix) for r in raw]
        for case in expected:
            rr=[r for r in raw if r['case']==case]
            assert len({digest(r['initial']['plan']) for r in rr})==1 and len({round(r['initial']['J'],7) for r in rr})==1
        selections=rd.read(a.run/'NATIVE_SELECTION.json');reconstructed=[];selected={}
        for case in expected:
            for arm,ms in SCHEDULE:
                group=[r for r in raw if (r['case'],r['arm'],round(r['budget_seconds']*1000))==(case,arm,ms)]
                for sig in sorted({r['executed_signature'] for r in group}):
                    same=sorted([r for r in group if r['executed_signature']==sig],key=lambda r:(r['elapsed_seconds'],r['rep']))
                    choose=same[(len(same)-1)//2];key=(case,sig,choose['activation_tick']);selected.setdefault(key,choose)
                    reconstructed.append(dict(case=case,arm=arm,budget_seconds=ms/1000,signature=sig,represented_reps=[r['rep'] for r in same],
                        selected_rep=choose['rep'],planning_seconds=choose['elapsed_seconds'],activation_tick=choose['activation_tick'],
                        quantization_seconds=(choose['activation_tick']-30)/5-choose['elapsed_seconds'],deadline_fallback=choose['deadline_fallback']))
        assert selections==reconstructed
        physical=rd.read(a.run/'PHYSICAL.json');failures=rd.read(a.run/'FAILURES.json');native_rows=[];customers=[]
        assert len({(r['case'],r['signature'],r['activation_tick']) for r in physical})==len(physical)
        assert {(r['case'],r['signature'],r['activation_tick']) for r in physical}==set(selected)
        assert failures==[r for r in physical if r['status']=='FAIL']
        for p in physical:
            key=(p['case'],p['signature'],p['activation_tick']);folder=(a.run/p['folder']).resolve();assert folder.is_relative_to(a.run.resolve())
            if p['status']=='PASS':
                net=next(Path(path) for path in protocol['sources'] if path.endswith(f'cycle_{snapshots[p["case"]]["offset"]}.net.xml'))
                metrics,cc=audit_native(rd,folder,p,snapshots[p['case']],net,matrix);customers.extend(cc)
                close(rd.read(folder/'INPUT.json')['planning_seconds'],selected[key]['elapsed_seconds'])
            else:
                assert rd.read(folder/'NATIVE_FAILURE.json')==p
                if (folder/'RESULT.json').exists():
                    partial=rd.read(folder/'RESULT.json');assert partial['completed']==p['completed']
                    if (folder/'trace.jsonl.gz').exists():rd.track(folder/'trace.jsonl.gz')
                metrics=dict(status='FAIL',actual_J=None,completed_customers=len(p.get('completed',{})),
                    unfinished_customers=len(p['unfinished_customers']) if p.get('unfinished_customers') is not None else None)
            native_rows.append(dict(case=p['case'],seed=snapshots[p['case']]['seed'],signature=p['signature'],activation_tick=p['activation_tick'],folder=p['folder'],**metrics))
        if failures:
            assert summary['status']=='FAIL' and (a.run/'FAILURE.json').exists();rd.read(a.run/'FAILURE.json')
        else:
            pc=rd.read(a.run/'PROCESS_COMPLETE.json');assert pc['status']==summary['status']=='PASS' and pc['summary_sha256']==sha(a.run/'SUMMARY.json')
            assert host and host['status']=='PASS' and monitor and monitor['Status']=='PASS'
        assert summary['policy_rows']==summary['planned_policy_rows']==len(raw)==len(expected)*27
        cases,links=aggregate_cases(snapshots,raw,selections,native_rows);pairs,pair_summary,mothers=pair_tables(cases)
        for name,rows in [('Calls',calls),('Native_Events',native_rows),('Customer_Completions',customers),('Representative_Selections',links),('Case_Budget_Results',cases),('Pair_Cases',pairs),('Pair_Summary',pair_summary),('Mother_Pairs',mothers)]:csvwrite(a.out/(name+'.csv'),rows)
        result=dict(status='PASS',scope='Independent saved-evidence audit; no optimization or SUMO rerun',cases=len(expected),mothers=len({s['seed'] for s in snapshots.values()}),
            policy_calls=len(raw),native_representatives=len(native_rows),native_failed_representatives=len(failures),
            complete_case_arm_budget_aggregates=sum(r['complete_representative_replays'] for r in cases),planned_case_arm_budget_aggregates=len(cases),
            aggregation='policy-frequency-weighted representative replay J; never a mean of three native repetitions',
            raw_results_changed=False,actual_RAM_measured=False,source_sha256=sha(__file__))
        rd.unchanged();dump(a.out/'Audit_Source_Hashes.json',rd.hashes);dump(a.out/'SUMMARY.json',result)
        report=['# Independent V450 online audit','',f"PASS: {len(expected)} scenarios, {result['mothers']} mothers, {len(raw)} policy calls; {len(native_rows)} representative native replays, including {len(failures)} retained failures.",'',
            'Every case remains in the tables. Any failed or missing plan representative makes its full case/arm/budget physical aggregate unknown; weights are never renormalized over survivors.',
            'The primary physical quantity is policy-frequency-weighted representative replay J. It is not three independent native replications. The direct same-plan/same-activation subset is shown alongside its full denominator, never substituted for all scenarios.',
            'Within-budget forecast quality excludes late fallback plans. Execution includes planning latency rounded up to 0.2 seconds. Forecast-to-actual reversals include both traffic-model error and activation-delay differences.',
            'Truck last handoff, release command, first observed motion and observed departure from the hub are separate columns. Pedestrian proximity is exposure, not an identified causal delay.',
            'Mother_Pairs.csv uses the mother as the independent unit; a mother mean is unknown if any planned condition is unknown. No statistical-power claim is made.',
            'This is a single frozen decision epoch, not continuous rolling dispatch. No actual RAM bytes are supplied by these records.']
        (a.out/'Independent_Online_Audit.md').write_text('\n\n'.join(report)+'\n',encoding='utf8')
        dump(a.out/'PROCESS_COMPLETE.json',dict(status='PASS',summary_sha256=sha(a.out/'SUMMARY.json'),native_failures_retained=len(failures)))
        print(json.dumps(result,indent=2))
    except BaseException:
        dump(a.out/'FAILURE.json',dict(error=traceback.format_exc(),source_sha256=sha(__file__)));raise
if __name__=='__main__':main()
