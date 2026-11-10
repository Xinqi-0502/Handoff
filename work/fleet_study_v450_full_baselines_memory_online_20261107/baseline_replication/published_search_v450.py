"""Independent complete published search engines, prepared without executing search.

AWA: Hansen & Zhou (2007), Algorithm 1.
ANA: van den Berg et al. (2011), Figure 1, including goal-pop and global rekey.
Shared domain, feasible initializer, forward Pathmax and finite timed-state
dominance are explicitly documented adaptations, not freight-paper reproduction.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import heapq
import math
from pathlib import Path
import time

METHODS=("HZ_AWA_RADIUS","HZ_AWA_RADIUS_PAIR_GATED","ANA_RADIUS")
DOMAIN_SHA="f955dcb082a1e8fb4e683741a657c433209202f313571c07174d9ab15de42a6c"
_DOMAIN=None

def configure_domain(sp):
    """Call once for every measured worker; no solver or context is created."""
    global _DOMAIN
    path=Path(sp.__file__)
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=DOMAIN_SHA:raise ValueError("Expected the frozen V448 common domain")
    if not hasattr(sp,"Context") or not hasattr(sp,"Watchdog"):raise TypeError("Missing domain API")
    _DOMAIN=sp
    return {"domain_source":str(path),"sha256":actual}

def _number(value,name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError((name,value))
    return value

@dataclass(frozen=True)
class _Label:
    state: object
    plan: tuple
    g: float
    lower: float
    serial: int
    key: object
    vector: tuple

class _Search:
    """Independent OPEN/archive/parent-plan implementation, not sp.solve."""
    def __init__(self,domain,algorithm,weight,watchdog,started,deadline,node_limit,inherit,audit):
        self.d=domain;self.algorithm=algorithm;self.weight=weight;self.watchdog=watchdog
        self.started=started;self.deadline=deadline;self.node_limit=node_limit
        self.inherit=inherit;self.audit=audit;self.serial=0
        self.heap=[];self.live={};self.archive={};self.expanded_keys=set()
        self.trace=[];self.audit_trace=[];self.E=math.inf
        self.count=dict(expanded=0,expanded_phase0=0,expanded_phase1=0,expanded_other=0,
            generated=0,queued=0,pruned=0,dominated=0,stale_pops=0,reopened=0,
            terminal_generated=0,goal_pops=0,frontier_rekeys=0,rekey_labels=0,
            peak_frontier=0,extra_prune_calls=0,extra_pruned=0)
        self.U=None;self.best_plan=None

    def hard_check(self):
        if self.watchdog is not None:self.watchdog.check()

    def should_stop(self):
        self.hard_check()
        if self.node_limit is not None and self.count["expanded"]>=self.node_limit:
            return "node_budget"
        if self.deadline is not None and time.perf_counter()>=self.deadline:
            return "wall_budget"
        return None

    def goal(self,s):return bool(self.d.is_goal(s))

    def lower(self,s,g,parent=None):
        value=g if self.goal(s) else _number(self.d.lower_cost(s),"lower_cost")
        if value<g:raise AssertionError("Nonnegative remaining-cost heuristic required")
        if parent is not None and self.inherit:
            if self.goal(s):
                if parent.lower>g:raise AssertionError("Parent bound exceeds actual goal")
            else:value=max(value,parent.lower)
        return value

    def vector(self,s):
        vector=tuple(self.d.dominance_vector(s))
        if not vector:raise ValueError("Nonempty explicit dominance vector required")
        for v in vector:_number(v,"dominance component")
        return vector

    def potential(self,label):
        h=label.lower-label.g
        if h<0:raise AssertionError("Negative remaining heuristic")
        if h==0:return math.inf if label.g<self.U else -math.inf
        return (self.U-label.g)/h

    def priority(self,label):
        if self.algorithm=="AWA":return label.g+self.weight*(label.lower-label.g)
        return -self.potential(label)

    def admit(self,s,plan,parent=None):
        """Strict Pareto improvement under the domain's proven dominance contract."""
        g=_number(self.d.g(s),"g")
        if g<0 or (parent is not None and g<parent.g):
            raise AssertionError("Nonnegative objective increments required")
        key=self.d.dominance_key(s);vector=self.vector(s)
        bucket=self.archive.setdefault(key,{})
        for old in bucket.values():
            if len(old)!=len(vector):raise AssertionError("Dominance dimension changed")
            if all(a<=b for a,b in zip(old,vector)):
                self.count["dominated"]+=1;return None
        for ident,old in list(bucket.items()):
            if all(a<=b for a,b in zip(vector,old)):
                del bucket[ident]
                self.live.pop(ident,None)
        ident=self.serial;self.serial+=1
        bucket[ident]=vector
        if key in self.expanded_keys:self.count["reopened"]+=1
        lower=self.lower(s,g,parent)
        if lower>=self.U:
            self.count["pruned"]+=1;return None
        label=_Label(s,tuple(plan),g,lower,ident,key,vector)
        self.live[ident]=label
        heapq.heappush(self.heap,(self.priority(label),ident))
        self.count["queued"]+=1
        self.count["peak_frontier"]=max(self.count["peak_frontier"],len(self.live))
        return label

    def pop(self):
        while self.heap:
            _,ident=heapq.heappop(self.heap)
            label=self.live.pop(ident,None)
            if label is None:
                self.count["stale_pops"]+=1;continue
            if label.lower>=self.U:
                self.count["pruned"]+=1;continue
            return label
        if self.live:raise AssertionError("Live OPEN label missing from heap")
        return None

    def improve(self,label,kind):
        if label.g>=self.U:return False
        self.U=label.g;self.best_plan=label.plan
        k=self.count["expanded"]
        self.trace.append(dict(seconds=time.perf_counter()-self.started,cost=self.U,
            plan=list(self.best_plan),expansion_index=k,
            expansions_completed=k if kind=="goal_pop" else k-1,event_kind=kind))
        return True

    def rekey_ana(self):
        """Figure 1 line 20: every surviving OPEN key uses the NEW incumbent."""
        self.hard_check();self.count["frontier_rekeys"]+=1
        heap=[]
        for ident,label in list(self.live.items()):
            self.hard_check()
            if label.lower>=self.U:
                del self.live[ident];self.count["pruned"]+=1
            else:
                heap.append((self.priority(label),ident))
                self.count["rekey_labels"]+=1
        heapq.heapify(heap);self.heap=heap

    def expand(self,label):
        self.count["expanded"]+=1
        phase=self.d.phase(label.state) if hasattr(self.d,"phase") else None
        field="expanded_phase0" if phase==0 else "expanded_phase1" if phase==1 else "expanded_other"
        self.count[field]+=1;self.expanded_keys.add(label.key)
        if self.audit:
            state=self.d.audit_state(label.state) if hasattr(self.d,"audit_state") else repr(label.state)
            self.audit_trace.append(dict(state=state,plan=list(label.plan),g=label.g,lower=label.lower))
        for child,action in self.d.successors(label.state):
            self.hard_check();self.count["generated"]+=1
            plan=label.plan+(action,)
            if self.goal(child):
                self.count["terminal_generated"]+=1
                g=_number(self.d.g(child),"goal cost")
                if g<label.g:raise AssertionError("Negative objective edge")
                if self.inherit and label.lower>g:raise AssertionError("Invalid inherited goal bound")
                if self.algorithm=="AWA":
                    # Hansen-Zhou Algorithm 1 reports a goal as soon as generated.
                    target=_Label(child,plan,g,g,-1,None,())
                    self.improve(target,"goal_generated")
                else:
                    # ANA Figure 1 lines 6-8 require selection from OPEN first.
                    self.admit(child,plan,label)
            else:self.admit(child,plan,label)

    def loop(self):
        while self.heap:
            stop=self.should_stop()
            if stop:return stop
            label=self.pop()
            if label is None:break
            if self.algorithm=="ANA":
                self.E=min(self.E,self.potential(label))
                if self.goal(label.state):
                    self.count["goal_pops"]+=1
                    if not self.improve(label,"goal_pop"):
                        raise AssertionError("ANA extracted a non-improving goal")
                    self.rekey_ana()
                    continue
            elif self.goal(label.state):
                raise AssertionError("AWA does not queue generated goals")
            extra=getattr(self.d,"extra_prune",None)
            if extra is not None:
                self.count["extra_prune_calls"]+=1
                if extra(label.state,self.U,label.lower):
                    self.count["extra_pruned"]+=1;self.count["pruned"]+=1
                    continue
            self.expand(label)
        return "exhausted"

    def certificate(self):
        # All successor operations have completed at normal soft-stop boundaries.
        lower=min([self.U]+[x.lower for x in self.live.values()])
        if lower>self.U:raise AssertionError("Invalid frontier certificate")
        return lower

