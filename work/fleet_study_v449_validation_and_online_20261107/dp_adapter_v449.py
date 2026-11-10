"""Timed complete topological-DP baseline; no proposed bound or incumbent pruning.
The frozen V447 network/validation are reused. Oracle answers never enter solve.
"""
import math,time

class SoftStop(RuntimeError):pass

class ClockBudget:
    def __init__(self,dp,started,wall_ms,hard_seconds):
        self.dp=dp;self.started=started;self.active=False
        self.soft=None if wall_ms is None else started+wall_ms/1000
        self.hard=None if hard_seconds is None else started+hard_seconds
    def check(self):
        now=time.perf_counter()
        if self.hard is not None and now>=self.hard:raise self.dp.OracleLimit('hard_watchdog')
        if self.active and self.soft is not None and now>=self.soft:raise SoftStop('wall_limit')

def greedy(spec,net,budget):
    """Same rule/tie as frozen Context.greedy; own timed closure, no G calls."""
    remaining=set(range(len(spec['old'])));pos=spec['start_node'];now=spec['t0'];plan=[]
    while remaining:
        budget.check()
        done,i,node=min((net.arrive(pos,spec['old'][i]['node'],now)+spec['old'][i]['service'],i,spec['old'][i]['node']) for i in remaining)
        remaining.remove(i);pos=node;now=done;plan.append(f'old:{i}')
    h1=max(net.arrive(pos,spec['hub'],now),spec['A'])+spec['tau_a']
    done=net.arrive(spec['hub'],spec['a_node'],h1)+spec['a_service']
    h2=net.arrive(spec['a_node'],spec['hub'],done)+spec['tau_b']
    return h2,tuple(plan+['handoff:a','deliver:a','handoff:b'])

