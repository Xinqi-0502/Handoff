import gzip
import json
import xml.etree.ElementTree as ET
from model_turn2 import *
def frames(d):
    with gzip.open(d/'trace.jsonl.gz','rt',encoding='utf8') as f:return [json.loads(x) for x in f]
def observe(d):
    fr=frames(d)
    x=fr[EPOCH-1]
    assert x['tick']==EPOCH and 'T' not in x['vehicles']
    return x['people']
def get(d):
    inp=read(d/'INPUT.json');r=read(d/'RESULT.json')
    fr=frames(d);assert fr and len(fr)==fr[-1]['tick']
    observed=observe(d);sig=Crossing(int(inp['offset']),observed,False)
    assert all(q['signal']==sig.signal(q['tick']/HZ) for q in fr)
    assert not r['collision_ticks'] and not r['teleports']
    assert not any('T' in q['vehicles'] for q in fr[:EPOCH])
    assert all(r['epoch_context'][v]['ready']==E*SCALE for v in inp['c']['actors'])
    # Verify hashes independent of the controller and independently match each delivery to parked physical intervals.
    import hashlib
    prefix=hashlib.sha256();total=hashlib.sha256()
    for f in fr:
        b=(json.dumps(f,sort_keys=True,separators=(',',':'))+'\n').encode()
        total.update(b)
        if f['tick']<=EPOCH:prefix.update(b)
    assert total.hexdigest()==r['trace_hash'] and prefix.hexdigest()==r['prefix']
    c=inp['c'];w=inp['wave'];plan=inp['plan'];done={};held={v:set(items(c,v)) for v in c['actors']}
    def stopped(frame,v,site):
        edge,y=SITES[site];x=frame['vehicles'].get(v)
        return x is not None and x[0]==edge and abs(y-x[1])<1.6 and x[2]==0 and x[3]&1
    for tick,tag,v,j,*rest in r['events']:
        if tag=='transfer':
            assert sum(c['size'][k] for k in held[v])+4<=CAP[v] and 'i' not in held[v]
            for f in fr[tick-11:tick]:
                assert stopped(f,v,plan['hub']) and stopped(f,'T','T'+plan['hub'][-1])
            held[v].add('i')
        if tag=='delivery':
            assert j in held[v] and j not in done
            held[v].remove(j);done[j]=tick
            site=w['i'] if j=='i' else c['old'][j]
            assert all(stopped(f,v,site) for f in fr[tick-21:tick])
    assert done==r['completed']
    for v in c['actors']:assert done[items(c,v)[0]]==EPOCH
    jobs=[*c['old'],'i']
    status='complete' if not r['error'] and len(done)==len(jobs) else 'horizon' if len(fr)==3000 and len(done)<len(jobs) else 'failed'
    ret=dict(status=status,done=len(done),tr=total.hexdigest(),prefix=prefix.hexdigest(),J600=(sum(done.get(j,3000) for j in jobs)-EPOCH)/HZ,
             vehstop={},crosses={},ped={})
    if status=='complete':
        assert not any(held[v] for v in c['actors'])
        truck_arr=next(f['tick'] for f in fr if stopped(f,'T','T'+plan['hub'][-1]))
        hand=next(f['tick'] for f in fr if stopped(f,'T','T'+plan['hub'][-1]) and stopped(f,plan['receiver'],plan['hub']))
        ret.update(J=ret['J600'],old=(sum(done.values())-done['i'])/HZ,new=(done['i']-EPOCH)/HZ,wait=(hand-truck_arr)/HZ,handoff=hand/HZ)
    for v in ('A','B','T','bg'):
        seen=None;st={'protected_red_yellow':0,'permissive_no_crossing':0,'permissive_with_crossing':0,'protected_green':0,'right_interior_clear':0,'right_interior_with_crossing':0}
        transitions=[]
        for f in fr:
            x=f['vehicles'].get(v)
            if x is None:continue
            if x[0] in ('WC','EC') and x[2]<0.1 and not(x[3]&1) and 0<=sig.length[x[0]]/100-x[1]<=12:
                link=2 if x[0]=='WC' else 0
                crossing=any(y[0]==':C_c0' for y in f['people'].values())
                key='protected_red_yellow' if f['signal'][link] not in 'gG' else 'protected_green' if f['signal'][link]=='G' else 'permissive_with_crossing' if crossing else 'permissive_no_crossing'
                st[key]+=1
            if x[0] in (':C_2',':C_4') and x[2]<.1 and not(x[3]&1):
                occupied=any(y[0]==':C_c0' for y in f['people'].values())
                st['right_interior_with_crossing' if occupied else 'right_interior_clear']+=1
            if x[0] in (':C_0',':C_2') and seen!=x[0]:
                transitions.append([x[0],f['tick']/HZ, int((f['tick']/HZ+sig.offset-1/HZ)//48)])
            seen=x[0]
        ret['vehstop'][v]={k:n/HZ for k,n in st.items()};ret['crosses'][v]=transitions
    ids={p for f in fr for p in f['people']}
    for p in ids:
        obs=[(f['tick'],f['people'][p]) for f in fr if p in f['people']]
        ctimes=[t for t,y in obs if y[0]==':C_c0']
        wait_ticks=sum(1 for (t,y),(n,z) in zip(obs,obs[1:]) if y[0] in ('NC',':C_w0') and (n-t)==1 and math.dist(z[1:],y[1:])<.02)
        ret['ped'][p]=dict(start=obs[0][0]/HZ,last=obs[-1][0]/HZ,cross_start=min(ctimes)/HZ if ctimes else None,
            cross_finish=(max(ctimes)+1)/HZ if ctimes else None,near_cross_still_s=wait_ticks/HZ)
    tree=ET.parse(d/'trips.xml')
    trips={v.get('id'):v.attrib for v in tree.findall('tripinfo')}
    ret['trip_loss']={k:float(x['timeLoss']) for k,x in trips.items()}
    if status=='complete':assert set(trips)=={'A','B','T','bg'} and all(float(x['arrival'])>0 for x in trips.values()) and len(ids)==(10 if inp['people'] else 0) and all(v['cross_finish'] is not None for v in ret['ped'].values())
    return ret
