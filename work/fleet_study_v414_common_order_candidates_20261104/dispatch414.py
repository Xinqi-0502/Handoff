from itertools import combinations, permutations
import math
from pathlib import Path
import random
import sys
import time

HERE = Path(__file__).resolve().parent
V410 = HERE.parent/'fleet_study_v410_traffic_budget_policy_20261104'
sys.path.insert(0,str(V410))
import policy as v410
from models import CAP, EPOCH, HZ, SERV, SCALE, XFER, SITES, items, fh, digest, put, read, reveal

V408 = v410.V408
MATRIX = read(V408/'network/expanded_legs.json')
SEEDS = tuple(range(414411,414417))
ARMS = ('SET_SEP','SET_COMMON','P_SEP','APART_SEP','APART_COMMON')
T0, SERVICE, TRANSFER = EPOCH/HZ, SERV/SCALE, XFER/SCALE

def parent(seed):
    rng=random.Random(seed)
    addresses=[s+b+t for s in 'WE' for b in 'UD' for t in 'uvx']
    dest=rng.sample(addresses,8)
    sizes={}
    old={}
    starts={}
    for k,v in enumerate('AB'):
        starts[v]=v+'in'+rng.choice('WE')
        weights=[1,1,2] if v=='A' else [1,1,1]
        rng.shuffle(weights)
        for n,weight in enumerate(([1] if v=='A' else [2])+weights):
            name=v.lower()+str(n)
            sizes[name]=weight
            old[name]=dest[4*k+n]
    return {'seed':seed,'actors':['A','B'],'start':starts,'size':sizes,'old':old}

def powersets(jobs):
    for n in range(len(jobs)+1):
        yield from combinations(jobs,n)

def first_completion(sig,state,phase):
    route=state['native_route'][state['route_index']:]
    assert route[0]==state['edge']
    return sig.traverse(T0,route,round(state['pos_m']*100),state['remaining_cm'],8,phase,[])+SERVICE

def customer_leg(sig,t,site,dest,phase):
    return sig.leg(t,site,dest,8,MATRIX,phase,[])+SERVICE

def old_alone(c,v,ready,sig,phase):
    first,*others=items(c,v)
    values=[]
    for seq in permutations(others):
        site=c['old'][first]; t=ready; costs=t
        for j in seq:
            dest=c['old'][j]
            t=customer_leg(sig,t,site,dest,phase)
            costs+=t;site=dest
        values.append((costs,seq))
    return min(values)[0]

def project(c,w,ready,sig,v,h,phase):
    first,*remaining=items(c,v)
    deficit=max(0,sum(c['size'][j] for j in remaining)+w['weight']-CAP[v])
    truck=sig.leg(T0,w['T'],'T'+h[-1],6,MATRIX,phase,[])
    result=[]
    for S in powersets(remaining):
        if sum(c['size'][j] for j in S)<deficit:continue
        other=tuple(j for j in remaining if j not in S)
        rows=[]
        for prefix in permutations(S):
            site=c['old'][first]; clock=ready; sent=clock
            for j in prefix:
                dest=c['old'][j];clock=customer_leg(sig,clock,site,dest,phase)
                sent+=clock;site=dest
            meeting=max(truck,sig.leg(clock,site,h,8,MATRIX,phase,[]))
            leave=meeting+TRANSFER
            new=customer_leg(sig,leave,h,w['i'],phase)-T0
            for tail in permutations(other):
                old=sent;site=h;clock=leave
                for j in tail:
                    dest=c['old'][j];clock=customer_leg(sig,clock,site,dest,phase)
                    old+=clock;site=dest
                rows.append(dict(pi=prefix+tail,O=old,N=new,meeting=meeting))
        assert rows
        result.append((S,rows))
    return result

def candidates(c,w,ctx,sig,phase=True):
    ready={v:first_completion(sig,ctx[v],phase) for v in c['actors']}
    solo={v:old_alone(c,v,ready[v],sig,phase) for v in c['actors']}
    result=[]
    for v in c['actors']:
        others=sum(solo[a] for a in c['actors'] if a!=v)
        for h in ('HE','HW'):
            for S,rows in project(c,w,ready[v],sig,v,h,phase):
                sep=others+min(r['O'] for r in rows)+min(r['N'] for r in rows)
                common=others+min(r['O']+r['N'] for r in rows)
                assert sep<=common+1e-6
                result.append(dict(v=v,h=h,S=S,rows=rows,sep=sep,common=common,other=others))
    return result

