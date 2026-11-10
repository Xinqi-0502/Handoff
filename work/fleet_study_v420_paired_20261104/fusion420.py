"""Budgeted route construction with mandatory capacity release, under aggregate traffic."""
from itertools import permutations
from pathlib import Path
import sys,time
HOME = Path(__file__).resolve().parent
PRIOR = HOME.parent/'fleet_study_v419_signal_pedestrian_traffic_20261104'
PAPER = HOME.parent/'fleet_study_v420_published_baseline_20261104'
sys.path[:0] = [str(PRIOR),str(PAPER)]
from model_turn2 import CAP,MATRIX,E,EPOCH,HZ,SERV,SCALE,XFER,NET,items,parent,reveal,fh,digest,put,read
from coarse import summary,ShortForecast
from paper_oropt import select_plans
sys.path.insert(0,str(HOME.parent/'fleet_study_v420_algorithm_evidence_20261104'))
import fixed_order_insert
ARMS=('GREEDY_ONE','GREEDY','SEP','FUSED','FUSED_STATIC','GMIRA_OROPT','PAPER_INSERT')
POINTS=('HE','HW')
def legal(c,w,plan):
    v=plan['receiver']
    if v not in c['actors'] or plan['hub'] not in POINTS or set(plan['route'])!=set(c['actors']):
        return False
    for a,seq in plan['route'].items():
        jobs=items(c,a)
        if not seq or seq[0]!=jobs[0] or sorted(seq)!=sorted(list(jobs)+(['X','i'] if a==v else [])):
            return False
        if a==v:
            idx=seq.index('X')
            if seq.index('i')<idx or sum(c['size'][j] for j in seq[idx+1:] if j!='i')+w['weight']>CAP[v]:
                return False
    return True
def lengths(c,v):
    first,*jobs=items(c,v)
    def steps(seq):
        return tuple(MATRIX[c['old'][a]][c['old'][b]][0] for a,b in zip(seq,seq[1:]))
    return min(((first,)+o for o in permutations(jobs)),key=lambda s:(steps(s),s))
def branch_pool(c,w,v,h,other):
    f,*jobs=items(c,v)
    for o in permutations(jobs):
        for k in range(1,len(jobs)+1):
            if sum(c['size'][i] for i in o[k:])+w['weight']>CAP[v]:continue
            before=o[:k];tail=o[k:]
            for n in range(len(tail)+1):
                seq=(f,)+before+('X',)+tail[:n]+('i',)+tail[n:]
                plan={'receiver':v,'hub':h,'route':{v:list(seq),other[0]:list(other[1])}}
                yield seq, plan
def refsite(c,w,h,token):
    if token=='X':return h
    if token=='i':return w['i']
    return c['old'][token]
def greedy_key(c,w,h,seq):
    sites=[refsite(c,w,h,j) for j in seq]
    # First deliver until freed; as soon as capacity permits, prefer pickup; tie by nearest continuation.
    return (seq.index('X'),tuple(MATRIX[a][b][0] for a,b in zip(sites,sites[1:])),tuple(seq))
class Projection:
    def __init__(self,sig,traffic):
        self.sig=sig;self.traffic=traffic;self.weights={}
        ticks=range(int(sum(d for d,_ in sig.phases)*HZ))
        self.mean_wait={link:sum(sig.waiting(t/HZ,link) for t in ticks)/len(ticks) for link in set(sig.turns.values())} if traffic else {}
    def leg(self,orig,dest,speed,t):
        key=(orig,dest,speed)
        if key not in self.weights:
            d,edges=MATRIX[orig][dest]
            base=d/100/speed;extra=0.
            if self.traffic:
                for a,b in zip(edges,edges[1:]):
                    link=self.sig.turns.get((a,b))
                    if link is not None:
                        base+=self.mean_wait[link]
                        edge='WC' if link in self.sig.right_links else 'EC'
                        extra+={'slow':2,'nearstop':4}.get(self.sig.obs[edge]['category'],0)
            self.weights[key]=base,extra
        base,extra=self.weights[key]
        return base+(extra if t<=E+48 else 0)
    def old_new(self,c,w,h,seq,truck):
        clock=E;old=E;new=None
        site=c['old'][seq[0]]
        for j in seq[1:]:
            dest=refsite(c,w,h,j);clock+=self.leg(site,dest,8,clock)
            if j=='X':
                clock=max(truck,clock)+XFER/SCALE
            else:
                clock+=SERV/SCALE
                if j=='i':new=clock-E
                else:old+=clock
            site=dest
        return round(old,7),round(new,7)
