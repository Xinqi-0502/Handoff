"""V450 larger-load native SUMO execution with planning latency and trace auditing.
No predicted clock determines a physical arrival. The truck stays parked after
handoff a and leaves immediately after handoff b. All old/new deliveries and
both small vehicles remain in actual J. See online_model for restricted domain.
"""
from pathlib import Path
import gzip,hashlib,json,math,time,traceback,xml.etree.ElementTree as ET
import online_model_v450 as model
from online_model_v450 import old
import native420 as native
from schedule import StopController


def augmented_case(c,w,plan):
    return dict(c,old=dict(c['old'])|{'Xa':plan['hub'],'Xb':plan['hub'],
        'a':w['orders']['a']['dest'],'b':w['orders']['b']['dest']})


def simulate(snapshot,plan,out,planning_seconds=0.):
    out=Path(out);out.mkdir(exist_ok=False)
    context=model.Context(snapshot)
    if planning_seconds<0 or not math.isfinite(planning_seconds):raise ValueError("Invalid planning latency")
    activation_tick=old.EPOCH+math.ceil(planning_seconds*old.HZ)
    if not context.legal(plan):raise ValueError('Illegal plan')
    c=snapshot['c'];w=snapshot['wave2'];offset=snapshot['offset'];people=bool(snapshot['people'])
    tc,_,env=native.discover_runtime();C=tc.constants;mat=old.MATRIX
    native.scene(c,out/'old_batch.rou.xml',people,mat)
    inp=dict(snapshot=snapshot,plan=plan,runtime=env,net=old.fh(old.NET/f'cycle_{offset}.net.xml'),
             initial_xml_hash=old.fh(out/'old_batch.rou.xml'),planning_seconds=planning_seconds,
             activation_tick=activation_tick,quantization_seconds=(activation_tick-old.EPOCH)/old.HZ-planning_seconds)
    old.put(out/'INPUT.json',inp)
    args=[env['sumo_binary'],'-n',str(old.NET/f'cycle_{offset}.net.xml'),'-r',str(out/'old_batch.rou.xml'),
          '--step-length','0.2','--seed','40801','--collision.check-junctions','true','--collision.action','warn',
          '--time-to-teleport','-1','--no-step-log','true','--duration-log.disable','true','--xml-validation','never',
          '--pedestrian.striping.dawdling','0','--pedestrian.striping.jamtime','1000',
          '--pedestrian.striping.jamtime.crossing','1000','--tripinfo-output',str(out/'trips.xml'),
          '--tripinfo-output.write-unfinished','true','--collision-output',str(out/'collisions.xml'),
          '--error-log',str(out/'sumo.log')]
    conn=None;prefix=hashlib.sha256();total=hashlib.sha256();events=[];done={};dx=tel=0;error=None
    controller=StopController(out,True);clock=time.perf_counter();ac=augmented_case(c,w,plan)
    try:
        with (out/'stdout.log').open('x') as stdout,gzip.open(out/'trace.jsonl.gz','xt',encoding='utf8') as stream:
            tc.start(args,label=out.name,stdout=stdout,numRetries=2);conn=tc.getConnection(out.name)
            assert conn.trafficlight.getProgram('C')=='custom'
            seen=set();exitset=set();pseen=set();pexit=set();held={v:set(old.items(c,v)) for v in c['actors']};held['T']=set()
            idx={v:0 for v in c['actors']+['T']};acts={v:[old.items(c,v)[0]] for v in c['actors']};acts['T']=[]
            parked={};transfer_start={}
            for tick in range(1,9001):
                conn.simulationStep();assert round(conn.simulation.getTime()*old.HZ)==tick
                for v in conn.simulation.getDepartedIDList():
                    seen.add(v);conn.vehicle.subscribe(v,[C.VAR_ROAD_ID,C.VAR_LANEPOSITION,C.VAR_SPEED,C.VAR_STOPSTATE,C.VAR_POSITION])
                for p in conn.simulation.getDepartedPersonIDList():
                    pseen.add(p);conn.person.subscribe(p,[C.VAR_ROAD_ID,C.VAR_POSITION])
                exitset.update(conn.simulation.getArrivedIDList());pexit.update(conn.simulation.getArrivedPersonIDList())
                dx+=conn.simulation.getCollidingVehiclesNumber();tel+=conn.simulation.getStartingTeleportNumber()
                veh={v:[r[C.VAR_ROAD_ID],round(r[C.VAR_LANEPOSITION],6),round(r[C.VAR_SPEED],6),r[C.VAR_STOPSTATE],*[round(z,6) for z in r[C.VAR_POSITION]]] for v,r in conn.vehicle.getAllSubscriptionResults().items() if r and v not in exitset}
                ped={p:[r[C.VAR_ROAD_ID],*[round(z,6) for z in r[C.VAR_POSITION]]] for p,r in conn.person.getAllSubscriptionResults().items() if r and p not in pexit}
                frame={'tick':tick,'vehicles':veh,'people':ped,'signal':conn.trafficlight.getRedYellowGreenState('C')}
                if tick>old.EPOCH:
                    movement={}
                    for v in veh:
                        route=conn.vehicle.getRoute(v);index=conn.vehicle.getRouteIndex(v)
                        if 0<=index<len(route)-1:movement[v]=route[index+1]
                    frame['next_edges']=movement
                line=json.dumps(frame,sort_keys=True,separators=(',',':'))+'\n';stream.write(line);total.update(line.encode())
                if tick<=old.EPOCH:prefix.update(line.encode());assert 'T' not in veh
                if tick==old.EPOCH:
                    assert prefix.hexdigest()==snapshot['prefix']
                    assert old.fh(out/'old_batch.rou.xml')==snapshot['xml']
                    for v in c['actors']:assert native.hit(veh[v],c['old'][old.items(c,v)[0]]) and parked[v]==10
                    held['T']={'a','b'}
                    for j in ('a','b'):events.append([tick,'release','T',j,'DEPOT'])
                controller.new_step(conn,veh,idx,acts,tick,native.hit)
                for v in c['actors']+['T']:
                    if idx[v]>=len(acts[v]):continue
                    act=acts[v][idx[v]]
                    dest=('T'+plan['hub'][-1] if v=='T' else plan['hub']) if act in ('Xa','Xb') else ac['old'][act]
                    if v in c['actors'] and idx[v]==0 and tick<10:continue
                    if not native.hit(veh.get(v),dest):continue
                    if v not in parked:parked[v]=tick;events.append([tick,'arrive',v,act,dest])
                    if act not in ('Xa','Xb') and tick==parked[v]+4*old.HZ:
                        assert act in held[v] and act not in done
                        if idx[v]==0:assert tick==old.EPOCH
                        held[v].remove(act);done[act]=tick;events.append([tick,'delivery',v,act,dest])
                        if idx[v]==0:
                            # Keep the committed-stop vehicle parked while CPU latency elapses.
                            idx[v]+=1
                        else:
                            conn.vehicle.resume(v);idx[v]+=1;del parked[v]
                if tick==activation_tick:
                    assert all(done[old.items(c,v)[0]]==old.EPOCH for v in c['actors'])
                    acts={v:plan['route'][v] for v in c['actors']}|{'T':['Xa','Xb']}
                    native.add_truck(conn,w,plan,mat)
                    events.append([tick,'plan_activation','SYSTEM','all','DEPOT'])
                    for v in c['actors']:
                        site=c['old'][old.items(c,v)[0]]
                        assert native.hit(veh[v],site)
                        conn.vehicle.resume(v)
                        controller.install(conn,v,site,acts[v][1:],ac,w,plan,mat,tick)
                        del parked[v]
                if tick>=activation_tick:
                    v=plan['receiver'];h=plan['hub']
                    if v in parked and 'T' in parked and idx[v]<len(acts[v]) and acts[v][idx[v]] in ('Xa','Xb'):
                        j=acts[v][idx[v]][1]
                        assert acts['T'][idx['T']]=='X'+j and j in held['T']
                        assert native.hit(veh[v],h) and native.hit(veh['T'],'T'+h[-1]) and math.dist(veh[v][4:],veh['T'][4:])<=12
                        load=sum(w['orders'][k]['weight'] if k in ('a','b') else c['size'][k] for k in held[v])
                        assert load+w['orders'][j]['weight']<=snapshot['capacity'][v]
                        if j not in transfer_start:transfer_start[j]=tick;events.append([tick,'beginX',v,j,h])
                        if tick==transfer_start[j]+2*old.HZ:
                            held['T'].remove(j);held[v].add(j);events.append([tick,'transfer',v,j,h])
                            conn.vehicle.resume(v);del parked[v];idx[v]+=1;idx['T']+=1
                            if j=='b':
                                assert not held['T'];conn.vehicle.resume('T');del parked['T'];events.append([tick,'truck_release','T','b',h])
                    controller.arm_next(conn,veh,idx,acts,tick)
                    if len(done)==len(c['old'])+2 and conn.simulation.getMinExpectedNumber()==0:break
            assert len(done)==len(c['old'])+2 and not any(held.values())
            assert exitset==seen==(set(c['actors'])|{'bg','T'}|({'slow0','slow1'} if c['slow'] else set()))
            assert len(pexit)==len(pseen)==(10 if people else 0) and dx==tel==0
    except BaseException:error=traceback.format_exc()
    finally:
        controller.close()
        if conn:
            try:conn.close()
            except Exception:pass
    result={'error':error,'prefix':prefix.hexdigest(),'trace_hash':total.hexdigest(),'events':events,
            'completed':done,'collision_ticks':dx,'teleports':tel,'elapsed_seconds':time.perf_counter()-clock,'planning_seconds':planning_seconds,
            'activation_tick':activation_tick,'activation_delay_seconds':(activation_tick-old.EPOCH)/old.HZ,
            'unfinished_customers':sorted((set(c['old'])|{'a','b'})-set(done)),'simulated_seconds':tick/old.HZ}
    old.put(out/'RESULT.json',result)
    if error:raise RuntimeError(error)
    audit=audit_trace(out);old.put(out/'AUDIT.json',audit)
    return audit


