#!/usr/bin/env python3
"""V443: restricted two-handoff departure-bound pilot, standard library only.

This file does not execute on import. See code_notes.md and the frozen derivation.
All travel/time values and cargo weights are integer ticks/units. This is not SUMO.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import random
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from typing import Any

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ARMS = ("NO_BOUND", "RADIUS_PRECEDENCE", "ROUTE_PRECEDENCE", "PAIR_ADD", "PAIR_UNION")
DEV_SEEDS = tuple(range(443001, 443014))
HOLDOUT_SEEDS = tuple(range(443101, 443109))
SOURCE_VERSION = "v443-pilot-1"
INF = float("inf")


class PilotTimeout(RuntimeError):
    pass


class Watchdog:
    def __init__(self, seconds: float):
        self.started = time.perf_counter()
        self.deadline = self.started + seconds
        self.calls = 0

    def check(self, force: bool = False) -> None:
        self.calls += 1
        if (force or self.calls % 128 == 0) and time.perf_counter() >= self.deadline:
            raise PilotTimeout("Overall pilot limit reached; incomplete work is not a pass.")


@dataclass(frozen=True)
class State:
    phase: int
    oldmask: int
    a_delivered: bool
    pos: int
    t: int

    @property
    def key(self) -> tuple[int, int, bool, int]:
        # Earlier arrival dominates only because objective is earliest H2, waiting is
        # allowed, resources at this key are identical, and all closures are FIFO.
        return self.phase, self.oldmask, self.a_delivered, self.pos


@dataclass(frozen=True)
class Edge:
    dest: int
    travel: int
    period: int = 0
    green: int = 0
    offset: int = 0

    def arrive(self, t: int) -> int:
        if not self.period:
            return t + self.travel
        phase = (t - self.offset) % self.period
        wait = 0 if phase < self.green else self.period - phase
        return t + wait + self.travel


class Network:
    """Exact earliest-arrival closure of a finite FIFO directed edge network."""
    def __init__(self, spec: dict[str, Any], watchdog: Watchdog):
        self.n = int(spec["n_nodes"])
        self.adj: list[list[Edge]] = [[] for _ in range(self.n)]
        for src, dest, travel, period, green, offset in spec["edges"]:
            if travel < 0 or period < 0 or (period and not 1 <= green <= period):
                raise ValueError("Invalid nonnegative FIFO edge.")
            self.adj[src].append(Edge(dest, travel, period, green, offset))
        self.watchdog = watchdog
        self.cache: dict[tuple[int, int, int], int] = {}
        self.stats = dict(closure_queries=0, closure_cache_hits=0,
                          dijkstra_runs=0, edges_relaxed=0)

    def arrive(self, src: int, dest: int, t: int) -> int:
        self.watchdog.check()
        self.stats["closure_queries"] += 1
        key = (src, dest, t)
        if key in self.cache:
            self.stats["closure_cache_hits"] += 1
            return self.cache[key]
        if src == dest:
            self.cache[key] = t
            return t
        self.stats["dijkstra_runs"] += 1
        best = [INF] * self.n
        best[src] = t
        heap = [(t, src)]
        while heap:
            arrival, u = heapq.heappop(heap)
            if arrival != best[u]:
                continue
            if u == dest:
                self.cache[key] = arrival
                return arrival
            for edge in self.adj[u]:
                self.stats["edges_relaxed"] += 1
                nxt = edge.arrive(arrival)
                if nxt < best[edge.dest]:
                    best[edge.dest] = nxt
                    heapq.heappush(heap, (nxt, edge.dest))
        raise ValueError("Network must connect every required location.")


def bit_ids(mask: int):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def threshold(values: list[tuple[int, int]], quota: int, zero: int) -> int:
    if quota <= 0:
        return zero
    weight = 0
    for value, w in sorted(values):
        weight += w
        if weight >= quota:
            return value
    raise ValueError("Requested threshold quota exceeds available old goods.")


def validate_instance(spec: dict[str, Any]) -> None:
    m = len(spec["old"])
    if not 0 <= m <= 12:
        raise ValueError("Pilot restricts old-goods count to at most twelve.")
    q, wa, wb = spec["Q"], spec["wa"], spec["wb"]
    if not (0 < wa < wb <= q and wa + wb > q):
        raise ValueError("Required atomic capacity incompatibility is absent.")
    if sum(o["weight"] for o in spec["old"]) > q:
        raise ValueError("Initial old load exceeds capacity.")
    if any(o["weight"] <= 0 or o["service"] <= 0 for o in spec["old"]):
        raise ValueError("Old goods require positive weights and services.")
    if min(spec["a_service"], spec["tau_a"], spec["tau_b"]) <= 0:
        raise ValueError("Pilot requires positive delivery and handoff services.")
    numeric = [q, wa, wb, spec["t0"], spec["A"], spec["a_service"],
               spec["tau_a"], spec["tau_b"]]
    numeric += [v for o in spec["old"] for v in (o["weight"], o["service"])]
    numeric += [v for edge in spec["edges"] for v in edge]
    if any(not isinstance(v, int) for v in numeric):
        raise ValueError("All time, weight and edge inputs must be integer.")
    if min(spec["t0"], spec["A"]) < 0:
        raise ValueError("This pilot uses nonnegative absolute times.")


class Context:
    """Search context, with arm-specific work charged to each fresh solve."""
    def __init__(self, spec: dict[str, Any], watchdog: Watchdog):
        validate_instance(spec)
        self.spec = spec
        self.watchdog = watchdog
        self.net = Network(spec, watchdog)
        self.old = spec["old"]
        self.m = len(self.old)
        self.h = spec["hub"]
        self.a = spec["a_node"]
        self.weights = [0] * (1 << self.m)
        for mask in range(1, 1 << self.m):
            bit = mask & -mask
            self.weights[mask] = self.weights[mask ^ bit] + self.old[bit.bit_length()-1]["weight"]
        self.quota_cache: dict[tuple[int, int, int], dict[int, int]] = {}
        self.via_cache: dict[tuple[int, int, int], dict[int, int]] = {}
        self.fa_cache: dict[int, int] = {}
        self.gamma_cache: dict[tuple[int, int], int] = {}
        self.bound_cache: dict[tuple[State, str], tuple[int, dict[str, Any]]] = {}
        self.counts = dict(quota_queries=0, quota_cache_hits=0, quota_dp_labels=0,
                           radius_queries=0, individual_via_queries=0,
                           individual_via_cache_hits=0, fa_queries=0, fa_cache_hits=0,
                           gamma_queries=0, gamma_cache_hits=0, bound_queries=0,
                           bound_cache_hits=0, bound_time_ns=0, quota_time_ns=0,
                           individual_via_time_ns=0, pair_projection_time_ns=0,
                           pair_events_evaluated=0, pair_skip_exact_quota=0,
                           pair_skip_alpha_union=0)

    def initial(self) -> State:
        return State(0, (1 << self.m) - 1, False,
                     self.spec["start_node"], self.spec["t0"])

    def individual_vias(self, s: State) -> dict[int, int]:
        self.counts["individual_via_queries"] += 1
        key = (s.oldmask, s.pos, s.t)
        if key in self.via_cache:
            self.counts["individual_via_cache_hits"] += 1
            return self.via_cache[key]
        started = time.perf_counter_ns()
        result = {}
        for i in bit_ids(s.oldmask):
            o = self.old[i]
            at = self.net.arrive(s.pos, o["node"], s.t) + o["service"]
            result[i] = self.net.arrive(o["node"], self.h, at)
        self.via_cache[key] = result
        self.counts["individual_via_time_ns"] += time.perf_counter_ns() - started
        return result

    def quota(self, s: State, quota: int, radius: bool = False) -> int:
        if radius:
            self.counts["radius_queries"] += 1
            if quota <= 0:
                return self.net.arrive(s.pos, self.h, s.t)
            vias = self.individual_vias(s)
            return threshold([(value, self.old[i]["weight"]) for i, value in vias.items()],
                             quota, s.t)
        self.counts["quota_queries"] += 1
        if quota <= 0:
            return self.net.arrive(s.pos, self.h, s.t)
        key = (s.oldmask, s.pos, s.t)
        if key in self.quota_cache:
            self.counts["quota_cache_hits"] += 1
            table = self.quota_cache[key]
        else:
            started = time.perf_counter_ns()
            # Conventional subset DP; each subset/last keeps its earliest arrival.
            # No two-batch bound or full scheduling oracle is used here.
            labels: list[dict[int, int]] = [{} for _ in range(1 << self.m)]
            labels[0][s.pos] = s.t
            table = {}
            for subset in range(1 << self.m):
                if subset & ~s.oldmask or not labels[subset]:
                    continue
                self.watchdog.check()
                table[subset] = min(self.net.arrive(last, self.h, at)
                                    for last, at in labels[subset].items())
                for last, at in list(labels[subset].items()):
                    self.counts["quota_dp_labels"] += 1
                    for i in bit_ids(s.oldmask & ~subset):
                        o = self.old[i]
                        nxt = self.net.arrive(last, o["node"], at) + o["service"]
                        newmask = subset | (1 << i)
                        old = labels[newmask].get(o["node"], INF)
                        if nxt < old:
                            labels[newmask][o["node"]] = nxt
            self.quota_cache[key] = table
            self.counts["quota_time_ns"] += time.perf_counter_ns() - started
        return min(value for subset, value in table.items()
                   if self.weights[subset] >= quota)

    def fa(self, t: int) -> int:
        self.counts["fa_queries"] += 1
        if t in self.fa_cache:
            self.counts["fa_cache_hits"] += 1
            return self.fa_cache[t]
        at = self.net.arrive(self.h, self.a, t) + self.spec["a_service"]
        result = self.net.arrive(self.a, self.h, at)
        self.fa_cache[t] = result
        return result

    def gamma(self, i: int, t: int) -> int:
        self.counts["gamma_queries"] += 1
        key = (i, t)
        if key in self.gamma_cache:
            self.counts["gamma_cache_hits"] += 1
            return self.gamma_cache[key]
        o = self.old[i]
        at_a = self.net.arrive(self.h, self.a, t) + self.spec["a_service"]
        then_o = self.net.arrive(self.a, o["node"], at_a) + o["service"]
        ao = self.net.arrive(o["node"], self.h, then_o)
        at_o = self.net.arrive(self.h, o["node"], t) + o["service"]
        then_a = self.net.arrive(o["node"], self.a, at_o) + self.spec["a_service"]
        oa = self.net.arrive(self.a, self.h, then_a)
        result = min(ao, oa)
        self.gamma_cache[key] = result
        return result

    def _compute_bound(self, s: State, arm: str) -> tuple[int, dict[str, Any]]:
        # All arms use the same trivial time bound after first handoff.
        # The increment is isolated to phase 0.
        if arm == "NO_BOUND" or s.phase != 0:
            return s.t, {"phase": s.phase, "trivial_time": s.t}
        sp = self.spec
        load = self.weights[s.oldmask]
        qa = max(0, load + sp["wa"] - sp["Q"])
        qb = max(0, load + sp["wb"] - sp["Q"])
        radius = arm == "RADIUS_PRECEDENCE"
        ga = self.quota(s, qa, radius)
        gb = self.quota(s, qb, radius)
        B = max(sp["A"], ga) + sp["tau_a"]
        hind = max(self.fa(B), max(sp["A"], gb)) + sp["tau_b"]
        detail = dict(qa=qa, qb=qb, G_qa=ga, G_qb=gb, B=B, H_ind=hind)
        if arm in ("RADIUS_PRECEDENCE", "ROUTE_PRECEDENCE"):
            return hind, detail
        if arm not in ("PAIR_ADD", "PAIR_UNION"):
            raise ValueError("Unknown arm.")
        pair_started = time.perf_counter_ns()
        try:
            # Exact-G witness implies enough old load can already be released by B.
            # This is an equivalent shortcut only because this pilot uses exact G.
            if gb + sp["tau_a"] <= B:
                self.counts["pair_skip_exact_quota"] += 1
                detail.update(skip="exact_quota_witness", H_raw=self.fa(B)+sp["tau_b"])
                return hind, detail
            alpha = {i: value + sp["tau_a"] for i, value in self.individual_vias(s).items()}
            early_B = sum(self.old[i]["weight"] for i, value in alpha.items() if value <= B)
            if early_B >= qb:
                self.counts["pair_skip_alpha_union"] += 1
                detail.update(skip="alpha_union_at_B", alpha=alpha,
                              H_raw=self.fa(B)+sp["tau_b"])
                return hind, detail
            events = sorted({B} | {value for value in alpha.values() if value >= B})
            candidates = []
            for x in events:
                early = {i for i, value in alpha.items() if value <= x}
                released = sum(self.old[i]["weight"] for i in early)
                if released < qa:
                    continue
                self.counts["pair_events_evaluated"] += 1
                qrem = max(0, qb - released)
                pool = list(bit_ids(s.oldmask)) if arm == "PAIR_ADD" else [
                    i for i in bit_ids(s.oldmask) if i not in early]
                if qrem:
                    vals = [(self.gamma(i, x), self.old[i]["weight"]) for i in pool]
                    v = threshold(vals, qrem, x)
                else:
                    v = x
                hx = max(self.fa(x), v) + sp["tau_b"]
                candidates.append(dict(x=x, early=sorted(early), released=released,
                                       qrem=qrem, threshold=v, H=hx))
            if not candidates:
                raise AssertionError("Finite complete network should have a valid final event.")
            raw = min(row["H"] for row in candidates)
            detail.update(alpha=alpha, events=candidates, H_raw=raw)
            return max(hind, raw), detail
        finally:
            self.counts["pair_projection_time_ns"] += time.perf_counter_ns() - pair_started

    def bound(self, s: State, arm: str) -> tuple[int, dict[str, Any]]:
        started = time.perf_counter_ns()
        self.counts["bound_queries"] += 1
        try:
            key = (s, arm)
            if key in self.bound_cache:
                self.counts["bound_cache_hits"] += 1
                return self.bound_cache[key]
            result = self._compute_bound(s, arm)
            self.bound_cache[key] = result
            return result
        finally:
            self.counts["bound_time_ns"] += time.perf_counter_ns() - started

    def children(self, s: State):
        # This event generator is not called by ReferenceOracle.
        sp = self.spec
        if s.phase == 2:
            return
        for i in bit_ids(s.oldmask):
            o = self.old[i]
            done = self.net.arrive(s.pos, o["node"], s.t) + o["service"]
            yield State(s.phase, s.oldmask ^ (1 << i), s.a_delivered, o["node"], done), f"old:{i}"
        if s.phase == 0:
            if self.weights[s.oldmask] + sp["wa"] <= sp["Q"]:
                arrived = self.net.arrive(s.pos, self.h, s.t)
                done = max(arrived, sp["A"]) + sp["tau_a"]
                yield State(1, s.oldmask, False, self.h, done), "handoff:a"
        elif not s.a_delivered:
            done = self.net.arrive(s.pos, self.a, s.t) + sp["a_service"]
            yield State(1, s.oldmask, True, self.a, done), "deliver:a"
        elif self.weights[s.oldmask] + sp["wb"] <= sp["Q"]:
            done = self.net.arrive(s.pos, self.h, s.t) + sp["tau_b"]
            yield State(2, s.oldmask, True, self.h, done), "handoff:b"

    def greedy(self) -> tuple[int, tuple[str, ...]]:
        s = self.initial()
        plan: list[str] = []
        while s.oldmask:
            options = []
            for i in bit_ids(s.oldmask):
                o = self.old[i]
                done = self.net.arrive(s.pos, o["node"], s.t) + o["service"]
                options.append((done, i, o["node"]))
            done, i, node = min(options)
            s = State(0, s.oldmask ^ (1 << i), False, node, done)
            plan.append(f"old:{i}")
        start = max(self.net.arrive(s.pos, self.h, s.t), self.spec["A"])
        h1 = start + self.spec["tau_a"]
        done_a = self.net.arrive(self.h, self.a, h1) + self.spec["a_service"]
        h2 = self.net.arrive(self.a, self.h, done_a) + self.spec["tau_b"]
        return h2, tuple(plan + ["handoff:a", "deliver:a", "handoff:b"])

    def stats(self) -> dict[str, int]:
        out = {**self.counts, **self.net.stats}
        out.update(closure_cache_size=len(self.net.cache),
                   quota_cache_size=len(self.quota_cache), via_cache_size=len(self.via_cache),
                   fa_cache_size=len(self.fa_cache), gamma_cache_size=len(self.gamma_cache),
                   bound_cache_size=len(self.bound_cache))
        return out


class ReferenceOracle:
    """Independent exhaustive feasible event sequences, without proposed bounds.

    Only exact memoization of the complete state INCLUDING absolute time is used.
    No earliest-time dominance, incumbent pruning or bound routine is called.
    """
    def __init__(self, spec: dict[str, Any], watchdog: Watchdog):
        validate_instance(spec)
        self.sp = spec
        self.net = Network(spec, watchdog)
        self.watchdog = watchdog
        self.memo: dict[State, int] = {}
        self.memo_hits = 0
        self.transitions = 0

    def initial(self) -> State:
        return State(0, (1 << len(self.sp["old"])) - 1, False,
                     self.sp["start_node"], self.sp["t0"])

    def suffix(self, s: State) -> int:
        self.watchdog.check()
        if s in self.memo:
            self.memo_hits += 1
            return self.memo[s]
        if s.phase == 2:
            self.memo[s] = s.t
            return s.t
        sp = self.sp
        old = sp["old"]
        load = sum(old[i]["weight"] for i in range(len(old)) if s.oldmask & (1 << i))
        successors: list[State] = []
        # Deliberately separate code from Context.children and quota/bound logic.
        for i, item in enumerate(old):
            if s.oldmask & (1 << i):
                when = self.net.arrive(s.pos, item["node"], s.t) + item["service"]
                successors.append(State(s.phase, s.oldmask & ~(1 << i),
                                        s.a_delivered, item["node"], when))
        if s.phase == 0 and load + sp["wa"] <= sp["Q"]:
            when = max(self.net.arrive(s.pos, sp["hub"], s.t), sp["A"]) + sp["tau_a"]
            successors.append(State(1, s.oldmask, False, sp["hub"], when))
        if s.phase == 1 and not s.a_delivered:
            when = self.net.arrive(s.pos, sp["a_node"], s.t) + sp["a_service"]
            successors.append(State(1, s.oldmask, True, sp["a_node"], when))
        if s.phase == 1 and s.a_delivered and load + sp["wb"] <= sp["Q"]:
            when = self.net.arrive(s.pos, sp["hub"], s.t) + sp["tau_b"]
            successors.append(State(2, s.oldmask, True, sp["hub"], when))
        if not successors:
            raise AssertionError("Unexpected infeasible leaf in unrestricted finite pilot.")
        self.transitions += len(successors)
        answer = min(self.suffix(child) for child in successors)
        self.memo[s] = answer
        return answer


def replay_plan(spec: dict[str, Any], plan: list[str] | tuple[str, ...],
                watchdog: Watchdog) -> int:
    """Independent feasibility replay; no bound code, no solver transitions."""
    net = Network(spec, watchdog)
    remaining = set(range(len(spec["old"])))
    phase, delivered, pos, now = 0, False, spec["start_node"], spec["t0"]
    for action in plan:
        if phase == 2:
            raise AssertionError("Plan continues after final handoff.")
        if action.startswith("old:"):
            i = int(action.split(":")[1])
            if i not in remaining:
                raise AssertionError("An old parcel was delivered twice.")
            item = spec["old"][i]
            now = net.arrive(pos, item["node"], now) + item["service"]
            pos = item["node"]
            remaining.remove(i)
        elif action == "handoff:a":
            if phase != 0 or sum(spec["old"][i]["weight"] for i in remaining) + spec["wa"] > spec["Q"]:
                raise AssertionError("Illegal first handoff.")
            now = max(net.arrive(pos, spec["hub"], now), spec["A"]) + spec["tau_a"]
            pos, phase = spec["hub"], 1
        elif action == "deliver:a":
            if phase != 1 or delivered:
                raise AssertionError("Illegal new-item delivery.")
            now = net.arrive(pos, spec["a_node"], now) + spec["a_service"]
            pos, delivered = spec["a_node"], True
        elif action == "handoff:b":
            if phase != 1 or not delivered:
                raise AssertionError("Second handoff precedes mandatory a delivery.")
            if sum(spec["old"][i]["weight"] for i in remaining) + spec["wb"] > spec["Q"]:
                raise AssertionError("Second handoff exceeds capacity.")
            now = net.arrive(pos, spec["hub"], now) + spec["tau_b"]
            pos, phase = spec["hub"], 2
        else:
            raise AssertionError("Unknown plan action.")
    if phase != 2:
        raise AssertionError("Plan lacks a completed final handoff.")
    return now


def solve(spec: dict[str, Any], arm: str, watchdog: Watchdog,
          wall_ms: float | None = None) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(arm)
    started = time.perf_counter()
    ctx = Context(spec, watchdog)
    setup = time.perf_counter() - started
    initial_started = time.perf_counter()
    best, best_plan = ctx.greedy()
    initial_seconds = time.perf_counter() - initial_started
    trace = [dict(seconds=time.perf_counter()-started, H2=best, plan=list(best_plan))]
    counts = dict(expanded=0, generated=0, terminal_generated=0, pruned=0,
                  dominated=0, stale_pops=0, queued=0, peak_frontier=0)
    deadline = None if wall_ms is None else started + wall_ms / 1000.0
    initial_overrun = deadline is not None and time.perf_counter() >= deadline
    heap: list[tuple[int, int, State, tuple[str, ...]]] = []
    best_time: dict[tuple[int, int, bool, int], int] = {}
    serial = 0
    stop = "initialization_budget" if initial_overrun else "exhausted"
    root_bound = None
    if not initial_overrun:
        root = ctx.initial()
        root_bound = ctx.bound(root, arm)[0]
        best_time[root.key] = root.t
        if root_bound < best:
            heapq.heappush(heap, (root_bound, serial, root, ()))
            counts["queued"] = counts["peak_frontier"] = 1
        else:
            counts["pruned"] += 1
        while heap:
            watchdog.check()
            # Soft budget: checked only at complete expansion boundaries.
            if deadline is not None and time.perf_counter() >= deadline:
                stop = "wall_budget"
                break
            lb, _, state, plan = heapq.heappop(heap)
            if best_time.get(state.key) != state.t:
                counts["stale_pops"] += 1
                continue
            if lb >= best:
                counts["pruned"] += 1
                continue
            counts["expanded"] += 1
            for child, action in ctx.children(state):
                counts["generated"] += 1
                child_plan = plan + (action,)
                if child.phase == 2:
                    counts["terminal_generated"] += 1
                    if child.t < best:
                        best, best_plan = child.t, child_plan
                        trace.append(dict(seconds=time.perf_counter()-started,
                                          H2=best, plan=list(best_plan)))
                    continue
                if child.t >= best_time.get(child.key, INF):
                    counts["dominated"] += 1
                    continue
                best_time[child.key] = child.t
                child_lb = ctx.bound(child, arm)[0]
                if child_lb >= best:
                    counts["pruned"] += 1
                    continue
                serial += 1
                heapq.heappush(heap, (child_lb, serial, child, child_plan))
                counts["queued"] += 1
            counts["peak_frontier"] = max(counts["peak_frontier"], len(heap))
    live = [lb for lb, _, s, _ in heap if best_time.get(s.key) == s.t]
    remaining = None if initial_overrun else min([best] + live)
    gap = None if remaining is None else best - remaining
    stats = ctx.stats()
    elapsed = time.perf_counter() - started
    return dict(case=spec["case"], split=spec["split"], seed=spec["seed"], arm=arm,
                wall_budget_ms=wall_ms, H2=best, plan=list(best_plan), trace=trace,
                elapsed_seconds=elapsed, setup_seconds=setup, initial_seconds=initial_seconds,
                search_seconds=max(0.0, elapsed-setup-initial_seconds),
                bound_seconds=stats["bound_time_ns"]/1e9,
                quota_seconds=stats["quota_time_ns"]/1e9,
                individual_via_seconds=stats["individual_via_time_ns"]/1e9,
                pair_projection_seconds=stats["pair_projection_time_ns"]/1e9,
                initialization_overrun=initial_overrun, stop_reason=stop,
                overrun_seconds=0.0 if wall_ms is None else max(0.0, elapsed-wall_ms/1000),
                root_bound=root_bound, remaining_bound=remaining, certified_gap=gap,
                certified_optimal=(gap == 0), **counts, stats=stats)


def line_case(name: str = "analytic_34_40_52_56", A: int = 0,
              far: int = 10) -> dict[str, Any]:
    coords = [0, -10, 1, far]
    edges = [[i, j, abs(x-y), 0, 0, 0]
             for i, x in enumerate(coords) for j, y in enumerate(coords) if i != j]
    return dict(case=name, split="dev", seed=None, n_nodes=4, edges=edges,
                hub=0, a_node=1, start_node=0, t0=0, A=A, Q=2, wa=1, wb=2,
                a_service=4, tau_a=2, tau_b=2,
                old=[dict(node=2, weight=1, service=4),
                     dict(node=3, weight=1, service=4)],
                generation="deterministic boundary scenario")


def random_case(seed: int, split: str, index: int) -> dict[str, Any]:
    rng = random.Random(seed)
    m = 1 + index % 5
    coords = [(0, 0), (rng.randint(-12, 12), rng.randint(-12, 12))]
    coords += [(rng.randint(-12, 12), rng.randint(-12, 12)) for _ in range(m)]
    if index % 7 == 0:
        coords[-1] = coords[1]  # Co-located but separately serviced tasks.
    old = [dict(node=i+2, weight=rng.randint(1, 3), service=rng.randint(1, 5))
           for i in range(m)]
    Q = max(3, sum(o["weight"] for o in old) + (index % 3 == 0))
    pairs = [(a, b) for a in range(1, Q) for b in range(a+1, Q+1) if a+b > Q]
    wa, wb = rng.choice(pairs)
    edges = []
    for i, xy in enumerate(coords):
        for j, uv in enumerate(coords):
            if i == j:
                continue
            travel = abs(xy[0]-uv[0]) + abs(xy[1]-uv[1]) + rng.randint(0, 3)
            period = rng.choice((8, 12, 16)) if index % 4 and rng.random() < 0.65 else 0
            green = rng.choice((2, period//2, period-1)) if period else 0
            offset = rng.randrange(period) if period else 0
            edges.append([i, j, travel, period, green, offset])
    return dict(case=f"{split}_{seed}", split=split, seed=seed,
                n_nodes=len(coords), edges=edges, coordinates=coords,
                hub=0, a_node=1, start_node=0 if index % 3 else m+1,
                t0=(index % 5)*2, A=(0, 8, 25, 80)[index % 4],
                Q=Q, wa=wa, wb=wb, a_service=rng.randint(1, 5),
                tau_a=rng.randint(1, 3), tau_b=rng.randint(1, 3), old=old,
                generation="prespecified seeded directed FIFO synthetic network")


def cases(split: str) -> list[dict[str, Any]]:
    dev = [line_case(), line_case("eta_dominates", A=100),
           line_case("equal_alpha_coincident_old", far=1)]
    dev += [random_case(seed, "dev", i) for i, seed in enumerate(DEV_SEEDS)]
    holdout = [random_case(seed, "holdout", i+17) for i, seed in enumerate(HOLDOUT_SEEDS)]
    return dev if split == "dev" else holdout if split == "holdout" else dev + holdout


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=True, indent=2, allow_nan=False)+"\n",
                    encoding="utf-8")


def write_jsonl(stream, obj: Any) -> None:
    stream.write(json.dumps(obj, ensure_ascii=True, separators=(",", ":"), allow_nan=False)+"\n")
    stream.flush()


def decorate_target(row: dict[str, Any], oracle: int) -> None:
    # Post-hoc only: no target or oracle value is passed into solve().
    row["oracle_H2"] = oracle
    row["regret_ticks"] = row["H2"] - oracle
    row["first_target_seconds"] = next((item["seconds"] for item in row["trace"]
                                        if item["H2"] <= oracle), None)
    row["initial_already_optimal"] = row["trace"][0]["H2"] == oracle
    cutoff = None if row["wall_budget_ms"] is None else row["wall_budget_ms"]/1000.0
    timely = [item["H2"] for item in row["trace"]
              if cutoff is None or item["seconds"] <= cutoff]
    within = min(timely) if timely else None
    row["H2_within_budget"] = within
    row["solution_available_within_budget"] = within is not None
    row["regret_within_budget"] = None if within is None else within-oracle
    row["target_reached_within_budget"] = within is not None and within <= oracle
    row["certified_within_budget"] = bool(row["certified_optimal"] and
        (cutoff is None or row["elapsed_seconds"] <= cutoff))


def check_edge_fifo(spec: dict[str, Any]) -> int:
    count = 0
    for _, dest, travel, period, green, offset in spec["edges"]:
        edge = Edge(dest, travel, period, green, offset)
        for t in range(2 * max(1, period) + 3):
            if edge.arrive(t) < t or edge.arrive(t+1) < edge.arrive(t):
                raise AssertionError("FIFO edge violation.")
            count += 1
    return count


def verify_closure_independently(spec: dict[str, Any], watchdog: Watchdog) -> dict[str, Any]:
    """Independent n-1-pass Bellman-Ford closure with inline edge calendar math."""
    actual = Network(spec, watchdog)
    n = spec["n_nodes"]
    departures = sorted(set(range(48)) | {spec["t0"], spec["A"]})
    comparisons = passes = edge_evaluations = 0
    for source in range(n):
        for departure in departures:
            watchdog.check()
            best = [INF] * n
            best[source] = departure
            # A FIFO nonnegative path can discard cycles; n-1 edges suffice.
            # Synchronous passes use only the previous pass, independent of
            # Dijkstra, Network.arrive and Edge.arrive.
            for _ in range(n-1):
                updated = best.copy()
                for u, v, travel, period, green, offset in spec["edges"]:
                    if best[u] == INF:
                        continue
                    edge_evaluations += 1
                    start = best[u]
                    wait = 0
                    if period:
                        phase = (start-offset) % period
                        if phase >= green:
                            wait = period-phase
                    arrival = start + wait + travel
                    if arrival < updated[v]:
                        updated[v] = arrival
                passes += 1
                if updated == best:
                    break
                best = updated
            for destination in range(n):
                dijkstra = actual.arrive(source, destination, departure)
                if dijkstra != best[destination]:
                    raise AssertionError(dict(reason="independent_closure_mismatch",
                        case=spec["case"], source=source, destination=destination,
                        departure=departure, dijkstra=dijkstra,
                        bellman_ford=best[destination]))
                comparisons += 1
    return dict(case=spec["case"], status="PASS", departure_ticks=departures,
                comparison_count=comparisons, bellman_ford_passes=passes,
                bellman_ford_edge_evaluations=edge_evaluations,
                dijkstra_stats=actual.stats,
                scope="synthetic FIFO graph primitive, not a simulator validation")


def run_correctness(specs: list[dict[str, Any]], run: Path,
                    watchdog: Watchdog) -> dict[str, Any]:
    total_states = total_bounds = total_edges = total_closure_checks = 0
    summaries = []
    with gzip.open(run/"PREFIX_BOUNDS.jsonl.gz", "wt", encoding="utf-8") as prefix_out, \
            (run/"ORACLES.jsonl").open("w", encoding="utf-8") as oracle_out, \
            (run/"SOLVER_RUNS.jsonl").open("w", encoding="utf-8") as solve_out, \
            (run/"PROJECTION_CHECKS.jsonl").open("w", encoding="utf-8") as projection_out, \
            (run/"CLOSURE_CHECKS.jsonl").open("w", encoding="utf-8") as closure_out:
        for spec in specs:
            watchdog.check(True)
            total_edges += check_edge_fifo(spec)
            closure_check = verify_closure_independently(spec, watchdog)
            total_closure_checks += closure_check["comparison_count"]
            write_jsonl(closure_out, closure_check)
            started = time.perf_counter()
            oracle = ReferenceOracle(spec, watchdog)
            optimum = oracle.suffix(oracle.initial())
            oracle_seconds = time.perf_counter()-started
            row = dict(case=spec["case"], optimum_H2=optimum, states=len(oracle.memo),
                       transitions=oracle.transitions, memo_hits=oracle.memo_hits,
                       elapsed_seconds=oracle_seconds, closure_stats=oracle.net.stats)
            write_jsonl(oracle_out, row)
            ctx = Context(spec, watchdog)
            strict = dict(radius_to_route=0, route_to_add=0, add_to_union=0)
            phase0 = 0
            for state, true_suffix in sorted(oracle.memo.items(), key=lambda kv:
                    (kv[0].phase, kv[0].oldmask, kv[0].a_delivered, kv[0].pos, kv[0].t)):
                watchdog.check()
                values = {arm: ctx.bound(state, arm)[0] for arm in ARMS}
                if any(value > true_suffix for value in values.values()):
                    raise AssertionError(dict(reason="inadmissible", case=spec["case"],
                                              state=asdict(state), bounds=values, oracle=true_suffix))
                chain = [values[arm] for arm in ARMS]
                if any(a > b for a, b in zip(chain, chain[1:])):
                    raise AssertionError(dict(reason="bound_order", case=spec["case"],
                                              state=asdict(state), bounds=values))
                if state.phase == 0:
                    phase0 += 1
                    strict["radius_to_route"] += values[ARMS[2]] > values[ARMS[1]]
                    strict["route_to_add"] += values[ARMS[3]] > values[ARMS[2]]
                    strict["add_to_union"] += values[ARMS[4]] > values[ARMS[3]]
                write_jsonl(prefix_out, dict(case=spec["case"], state=asdict(state),
                                            oracle_suffix_H2=true_suffix, bounds=values))
                total_states += 1
                total_bounds += len(ARMS)
            root = oracle.initial()
            projection = brute_integer_projection(ctx, root)
            write_jsonl(projection_out, projection)
            root_details = {arm: dict(value=ctx.bound(root, arm)[0],
                                     detail=ctx.bound(root, arm)[1]) for arm in ARMS}
            if spec["case"] == "analytic_34_40_52_56":
                expected = {"ROUTE_PRECEDENCE": 34, "PAIR_ADD": 40, "PAIR_UNION": 52}
                actual = {arm: root_details[arm]["value"] for arm in expected}
                if actual != expected or optimum != 56:
                    raise AssertionError(dict(reason="analytic_mismatch", actual=actual, optimum=optimum))
            for arm in ARMS:
                result = solve(spec, arm, watchdog)
                replayed = replay_plan(spec, result["plan"], watchdog)
                if result["H2"] != optimum or replayed != optimum or not result["certified_optimal"]:
                    raise AssertionError(dict(reason="solver_exactness", result=result, oracle=optimum,
                                              replayed=replayed))
                decorate_target(result, optimum)
                result.update(mode="correctness_unlimited", repeat=0)
                write_jsonl(solve_out, result)
            summaries.append(dict(**row, phase0_states=phase0, strict_prefix_counts=strict,
                                  root_bounds=root_details, projection_check=projection))
            print(json.dumps(dict(case=spec["case"], status="correctness_pass",
                                  states=len(oracle.memo), optimum_H2=optimum)), flush=True)
    result = dict(status="PASS", case_count=len(specs), reachable_states=total_states,
                  admissibility_checks=total_bounds, edge_fifo_checks=total_edges,
                  independent_closure_comparisons=total_closure_checks,
                  exact_solver_checks=len(specs)*len(ARMS), cases=summaries)
    analytic = next((row for row in summaries if row["case"] == "analytic_34_40_52_56"), None)
    result["truck_interface_checks"] = (
        traffic_interface_checks(analytic, run)["status"] if analytic else "NOT_RUN")
    watchdog.check(True)
    write_json(run/"CORRECTNESS_SUMMARY.json", result)
    return result




def brute_integer_projection(ctx: Context, state: State) -> dict[str, Any]:
    """Check event minimization against every integer H1 in a complete finite range.

    This checks the relaxation's projection, including deliberately delayed H1,
    not an additional physical-plan oracle. After the last alpha, qrem is zero
    and FIFO Fa is nondecreasing, so no later tick can improve the relaxation.
    """
    _, base = ctx.bound(state, "ROUTE_PRECEDENCE")
    B, qa, qb, hind = base["B"], base["qa"], base["qb"], base["H_ind"]
    alpha = {i: value+ctx.spec["tau_a"] for i, value in ctx.individual_vias(state).items()}
    end = max([B] + list(alpha.values()))
    raw = {"PAIR_ADD": INF, "PAIR_UNION": INF}
    valid_ticks = 0
    for x in range(B, end+1):
        ctx.watchdog.check()
        early = {i for i, value in alpha.items() if value <= x}
        released = sum(ctx.old[i]["weight"] for i in early)
        if released < qa:
            continue
        valid_ticks += 1
        qrem = max(0, qb-released)
        for arm in raw:
            pool = list(bit_ids(state.oldmask)) if arm == "PAIR_ADD" else [
                i for i in bit_ids(state.oldmask) if i not in early]
            value = threshold([(ctx.gamma(i, x), ctx.old[i]["weight"]) for i in pool],
                              qrem, x) if qrem else x
            raw[arm] = min(raw[arm], max(ctx.fa(x), value)+ctx.spec["tau_b"])
    projected = {arm: ctx.bound(state, arm)[0] for arm in raw}
    brute = {arm: max(hind, value) for arm, value in raw.items()}
    if projected != brute:
        raise AssertionError(dict(reason="finite_event_projection", state=asdict(state),
                                  projected=projected, brute=brute, B=B, end=end))
    return dict(case=ctx.spec["case"], B=B, last_tick=end, examined_ticks=end-B+1,
                valid_ticks=valid_ticks, brute_raw=raw, brute_final=brute,
                finite_event_final=projected, status="PASS")


def traffic_interface_checks(analytic: dict[str, Any], run: Path) -> dict[str, Any]:
    """Synthetic truck continuation only; receiver analytic network stays static."""
    roots = analytic["root_bounds"]
    h2 = {"ROUTE_PRECEDENCE": roots["ROUTE_PRECEDENCE"]["value"],
          "PAIR_ADD": roots["PAIR_ADD"]["value"],
          "PAIR_UNION": roots["PAIR_UNION"]["value"],
          "ORACLE": analytic["optimum_H2"]}
    scenarios = [
        ("green_40_of_60", Edge(1, 5, 60, 40, 0),
         {"ROUTE_PRECEDENCE": 39, "PAIR_ADD": 65, "PAIR_UNION": 65, "ORACLE": 65}),
        ("green_50_of_60", Edge(1, 5, 60, 50, 0),
         {"ROUTE_PRECEDENCE": 39, "PAIR_ADD": 45, "PAIR_UNION": 65, "ORACLE": 65}),
        ("green_20_of_60", Edge(1, 5, 60, 20, 0),
         {"ROUTE_PRECEDENCE": 65, "PAIR_ADD": 65, "PAIR_UNION": 65, "ORACLE": 65}),
        ("always_green", Edge(1, 5),
         {"ROUTE_PRECEDENCE": 39, "PAIR_ADD": 45, "PAIR_UNION": 57, "ORACLE": 61}),
    ]
    rows = []
    for name, edge, expected in scenarios:
        arrivals = {arm: edge.arrive(departure) for arm, departure in h2.items()}
        if arrivals != expected:
            raise AssertionError(dict(reason="truck_interface_mismatch", case=name,
                                      computed=arrivals, expected=expected))
        rows.append(dict(case=name, edge=asdict(edge), departure_bounds=h2,
                         computed_arrival_bounds=arrivals, arrival_deadline=60,
                         excludes_deadline={arm: value > 60 for arm, value in arrivals.items()},
                         expected_values_checked=True))
    result = dict(status="PASS", scope="prespecified synthetic truck interface checks",
                  receiver_graph="static analytic line metric, positive services",
                  truck_graph="one separate FIFO edge after H2",
                  no_sumo=True, no_customer_benefit_claim=True, cases=rows)
    write_json(run/"TRAFFIC_INTERFACE_CHECKS.json", result)
    return result


def check_gate(path: Path) -> dict[str, Any]:
    if (path.parent/"FAILURE.json").exists() or not (path.parent/"PROCESS_COMPLETE.json").exists():
        raise ValueError("Gate run is incomplete or contains a failure record.")
    complete = json.loads((path.parent/"PROCESS_COMPLETE.json").read_text(encoding="utf-8"))
    if complete.get("status") != "PASS":
        raise ValueError("Gate run did not finish successfully.")
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS" or gate.get("source_sha256") != file_hash(Path(__file__)):
        raise ValueError("A PASS correctness gate for this exact source file is required.")
    if gate.get("derivation_sha256") != file_hash(HERE/"Constructive_Bound_Derivation.md"):
        raise ValueError("Correctness gate does not match the frozen derivation.")
    return gate


def run_measurements(specs: list[dict[str, Any]], run: Path, watchdog: Watchdog,
                     repeats: int, budgets: list[float], allocations: bool) -> dict[str, Any]:
    rows = []
    targets = {}
    with (run/"TARGET_ORACLES.jsonl").open("w", encoding="utf-8") as out:
        for spec in specs:
            watchdog.check(True)
            oracle = ReferenceOracle(spec, watchdog)
            target = oracle.suffix(oracle.initial())
            targets[spec["case"]] = target
            write_jsonl(out, dict(case=spec["case"], optimum_H2=target, states=len(oracle.memo),
                                  outside_measured_solves=True))
    with (run/"MEASUREMENTS.jsonl").open("w", encoding="utf-8") as out:
        for case_index, spec in enumerate(specs):
            for repeat in range(repeats):
                order = list(ARMS)
                rotate = (case_index + repeat) % len(order)
                order = order[rotate:] + order[:rotate]
                if repeat % 2:
                    order.reverse()
                for budget in ([0.0] if allocations else budgets):
                    for position, arm in enumerate(order):
                        watchdog.check(True)
                        if allocations:
                            import gc
                            import tracemalloc
                            gc.collect()
                            tracemalloc.start()
                            try:
                                row = solve(spec, arm, watchdog)
                                current, peak = tracemalloc.get_traced_memory()
                            finally:
                                tracemalloc.stop()
                            row["python_traced_current_bytes"] = current
                            row["python_traced_peak_bytes"] = peak
                            row["memory_measure"] = "Python allocations only; not whole-process memory"
                            row["timing_interpretable"] = False
                        else:
                            row = solve(spec, arm, watchdog, None if budget == 0 else budget)
                            row["timing_interpretable"] = True
                        decorate_target(row, targets[spec["case"]])
                        if replay_plan(spec, row["plan"], watchdog) != row["H2"]:
                            raise AssertionError("Measured solver plan failed independent replay.")
                        if row["regret_ticks"] < 0:
                            raise AssertionError("Solver beats exhaustive oracle: correctness failure.")
                        if budget == 0 and (row["regret_ticks"] or not row["certified_optimal"]):
                            raise AssertionError("Nonbinding measured solve failed exactness.")
                        row.update(mode="python_allocations" if allocations else "timing",
                                   repeat=repeat, arm_position=position)
                        write_jsonl(out, row)
                        rows.append(row)
            print(json.dumps(dict(case=spec["case"], status="measurements_recorded")), flush=True)
    return dict(status="PASS", case_count=len(specs), observations=len(rows),
                technical_repeats=repeats, independent_seed_count=sum(s["seed"] is not None for s in specs),
                quality_optimal=sum(r["regret_ticks"] == 0 for r in rows),
                certified_optimal=sum(r["certified_optimal"] for r in rows),
                initialization_overruns=sum(r["initialization_overrun"] for r in rows),
                within_budget_available=sum(r["solution_available_within_budget"] for r in rows),
                within_budget_optimal=sum(r["target_reached_within_budget"] for r in rows),
                within_budget_certified=sum(r["certified_within_budget"] for r in rows),
                memory_scope="Python allocations only" if allocations else "not measured")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("correctness", "timing", "allocations"))
    parser.add_argument("--run", required=True, help="Fresh run directory, relative to this script or absolute below it.")
    parser.add_argument("--split", choices=("dev", "holdout", "all"), default=None)
    parser.add_argument("--max-seconds", type=float, default=60.0)
    parser.add_argument("--limit-cases", type=int, default=0)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--budgets-ms", nargs="+", type=float, default=[0.0, 1.0, 5.0])
    parser.add_argument("--gate", type=Path, help="Required PASS.json from correctness for measurement modes.")
    args = parser.parse_args()
    if not 1 <= args.max_seconds <= 60:
        parser.error("Initial pilot maximum must be between 1 and 60 seconds.")
    if args.repeats < 1 or args.limit_cases < 0 or any(b < 0 for b in args.budgets_ms):
        parser.error("Invalid repeat, case or budget count.")
    split = args.split or ("dev" if args.mode == "correctness" else "holdout")
    specs = cases(split)
    if args.limit_cases:
        specs = specs[:args.limit_cases]
    run = Path(args.run)
    if not run.is_absolute():
        run = HERE/run
    run = run.resolve()
    if run == HERE or HERE not in run.parents:
        parser.error("Run path must be a new directory beneath the V443 script directory.")
    if run.exists():
        parser.error("Run path already exists; preserve it and choose a new version.")
    if args.mode != "correctness" and args.gate is None:
        parser.error("Measurement modes require --gate and root authorization.")
    run.mkdir(parents=True, exist_ok=False)
    os.environ["TEMP"] = r"E:\CodexResearch-xi\temp"
    os.environ["TMP"] = r"E:\CodexResearch-xi\temp"
    watchdog = Watchdog(args.max_seconds)
    protocol = dict(source_version=SOURCE_VERSION, mode=args.mode, split=split,
                    source_sha256=file_hash(Path(__file__)),
                    derivation_sha256=file_hash(HERE/"Constructive_Bound_Derivation.md"),
                    arguments=vars(args) | {"gate": str(args.gate) if args.gate else None},
                    case_ids=[s["case"] for s in specs], development_seeds=DEV_SEEDS,
                    holdout_seeds=HOLDOUT_SEEDS, arms=ARMS,
                    objective="minimize absolute second-handoff completion H2",
                    phase1_bound="common trivial absolute time",
                    receiver_graph="generic synthetic transport; not literal indoor traffic signals",
                    truck_interface="separate edge composition on the static receiver analytic case",
                    oracle="independent exhaustive event sequences with exact full-time memoization",
                    no_sumo=True, no_process_memory_claim=True,
                    timing_scope="fresh context, all solver caches, common incumbent and complete search",
                    budgets="soft boundaries after complete node expansions, initialization included",
                    zero_budget_means="nonbinding solve, still subject to overall pilot watchdog")
    write_json(run/"INPUTS.json", specs)
    protocol["inputs_sha256"] = file_hash(run/"INPUTS.json")
    write_json(run/"PROTOCOL.json", protocol)
    try:
        if args.mode == "correctness":
            result = run_correctness(specs, run, watchdog)
            gate = dict(status="PASS", source_sha256=protocol["source_sha256"],
                        derivation_sha256=protocol["derivation_sha256"],
                        split=split, case_ids=protocol["case_ids"],
                        reachable_states=result["reachable_states"],
                        admissibility_checks=result["admissibility_checks"],
                        analytic_case_included="analytic_34_40_52_56" in protocol["case_ids"])
            write_json(run/"PASS.json", gate)
        else:
            gate = check_gate(args.gate)
            if not gate.get("analytic_case_included") or len(gate.get("case_ids", [])) < 16:
                raise ValueError("Full 16-case development gate including analytic case is required.")
            write_json(run/"USED_GATE.json", gate)
            result = run_measurements(specs, run, watchdog, args.repeats,
                                      args.budgets_ms, args.mode == "allocations")
        result["elapsed_wall_seconds"] = time.perf_counter()-watchdog.started
        write_json(run/"SUMMARY.json", result)
        write_json(run/"PROCESS_COMPLETE.json", dict(status="PASS", mode=args.mode,
                                                     elapsed_seconds=result["elapsed_wall_seconds"]))
        return 0
    except BaseException as exc:
        failure = dict(status="INCOMPLETE" if isinstance(exc, PilotTimeout) else "FAIL",
                       exception_type=type(exc).__name__, message=str(exc),
                       traceback=traceback.format_exc(),
                       elapsed_wall_seconds=time.perf_counter()-watchdog.started)
        write_json(run/"FAILURE.json", failure)
        print(json.dumps(failure), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
