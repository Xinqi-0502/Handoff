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
    def lower_cost(self,s):
        # Common downward rounding guard for real-valued travel arithmetic.
        return max(self.g(s),super().lower_cost(s)-1e-7)
    def phase(self,s):
        if s is None:return -1
        return 2 if 'Xb' in s.tokens else 1 if 'Xa' in s.tokens else 0
    def stats(self):return dict(self.ctx.counts,**self.ctx.profile_ns,profile_enabled=self.ctx.profile)
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
