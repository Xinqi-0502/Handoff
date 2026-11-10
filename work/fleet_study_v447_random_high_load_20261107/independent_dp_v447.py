"""Independent FIFO forward-DP oracle for V447. Import-safe; no experiment runs.

No production Context, children, bound, queue, closure or dominance helper is used.
Each structural state retains its earliest absolute time. All edges raise
rank=delivered_old+phase+int(a_delivered), so labels are finalized topologically.
This is an exact oracle only for the shared FIFO model, not an external simulator.
"""
from __future__ import annotations
import heapq
import math
import time

INF=float("inf")


class OracleLimit(RuntimeError):
    pass


class Budget:
    def __init__(self, max_seconds):
        self.started=time.perf_counter()
        if max_seconds is not None and (not math.isfinite(max_seconds) or max_seconds<=0):
            raise ValueError("max_seconds must be positive finite or None.")
        self.deadline=None if max_seconds is None else self.started+max_seconds
    def check(self):
        if self.deadline is not None and time.perf_counter()>=self.deadline:
            raise OracleLimit("time_limit")


def validate(spec):
    old=spec["old"];m=len(old);n=spec["n_nodes"]
    if not 0<=m<=12 or not isinstance(n,int) or n<1:
        raise ValueError("Independent DP restricts m<=12 and a positive graph size.")
    fields=("Q","wa","wb","A","t0","tau_a","tau_b","a_service","hub","a_node","start_node")
    if any(not isinstance(spec[k],int) for k in fields):
        raise ValueError("Integer model inputs required.")
    if not 0<spec["wa"]<spec["wb"]<=spec["Q"] or spec["wa"]+spec["wb"]<=spec["Q"]:
        raise ValueError("Atomic capacity assumptions violated.")
    if min(spec["A"],spec["t0"])<0 or min(spec["tau_a"],spec["tau_b"],spec["a_service"])<=0:
        raise ValueError("Nonnegative clocks and positive services required.")
    for k in ("hub","a_node","start_node"):
        if not 0<=spec[k]<n:raise ValueError("Node index outside graph.")
    for o in old:
        if any(not isinstance(o[k],int) for k in ("node","weight","service")):
            raise ValueError("Integer old-item data required.")
        if not 0<=o["node"]<n or min(o["weight"],o["service"])<=0:
            raise ValueError("Invalid old item.")
    if sum(o["weight"] for o in old)>spec["Q"]:
        raise ValueError("Initial cargo exceeds capacity.")
    for e in spec["edges"]:
        if len(e)!=6 or any(not isinstance(v,int) for v in e):
            raise ValueError("Invalid edge tuple.")
        u,v,c,p,g,offset=e
        if not 0<=u<n or not 0<=v<n or c<0 or p<0 or (p and not 1<=g<=p):
            raise ValueError("Invalid FIFO edge.")
    return m,n


class IndependentNetwork:
    """Full destination-vector Dijkstra with inline periodic-green arithmetic.

    Production uses per-(source,destination,time) queries. This implementation
    computes and caches the whole vector for (source,time) independently.
    The optional cache cap clears cached results only; it never removes DP labels.
    """
    def __init__(self,spec,budget,max_cache_entries=100000):
        if not isinstance(max_cache_entries,int) or max_cache_entries<0:
            raise ValueError("Cache cap must be a nonnegative integer.")
        self.n=spec["n_nodes"];self.adj=[[] for _ in range(self.n)]
        for u,v,c,p,g,off in spec["edges"]:self.adj[u].append((v,c,p,g,off))
        self.budget=budget;self.cap=max_cache_entries;self.cache={}
        self.queries=self.hits=self.runs=self.relaxations=self.cache_clears=0

    def arrive(self,source,destination,departure):
        self.budget.check();self.queries+=1
        key=(source,departure)
        if key in self.cache:
            self.hits+=1
            answer=self.cache[key][destination]
        else:
            self.runs+=1
            earliest=[INF]*self.n;earliest[source]=departure
            pending=[(departure,source)]
            while pending:
                self.budget.check()
                now,u=heapq.heappop(pending)
                if now!=earliest[u]:continue
                for v,travel,period,green,offset in self.adj[u]:
                    self.relaxations+=1
                    if period:
                        position=(now-offset)%period
                        leave=now if position<green else now+period-position
                    else:leave=now
                    at=leave+travel
                    if at<earliest[v]:
                        earliest[v]=at;heapq.heappush(pending,(at,v))
            if self.cap:
                if len(self.cache)>=self.cap:
                    self.cache.clear();self.cache_clears+=1
                self.cache[key]=tuple(earliest)
            answer=earliest[destination]
        if answer==INF:raise ValueError("Required destination is unreachable.")
        return answer

    def stats(self):
        return dict(closure_queries=self.queries,closure_cache_hits=self.hits,
                    dijkstra_runs=self.runs,edge_relaxations=self.relaxations,
                    closure_cache_entries=len(self.cache),cache_clears=self.cache_clears,
                    closure_cache_cap=self.cap)