def search_domain(domain_factory,algorithm="AWA",*,watchdog=None,wall_ms=1000,
                  node_limit=None,weight=2,inherit_bound=True,audit=False,
                  started_clock=None):
    """Complete published search with an explicit, import-free domain interface.

    Domain: initial(), greedy()->(cost, tuple(actions)), successors(state),
    is_goal(state), g(state), lower_cost(state), dominance_key(state),
    dominance_vector(state). Optional phase/audit_state/stats and extra_prune.
    lower_cost is cumulative g+h in the SAME units as the feasible objective.
    AWA/ANA share an initial feasible incumbent as a documented adaptation.
    """
    started=time.perf_counter() if started_clock is None else started_clock
    if algorithm not in ("AWA","ANA"):raise ValueError("Unknown published algorithm")
    if wall_ms is not None and (not math.isfinite(wall_ms) or wall_ms<=0):raise ValueError("Positive wall_ms or None")
    if node_limit is not None and (isinstance(node_limit,bool) or not isinstance(node_limit,int) or node_limit<0):raise ValueError("Nonnegative node_limit or None")
    if not math.isfinite(weight) or weight<1:raise ValueError("Weight must be >=1")
    deadline=None if wall_ms is None else started+wall_ms/1000
    domain=domain_factory();root=domain.initial()
    root_g=_number(domain.g(root),"root g")
    if root_g<0:raise AssertionError("Negative initial cost")
    setup_end=time.perf_counter()
    incumbent,plan=domain.greedy();incumbent=_number(incumbent,"feasible incumbent")
    if incumbent<root_g:raise AssertionError("Initial plan below sunk cost")
    initial_end=time.perf_counter()
    engine=_Search(domain,algorithm,weight,watchdog,started,deadline,node_limit,inherit_bound,audit)
    engine.U=incumbent;engine.best_plan=tuple(plan)
    engine.trace=[dict(seconds=initial_end-started,cost=incumbent,plan=list(plan),
        expansion_index=0,expansions_completed=0,event_kind="initial")]
    initial_overrun=deadline is not None and initial_end>=deadline
    root_bound=None;root_priority=None;root_seconds=0.0
    if initial_overrun:
        reason="initialization_overrun";lower=root_g
    elif node_limit==0:
        reason="node_budget";lower=root_g
    else:
        t=time.perf_counter();label=engine.admit(root,())
        root_seconds=time.perf_counter()-t
        # If root pruned by a proved bound, the incumbent is already certified.
        root_bound=label.lower if label is not None else incumbent
        root_priority=engine.priority(label) if label is not None else None
        reason=engine.loop();lower=engine.certificate()
    stats=dict(domain.stats()) if hasattr(domain,"stats") else {}
    stats.update(engine.count,structural_keys=len(engine.archive),
        dominance_records=sum(len(v) for v in engine.archive.values()),
        detailed_profile_enabled=False,published_search_algorithm=algorithm,
        extra_prune_enabled=hasattr(domain,"extra_prune"))
    elapsed=time.perf_counter()-started
    gap=engine.U-lower
    return dict(objective_value=engine.U,plan=list(engine.best_plan),trace=engine.trace,
        lower_bound=lower,certified_gap=gap,certified_optimal=(gap==0),
        elapsed_seconds=elapsed,setup_seconds=setup_end-started,
        initial_seconds=initial_end-setup_end,search_seconds=started+elapsed-initial_end,
        root_bound_seconds=root_seconds,root_bound=root_bound,root_priority=root_priority,
        initialization_overrun=initial_overrun,wall_budget_ms=wall_ms,
        overrun_seconds=0 if wall_ms is None else max(0,elapsed-wall_ms/1000),
        stop_reason=reason,timing_interpretable=True,stats=stats,
        audit_trace=engine.audit_trace,ana_reported_e_bound=None if not math.isfinite(engine.E) else max(1,engine.E),
        algorithm=algorithm,weight=weight if algorithm=="AWA" else None,
        **engine.count,_started_clock=started)