def flat_candidates(profiles):
    result=[]
    for v,h in sorted({(r['v'],r['h']) for r in profiles}):
        pieces=[r for r in profiles if (r['v'],r['h'])==(v,h)]
        other=pieces[0]['other']
        rows=[a for piece in pieces for a in piece['rows']]
        result.append(dict(v=v,h=h,S=None,rows=rows,
            sep=other+min(r['O'] for r in rows)+min(r['N'] for r in rows),
            common=other+min(r['O']+r['N'] for r in rows),other=other))
    return result

def tokens(c,w,v,S,chosen):
    first,*remaining=items(c,v)
    if not chosen:
        for seq in permutations(remaining):yield (first,)+seq
        return
    for prefix in powersets(remaining):
        if S is not None and prefix!=S:continue
        tail=tuple(j for j in remaining if j not in prefix)
        if sum(c['size'][j] for j in tail)+w['weight']>CAP[v]:continue
        for p in permutations(prefix):
            for r in permutations(tail+('i',)):
                yield (first,)+p+('X',)+r

def forecast_one(c,w,sig,v,h,seq,ready,truck,phase=True):
    site=c['old'][seq[0]]; t=ready; val=t
    for j in seq[1:]:
        if j=='X':
            t=max(truck,sig.leg(t,site,h,8,MATRIX,phase,[]))+TRANSFER
            site=h
        else:
            dest=w['i'] if j=='i' else c['old'][j]
            t=customer_leg(sig,t,site,dest,phase)
            val+=t-(T0 if j=='i' else 0)
            site=dest
    return val

def exact(c,w,ctx,sig,branch,phase=True):
    v,h,S=branch['v'],branch['h'],branch['S']
    truck=sig.leg(T0,w['T'],'T'+h[-1],6,MATRIX,phase,[])
    lengths={};routes={};total=0
    for a in c['actors']:
        ready=first_completion(sig,ctx[a],phase)
        options=[]
        for seq in tokens(c,w,a,S,a==v):
            options.append((round(forecast_one(c,w,sig,a,h,seq,ready,truck,phase),8),seq))
        val,seq=min(options)
        total+=val;routes[a]=list(seq);lengths[a]=len(options)
    plan=dict(receiver=v,hub=h,route=routes)
    score=sig.forecast(c,ctx,w,MATRIX,plan,phase)
    assert abs(total-score['J'])<1e-6
    return dict(key=branch_key(branch),plan=plan,pred=score,eval_counts=lengths)

def branch_key(row):
    return row['v']+row['h'][-1]+'/'+('flat' if row['S'] is None else '.'.join(row['S']))

def decide(c,w,ctx,sig,arm):
    if arm=='P_SEP':
        start=time.perf_counter()
        ranked=sorted((v410.reference(None,c,w,MATRIX,ctx,v,h,True),v,h) for v in c['actors'] for h in ('HE','HW'))
        opened=[];best=math.inf
        for lb,v,h in ranked:
            if len(opened)==2 or lb>best:break
            code=v+h[-1]
            val,paths=v410.evaluate(c,w,MATRIX,ctx,v,h)
            best=min(best,val)
            plan=dict(receiver=v,hub=h,route=paths)
            pred=sig.forecast(c,ctx,w,MATRIX,plan)
            opened.append(dict(key=code,plan=plan,pred=pred))
        sel=min(opened,key=lambda x:(round(x['pred']['J'],8),x['key']))
        dt=time.perf_counter()-start
        assert dt<1
        return dict(arm=arm,choice=sel['key'],plan=sel['plan'],signature=digest(sel['plan']),
                    opened=[a['key'] for a in opened],alternatives=opened,seconds=dt)
    start=time.perf_counter()
    profiles=candidates(c,w,ctx,sig)
    menu=profiles if arm.startswith('SET_') else flat_candidates(profiles)
    field=arm.split('_')[-1].lower()
    ranked=sorted(menu,key=lambda r:(round(r[field],8),branch_key(r)))
    opened=[exact(c,w,ctx,sig,r) for r in ranked[:2]]
    sel=min(opened,key=lambda x:(round(x['pred']['J'],8),x['key']))
    dt=time.perf_counter()-start
    assert dt<1 and len(opened)==2
    return dict(arm=arm,ranked=[dict(key=branch_key(r),sep=r['sep'],common=r['common'],
           witnesses=r['rows']) for r in ranked],choice=sel['key'],plan=sel['plan'],
           signature=digest(sel['plan']),opened=[a['key'] for a in opened],alternatives=opened,seconds=dt)
