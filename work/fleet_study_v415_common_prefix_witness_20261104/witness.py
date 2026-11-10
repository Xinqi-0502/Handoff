import itertools
import math
import random
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
V414=HERE.parent/'fleet_study_v414_common_order_candidates_20261104'
sys.path.insert(0,str(V414))
import dispatch414 as prev
from dispatch414 import CAP, MATRIX, SCALE, V408, V410, v410, items, fh, put, read, digest, reveal
import models, audit, street_cycle

CAP.update({'A':6,'B':5})
assert CAP is models.CAP and CAP is audit.CAP and CAP is street_cycle.CAP
ARMS=('EXTREME_SEP','COMMON_WIT','FREE_PHASE','STATIC_RESCORE')
SEEDS=tuple(range(415411,415417))

def parent(seed):
    rng=random.Random(seed)
    pool=[side+turn+stop for side in 'WE' for turn in 'UD' for stop in 'uvx']
    destinations=rng.sample(pool,10)
    sizes={};old={};starts={}
    for k,v in enumerate('AB'):
        starts[v]=v+'in'+rng.choice('WE')
        weights=[2,1,1,1] if v=='A' else [1,1,1,1]
        rng.shuffle(weights)
        for j,weight in enumerate([1]+weights):
            x=v.lower()+str(j);sizes[x]=weight;old[x]=destinations[k*5+j]
        assert sum(sizes[v.lower()+str(j)] for j in range(5))==CAP[v]
    return dict(seed=seed,actors=['A','B'],start=starts,size=sizes,old=old)

def profiles(c,w,ctx,sig,v,h):
    ready=prev.first_completion(sig,ctx[v],True)
    rows=[]
    for S,plans in prev.project(c,w,ready,sig,v,h,True):
        for plan in plans:
            prefix=plan['pi'][:len(S)]
            rows.append(dict(prefix=prefix,pi=plan['pi'],O=round(plan['O'],8),N=round(plan['N'],8),
                               J=round(plan['O']+plan['N'],8)))
    return rows

def select(rows):
    min_o=min(x['O'] for x in rows);min_n=min(x['N'] for x in rows)
    extremes=[x for x in rows if x['O']==min_o or x['N']==min_n]
    def key(x):
        return (x['J'],x['prefix'],x['pi'])
    return min(extremes,key=key),min(rows,key=key),min_o,min_n

def solve(c,w,ctx,sig,v,h,prefix):
    truck=sig.leg(prev.T0,w['T'],'T'+h[-1],6,MATRIX,True,[])
    paths={};counts={};score=0
    for a in c['actors']:
        ready=prev.first_completion(sig,ctx[a],True)
        first,*jobs=items(c,a)
        if a!=v:
            seqs=([first,*old] for old in itertools.permutations(jobs))
        elif prefix is None:
            seqs=prev.tokens(c,w,a,None,True)
        else:
            assert set(prefix)<=set(jobs) and len(prefix)==len(set(prefix))
            tail=[j for j in jobs if j not in prefix]
            assert sum(c['size'][j] for j in tail)+w['weight']<=CAP[v]
            seqs=([first,*prefix,'X',*after] for after in itertools.permutations(tail+['i']))
        vals=[(round(prev.forecast_one(c,w,sig,a,h,seq,ready,truck,True),8),tuple(seq)) for seq in seqs]
        cost,order=min(vals)
        paths[a]=list(order);score+=cost;counts[a]=len(vals)
    plan=dict(receiver=v,hub=h,route=paths)
    pred=sig.forecast(c,ctx,w,MATRIX,plan,True)
    assert abs(pred['J']-score)<1e-6
    return plan,pred,counts

def decide(c,w,ctx,sig,arm):
    t=time.perf_counter()
    menu=sorted((v410.reference(None,c,w,MATRIX,ctx,v,h,True),v,h)
                for v in c['actors'] for h in ('HE','HW'))[:2]
    alts=[]
    for _,v,h in menu:
        witness=None;rows=[];counts={}
        if arm in ('COMMON_WIT','EXTREME_SEP'):
            rows=profiles(c,w,ctx,sig,v,h)
            sep,common,min_o,min_n=select(rows)
            chosen=common if arm=='COMMON_WIT' else sep
            prefix=chosen['prefix']
            witness=dict(prefix=prefix,pi=chosen['pi'],O=chosen['O'],N=chosen['N'],J=chosen['J'],
                         extreme=chosen['O']==min_o or chosen['N']==min_n,min_O=min_o,min_N=min_n,
                         proper=len(prefix)<len(items(c,v))-1,profile_count=len(rows),
                         reference_sep=sep,reference_common=common)
            plan,pred,counts=solve(c,w,ctx,sig,v,h,prefix)
        elif arm=='FREE_PHASE':
            plan,pred,counts=solve(c,w,ctx,sig,v,h,None)
        else:
            val,paths=v410.evaluate(c,w,MATRIX,ctx,v,h)
            plan=dict(receiver=v,hub=h,route=paths);pred=sig.forecast(c,ctx,w,MATRIX,plan)
            for a in c['actors']:
                counts[a]=sum(1 for _ in prev.tokens(c,w,a,None,a==v))
        alts.append(dict(key=v+h[-1],plan=plan,pred=pred,witness=witness,profiles=rows,eval_counts=counts))
    selected=min(alts,key=lambda x:(round(x['pred']['J'],8),x['key']))
    sec=time.perf_counter()-t
    assert len(menu)==2 and sec<1
    return dict(arm=arm,opened=[x['key'] for x in alts],choice=selected['key'],plan=selected['plan'],
                signature=digest(selected['plan']),alternatives=alts,seconds=sec)