class RadiusDomain:
    """Common V448 domain and heuristic only; never invokes its search engine."""
    def __init__(self,sp,spec,watchdog):
        self.sp=sp;self.spec=spec;self.t0=spec["t0"]
        self.ctx=sp.Context(spec,watchdog,False,basis="radius")
        self.base_cache={};self.base_cache_hits=0
    def initial(self):return self.ctx.initial()
    def greedy(self):
        value,plan=self.ctx.greedy();return value-self.t0,tuple(plan)
    def successors(self,s):return self.ctx.children(s)
    def is_goal(self,s):return s.phase==2
    def g(self,s):return s.t-self.t0
    def base(self,s):
        key=(s.key,s.t)
        if key in self.base_cache:
            self.base_cache_hits+=1;return self.base_cache[key]
        value=self.ctx.base(s);self.base_cache[key]=value;return value
    def lower_cost(self,s):
        base=self.base(s)
        return (s.t if base is None else base.value)-self.t0
    def dominance_key(self,s):return s.key
    def dominance_vector(self,s):return (s.t,)
    def phase(self,s):return s.phase
    def audit_state(self,s):return [s.phase,s.oldmask,s.a_delivered,s.pos,s.t]
    def stats(self):
        return dict(self.ctx.stats(),common_base_cache_entries=len(self.base_cache),
                    common_base_cache_hits=self.base_cache_hits)

