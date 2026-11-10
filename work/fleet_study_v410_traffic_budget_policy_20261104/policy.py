import importlib.util
import itertools
import math
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE=Path(__file__).resolve().parent
V408=HERE.parent/'fleet_study_v408_rolling_transfer_traffic_20261104'
sys.path.insert(0,str(V408/'source'))
from models import HZ,EPOCH,SCALE,SERV,XFER,SITES,items,read,put,fh,digest,parent,reveal,costs
from dispatch import dispatch,evaluate,reference
spec=importlib.util.spec_from_file_location('v408_controls',V408/'native_budget_controls_01/ops.py')
prior=importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
ARMS=('DIRECT','SEP','COMMON','C_COMMON','P_COMMON','CP_COMMON','CP_SEP','CP_DIRECT','FULL_COMMON','FULL_PHASE')
SEEDS=tuple(range(410411,410417))
SITES_BY_ID=[('A','HE'),('A','HW'),('B','HE'),('B','HW')]

class PublicSignal:
    def __init__(self,offset):
        root=ET.parse(V408/'network'/f'cycle_{offset}.net.xml').getroot()
        self.length={e.get('id'):round(100*float(e.find('lane').get('length'))) for e in root.findall('edge')}
        program=root.find("tlLogic[@id='C']")
        self.offset=float(program.attrib['offset'])
        self.phases=[(float(p.get('duration')),p.get('state')) for p in program.findall('phase')]
        assert sum(d for d,_ in self.phases)==48
        self.turns={(c.get('from'),c.get('to')):int(c.get('linkIndex')) for c in root.findall('connection') if c.get('tl')=='C'}
    def signal(self,t):
        pos=round((t+self.offset-1/HZ)%48,9)
        for dur,state in self.phases:
            if pos<dur:return state
            pos-=dur
        raise AssertionError(t)
    def waiting(self,t,link):
        pos=round((t+self.offset-1/HZ)%48,9)
        for j,(dur,state) in enumerate(self.phases):
            if pos<dur:
                if state[link] in 'gG':return 0
                delay=dur-pos
                for k in range(1,len(self.phases)+1):
                    duration,next_state=self.phases[(j+k)%len(self.phases)]
                    if next_state[link] in 'gG':return delay
                    delay+=duration
            pos-=dur
        raise AssertionError(t)
    def traverse(self,start,route,start_cm,total_cm,speed,on,passages):
        clock=start
        pos=0
        old=0
        for ix,(e,z) in enumerate(zip(route,route[1:])):
            pos+=self.length[e]-(start_cm if ix==0 else 0)
            link=self.turns.get((e,z))
            if link is not None:
                assert 0<=pos<=total_cm+1,(route,start_cm,pos,total_cm)
                clock+=(pos-old)/100/speed
                wait=self.waiting(clock,link) if on else 0
                passages.append([e,z,clock,wait])
                clock+=wait
                old=pos
        return clock+(total_cm-old)/100/speed
    def leg(self,clock,origin,dest,speed,mat,on,visits):
        dist,edges=mat[origin][dest]
        return self.traverse(clock,edges,round(SITES[origin][1]*100),dist,speed,on,visits)
    def forecast(self,case,ctx,wave,mat,plan,on=True):
        hub=plan['hub']
        visits=[]
        truck=self.leg(EPOCH/HZ,wave['T'],'T'+hub[-1],6,mat,on,visits)
        completed={}
        wait=None
        for v,seq in plan['route'].items():
            observed=ctx[v]
            edges=observed['native_route'][observed['route_index']:]
            assert observed['edge']==edges[0]
            clock=self.traverse(EPOCH/HZ,edges,round(observed['pos_m']*100),observed['remaining_cm'],8,on,visits)+SERV/SCALE
            first=seq[0];completed[first]=clock
            site=case['old'][first]
            for a in seq[1:]:
                dest=hub if a=='X' else wave['i'] if a=='i' else case['old'][a]
                clock=self.leg(clock,site,dest,8,mat,on,visits)
                if a=='X':
                    wait=max(0,clock-truck);clock=max(clock,truck)+XFER/SCALE
                else:
                    clock+=SERV/SCALE;completed[a]=clock
                site=dest
        return {'J':sum(completed.values())-EPOCH/HZ,'old':sum(t for j,t in completed.items() if j!='i'),
                'new':completed['i']-EPOCH/HZ,'truck_wait':wait,'crossings':visits}

def decide(c,w,ctx,m,sig,arm):
    start=time.perf_counter()
    sr={'c':c,'wave2':w,'context':ctx}
    if arm in ('COMMON','SEP'):
        d=dispatch(c,w,m,ctx,arm,2)
        plan=d['plan'];choice=d['choice'];opened=d['opened'];score=d['score'];details=[];ranks=d['rank']
    else:
        basis='DIRECT' if arm.endswith('DIRECT') else 'SEP' if arm.endswith('SEP') else 'COMMON'
        def bound(v,h):
            if basis=='DIRECT':return prior.direct(sr,m,v,h)
            return reference(None,c,w,m,ctx,v,h,basis=='SEP')
        ranks=sorted((bound(v,h),v,h) for v,h in SITES_BY_ID)
        cover=arm.startswith('C')
        phase=arm.startswith('CP_') or arm in ('P_COMMON','FULL_PHASE')
        menu=[ranks[0],next(r for r in ranks if r[1]!=ranks[0][1])] if cover else ranks[:2]
        incumbent=math.inf
        details=[]
        for lb,v,h in menu:
            if not cover and not arm.startswith('FULL_') and lb>incumbent:break
            static,route=evaluate(c,w,m,ctx,v,h);incumbent=min(incumbent,static)
            plan={'receiver':v,'hub':h,'route':route}
            pred=sig.forecast(c,ctx,w,m,plan) if phase else None
            details.append({'choice':v+h[-1],'score':static,'plan':plan,'pred':pred})
        winner=min(details,key=lambda d:((round(d['pred']['J'],8) if phase else d['score']),d['choice']))
        plan=winner['plan'];choice=winner['choice'];score=winner['score'];opened=[row['choice'] for row in details]
    elapsed=time.perf_counter()-start
    assert len(opened)<=2 and elapsed<1 and len(set(opened))==len(opened)
    return dict(choice=choice,score=score,plan=plan,opened=opened,details=details,rank=ranks,seconds=elapsed,signature=digest(plan))