def audit_trace(out):
    """Reconstruct customer/load/transfer invariants from native frame/event evidence."""
    out=Path(out);inp=old.read(out/'INPUT.json');r=old.read(out/'RESULT.json');s=inp['snapshot'];c=s['c'];w=s['wave2'];p=inp['plan']
    with gzip.open(out/'trace.jsonl.gz','rt',encoding='utf8') as f:frames=[json.loads(x) for x in f]
    assert not r['error'] and not r['collision_ticks'] and not r['teleports']
    assert frames and len(frames)==frames[-1]['tick']
    total=hashlib.sha256();prefix=hashlib.sha256()
    for f in frames:
        line=(json.dumps(f,sort_keys=True,separators=(',',':'))+'\n').encode();total.update(line)
        if f['tick']<=old.EPOCH:prefix.update(line);assert 'T' not in f['vehicles']
    assert total.hexdigest()==r['trace_hash'] and prefix.hexdigest()==r['prefix']==s['prefix']
    held={v:set(old.items(c,v)) for v in c['actors']};truck={'a','b'};done={};trans={};begins={};released=[]
    def stopped(f,v,dest):return native.hit(f['vehicles'].get(v),dest)
    for tick,tag,v,j,*rest in r['events']:
        if tag=='beginX':begins[j]=tick
        if tag=='transfer':
            assert j in truck and j not in held[v] and v==p['receiver']
            assert (j=='a' and not trans) or (j=='b' and set(trans)=={'a'} and 'a' in done)
            assert tick-begins[j]==2*old.HZ
            for f in frames[begins[j]-1:tick]:assert stopped(f,v,p['hub']) and stopped(f,'T','T'+p['hub'][-1])
            load=sum(w['orders'][k]['weight'] if k in ('a','b') else c['size'][k] for k in held[v])
            assert load+w['orders'][j]['weight']<=s['capacity'][v]
            truck.remove(j);held[v].add(j);trans[j]=tick
        if tag=='delivery':
            assert j in held[v] and j not in done
            site=w['orders'][j]['dest'] if j in ('a','b') else c['old'][j]
            assert all(stopped(f,v,site) for f in frames[tick-4*old.HZ-1:tick])
            held[v].remove(j);done[j]=tick
        if tag=='truck_release':released.append(tick)
    assert done==r['completed'] and set(done)==set(c['old'])|{'a','b'} and not truck and not any(held.values())
    assert released==[trans['b']]
    # The truck remains physically parked during the intervening release/delivery loop.
    assert all(stopped(f,'T','T'+p['hub'][-1]) for f in frames[trans['a']-1:trans['b']])
    assert all(done[old.items(c,v)[0]]==old.EPOCH for v in c['actors'])
    activation=inp['activation_tick']
    assert [e[0] for e in r['events'] if e[1]=='plan_activation']==[activation]
    assert activation==old.EPOCH+math.ceil(inp['planning_seconds']*old.HZ)
    for v in c['actors']:
        site=c['old'][old.items(c,v)[0]]
        assert all(stopped(f,v,site) for f in frames[old.EPOCH-1:activation])
    assert all('T' not in f['vehicles'] for f in frames[:activation])
    trip=ET.parse(out/'trips.xml').getroot();trips={v.get('id'):v.attrib for v in trip.findall('tripinfo')}
    assert set(trips)==set(c['actors'])|{'bg','T'}|({'slow0','slow1'} if c['slow'] else set())
    assert all(float(x['arrival'])>0 for x in trips.values())
    # Observed exposure only; proximity is not evidence that a pedestrian caused delay.
    net=ET.parse(old.NET/f'cycle_{s["offset"]}.net.xml').getroot()
    lengths={e.get('id'):float(e.find('lane').get('length')) for e in net.findall('edge')}
    links={(x.get('from'),x.get('to')):int(x.get('linkIndex')) for x in net.findall('connection') if x.get('tl')=='C'}
    near_pairs=set();near_ticks=0;crosswalk_ticks=0;red_stops={v:0 for v in c['actors']+['T']}
    for f in frames[activation:]:
        crosswalk_ticks+=any(row[0]==':C_c0' for row in f['people'].values())
        for v in red_stops:
            row=f['vehicles'].get(v)
            if row is None:continue
            link=links.get((row[0],f.get('next_edges',{}).get(v)))
            if link is not None and 0<=lengths[row[0]]-row[1]<=45 and not row[3]&1 and row[2]<.1 and f['signal'][link] in 'rRyY':red_stops[v]+=1
            for person,pr in f['people'].items():
                if math.dist(row[4:6],pr[1:3])<=15:
                    near_pairs.add((v,person));near_ticks+=1
    J=(sum(done.values())-2*old.EPOCH)/old.HZ
    return {'status':'PASS','J_customer_seconds':J,'completed':done,'handoff_a_seconds':trans['a']/old.HZ,
            'last_handoff_seconds':trans['b']/old.HZ,'truck_release_seconds':released[0]/old.HZ,
            'all_customers':len(done),'prefix':prefix.hexdigest(),'trace_sha256':total.hexdigest(),
            'collision_ticks':r['collision_ticks'],'teleports':r['teleports'],
            'planning_seconds':inp['planning_seconds'],'activation_seconds':activation/old.HZ,
            'activation_delay_seconds':(activation-old.EPOCH)/old.HZ,
            'quantization_seconds':inp['quantization_seconds'],
            'old_flow_seconds':sum(t for j,t in done.items() if j not in ('a','b'))/old.HZ,
            'new_flow_seconds':{j:(done[j]-old.EPOCH)/old.HZ for j in ('a','b')},
            'truck_arrival_seconds':next(e[0]/old.HZ for e in r['events'] if e[1]=='arrive' and e[2]=='T'),
            'truck_dwell_seconds':(trans['b']-next(e[0] for e in r['events'] if e[1]=='arrive' and e[2]=='T'))/old.HZ,
            'truck_wait_excluding_transfer_seconds':(trans['b']-next(e[0] for e in r['events'] if e[1]=='arrive' and e[2]=='T'))/old.HZ-4,
            'unfinished_customers':sorted((set(c['old'])|{'a','b'})-set(done)),
            'traffic_trip_metrics':{v:{k:x.get(k) for k in ('duration','waitingTime','timeLoss','routeLength','arrival')} for v,x in trips.items()},
            'pedestrian_arrivals':len(ET.parse(out/'trips.xml').getroot().findall('personinfo')),
            'observed_exposure':{'red_or_yellow_signal_stopped_ticks':red_stops,'ped_near_vehicle_pair_ticks':near_ticks,
                'ped_near_vehicle_pairs':sorted(near_pairs),'crosswalk_occupied_ticks_after_activation':crosswalk_ticks,
                'proximity_radius_metres':15,'interpretation':'Observed exposure, not identified causal pedestrian delay'}}