class RadiusPairGatedDomain(RadiusDomain):
    """Study enhancement: identical AWA key, extra safe Boolean pop pruning."""
    def __init__(self,sp,spec,watchdog):
        super().__init__(sp,spec,watchdog);self.joint_pop_calls=0
    def extra_prune(self,s,incumbent,stored_lower):
        if s.phase!=0:return False
        self.joint_pop_calls+=1
        return self.ctx.cutoff(s,self.base(s),incumbent+self.t0,True)
    def stats(self):return dict(super().stats(),joint_pop_calls=self.joint_pop_calls)

def solve(spec,method,watchdog=None,wall_ms=1000,hard_seconds=15,
          domain_module=None,audit=False,node_limit=None):
    """V449-compatible local H2 adapter; no oracle input, fresh Context per call."""
    started=time.perf_counter()
    if method not in METHODS:raise ValueError(("Unknown public method",method))
    sp=domain_module if domain_module is not None else _DOMAIN
    if sp is None:raise RuntimeError("Call configure_domain(sp), or pass domain_module=sp")
    if hard_seconds is not None and (not math.isfinite(hard_seconds) or hard_seconds<=0):raise ValueError("Positive hard_seconds")
    watchdog=watchdog if watchdog is not None else sp.Watchdog(float("inf") if hard_seconds is None else hard_seconds)
    algorithm="ANA" if method=="ANA_RADIUS" else "AWA"
    domain_type=RadiusPairGatedDomain if method=="HZ_AWA_RADIUS_PAIR_GATED" else RadiusDomain
    result=search_domain(lambda:domain_type(sp,spec,watchdog),algorithm,
        watchdog=watchdog,wall_ms=wall_ms,node_limit=node_limit,weight=2,
        inherit_bound=True,audit=audit,started_clock=started)
    origin=spec["t0"]
    trace=[dict(x,H2=x["cost"]+origin) for x in result["trace"]]
    result.update(method=method,arm=("HZ_AWA_PAIR_GATED" if method=="HZ_AWA_RADIUS_PAIR_GATED" else "HZ_AWA") if algorithm=="AWA" else "ANA",
        bound_basis="radius",H2=result["objective_value"]+origin,trace=trace,
        remaining_bound=result["lower_bound"]+origin,
        root_bound=None if result["root_bound"] is None else result["root_bound"]+origin,
        partial_expansions=0,joint_checks_at_pop=result["stats"].get("joint_pop_calls",0),
        joint_pruned_at_pop=result["extra_pruned"],
        node_trace=[],certificate_scope="Admissible unweighted live frontier; full objective offset restored",
        public_algorithm_complete_loop=True,freight_paper_reproduction=False)
    if audit:
        result["audit_trace"]=[x["state"]+[x["plan"]] for x in result["audit_trace"]]
    result.pop("_started_clock")
    elapsed=time.perf_counter()-started
    result["elapsed_seconds"]=elapsed
    result["search_seconds"]=elapsed-result["setup_seconds"]-result["initial_seconds"]
    result["overrun_seconds"]=0 if wall_ms is None else max(0,elapsed-wall_ms/1000)
    return result
