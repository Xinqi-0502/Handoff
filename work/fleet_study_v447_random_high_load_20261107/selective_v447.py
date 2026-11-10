#!/usr/bin/env python3
"""V447 random high-load scale copy of frozen V446.
Parent solver SHA256 96874E0994D5F736AA40FAEA94EED72D8D4D4E4C9EB6BC9263F6EB37DECBE539.
Only the local reference validation cap changes from m<=6 to m<=12.
Import/hash/version metadata change accordingly. Bounds, queue policies,
initialization, caches, dominance, node accounting and formulas are unchanged.
A common root_bound_seconds timer records existing work for every arm; it is
nested in search/total elapsed and does not change the budget or search policy.
No scaling correctness or performance is implied by this source preparation.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import gzip
import hashlib
import heapq
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REFERENCE = HERE/"reference_v447.py"
REFERENCE_SHA256 = "9810d96023a7710329d34a42f5c831687ea73e09fbfb42968fe4c660366a7416"
if hashlib.sha256(REFERENCE.read_bytes()).hexdigest() != REFERENCE_SHA256:
    raise RuntimeError("Frozen local V447 reference source hash changed.")
_spec = importlib.util.spec_from_file_location("v447_frozen_reference", REFERENCE)
ref = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ref
_spec.loader.exec_module(ref)

State, Edge, Watchdog = ref.State, ref.Edge, ref.Watchdog
INF = float("inf")
ARMS = ("NO_BOUND","ROUTE","PAIR_EAGER","LAZY_ASTAR","FULL_GATE","CUTOFF","GATED_CUTOFF",
        "AWA_ROUTE","AWA_PAIR","AWA_GATED")
AWA_ARMS = ("AWA_ROUTE","AWA_PAIR","AWA_GATED")
AWA_WEIGHT = 2
NODE_CHECKPOINTS = (10,25,50,100,250)
GATE_ARMS = ("FULL_GATE", "CUTOFF", "GATED_CUTOFF")
NEW_SEEDS = tuple(range(444101, 444117))
SOURCE_VERSION = "v447-random-high-load-validation12-1"
LAZY_ASTAR_SOURCE = "https://tzin.bgu.ac.il/~felner/2013/lazya.pdf"


class Network:
    """Same FIFO edge rule and Dijkstra as V443; detailed counters are optional."""
    def __init__(self, spec, watchdog, profile=False):
        self.n = spec["n_nodes"]
        self.adj = [[] for _ in range(self.n)]
        for u, v, travel, period, green, offset in spec["edges"]:
            if travel < 0 or period < 0 or (period and not 1 <= green <= period):
                raise ValueError("Invalid nonnegative FIFO edge.")
            self.adj[u].append(Edge(v, travel, period, green, offset))
        self.watchdog, self.profile = watchdog, profile
        self.cache = {}
        self.queries = self.hits = self.runs = self.relaxed = 0

    def arrive(self, src, dest, t):
        self.watchdog.check()
        if self.profile:
            self.queries += 1
        key = src, dest, t
        if key in self.cache:
            if self.profile:
                self.hits += 1
            return self.cache[key]
        if src == dest:
            self.cache[key] = t
            return t
        if self.profile:
            self.runs += 1
        best = [INF]*self.n
        best[src] = t
        heap = [(t, src)]
        while heap:
            at, u = heapq.heappop(heap)
            if at != best[u]:
                continue
            if u == dest:
                self.cache[key] = at
                return at
            for edge in self.adj[u]:
                if self.profile:
                    self.relaxed += 1
                nxt = edge.arrive(at)
                if nxt < best[edge.dest]:
                    best[edge.dest] = nxt
                    heapq.heappush(heap, (nxt, edge.dest))
        raise ValueError("Required locations are disconnected.")


@dataclass(frozen=True, slots=True)
class Base:
    value: int
    B: int
    qa: int
    qb: int
    gb: int


@dataclass(slots=True)
class Label:
    state: State
    plan: tuple
    base: Base | None
    value: int
    serial: int
    ready: bool


class Context:
    """No global bound/detail/via/quota-table caches; scalar shared caches retained."""
    def __init__(self, spec, watchdog, profile=False):
        ref.validate_instance(spec)
        self.spec, self.watchdog, self.profile = spec, watchdog, profile
        self.old, self.m = spec["old"], len(spec["old"])
        self.h, self.a = spec["hub"], spec["a_node"]
        self.net = Network(spec, watchdog, profile)
        self.weights = [0]*(1 << self.m)
        for mask in range(1, 1 << self.m):
            bit = mask & -mask
            self.weights[mask] = self.weights[mask ^ bit] + self.old[bit.bit_length()-1]["weight"]
        self.fa_cache, self.gamma_cache = {}, {}
        self.base_calls = self.full_calls = self.cutoff_calls = self.gate_calls = 0
        self.exact_quota_skips = self.alpha_skips = self.urel_skips = 0
        self.lazy_generation_bypasses = self.lazy_pop_bypasses = 0
        self.lazy_reinsertions = 0
        self.base_ns = self.pair_ns = self.quota_ns = 0
        self.quota_labels = self.via_items = self.fa_queries = self.fa_hits = 0
        self.gamma_queries = self.gamma_hits = self.gamma_orders = self.events = 0
        self.phase1_calls = self.phase1_via_items = self.phase1_ns = 0

    # Feasible domain and initial incumbent reuse the exact frozen implementations.
    initial = ref.Context.initial
    children = ref.Context.children
    greedy = ref.Context.greedy

    def quota_pair(self, s, qa, qb):
        """One conventional local subset DP answers both quotas; table is released."""
        started = time.perf_counter_ns() if self.profile else 0
        direct = self.net.arrive(s.pos, self.h, s.t)
        if qb == 0:
            if self.profile:
                self.quota_ns += time.perf_counter_ns()-started
            return direct, direct
        labels = [{} for _ in range(1 << self.m)]
        labels[0][s.pos] = s.t
        ga = direct if qa == 0 else INF
        gb = INF
        for subset in range(1 << self.m):
            if subset & ~s.oldmask or not labels[subset]:
                continue
            self.watchdog.check()
            returned = min(self.net.arrive(last, self.h, at)
                           for last, at in labels[subset].items())
            if self.weights[subset] >= qa:
                ga = min(ga, returned)
            if self.weights[subset] >= qb:
                gb = min(gb, returned)
            for last, at in list(labels[subset].items()):
                if self.profile:
                    self.quota_labels += 1
                for i in ref.bit_ids(s.oldmask & ~subset):
                    item = self.old[i]
                    done = self.net.arrive(last, item["node"], at) + item["service"]
                    newmask = subset | (1 << i)
                    if done < labels[newmask].get(item["node"], INF):
                        labels[newmask][item["node"]] = done
        if self.profile:
            self.quota_ns += time.perf_counter_ns()-started
        return ga, gb

    def fa(self, x):
        if self.profile:
            self.fa_queries += 1
        if x in self.fa_cache:
            if self.profile:
                self.fa_hits += 1
            return self.fa_cache[x]
        at = self.net.arrive(self.h, self.a, x) + self.spec["a_service"]
        value = self.net.arrive(self.a, self.h, at)
        self.fa_cache[x] = value
        return value

    def gamma_order(self, i, x, a_first):
        if self.profile:
            self.gamma_orders += 1
        item = self.old[i]
        if a_first:
            at = self.net.arrive(self.h, self.a, x) + self.spec["a_service"]
            at = self.net.arrive(self.a, item["node"], at) + item["service"]
            return self.net.arrive(item["node"], self.h, at)
        at = self.net.arrive(self.h, item["node"], x) + item["service"]
        at = self.net.arrive(item["node"], self.a, at) + self.spec["a_service"]
        return self.net.arrive(self.a, self.h, at)

    def gamma(self, i, x):
        if self.profile:
            self.gamma_queries += 1
        key = i, x
        if key in self.gamma_cache:
            if self.profile:
                self.gamma_hits += 1
            return self.gamma_cache[key]
        value = min(self.gamma_order(i, x, True), self.gamma_order(i, x, False))
        self.gamma_cache[key] = value
        return value

    def gamma_at_most(self, i, x, deadline):
        """Exact Boolean test; a successful first order need not evaluate the other."""
        if self.profile:
            self.gamma_queries += 1
        key = i, x
        if key in self.gamma_cache:
            if self.profile:
                self.gamma_hits += 1
            return self.gamma_cache[key] <= deadline
        first = self.gamma_order(i, x, True)
        if first <= deadline:
            # Do NOT store first as exact min: the uncomputed order can be earlier.
            return True
        second = self.gamma_order(i, x, False)
        value = min(first, second)
        self.gamma_cache[key] = value
        return value <= deadline

    def continuation(self, s):
        """Common phase-1 bound: mandatory a/direct return plus radius quota."""
        self.phase1_calls += 1
        started = time.perf_counter_ns() if self.profile else 0
        direct = self.net.arrive(s.pos, self.h, s.t)
        if s.a_delivered:
            mandatory = direct
        else:
            at = self.net.arrive(s.pos, self.a, s.t) + self.spec["a_service"]
            mandatory = self.net.arrive(self.a, self.h, at)
        quota = max(0, self.weights[s.oldmask] + self.spec["wb"] - self.spec["Q"])
        radius = direct
        if quota:
            values = []
            for i in ref.bit_ids(s.oldmask):
                if self.profile:
                    self.phase1_via_items += 1
                item = self.old[i]
                at = self.net.arrive(s.pos, item["node"], s.t) + item["service"]
                returned = self.net.arrive(item["node"], self.h, at)
                values.append((returned, item["weight"]))
            radius = ref.threshold(values, quota, direct)
        value = max(mandatory, radius) + self.spec["tau_b"]
        if self.profile:
            self.phase1_ns += time.perf_counter_ns()-started
        return value

    def base(self, s):
        if s.phase == 1:
            # Only value has meaning in phase 1; pair formulas are phase-0 only.
            return Base(self.continuation(s), 0, 0, 0, 0)
        if s.phase != 0:
            return None
        self.base_calls += 1
        started = time.perf_counter_ns() if self.profile else 0
        load = self.weights[s.oldmask]
        qa = max(0, load + self.spec["wa"] - self.spec["Q"])
        qb = max(0, load + self.spec["wb"] - self.spec["Q"])
        ga, gb = self.quota_pair(s, qa, qb)
        B = max(self.spec["A"], ga) + self.spec["tau_a"]
        value = max(self.fa(B), max(self.spec["A"], gb)) + self.spec["tau_b"]
        if self.profile:
            self.base_ns += time.perf_counter_ns()-started
        return Base(value, B, qa, qb, gb)

    def alphas(self, s):
        values = []
        for i in ref.bit_ids(s.oldmask):
            if self.profile:
                self.via_items += 1
            item = self.old[i]
            at = self.net.arrive(s.pos, item["node"], s.t) + item["service"]
            returned = self.net.arrive(item["node"], self.h, at)
            values.append((i, returned + self.spec["tau_a"]))
        return values

    def full(self, s, base):
        if base is None:
            return s.t
        if s.phase != 0:
            return base.value
        self.full_calls += 1
        started = time.perf_counter_ns() if self.profile else 0
        try:
            if base.gb + self.spec["tau_a"] <= base.B:
                self.exact_quota_skips += 1
                return base.value
            alpha = self.alphas(s)
            if sum(self.old[i]["weight"] for i, a in alpha if a <= base.B) >= base.qb:
                self.alpha_skips += 1
                return base.value
            best_raw = INF
            for x in sorted({base.B} | {a for _, a in alpha if a >= base.B}):
                if self.profile:
                    self.events += 1
                early = sum(self.old[i]["weight"] for i, a in alpha if a <= x)
                if early < base.qa:
                    continue
                qrem = max(0, base.qb-early)
                if qrem:
                    values = [(self.gamma(i, x), self.old[i]["weight"])
                              for i, a in alpha if a > x]
                    v = ref.threshold(values, qrem, x)
                else:
                    v = x
                best_raw = min(best_raw, max(self.fa(x), v)+self.spec["tau_b"])
            return max(base.value, best_raw)
        finally:
            if self.profile:
                self.pair_ns += time.perf_counter_ns()-started

    def relaxation_upper(self, base, alpha):
        # alpha is individual-via + tau_a, so this threshold equals R_b + tau_a.
        acap = ref.threshold([(a, self.old[i]["weight"]) for i, a in alpha],
                             base.qb, base.B)
        xcap = max(base.B, acap)
        return self.fa(xcap) + self.spec["tau_b"]

    def cutoff(self, s, base, U, gated=False):
        """True iff the full numerical UNION bound is >= integer incumbent U."""
        if base is None:
            return s.t >= U
        if base.value >= U:
            return True
        if s.phase != 0:
            return False
        self.cutoff_calls += 1
        started = time.perf_counter_ns() if self.profile else 0
        try:
            if base.gb + self.spec["tau_a"] <= base.B:
                self.exact_quota_skips += 1
                return False
            alpha = self.alphas(s)
            early_B = sum(self.old[i]["weight"] for i, a in alpha if a <= base.B)
            if early_B >= base.qb:
                self.alpha_skips += 1
                return False
            if gated:
                self.gate_calls += 1
                if self.relaxation_upper(base, alpha) < U:
                    self.urel_skips += 1
                    return False
            D = U - self.spec["tau_b"] - 1
            for x in sorted({base.B} | {a for _, a in alpha if a >= base.B}):
                if self.profile:
                    self.events += 1
                if self.fa(x) > D:
                    break  # All later x also fail this mandatory-a test by FIFO.
                released = sum(self.old[i]["weight"] for i, a in alpha if a <= x)
                if released < base.qa:
                    continue
                if released >= base.qb:
                    return False
                # Fixed item-id order; no Gamma sorting or oracle-informed ordering.
                for i, a in alpha:
                    if a <= x:
                        continue
                    if self.gamma_at_most(i, x, D):
                        released += self.old[i]["weight"]
                        if released >= base.qb:
                            return False
            return True
        finally:
            if self.profile:
                self.pair_ns += time.perf_counter_ns()-started

    def stats(self):
        basic = dict(base_calls=self.base_calls, phase1_base_calls=self.phase1_calls,
                     full_calls=self.full_calls,
                     cutoff_calls=self.cutoff_calls, gate_calls=self.gate_calls,
                     skip_exact_quota=self.exact_quota_skips, skip_alpha_union=self.alpha_skips,
                     skip_urel=self.urel_skips, lazy_generation_bypasses=self.lazy_generation_bypasses,
                     lazy_pop_bypasses=self.lazy_pop_bypasses, lazy_reinsertions=self.lazy_reinsertions,
                     closure_cache_size=len(self.net.cache), fa_cache_size=len(self.fa_cache),
                     gamma_cache_size=len(self.gamma_cache), bound_cache_size=0,
                     global_quota_cache_size=0, global_via_cache_size=0,
                     detailed_profile_enabled=self.profile)
        if self.profile:
            basic.update(base_ns=self.base_ns, phase1_base_ns=self.phase1_ns,
                         phase1_individual_via_items=self.phase1_via_items,
                         pair_ns=self.pair_ns, quota_ns=self.quota_ns,
                         quota_dp_labels=self.quota_labels, individual_via_items=self.via_items,
                         fa_queries=self.fa_queries, fa_hits=self.fa_hits,
                         gamma_queries=self.gamma_queries, gamma_hits=self.gamma_hits,
                         gamma_orders=self.gamma_orders, events=self.events,
                         closure_queries=self.net.queries, closure_hits=self.net.hits,
                         dijkstra_runs=self.net.runs, edges_relaxed=self.net.relaxed)
        return basic


def queue_priority(arm, state, lower_bound, t0):
    """AWA*: g=t-t0, h=absolute admissible bound-t; never a pruning bound."""
    if arm in AWA_ARMS:
        if lower_bound < state.t:
            raise AssertionError("AWA* requires a nonnegative remaining-time heuristic.")
        return (state.t-t0) + AWA_WEIGHT*(lower_bound-state.t)
    return lower_bound


def solve(spec, arm, watchdog, wall_ms=None, profile=False, audit=False,
          _context_factory=None, node_limit=None, checkpoints=NODE_CHECKPOINTS):
    if arm not in ARMS:
        raise ValueError(arm)
    if node_limit is not None and (not isinstance(node_limit,int) or node_limit < 0):
        raise ValueError("node_limit must be a nonnegative integer or None.")
    if any(not isinstance(n,int) or n < 0 for n in checkpoints):
        raise ValueError("Checkpoint node counts must be nonnegative integers.")
    emit_node_trace = bool(checkpoints)
    checkpoint_set = set(checkpoints)
    checkpoint_set.discard(0)  # Initial record is emitted only when checkpoints are enabled.
    started = time.perf_counter()
    factory = Context if _context_factory is None else _context_factory
    ctx = factory(spec, watchdog, profile)
    setup = time.perf_counter()-started
    initial_started = time.perf_counter()
    best, best_plan = ctx.greedy()
    initial_seconds = time.perf_counter()-initial_started
    trace = [dict(seconds=time.perf_counter()-started,H2=best,plan=list(best_plan),
                  expansion_index=0,expansions_completed=0)]
    audit_trace = [] if audit else None
    count = dict(expanded=0, expanded_phase0=0, expanded_phase1=0,
                 generated=0, terminal_generated=0, pruned=0,
                 joint_checks_at_pop=0, joint_pruned_at_pop=0,
                 dominated=0, stale_pops=0, queued=0, peak_frontier=0)
    deadline = None if wall_ms is None else started+wall_ms/1000
    initial_overrun = deadline is not None and time.perf_counter() >= deadline
    initial_node_stop = node_limit == 0
    heap, best_time = [], {}
    serial = 0
    start_t = spec.get("t0",0)  # The existing standalone policy toy starts at zero.
    stop = ("initialization_budget" if initial_overrun else
            "node_budget_initial" if initial_node_stop else "exhausted")
    root_bound = root_priority = None
    root_bound_seconds = 0.0  # Nested in search/total; zero if root evaluation is skipped.
    node_trace = []

    def record_node_checkpoint(initial=False, final=False):
        # Read-only frontier inspection: do not pop stale/prunable labels here.
        live_bounds = [lab.value for _,_,lab in heap
                       if best_time.get(lab.state.key) == lab.state.t]
        lb = None if initial else min([best]+live_bounds)
        row = dict(expanded=count["expanded"],H2=best,plan=list(best_plan),
                   remaining_bound=lb,certified_gap=None if lb is None else best-lb,
                   certified_optimal=(lb == best),frontier_stored=len(heap),
                   frontier_live=len(live_bounds),
                   generated=count["generated"],pruned=count["pruned"],
                   dominated=count["dominated"],stale_pops=count["stale_pops"],
                   counts=dict(count),
                   reason="initial_incumbent" if initial else
                          "search_exhausted" if final else "complete_expansion")
        if profile:
            row["stats"] = ctx.stats()
        row["seconds"] = time.perf_counter()-started
        node_trace.append(row)

    if emit_node_trace:
        record_node_checkpoint(initial=True)

    def clean_open():
        while heap and best_time.get(heap[0][2].state.key) != heap[0][2].state.t:
            heapq.heappop(heap)
            count["stale_pops"] += 1

    def open_key():
        clean_open()
        return (heap[0][0],heap[0][1]) if heap else (INF,INF)

    if not initial_overrun and not initial_node_stop:
        s = ctx.initial()
        root_bound_started = time.perf_counter()
        base = None if arm == "NO_BOUND" else ctx.base(s)
        value = s.t if base is None else base.value
        ready = arm != "LAZY_ASTAR" or s.phase != 0
        if (arm in ("PAIR_EAGER","LAZY_ASTAR","AWA_PAIR") and
                s.phase == 0 and value < best):
            value = ctx.full(s,base)
            ready = True
        root_bound_seconds = time.perf_counter()-root_bound_started
        root_bound = value
        root_priority = queue_priority(arm,s,value,start_t)
        best_time[s.key] = s.t
        if value < best:  # Always compare the unweighted absolute lower bound.
            label = Label(s,(),base,value,serial,ready)
            heapq.heappush(heap,(root_priority,serial,label))
            count["queued"] = count["peak_frontier"] = 1
        else:
            count["pruned"] += 1
        while heap:
            watchdog.check()
            # No free prune/stale/lazy scan is allowed after the Nth expansion.
            if node_limit is not None and count["expanded"] >= node_limit:
                stop = "node_budget"
                break
            if deadline is not None and time.perf_counter() >= deadline:
                stop = "wall_budget"
                break
            clean_open()
            if not heap:
                break
            _,_,label = heapq.heappop(heap)
            s,plan,base = label.state,label.plan,label.base
            value = label.value
            if value >= best:
                count["pruned"] += 1
                continue
            if arm == "LAZY_ASTAR" and not label.ready:
                # Delayed h2 must not discard a stronger inherited Pathmax floor.
                value = max(value, ctx.full(s,base))
                label.value,label.ready = value,True
                if value >= best:
                    count["pruned"] += 1
                    continue
                key = queue_priority(arm,s,value,start_t)
                if (key,label.serial) > open_key():
                    heapq.heappush(heap,(key,label.serial,label))
                    ctx.lazy_reinsertions += 1
                    continue
                ctx.lazy_pop_bypasses += 1
            elif arm == "FULL_GATE" and base is not None and s.phase == 0:
                count["joint_checks_at_pop"] += 1
                if ctx.full(s,base) >= best:
                    count["joint_pruned_at_pop"] += 1
                    count["pruned"] += 1
                    continue
            elif (arm in ("CUTOFF","GATED_CUTOFF","AWA_GATED") and
                  base is not None and s.phase == 0):
                count["joint_checks_at_pop"] += 1
                if ctx.cutoff(s,base,best,arm in ("GATED_CUTOFF","AWA_GATED")):
                    count["joint_pruned_at_pop"] += 1
                    count["pruned"] += 1
                    continue
            # The count denotes this complete successor-generation operation.
            # Reopened labels count again. Bound-only/stale/pruned pops do not.
            count["expanded"] += 1
            count["expanded_phase0" if s.phase == 0 else "expanded_phase1"] += 1
            if audit:
                audit_trace.append([s.phase,s.oldmask,s.a_delivered,s.pos,s.t,list(plan)])
            for child,action in ctx.children(s):
                count["generated"] += 1
                child_plan = plan+(action,)
                if child.phase == 2:
                    count["terminal_generated"] += 1
                    if child.t < best:
                        best,best_plan = child.t,child_plan
                        trace.append(dict(seconds=time.perf_counter()-started,
                            H2=best,plan=list(best_plan),expansion_index=count["expanded"],
                            expansions_completed=count["expanded"]-1))
                    continue
                if child.t >= best_time.get(child.key,INF):
                    count["dominated"] += 1
                    continue
                best_time[child.key] = child.t
                child_base = None if arm == "NO_BOUND" else ctx.base(child)
                child_value = child.t if child_base is None else child_base.value
                if arm != "NO_BOUND":
                    # Absolute unweighted parent LB, never weighted key/U_rel.
                    # Gate arms retain the ROUTE channel even after a full test.
                    child_value = max(child_value, label.value)
                if child_value >= best:
                    count["pruned"] += 1
                    continue
                serial += 1
                child_ready = arm != "LAZY_ASTAR" or child.phase != 0
                if arm in ("PAIR_EAGER","AWA_PAIR") and child.phase == 0:
                    child_value = max(child_value, ctx.full(child,child_base))
                elif arm == "LAZY_ASTAR" and not child_ready:
                    child_key = queue_priority(arm,child,child_value,start_t)
                    if (child_key,serial) <= open_key():
                        child_value = max(child_value, ctx.full(child,child_base))
                        child_ready = True
                        ctx.lazy_generation_bypasses += 1
                if child_value >= best:
                    count["pruned"] += 1
                    continue
                child_label = Label(child,child_plan,child_base,child_value,serial,child_ready)
                child_key = queue_priority(arm,child,child_value,start_t)
                heapq.heappush(heap,(child_key,serial,child_label))
                count["queued"] += 1
            count["peak_frontier"] = max(count["peak_frontier"],len(heap))
            if count["expanded"] in checkpoint_set:
                record_node_checkpoint()
    if emit_node_trace and stop == "exhausted":
        record_node_checkpoint(final=True)
    # A weighted queue's best key is not a lower-bound certificate.
    live = [lab.value for _,_,lab in heap if best_time.get(lab.state.key) == lab.state.t]
    remaining = None if initial_overrun or initial_node_stop else min([best]+live)
    gap = None if remaining is None else best-remaining
    stats = ctx.stats()
    elapsed = time.perf_counter()-started
    return dict(case=spec["case"],seed=spec["seed"],split=spec["split"],arm=arm,
                H2=best,plan=list(best_plan),trace=trace,audit_trace=audit_trace,
                node_trace=node_trace,node_limit=node_limit,
                requested_checkpoints=sorted(checkpoint_set),
                wall_budget_ms=wall_ms,elapsed_seconds=elapsed,setup_seconds=setup,
                initial_seconds=initial_seconds,search_seconds=max(0,elapsed-setup-initial_seconds),
                initialization_overrun=initial_overrun,initial_node_stop=initial_node_stop,
                root_bound=root_bound,root_priority=root_priority,
                root_bound_seconds=root_bound_seconds,
                remaining_bound=remaining,certified_gap=gap,certified_optimal=(gap == 0),
                stop_reason=stop,overrun_seconds=0 if wall_ms is None else max(0,elapsed-wall_ms/1000),
                timing_interpretable=not profile,stats=stats,**count)



def get_cases(split):
    if split == "dev":
        return [dict(s, v443_split=s["split"], split="dev") for s in ref.cases("all")]
    return [ref.random_case(seed, "holdout", i+17) for i, seed in enumerate(NEW_SEEDS)]


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_closure(spec, watchdog):
    actual = Network(spec, watchdog, False)
    n, comparisons = spec["n_nodes"], 0
    for source in range(n):
        for departure in sorted(set(range(48)) | {spec["t0"], spec["A"]}):
            watchdog.check()
            best = [INF]*n
            best[source] = departure
            for _ in range(n-1):
                updated = best.copy()
                for u,v,travel,period,green,offset in spec["edges"]:
                    if best[u] == INF:
                        continue
                    start, wait = best[u], 0
                    if period:
                        phase = (start-offset) % period
                        if phase >= green:
                            wait = period-phase
                    arrival = start+wait+travel
                    if arrival < updated[v]:
                        updated[v] = arrival
                if updated == best:
                    break
                best = updated
            for destination in range(n):
                if actual.arrive(source,destination,departure) != best[destination]:
                    raise AssertionError(("closure",spec["case"],source,destination,departure))
                comparisons += 1
    return comparisons



def reference_phase1_bound(ctx, s):
    """Independent expression using frozen reference data and closure, no new Context."""
    spec = ctx.spec
    direct = ctx.net.arrive(s.pos, spec["hub"], s.t)
    mandatory = direct
    if not s.a_delivered:
        at_a = ctx.net.arrive(s.pos, spec["a_node"], s.t) + spec["a_service"]
        mandatory = ctx.net.arrive(spec["a_node"], spec["hub"], at_a)
    remaining = [ctx.old[i] for i in ref.bit_ids(s.oldmask)]
    quota = max(0, sum(o["weight"] for o in remaining) + spec["wb"] - spec["Q"])
    radius = direct
    if quota:
        visits = []
        for item in remaining:
            done = ctx.net.arrive(s.pos, item["node"], s.t) + item["service"]
            visits.append((ctx.net.arrive(item["node"], spec["hub"], done), item["weight"]))
        released = 0
        for returned, weight in sorted(visits):
            released += weight
            if released >= quota:
                radius = returned
                break
        else:
            raise AssertionError("Phase-1 quota exceeds remaining old load.")
    return max(mandatory, radius) + spec["tau_b"]


def reference_local_bound(ctx, s, arm):
    if s.phase == 1:
        return reference_phase1_bound(ctx, s)
    return ctx.bound(s, arm)[0]


def reference_lazy_policy(spec,watchdog):
    """Literal Algorithm-1 policy, no OPEN bypass; common phase 1 and Pathmax."""
    ctx = ref.Context(spec,watchdog)
    best,best_plan = ctx.greedy()
    improvements = [(best,list(best_plan))]
    root = ctx.initial()
    root_value = reference_local_bound(ctx, root, "PAIR_UNION")
    heap = [(root_value,0,True,root,())] if root_value < best else []
    best_time = {root.key:root.t}
    serial,reinsertions = 0,0
    expansions = []
    while heap:
        watchdog.check()
        value,birth,ready,s,plan = heapq.heappop(heap)
        if best_time.get(s.key) != s.t or value >= best:
            continue
        if not ready:
            full = max(value, reference_local_bound(ctx, s, "PAIR_UNION"))
            if full < best:
                heapq.heappush(heap,(full,birth,True,s,plan))
                reinsertions += 1
            continue
        expansions.append([s.phase,s.oldmask,s.a_delivered,s.pos,s.t,list(plan)])
        for child,action in ctx.children(s):
            cp = plan+(action,)
            if child.phase == 2:
                if child.t < best:
                    best,best_plan = child.t,cp
                    improvements.append((best,list(best_plan)))
                continue
            if child.t >= best_time.get(child.key,INF):
                continue
            best_time[child.key] = child.t
            cheap = max(value, reference_local_bound(ctx, child, "ROUTE_PRECEDENCE"))
            if cheap >= best:
                continue
            serial += 1
            heapq.heappush(heap,(cheap,serial,child.phase != 0,child,cp))
    return dict(H2=best,plan=list(best_plan),audit_trace=expansions,
                improvements=improvements,reinsertions=reinsertions)


def verify_lazy_toy(watchdog):
    """Hand-specified independent policy fixture, including inconsistent h2/reopen."""
    class ToyContext:
        def __init__(self,spec,watchdog,profile):
            self.spec=spec
            self.lazy_generation_bypasses=self.lazy_pop_bypasses=self.lazy_reinsertions=0
        def initial(self):
            return State(0,0,False,0,0)
        def greedy(self):
            return 100,("feasible_upper_bound_100",)
        def base(self,s):
            f1 = {0:0,1:4,2:6,3:7}.get(s.pos,s.t)
            return Base(f1,0,0,0,0)
        def full(self,s,base):
            return {0:0,1:4,2:10,3:8}.get(s.pos,s.t)
        def children(self,s):
            edges={0:((1,1),(2,2),(3,2),(4,10)),1:((4,4),),
                   2:((5,20),),3:((4,1),),4:((5,10),)}
            for dest,travel in edges.get(s.pos,()):
                yield State(2 if dest==5 else 0,0,False,dest,s.t+travel),str(dest)
        def stats(self):
            return dict(lazy_generation_bypasses=self.lazy_generation_bypasses,
                        lazy_pop_bypasses=self.lazy_pop_bypasses,
                        lazy_reinsertions=self.lazy_reinsertions)
    spec=dict(case="lazy_policy_toy",seed=None,split="dev")
    row=solve(spec,"LAZY_ASTAR",watchdog,audit=True,_context_factory=ToyContext)
    expanded=[(s[3],s[4]) for s in row["audit_trace"]]
    expected=[(0,0),(1,1),(4,5),(3,2),(4,3),(2,2)]
    targets=[x["H2"] for x in row["trace"]]
    if expanded!=expected or targets!=[100,15,13] or row["H2"]!=13:
        raise AssertionError(("independent_lazy_toy",row,expected))
    if (row["stats"]["lazy_reinsertions"]!=1 or
        row["stats"]["lazy_pop_bypasses"]!=1 or
        row["stats"]["lazy_generation_bypasses"]!=3 or row["stale_pops"]!=1):
        raise AssertionError(("lazy_toy_policy_counts",row))
    return dict(status="PASS",expanded=expanded,incumbents=targets,
                counts=row["stats"],stale_pops=row["stale_pops"],
                scope="hand-specified small graph, not a delivery benchmark")


def verify_pathmax_edges(ctx, oracle, local_bounds, watchdog):
    """Check unweighted inheritance over each independently enumerated valid edge.

    Local bounds were already checked against the exact suffix optimum. A
    parent's exact optimum cannot exceed any child's exact optimum. Induction
    therefore keeps any admissible ancestor floor valid along the actual path.
    """
    edges = combinations = 0
    for parent, parent_true in list(oracle.memo.items()):
        if parent.phase == 2:
            continue
        for child, action in ctx.children(parent):
            watchdog.check()
            if child not in oracle.memo or child not in local_bounds:
                raise AssertionError(("edge outside independent oracle", parent, child, action))
            true = child.t if child.phase == 2 else oracle.memo[child]
            if not parent.t < child.t or not parent_true <= true:
                raise AssertionError(("event/oracle edge monotonicity", parent, child))
            for parent_bound in local_bounds[parent]:
                if not parent.t <= parent_bound <= true:
                    raise AssertionError(("parent lower bound invalid for child", parent, child))
                for child_bound in local_bounds[child]:
                    inherited = max(parent_bound, child_bound)
                    if not child.t <= child_bound <= inherited <= true:
                        raise AssertionError(("Pathmax edge inadmissible", parent, child,
                                              parent_bound, child_bound, inherited, true))
                    combinations += 1
            edges += 1
    return edges, combinations


def run_correctness(specs, run, watchdog):
    total_states = cutoff_checks = closure_checks = phase0 = phase1 = 0
    pathmax_edges = pathmax_combinations = 0
    summaries = []
    ref.write_json(run/"LAZY_POLICY_TOY.json",verify_lazy_toy(watchdog))
    with gzip.open(run/"PREFIX_CHECKS.jsonl.gz","wt",encoding="utf-8") as prefixes, \
            (run/"SOLVES.jsonl").open("w",encoding="utf-8") as out, \
            (run/"LAZY_POLICY_CHECKS.jsonl").open("w",encoding="utf-8") as lazy_out:
        for spec in specs:
            watchdog.check(True)
            closure_checks += independent_closure(spec,watchdog)
            oracle = ref.ReferenceOracle(spec,watchdog)
            optimum = oracle.suffix(oracle.initial())
            ctx = Context(spec,watchdog,False)
            old_ctx = ref.Context(spec,watchdog)
            local_bounds = {}
            for s, true in list(oracle.memo.items()):
                total_states += 1
                local_bounds[s] = (s.t, s.t)
                if s.phase != 0:
                    if s.phase == 1:
                        phase1 += 1
                        continuation = ctx.base(s)
                        local_bounds[s] = (continuation.value, continuation.value)
                        independent = reference_phase1_bound(old_ctx, s)
                        if not s.t <= continuation.value == independent <= true:
                            raise AssertionError(("phase1 admissibility",spec["case"],s,
                                                  continuation.value,independent,true))
                        if ctx.full(s,continuation) != continuation.value:
                            raise AssertionError("Phase-1 numeric arms must share one local bound.")
                        for U in (continuation.value-1,continuation.value,continuation.value+1):
                            for gated in (False,True):
                                if ctx.cutoff(s,continuation,U,gated) != (continuation.value >= U):
                                    raise AssertionError("Phase-1 Boolean equivalence failed.")
                        ref.write_jsonl(prefixes,dict(case=spec["case"],state=ref.asdict(s),
                            base=continuation.value,full=continuation.value,oracle=true,
                            independent_phase1=independent))
                    elif s.t > true:
                        raise AssertionError("Terminal bound inadmissible.")
                    continue
                phase0 += 1
                base = ctx.base(s)
                full = ctx.full(s,base)
                local_bounds[s] = (base.value, full)
                if base.value != old_ctx.bound(s,"ROUTE_PRECEDENCE")[0]:
                    raise AssertionError(("base equivalence",spec["case"],s))
                if full != old_ctx.bound(s,"PAIR_UNION")[0] or not base.value <= full <= true:
                    raise AssertionError(("full equivalence/admissibility",spec["case"],s,full,true))
                alpha = ctx.alphas(s)
                urel = ctx.relaxation_upper(base,alpha)
                if full > max(base.value,urel):
                    raise AssertionError(("relaxation upper",spec["case"],s))
                tested = sorted({max(0,v+d) for v in (s.t,base.value,full,true) for d in (-1,0,1)})
                for U in tested:
                    for gated in (False,True):
                        ctx.gamma_cache.clear()  # Exercise cold first-order Boolean shortcuts.
                        answer = ctx.cutoff(s,base,U,gated)
                        if answer != (full >= U):
                            raise AssertionError(("cutoff equivalence",spec["case"],s,U,gated,answer,full))
                        cutoff_checks += 1
                ref.write_jsonl(prefixes,dict(case=spec["case"],state=ref.asdict(s),
                    base=base.value,full=full,oracle=true,relaxation_upper=urel,tested_incumbents=tested))
            case_edges, case_combinations = verify_pathmax_edges(
                ctx, oracle, local_bounds, watchdog)
            pathmax_edges += case_edges
            pathmax_combinations += case_combinations
            gate_rows = {}
            for arm in ARMS:
                row = solve(spec,arm,watchdog,audit=True)
                if row["H2"] != optimum or not row["certified_optimal"]:
                    raise AssertionError(("solve optimum",row,optimum))
                if ref.replay_plan(spec,row["plan"],watchdog) != optimum:
                    raise AssertionError("Plan replay mismatch.")
                ref.decorate_target(row,optimum)
                if arm in GATE_ARMS:
                    gate_rows[arm] = row
                if arm == "LAZY_ASTAR":
                    literal = reference_lazy_policy(spec,watchdog)
                    actual_improvements = [(r["H2"],r["plan"]) for r in row["trace"]]
                    if (literal["audit_trace"] != row["audit_trace"] or
                        literal["plan"] != row["plan"] or
                        literal["improvements"] != actual_improvements):
                        ref.write_json(run/"LAZY_POLICY_COUNTEREXAMPLE.json",
                                       dict(case=spec["case"],literal=literal,actual=row))
                        raise AssertionError(("lazy_policy_equivalence",spec["case"]))
                    ref.write_jsonl(lazy_out,dict(case=spec["case"],status="PASS",
                        expanded=len(row["audit_trace"]),literal_reinsertions=literal["reinsertions"],
                        bypass_generation=row["stats"]["lazy_generation_bypasses"],
                        bypass_pop=row["stats"]["lazy_pop_bypasses"]))
                ref.write_jsonl(out,row)
            a = gate_rows["FULL_GATE"]
            for arm in GATE_ARMS[1:]:
                b = gate_rows[arm]
                if a["audit_trace"] != b["audit_trace"] or a["plan"] != b["plan"]:
                    raise AssertionError(("prune-policy expansion/plan trace",spec["case"],arm))
                ta = [(r["H2"],r["plan"]) for r in a["trace"]]
                tb = [(r["H2"],r["plan"]) for r in b["trace"]]
                if ta != tb:
                    raise AssertionError(("prune-policy incumbent trace",spec["case"],arm))
            # Detailed diagnostics must not change the selected method's search behavior.
            prof = solve(spec,"GATED_CUTOFF",watchdog,profile=True,audit=True)
            if prof["audit_trace"] != a["audit_trace"] or prof["H2"] != optimum:
                raise AssertionError("Profiling changes semantic trace.")
            summaries.append(dict(case=spec["case"],optimum_H2=optimum,
                                  reachable_states=len(oracle.memo),gate_trace_equivalent=True,
                                  pathmax_edges=case_edges,
                                  pathmax_channel_combination_checks=case_combinations))
            print(json.dumps(summaries[-1]),flush=True)
    watchdog.check(True)
    return dict(status="PASS",cases=summaries,case_count=len(specs),
                reachable_states=total_states,phase0_states=phase0,phase1_states=phase1,
                phase1_independent_admissibility_checks=phase1,
                pathmax_edges=pathmax_edges,
                pathmax_channel_combination_checks=pathmax_combinations,
                cutoff_equivalence_checks=cutoff_checks,closure_checks=closure_checks,
                exact_solver_checks=len(specs)*len(ARMS),gate_trace_checks=len(specs)*2,
                lazy_literal_policy_checks=len(specs),lazy_independent_toy="PASS")


def run_measurements(specs,run,watchdog,repeats,budgets,profile,allocations=False):
    targets = {}
    with (run/"ORACLES.jsonl").open("w",encoding="utf-8") as out:
        for spec in specs:
            watchdog.check(True)
            oracle = ref.ReferenceOracle(spec,watchdog)
            targets[spec["case"]] = oracle.suffix(oracle.initial())
            ref.write_jsonl(out,dict(case=spec["case"],H2=targets[spec["case"]],
                                     states=len(oracle.memo),outside_measured_solves=True))
    rows = 0
    with (run/"MEASUREMENTS.jsonl").open("w",encoding="utf-8") as out:
        for ci,spec in enumerate(specs):
            for repeat in range(repeats):
                rotation = (ci+repeat)%len(ARMS)
                order = list(ARMS[rotation:]+ARMS[:rotation])
                if repeat%2:
                    order.reverse()
                for budget in ([0.0] if profile or allocations else budgets):
                    for position,arm in enumerate(order):
                        watchdog.check(True)
                        if allocations:
                            import gc
                            import tracemalloc
                            gc.collect()
                            tracemalloc.start()
                            try:
                                row = solve(spec,arm,watchdog)
                                current,peak = tracemalloc.get_traced_memory()
                            finally:
                                tracemalloc.stop()
                            row.update(python_traced_current_bytes=current,
                                       python_traced_peak_bytes=peak,
                                       timing_interpretable=False,
                                       memory_scope="Python allocations only, not whole-process peak")
                        else:
                            row = solve(spec,arm,watchdog,None if budget==0 else budget,profile)
                        ref.decorate_target(row,targets[spec["case"]])
                        row.update(mode="allocations" if allocations else "profile" if profile else "timing",
                                   repeat=repeat,arm_position=position)
                        if ref.replay_plan(spec,row["plan"],watchdog) != row["H2"]:
                            raise AssertionError("Measured plan fails replay.")
                        if row["regret_ticks"] < 0 or (budget == 0 and
                                (row["regret_ticks"] or not row["certified_optimal"])):
                            raise AssertionError("Measured solve violates exact reference.")
                        ref.write_jsonl(out,row)
                        rows += 1
            print(json.dumps(dict(case=spec["case"],status="recorded")),flush=True)
    return dict(status="PASS",observations=rows,cases=len(specs),technical_repeats=repeats,
                independent_seeds=sum(s["seed"] is not None for s in specs),mode="allocations" if allocations else "profile" if profile else "timing")


def check_gate(path):
    if (path.parent/"FAILURE.json").exists() or not (path.parent/"PROCESS_COMPLETE.json").exists():
        raise ValueError("Incomplete or failed correctness gate.")
    complete = json.loads((path.parent/"PROCESS_COMPLETE.json").read_text(encoding="utf-8"))
    if complete.get("status") != "PASS":
        raise ValueError("Correctness run did not finish successfully.")
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS" or gate.get("source_sha256") != file_hash(__file__):
        raise ValueError("Correctness gate must match this source.")
    if gate.get("reference_sha256") != REFERENCE_SHA256 or gate.get("case_count",0) < 24:
        raise ValueError("Full frozen 24-case development correctness is required.")
    if gate.get("split") != "dev":
        raise ValueError("Development gate required before using new seeds.")
    return gate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("correctness","profile","timing","allocations"))
    parser.add_argument("--run",help="Fresh descendant of the V444 directory.")
    parser.add_argument("--split",choices=("dev","holdout"),default=None)
    parser.add_argument("--max-seconds",type=float,default=60)
    parser.add_argument("--repeats",type=int,default=3)
    parser.add_argument("--budgets-ms",type=float,nargs="+",default=[0,1,5])
    parser.add_argument("--limit-cases",type=int,default=0)
    parser.add_argument("--gate",type=Path)
    args = parser.parse_args()
    if not 0 < args.max_seconds <= 60 or args.repeats < 1 or args.limit_cases < 0:
        parser.error("Initial stage permits at most 60 seconds and positive repeats.")
    if any(b < 0 for b in args.budgets_ms):
        parser.error("Budgets must be nonnegative.")
    args.split = args.split or ("dev" if args.mode=="correctness" else "holdout")
    os.environ.update(TEMP=r"E:\CodexResearch-xi\temp",TMP=r"E:\CodexResearch-xi\temp",
                      PYTHONDONTWRITEBYTECODE="1")
    specs = get_cases(args.split)
    if args.limit_cases:
        specs = specs[:args.limit_cases]
    if not args.run:
        parser.error("A fresh --run directory is required.")
    run = Path(args.run)
    if not run.is_absolute():
        run = HERE/run
    run = run.resolve()
    if run == HERE or HERE not in run.parents or run.exists():
        parser.error("Use a new descendant run directory; existing artifacts are preserved.")
    if args.mode != "correctness" and not args.gate:
        parser.error("A matching completed correctness --gate and root approval are required.")
    run.mkdir(parents=True,exist_ok=False)
    watchdog = Watchdog(args.max_seconds)
    ref.write_json(run/"INPUTS.json",specs)
    protocol = dict(source_version=SOURCE_VERSION,mode=args.mode,split=args.split,
                    source_sha256=file_hash(__file__),reference_sha256=REFERENCE_SHA256,
                    reference_path=str(REFERENCE),inputs_sha256=file_hash(run/"INPUTS.json"),
                    arguments=vars(args)|{"gate":str(args.gate) if args.gate else None},
                    arms=ARMS,new_seeds=NEW_SEEDS,objective="minimum second-handoff completion H2",
                    lazy_astar_source=LAZY_ASTAR_SOURCE,
                    timers="detailed instrumentation enabled only in profile mode",
                    common_order="absolute bound then stable generation serial",
                    no_sumo=True,no_process_memory_inference_from_python_allocations=True)
    ref.write_json(run/"PROTOCOL.json",protocol)
    try:
        if args.mode == "correctness":
            summary = run_correctness(specs,run,watchdog)
            ref.write_json(run/"PASS.json",dict(status="PASS",source_sha256=protocol["source_sha256"],
                reference_sha256=REFERENCE_SHA256,case_count=len(specs),split=args.split))
        else:
            ref.write_json(run/"USED_GATE.json",check_gate(args.gate))
            summary = run_measurements(specs,run,watchdog,args.repeats,args.budgets_ms,
                                       args.mode=="profile",args.mode=="allocations")
        watchdog.check(True)
        summary["elapsed_wall_seconds"] = time.perf_counter()-watchdog.started
        ref.write_json(run/"SUMMARY.json",summary)
        ref.write_json(run/"PROCESS_COMPLETE.json",dict(status="PASS",mode=args.mode,
                        elapsed_wall_seconds=summary["elapsed_wall_seconds"]))
        return 0
    except BaseException as exc:
        failure = dict(status="INCOMPLETE" if isinstance(exc,ref.PilotTimeout)
                       else "FAIL",exception_type=type(exc).__name__,message=str(exc),
                       traceback=traceback.format_exc(),elapsed_seconds=time.perf_counter()-watchdog.started)
        ref.write_json(run/"FAILURE.json",failure)
        print(json.dumps(failure),file=sys.stderr,flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit("Solver module only: use the root-owned V447 runner and explicit matched instances.")