def solve(spec, *, max_seconds=30.0, max_labels=None, max_cache_entries=100000):
    """Return exact optimum only with status PASS; CENSORED is not an optimum.

    No incumbent pruning or proposed lower bound is evaluated. Every reachable
    structural label is considered once at its final earliest time. max_labels
    caps the number of distinct retained DP labels. Partial feasible completions,
    when available, are reported separately on censoring. A tied optimal plan
    need not be the plan selected by a production search policy.
    """
    budget=Budget(max_seconds)
    m,n=validate(spec)
    if max_labels is not None and (not isinstance(max_labels,int) or max_labels<1):
        raise ValueError("max_labels must be a positive integer or None.")
    net=IndependentNetwork(spec,budget,max_cache_entries)
    weights=[0]*(1<<m)
    root=(0,(1<<m)-1,False,spec["start_node"])
    best_time={root:spec["t0"]};parents={}
    buckets=[set() for _ in range(m+4)];buckets[0].add(root)
    generated=updates=expanded=phase0_expanded=phase1_expanded=0
    best_goal=None;best_goal_time=None;reason=None

    def rank(key):
        phase,mask,delivered,pos=key
        return m-mask.bit_count()+phase+int(delivered)

    def offer(parent,child,when,action):
        nonlocal generated,updates,best_goal,best_goal_time
        generated+=1
        if rank(child)!=rank(parent)+1 or when<=best_time[parent]:
            raise AssertionError("Expected a positive-time adjacent topological event.")
        if when>=best_time.get(child,INF):return
        if child not in best_time and max_labels is not None and len(best_time)>=max_labels:
            raise OracleLimit("label_limit")
        best_time[child]=when;parents[child]=(parent,action);updates+=1
        if child[0]==2:
            if best_goal_time is None or when<best_goal_time:
                best_goal,best_goal_time=child,when
        else:buckets[rank(child)].add(child)

    try:
        for mask in range(1,1<<m):
            if mask%128==0:budget.check()
            bit=mask&-mask
            weights[mask]=weights[mask^bit]+spec["old"][bit.bit_length()-1]["weight"]
        for level in range(m+3):
            budget.check()
            for key in sorted(buckets[level]):
                budget.check()
                phase,mask,delivered,pos=key;now=best_time[key]
                if rank(key)!=level:raise AssertionError("Bad topological bucket.")
                expanded+=1
                if phase==0:phase0_expanded+=1
                elif phase==1:phase1_expanded+=1
                else:raise AssertionError("Terminal label must not be expanded.")
                # Handwritten old deliveries, independent from production actions.
                for idx,item in enumerate(spec["old"]):
                    bit=1<<idx
                    if mask&bit:
                        done=net.arrive(pos,item["node"],now)+item["service"]
                        offer(key,(phase,mask^bit,delivered,item["node"]),done,f"old:{idx}")
                load=weights[mask]
                if phase==0 and load+spec["wa"]<=spec["Q"]:
                    at=net.arrive(pos,spec["hub"],now)
                    done=max(at,spec["A"])+spec["tau_a"]
                    offer(key,(1,mask,False,spec["hub"]),done,"handoff:a")
                if phase==1 and not delivered:
                    done=net.arrive(pos,spec["a_node"],now)+spec["a_service"]
                    offer(key,(1,mask,True,spec["a_node"]),done,"deliver:a")
                if phase==1 and delivered and load+spec["wb"]<=spec["Q"]:
                    done=net.arrive(pos,spec["hub"],now)+spec["tau_b"]
                    offer(key,(2,mask,True,spec["hub"]),done,"handoff:b")
        budget.check()
    except OracleLimit as exc:
        reason=str(exc)
    if reason is None and best_goal_time is None:
        raise AssertionError("No feasible completion in a completed DP.")

    plan=None
    if best_goal is not None:
        plan=[];key=best_goal
        while key!=root:
            key,action=parents[key];plan.append(action)
        plan.reverse()
    complete=reason is None
    return dict(status="PASS" if complete else "CENSORED",case=spec.get("case"),
                optimum_H2=best_goal_time if complete else None,
                best_feasible_H2=best_goal_time,plan=plan,certified_optimal=complete,
                stop_reason="all_structural_labels_completed" if complete else reason,
                expanded=expanded,expanded_phase0=phase0_expanded,expanded_phase1=phase1_expanded,
                structural_labels=len(best_time),accepted_updates=updates,generated=generated,
                elapsed_seconds=time.perf_counter()-budget.started,stats=net.stats(),
                oracle_kind="Independent topological earliest-arrival FIFO DP",
                proposed_bound_used=False,incumbent_pruning_used=False)


def replay_plan(spec,plan,*,max_seconds=30.0):
    """Independent action feasibility replay; returns final H2 or raises."""
    validate(spec);budget=Budget(max_seconds);net=IndependentNetwork(spec,budget)
    remaining=set(range(len(spec["old"])))
    phase=0;delivered=False;pos=spec["start_node"];now=spec["t0"]
    for action in plan:
        budget.check()
        if phase==2:raise AssertionError("Action after final handoff.")
        load=sum(spec["old"][i]["weight"] for i in remaining)
        if action.startswith("old:"):
            i=int(action.split(":")[1])
            if i not in remaining:raise AssertionError("Repeated/unknown old item.")
            item=spec["old"][i]
            now=net.arrive(pos,item["node"],now)+item["service"]
            pos=item["node"];remaining.remove(i)
        elif action=="handoff:a":
            if phase!=0 or load+spec["wa"]>spec["Q"]:raise AssertionError("Invalid first handoff.")
            now=max(net.arrive(pos,spec["hub"],now),spec["A"])+spec["tau_a"]
            phase=1;pos=spec["hub"]
        elif action=="deliver:a":
            if phase!=1 or delivered:raise AssertionError("Invalid a delivery.")
            now=net.arrive(pos,spec["a_node"],now)+spec["a_service"]
            delivered=True;pos=spec["a_node"]
        elif action=="handoff:b":
            if phase!=1 or not delivered or load+spec["wb"]>spec["Q"]:
                raise AssertionError("Invalid second handoff.")
            now=net.arrive(pos,spec["hub"],now)+spec["tau_b"]
            phase=2;pos=spec["hub"]
        else:raise AssertionError("Unknown action.")
    if phase!=2:raise AssertionError("Incomplete plan.")
    return now


if __name__=="__main__":
    raise SystemExit("Import-only independent oracle. Root-controlled correctness/protocol gate required.")

