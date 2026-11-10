"""V450 customer-flow J domain; V449 is imported read-only with an exact pin.

The two incoming atomic parcels share one receiver and hub, in order a then b.
Both vehicles' old customers remain in J. Four branches are unchanged across
methods. General traffic forecasts are not FIFO: no earliest-state dominance.
The model predicts dispatch at decision time; native execution separately adds
measured planning latency before activating the chosen plan.

Context(snapshot, basis='radius'), State/Branch, solve(...), and AWADomain are
public. AWADomain implements the independent published AWA engine contract.
Its optional extra_prune is a Boolean test; U_rel is never an incumbent or LB.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, sys, math, heapq, itertools, time
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]
PREVIOUS=WORK/'fleet_study_v449_validation_and_online_20261107'/'online'/'online_model.py'
PREVIOUS_SHA='31d5521a1424608b6f0654744fbb7e0cfc83978071dd0ec96e4b83993a76fb06'
if hashlib.sha256(PREVIOUS.read_bytes()).hexdigest()!=PREVIOUS_SHA:
    raise RuntimeError('Frozen V449 model changed')
_spec=importlib.util.spec_from_file_location('_v449_online_readonly',PREVIOUS)
base=importlib.util.module_from_spec(_spec);sys.modules[_spec.name]=base;_spec.loader.exec_module(base)
old=base.old; Branch=base.Branch; State=base.State; EPS=base.EPS
ARMS=('RADIUS','RADIUS_WEIGHTED','PAIR_WEIGHTED_GATED','ROUTE')
signature=base.signature

class Context(base.Context):
    def __init__(self,snapshot,basis='radius'):
        if basis not in ('radius','exact'):raise ValueError('Invalid basis')
        self.s=snapshot;self.c=snapshot['c'];self.w=snapshot['wave2'];self.basis=basis;self.profile=False
        self.profile_ns=dict(bound_time_ns=0,pair_time_inclusive_ns=0,pair_time_exclusive_ns=0)
        self.epoch=float(snapshot.get('epoch',6.));self.service=4.;self.transfer=2.;self.matrix=old.MATRIX
        self.actors=tuple(self.c['actors']);self.cap=dict(snapshot['capacity'])
        if self.actors!=('A','B') or self.epoch!=6. or self.w['release']!=6.:
            raise ValueError('V450 stage 1 is the native six-second decision epoch')
        if set(self.w['orders'])!={'a','b'} or not 0<self.weight('a')<self.weight('b'):
            raise ValueError('Two positive ordered atomic parcels required')
        self.jobs={v:tuple(old.items(self.c,v)) for v in self.actors}
        for v in self.actors:
            if not self.jobs[v] or not self.weight('b')<=self.cap[v]<self.weight('a')+self.weight('b'):
                raise ValueError('Unsupported receiver capacity or empty committed first stop')
            if sum(self.c['size'][j] for j in self.jobs[v])>self.cap[v]:
                raise ValueError('Initial cargo overload')
            if any(self.c['size'][j]<=0 for j in self.jobs[v]):raise ValueError('Positive old weights required')
            ctx=snapshot['ctx'][v]
            if ctx['remaining_cm']!=0 or abs(ctx['ready']/old.SCALE-self.epoch)>EPS:
                raise ValueError('Both first committed customer services must end at decision epoch')
        self.sig=old.ShortForecast(snapshot['offset'],snapshot['obs'],'COARSE')
        self.counts={k:0 for k in ('leg_calls','prefix_leg_calls','forecast_leg_calls','full_forecasts',
            'bound_calls','pair_calls','pair_stronger','expanded','generated','base_pruned','pair_only_pruned',
            'pair_skip_upper','pair_events','pair_loop_queries','quota_dp_calls','quota_dp_cache_hits','quota_dp_labels')}
        self.d=self._closure(8);self.truck_d=self._closure(6);self.quota_cache={}
        self.fixed={v:self.fixed_route(v) for v in self.actors}
        self.truck={h:self.leg(self.epoch,self.w['T'],'T'+h[-1],6,'forecast') for h in old.POINTS}
        self.other_cost={v:self._old_cost(v) for v in self.actors}
    def fixed_route(self,v):
        first,*remaining=self.jobs[v];seq=[first];pos=self.c['old'][first]
        # Common deterministic nearest-next route, with stable ID tie-breaking.
        while remaining:
            j=min(remaining,key=lambda j:(self.matrix[pos][self.c['old'][j]][0],j))
            seq.append(j);remaining.remove(j);pos=self.c['old'][j]
        return tuple(seq)
    def _old_cost(self,v):
        seq=self.fixed[v];t=self.epoch;pos=self.c['old'][seq[0]];cost=0.
        for j in seq[1:]:
            t=self.leg(t,pos,self.c['old'][j],8,'forecast')+self.service
            cost+=t;pos=self.c['old'][j]
        return cost
    def initial(self,b):
        j=self.jobs[b.receiver][0]
        # Both already completed first customers count once, here, not in other_cost.
        return State(b,(j,),self.epoch,self.c['old'][j],len(self.actors)*self.epoch)
    def legal(self,p):
        try:
            b=Branch(p['receiver'],p['hub'])
            if b not in self.branches() or set(p['route'])!=set(self.actors):return False
            u=next(v for v in self.actors if v!=b.receiver)
            if tuple(p['route'][u])!=self.fixed[u]:return False
            seq=p['route'][b.receiver]
            if seq[0]!=self.jobs[b.receiver][0] or sorted(seq)!=sorted(self.jobs[b.receiver]+('Xa','a','Xb','b')):return False
            held=set(self.jobs[b.receiver][1:]);picked=set();old_done=0
            for j in seq[1:]:
                if j in ('Xa','Xb'):
                    k=j[1]
                    if k in picked or (k=='a' and old_done<1) or (k=='b' and 'a' not in picked):return False
                    load=sum(self.weight(o) if o in ('a','b') else self.c['size'][o] for o in held)
                    if load+self.weight(k)>self.cap[b.receiver]:return False
                    held.add(k);picked.add(k)
                else:
                    if j not in held:return False
                    held.remove(j)
                    if j not in ('a','b'):old_done+=1
            return not held
        except (KeyError,IndexError,TypeError):return False
    def quota_duration(self,s,quota):
        rem=self.remaining(s);h=s.branch.hub;key=(rem,s.pos,h,quota)
        self.counts['quota_dp_calls']+=1
        if key in self.quota_cache:
            self.counts['quota_dp_cache_hits']+=1;return self.quota_cache[key]
        if quota<=0:return self.d[s.pos][h]
        n=len(rem);weights=[0]*(1<<n);dp={};answer=math.inf
        for mask in range(1,1<<n):
            bit=mask&-mask;i=bit.bit_length()-1;weights[mask]=weights[mask^bit]+self.c['size'][rem[i]]
            for j in range(n):
                if not mask>>j&1:continue
                prev=mask^(1<<j);dest=self.c['old'][rem[j]]
                if not prev:value=self.d[s.pos][dest]+self.service
                else:value=min(dp[prev,k]+self.d[self.c['old'][rem[k]]][dest]+self.service for k in range(n) if prev>>k&1)
                dp[mask,j]=value;self.counts['quota_dp_labels']+=1
                if weights[mask]>=quota:answer=min(answer,value+self.d[dest][h])
        self.quota_cache[key]=answer;return answer
    def h2_bounds(self,s,with_pair=True):
        if self.basis=='radius':return super().h2_bounds(s,with_pair)
        if with_pair:raise ValueError('Exact ROUTE is the no-pair auxiliary baseline')
        h=s.branch.hub;L=sum(self.c['size'][j] for j in self.remaining(s));Q=self.cap[s.branch.receiver]
        qa=max(0,L+self.weight('a')-Q);qb=max(0,L+self.weight('b')-Q)
        A=self.epoch+self.truck_d[self.w['T']]['T'+h[-1]]
        B=max(A,s.t+self.quota_duration(s,qa))+self.transfer
        an=self.w['orders']['a']['dest'];loop=self.d[h][an]+self.service+self.d[an][h]
        value=max(B+loop,max(A,s.t+self.quota_duration(s,qb)))+self.transfer
        return B,value,value
    def bound(self,s,pair=False):
        if not self.profile:return super().bound(s,pair)
        start=time.perf_counter_ns()
        try:return super().bound(s,pair)
        finally:self.profile_ns['bound_time_ns']+=time.perf_counter_ns()-start
    def pair_cutoff(self,s,incumbent,local_base=None):
        if not self.profile:return self._pair_cutoff_impl(s,incumbent,local_base)
        start=time.perf_counter_ns();before=self.profile_ns['bound_time_ns']
        try:return self._pair_cutoff_impl(s,incumbent,local_base)
        finally:
            elapsed=time.perf_counter_ns()-start
            self.profile_ns['pair_time_inclusive_ns']+=elapsed
            self.profile_ns['pair_time_exclusive_ns']+=elapsed-(self.profile_ns['bound_time_ns']-before)
    def _pair_cutoff_impl(self,s,incumbent,local_base=None):
        """Equivalent strict full-pair J rejection; cheap upper bounds only skip it.

        J_pair=J_radius+(H_pair-H_radius). Thus target H is translated from J,
        and the min-over-events passes iff at least one event has sufficient
        distinct old weight in E1 union eligible two-visit loops. No weighted
        sort, no independent reuse of one old parcel, no U_rel propagation.
        """
        if self.basis!='radius' or 'Xa' in s.tokens:return False
        self.counts['pair_calls']+=1
        local=self.bound(s,False) if local_base is None else local_base
        B,H,_=self.h2_bounds(s,False);limit=H+incumbent+EPS-local
        if H>limit:return True
        h=s.branch.hub;ds=self.d;an=self.w['orders']['a']['dest'];rem=self.remaining(s)
        L=sum(self.c['size'][o] for o in rem);qb=max(0,L+self.weight('b')-self.cap[s.branch.receiver])
        r={o:s.t+ds[s.pos][self.c['old'][o]]+self.service+ds[self.c['old'][o]][h] for o in rem}
        Rb=self.quantile(((r[o],self.c['size'][o]) for o in rem),qb,s.t+ds[s.pos][h])
        loop=ds[h][an]+self.service+ds[an][h]
        upper=max(H,max(B,Rb+self.transfer)+loop+self.transfer)
        if upper<=limit:
            self.counts['pair_skip_upper']+=1;return False
        alpha={o:r[o]+self.transfer for o in rem}
        for x in sorted({B}|{v for v in alpha.values() if v>=B}):
            self.counts['pair_events']+=1
            if x+loop+self.transfer>limit:continue
            released=0
            for o in rem:
                if alpha[o]<=x:released+=self.c['size'][o]
                else:
                    on=self.c['old'][o];self.counts['pair_loop_queries']+=1
                    duration=min(ds[h][an]+self.service+ds[an][on]+self.service+ds[on][h],
                                 ds[h][on]+self.service+ds[on][an]+self.service+ds[an][h])
                    if x+duration+self.transfer<=limit:released+=self.c['size'][o]
                if released>=qb:break
            if released>=qb:return False
        return True


def solve(snapshot,arm,wall_seconds=0.05,per_branch_cap=10**9):
    """Internal paired kernel; external full published AWA has a separate adapter.
    Every setup, greedy, closure, bound, full forecast and final certificate is timed.
    Both weighted arms have the same radius/pathmax queue channel; only the
    extra safe pop rejection differs. No cross-clock duplicate dominance.
    """
    if arm not in ARMS or wall_seconds is not None and wall_seconds<=0:raise ValueError('Bad method/budget')
    start=time.perf_counter();ctx=Context(snapshot,'exact' if arm=='ROUTE' else 'radius')
    best=math.inf;bestplan=None;trace=[];seen=set();evals={b:0 for b in ctx.branches()};serial=itertools.count()
    deadline=None if wall_seconds is None else start+wall_seconds
    def score(p):
        nonlocal best,bestplan
        sig=signature(p)
        if sig in seen:return
        seen.add(sig);b=Branch(p['receiver'],p['hub']);evals[b]+=1;pred=ctx.forecast(p);stamp=time.perf_counter()-start
        if (pred['J'],sig)<(best,signature(bestplan) if bestplan else '~'):
            best=pred['J'];bestplan=p
            trace.append(dict(seconds=stamp,J=best,signature=sig,plan=p,expanded=ctx.counts['expanded']))
    for b in ctx.branches():score(ctx.greedy(b))
    initial=dict(J=best,plan=bestplan,seconds=time.perf_counter()-start)
    # The common four-seed initialization is atomic for every method.
    trace[:]=[dict(seconds=initial['seconds'],J=best,signature=signature(bestplan),plan=bestplan,expanded=0)]
    heap=[];weighted=arm in ('RADIUS_WEIGHTED','PAIR_WEIGHTED_GATED')
    def push(s,floor=-math.inf):
        raw=ctx.bound(s,False);lb=max(raw,floor);g=s.cost
        key=g+2*(lb-g) if weighted else lb
        heapq.heappush(heap,(key,next(serial),s,lb,raw))
    for b in ctx.branches():push(ctx.initial(b))
    stopped='exhausted';discarded=False
    while heap:
        if deadline is not None and time.perf_counter()>=deadline:stopped='wall';break
        _,_,s,lb,raw=heapq.heappop(heap)
        if lb>best+EPS:ctx.counts['base_pruned']+=1;continue
        if evals[s.branch]>=per_branch_cap:discarded=True;continue
        if arm=='PAIR_WEIGHTED_GATED' and ctx.pair_cutoff(s,best,raw):
            ctx.counts['pair_only_pruned']+=1;continue
        ctx.counts['expanded']+=1
        for child in ctx.children(s):
            if ctx.terminal(child):score(ctx.plan(child))
            else:push(child,lb)
    if discarded and stopped=='exhausted':stopped='forecast_cap'
    # Raw, unweighted OPEN bounds provide the certificate, never the weighted top key.
    lower=min([best]+[x[3] for x in heap]) if not discarded else None
    certified=lower is not None and lower>=best-EPS
    elapsed=time.perf_counter()-start
    within=[r for r in trace if wall_seconds is None or r['seconds']<=wall_seconds]
    assert ctx.counts['full_forecasts']==sum(evals.values())
    return dict(arm=arm,J=best,plan=bestplan,signature=signature(bestplan),initial=initial,trace=trace,
        elapsed_seconds=elapsed,within_budget_J=within[-1]['J'] if within else None,
        within_budget_plan=within[-1]['plan'] if within else None,deadline_seconds=wall_seconds,
        overrun_seconds=max(0.,elapsed-wall_seconds) if wall_seconds is not None else 0.,
        lower_bound=lower,certified_forecast_optimal=certified,
        certified_forecast_optimal_by_deadline=certified and (wall_seconds is None or elapsed<=wall_seconds),
        stop_reason=stopped,counts=ctx.counts,per_branch_forecasts={b.receiver+b.hub:n for b,n in evals.items()})

class AWADomain:
    """Thin domain for a separately implemented Hansen--Zhou AWA engine.
    Artificial root is None. Only full exact state identity may merge labels.
    All actions carry enough identity to rebuild the plan without another search.
    """
    def __init__(self,snapshot,pair=False):self.ctx=Context(snapshot);self.pair=pair
    def initial(self):return None
    def is_goal(self,s):return s is not None and self.ctx.terminal(s)
    def g(self,s):
        if s is None:return 0.
        if self.is_goal(s):
            other=next(v for v in self.ctx.actors if v!=s.branch.receiver)
            return s.cost+self.ctx.other_cost[other]
        return s.cost
    def lower_cost(self,s):
        if s is None:return min(self.ctx.bound(self.ctx.initial(b),False) for b in self.ctx.branches())
        return self.ctx.bound(s,False)
    def successors(self,s):
        if s is None:
            for b in self.ctx.branches():yield self.ctx.initial(b),('branch',b.receiver,b.hub)
        else:
            for child in self.ctx.children(s):yield child,('visit',child.tokens[-1])
    def greedy(self):
        scored=[]
        for b in self.ctx.branches():
            p=self.ctx.greedy(b);value=self.ctx.forecast(p)['J']
            actions=(('branch',b.receiver,b.hub),)+tuple(('visit',j) for j in p['route'][b.receiver][1:])
            scored.append((value,signature(p),actions))
        v,_,a=min(scored);return v,a
    def dominance_key(self,s):return ('ROOT',) if s is None else (s.branch,s.tokens,s.t,s.pos,s.cost)
    def dominance_vector(self,s):return (self.g(s),)
    def extra_prune(self,s,incumbent,stored_lower):
        return bool(self.pair and s is not None and self.ctx.pair_cutoff(s,incumbent))
    def actions_plan(self,actions):
        _,v,h=actions[0];b=Branch(v,h);tokens=(self.ctx.jobs[v][0],)+tuple(a[1] for a in actions[1:])
        s=State(b,tokens,0.,'',0.);p=self.ctx.plan(s)
        if not self.ctx.legal(p):raise ValueError('AWA action chain is not a legal complete route')
        return p