def solve(spec,dp,*,wall_ms=1000,hard_seconds=15,max_cache_entries=100000):
    started=time.perf_counter()
    if wall_ms is not None and (not math.isfinite(wall_ms) or wall_ms<=0):raise ValueError('Positive wall_ms or None')
    if hard_seconds is not None and (not math.isfinite(hard_seconds) or hard_seconds<=0):raise ValueError('Positive hard_seconds or None')
    budget=ClockBudget(dp,started,wall_ms,hard_seconds)
    m,n=dp.validate(spec);net=dp.IndependentNetwork(spec,budget,max_cache_entries)
    weights=[0]*(1<<m)
    for mask in range(1,1<<m):
        if mask%128==0:budget.check()
        bit=mask&-mask;weights[mask]=weights[mask^bit]+spec['old'][bit.bit_length()-1]['weight']
    root=(0,(1<<m)-1,False,spec['start_node'])
    best_time={root:spec['t0']};parents={};buckets=[set() for _ in range(m+4)];buckets[0].add(root)
    generated=updates=expanded=phase0=phase1=0
    canonical_goal=None;canonical_goal_time=None;first_dp_feasible_seconds=None
    setup_end=time.perf_counter()
    best,best_plan=greedy(spec,net,budget)
    initial_end=time.perf_counter()
    trace=[dict(seconds=initial_end-started,H2=best,plan=list(best_plan),expansion_index=0,expansions_completed=0)]
    initial_overrun=budget.soft is not None and initial_end>=budget.soft
    complete=False;reason=None;partial=False;partial_expansion=0
    budget.active=True

    def rank(key):return m-key[1].bit_count()+key[0]+int(key[2])
    def path(key):
        actions=[]
        while key!=root:
            key,action=parents[key];actions.append(action)
        actions.reverse();return tuple(actions)
    def offer(parent,child,when,action):
        nonlocal generated,updates,canonical_goal,canonical_goal_time,best,best_plan,first_dp_feasible_seconds
        generated+=1
        if rank(child)!=rank(parent)+1 or when<=best_time[parent]:raise AssertionError('Positive adjacent-rank event required')
        if when>=best_time.get(child,float('inf')):return
        best_time[child]=when;parents[child]=(parent,action);updates+=1
        if child[0]==2:
            if first_dp_feasible_seconds is None:first_dp_feasible_seconds=time.perf_counter()-started
            if canonical_goal_time is None or when<canonical_goal_time:canonical_goal,canonical_goal_time=child,when
            if when<best:
                plan=path(child);best,best_plan=when,plan
                trace.append(dict(seconds=time.perf_counter()-started,H2=best,plan=list(plan),
                    expansion_index=expanded+1,expansions_completed=expanded))
        else:buckets[rank(child)].add(child)
    try:
        for level in range(m+3):
            budget.check()
            for key in sorted(buckets[level]):
                budget.check();partial=True
                phase,mask,delivered,pos=key;now=best_time[key]
                if rank(key)!=level:raise AssertionError('Bad rank')
                for i,item in enumerate(spec['old']):
                    bit=1<<i
                    if mask&bit:
                        done=net.arrive(pos,item['node'],now)+item['service']
                        offer(key,(phase,mask^bit,delivered,item['node']),done,f'old:{i}')
                load=weights[mask]
                if phase==0 and load+spec['wa']<=spec['Q']:
                    done=max(net.arrive(pos,spec['hub'],now),spec['A'])+spec['tau_a']
                    offer(key,(1,mask,False,spec['hub']),done,'handoff:a')
                if phase==1 and not delivered:
                    done=net.arrive(pos,spec['a_node'],now)+spec['a_service']
                    offer(key,(1,mask,True,spec['a_node']),done,'deliver:a')
                if phase==1 and delivered and load+spec['wb']<=spec['Q']:
                    done=net.arrive(pos,spec['hub'],now)+spec['tau_b']
                    offer(key,(2,mask,True,spec['hub']),done,'handoff:b')
                expanded+=1
                if phase==0:phase0+=1
                elif phase==1:phase1+=1
                else:raise AssertionError('Do not expand terminal labels')
                partial=False
        budget.check()
        if canonical_goal_time is None or canonical_goal_time!=best:raise AssertionError('Completed DP optimum/common incumbent mismatch')
        complete=True;reason='all_structural_labels_completed'
    except SoftStop as exc:
        reason=str(exc);partial_expansion=int(partial)
    # No rank-derived or incomplete-frontier certificate. t0 is always valid.
    lower=best if complete else spec['t0'];gap=best-lower
    stats=net.stats()
    stats.update(detailed_profile_enabled=False,structural_labels=len(best_time),accepted_updates=updates,
        partial_expansions=partial_expansion,proposed_bound_used=False,incumbent_pruning_used=False,
        common_initial_rule='all_old_min_completion_then_a_then_b',closure_cache_size=len(net.cache))
    elapsed=time.perf_counter()-started
    return dict(method='DP_ADAPTER',arm='TOPOLOGICAL_DP',bound_basis='none',H2=best,plan=list(best_plan),trace=trace,
        expanded=expanded,expanded_phase0=phase0,expanded_phase1=phase1,generated=generated,
        partial_expansions=partial_expansion,remaining_bound=lower,certified_gap=gap,certified_optimal=complete,
        elapsed_seconds=elapsed,setup_seconds=setup_end-started,initial_seconds=initial_end-setup_end,
        search_seconds=started+elapsed-initial_end,root_bound_seconds=0.0,root_bound=None,
        initialization_overrun=initial_overrun,wall_budget_ms=wall_ms,stop_reason=reason,
        overrun_seconds=0 if wall_ms is None else max(0,elapsed-wall_ms/1000),timing_interpretable=True,
        first_dp_feasible_seconds=first_dp_feasible_seconds,stats=stats,
        certificate_scope='Exact after complete DP only; otherwise state-clock lower bound',
        soft_interrupt_policy='Between closures/labels or during Dijkstra, after fully timed common initializer')