def propose(c,w,h,candidates,projection,arm):
    if arm=='GREEDY':
        return sorted(candidates,key=lambda x:greedy_key(c,w,h,x[0]))
    truck=E+projection.leg(w['T'],'T'+h[-1],6,E)
    scored=[]
    for seq,p in candidates:
        old,new=projection.old_new(c,w,h,seq,truck)
        group=tuple(sorted(seq[1:seq.index('X')]))
        scored.append((old,new,group,seq,p))
    if arm!='SEP':
        return [(q[3],q[4]) for q in sorted(scored,key=lambda q:(round(q[0]+q[1],7),q[3]))]
    bins={}
    for row in scored:bins.setdefault(row[2],[]).append(row)
    minima={g:(min(r[0] for r in rows),min(r[1] for r in rows)) for g,rows in bins.items()}
    def separate_key(row):
        old,new,grp,seq,_=row;mo,mn=minima[grp]
        return (round(mo+mn,7),grp,int(old!=mo and new!=mn),round(old+new,7),seq)
    return [(q[3],q[4]) for q in sorted(scored,key=separate_key)]
def select(c,w,ctx,observed,offset,arm):
    begin=time.perf_counter()
    sig=ShortForecast(offset,observed,'COARSE')
    proj=Projection(sig,arm!='FUSED_STATIC') if arm in ('SEP','FUSED','FUSED_STATIC') else None
    scores=[];branches={};old_orders={a:lengths(c,a) for a in c['actors']}
    for v in c['actors']:
        u=next(a for a in c['actors'] if a!=v)
        for h in POINTS:
            log=[];seen=set()
            pool=list(branch_pool(c,w,v,h,(u,old_orders[u])))
            incumbent=min(pool,key=lambda x:greedy_key(c,w,h,x[0]))[1]
            def score(p):
                sigkey=digest(p);assert sigkey not in seen and legal(c,w,p)
                seen.add(sigkey)
                val=sig.forecast(c,ctx,w,MATRIX,p)
                log.append(dict(signature=sigkey,plan=p,pred={n:val[n] for n in ('J','old','new','truck_wait')}))
                scores.append(log[-1])
                return val['J']
            if arm=='PAPER_INSERT':
                _,diagnosis=fixed_order_insert.select_plans(c,w,v,h,incumbent,score,lambda p:legal(c,w,p),6)
            elif arm=='GREEDY_ONE':
                score(incumbent);diagnosis={}
            elif arm=='GMIRA_OROPT':
                _,diagnosis=select_plans(c,w,v,h,incumbent,score,lambda p:legal(c,w,p),6)
            else:
                score(incumbent)
                for seq,p in propose(c,w,h,pool,proj,arm):
                    if digest(p) in seen:continue
                    score(p)
                    if len(log)==6:break
                diagnosis={'pool':len(pool)}
            assert 1<=len(log)<=6
            branches[v+h[-1]]={'evaluated':log,'diagnostics':diagnosis}
    winner=min(scores,key=lambda q:(round(q['pred']['J'],7),q['signature']))
    wall=time.perf_counter()-begin
    assert wall<1,(arm,wall)
    return dict(arm=arm,plan=winner['plan'],signature=winner['signature'],pred=winner['pred'],seconds=wall,n_eval=len(scores),branches=branches)
