"""Same-engine AWA no-pair / gated-pair and complete ANA on customer-flow J.
No separate freight paper or global multi-vehicle assignment reproduction is claimed.
The source closure of check_online_v450 pins the complete published engine.
"""
from pathlib import Path
import sys,time
import online_model_v450 as model
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'baseline_replication'))
import published_search_v450 as engine
METHODS=('HZ_AWA_RADIUS','HZ_AWA_PAIR_GATED','ANA_RADIUS')

class Domain(model.AWADomain):
    def __init__(self,snapshot,pair=False,profile=False):
        super().__init__(snapshot,pair);self.ctx.profile=profile
        self.raw_bounds={};self.raw_cache_queries=0;self.raw_cache_hits=0
    def raw_lower(self,s):
        # Store the local admissible J value, never an inherited Pathmax value.
        self.raw_cache_queries+=1
        if s in self.raw_bounds:
            self.raw_cache_hits+=1;return self.raw_bounds[s]
        value=(min(self.raw_lower(self.ctx.initial(b)) for b in self.ctx.branches())
               if s is None else self.ctx.bound(s,False))
        self.raw_bounds[s]=value;return value
    def lower_cost(self,s):
        # Identical cache and downward arithmetic guard for both AWA arms and ANA.
        return max(self.g(s),self.raw_lower(s)-1e-7)
    def extra_prune(self,s,incumbent,stored_lower):
        if not self.pair or s is None or 'Xa' in s.tokens:return False
        # J_pair-J_base is tied to the RAW local base. Using stored_lower here
        # would double-count an inherited parent floor and can cause unsafe cuts.
        return self.ctx.pair_cutoff(s,incumbent,local_base=self.raw_lower(s))
    def phase(self,s):
        if s is None:return -1
        return 2 if 'Xb' in s.tokens else 1 if 'Xa' in s.tokens else 0
    def stats(self):
        return dict(self.ctx.counts,**self.ctx.profile_ns,profile_enabled=self.ctx.profile,
            raw_bound_cache_queries=self.raw_cache_queries,raw_bound_cache_hits=self.raw_cache_hits,
            raw_bound_cache_entries=len(self.raw_bounds))
    def audit_state(self,s):
        if s is None:return None
        return dict(receiver=s.branch.receiver,hub=s.branch.hub,tokens=s.tokens,t=s.t,pos=s.pos,cost=s.cost)

def solve(snapshot,method,wall_seconds=.05,audit=False,node_limit=None,profile=False):
    if method not in METHODS:raise ValueError('Unknown complete published search method')
    start=time.perf_counter();holder=[]
    def factory():
        d=Domain(snapshot,pair=method=='HZ_AWA_PAIR_GATED',profile=profile);holder.append(d);return d
    r=engine.search_domain(factory,'ANA' if method=='ANA_RADIUS' else 'AWA',
        wall_ms=None if wall_seconds is None else 1000*wall_seconds,weight=2,
        inherit_bound=True,node_limit=node_limit,audit=audit,started_clock=start)
    d=holder[0];trace=[]
    for item in r['trace']:
        p=d.actions_plan(item['plan'])
        trace.append(dict(item,J=item['cost'],signature=model.signature(p),plan=p,
            expanded=item['expansion_index']))
    plan=d.actions_plan(r['plan']);initial=trace[0]
    within=[x for x in trace if wall_seconds is None or x['seconds']<=wall_seconds]
    r.pop('_started_clock',None)
    elapsed=time.perf_counter()-start
    return dict(arm=method,J=r['objective_value'],plan=plan,signature=model.signature(plan),
        initial=dict(J=initial['J'],plan=initial['plan'],seconds=initial['seconds']),trace=trace,
        within_budget_J=within[-1]['J'] if within else None,within_budget_plan=within[-1]['plan'] if within else None,
        elapsed_seconds=elapsed,deadline_seconds=wall_seconds,
        overrun_seconds=max(0.,elapsed-wall_seconds) if wall_seconds is not None else 0.,
        lower_bound=r['lower_bound'],certified_forecast_optimal=r['certified_optimal'],
        certified_forecast_optimal_by_deadline=r['certified_optimal'] and (wall_seconds is None or elapsed<=wall_seconds),
        stop_reason=r['stop_reason'],counts=r['stats'],published=dict(algorithm=r['algorithm'],
            weight=r['weight'],complete_loop=True,freight_paper_replication=False,
            custom_pair_hook=method=='HZ_AWA_PAIR_GATED',raw_engine=r),
        trace_time_scope='Complete executable action-sequence availability; final conversion and certificate charged to elapsed activation latency')
