#!/usr/bin/env python3
"""V448 micro correctness runner. PREPARED ONLY; execution needs root scheduling.

No timing experiment or main-result access. Defaults to one frozen micro case.
All numerical paths execute only from main(), never on import.
"""
from __future__ import annotations
import argparse
import ast
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "fleet_study_v447_random_high_load_20261107"
INPUTS = PARENT / "instances" / "micro_01" / "INPUTS.json"
FILES = {
    "old_solver": PARENT / "selective_v447.py",
    "old_reference": PARENT / "reference_v447.py",
    "new_solver": HERE / "selective_v448.py",
    "new_reference": HERE / "reference_v448.py",
    "independent_dp": PARENT / "independent_dp_v447.py",
    "micro_inputs": INPUTS,
}
PINS = {
    "old_solver": "1bbdf82f14286102e31ec35a9fec7b8f8588c5d5cbe63935787aef59fad3e4f4",
    "old_reference": "9810d96023a7710329d34a42f5c831687ea73e09fbfb42968fe4c660366a7416",
    "new_solver": "f955dcb082a1e8fb4e683741a657c433209202f313571c07174d9ab15de42a6c",
    "new_reference": "9810d96023a7710329d34a42f5c831687ea73e09fbfb42968fe4c660366a7416",
    "independent_dp": "8c59f8695dfa2347b0f8ac5c817aec93c0c41e07c0882d45f099abaf4d9c2431",
    "micro_inputs": "0a5f38eba0565fb28a344b5987d3d3d2c0cc1a84c38489bfd1690c74b19cc2cc",
}
COUNT_KEYS = (
    "expanded", "expanded_phase0", "expanded_phase1", "generated",
    "terminal_generated", "pruned", "joint_checks_at_pop", "joint_pruned_at_pop",
    "dominated", "stale_pops", "queued", "peak_frontier",
)
SEMANTIC_KEYS = (
    "H2", "plan", "audit_trace", "root_bound", "root_priority", "remaining_bound",
    "certified_gap", "certified_optimal", "stop_reason", "initialization_overrun",
    "initial_node_stop", "node_limit", "requested_checkpoints",
) + COUNT_KEYS


def require(condition, context):
    if not condition:
        raise AssertionError(context)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n",
                          encoding="utf-8")


def emit(stream, value):
    stream.write(json.dumps(value, allow_nan=False) + "\n")
    stream.flush()


def check_pins():
    actual = {name: digest(path) for name, path in FILES.items()}
    require(actual == PINS, {"source_or_input_hash_changed": actual, "expected": PINS})
    return actual


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CheckLimit(RuntimeError):
    pass


class Budget:
    def __init__(self, seconds, global_deadline):
        self.started = time.perf_counter()
        self.deadline = min(self.started + seconds, global_deadline)

    def check(self, force=False):
        if time.perf_counter() >= self.deadline:
            raise CheckLimit("Correctness budget reached; partial work is not PASS.")

    def remaining(self):
        self.check(True)
        return self.deadline - time.perf_counter()


def state_dict(s):
    return {key: getattr(s, key) for key in
            ("phase", "oldmask", "a_delivered", "pos", "t")}


def threshold(values, quota, zero):
    if quota <= 0:
        return zero
    weight = 0
    for value, mass in sorted(values):
        weight += mass
        if weight >= quota:
            return value
    raise AssertionError("Insufficient weight in literal relaxation.")


def literal_union(math_ctx, s, base, watchdog, integer_wait=False):
    """No production full/cutoff calls or early-return shortcuts.

    Uses the frozen reference closure and individual mandatory-trip formulas.
    The interval method and integer waiting are independently looped here.
    """
    sp = math_ctx.spec
    alpha = [(i, via + sp["tau_a"])
             for i, via in math_ctx.individual_vias(s).items()]
    if integer_wait:
        times = range(base.B, max([base.B] + [a for _, a in alpha]) + 1)
    else:
        times = sorted({base.B} | {a for _, a in alpha if a >= base.B})
    best = math.inf
    evaluations = 0
    for x in times:
        watchdog.check()
        early = sum(math_ctx.old[i]["weight"] for i, a in alpha if a <= x)
        if early < base.qa:
            continue
        remaining = max(0, base.qb - early)
        gamma_values = [(math_ctx.gamma(i, x), math_ctx.old[i]["weight"])
                        for i, a in alpha if a > x] if remaining else []
        needed = threshold(gamma_values, remaining, x)
        best = min(best, max(math_ctx.fa(x), needed) + sp["tau_b"])
        evaluations += 1
    require(math.isfinite(best), ("literal relaxation finite", state_dict(s)))
    return dict(raw=best, full=max(base.value, best), events=evaluations, alpha=alpha)


def semantic(row):
    result = {key: row[key] for key in SEMANTIC_KEYS}
    result["trace"] = [{key: entry[key] for key in
                       ("H2", "plan", "expansion_index", "expansions_completed")}
                      for entry in row["trace"]]
    return result


def compare_rows(left, right, tag):
    require(semantic(left) == semantic(right), ("semantic parity", tag, semantic(left), semantic(right)))
    for key, value in left["stats"].items():
        if not key.endswith("_ns"):
            require(key in right["stats"] and right["stats"][key] == value,
                    ("counter parity", tag, key, value, right["stats"].get(key)))


def check_solution(row, optimum, spec, independent, watchdog):
    watchdog.check()
    require(row["H2"] == optimum and row["certified_optimal"] and row["certified_gap"] == 0,
            ("unlimited optimum/certificate", row["arm"], row.get("bound_basis"), row["H2"], optimum))
    replayed = independent.replay_plan(spec, row["plan"], max_seconds=watchdog.remaining())
    require(replayed == row["H2"], ("independent replay", row["arm"], replayed, row["H2"]))
    require(0 <= row["root_bound_seconds"] <= row["search_seconds"] <= row["elapsed_seconds"],
            ("timer nesting", row["arm"]))
    parts = row["setup_seconds"] + row["initial_seconds"] + row["search_seconds"]
    require(abs(parts-row["elapsed_seconds"]) <= 1e-8, ("timer sum", row["arm"]))
    require(row["expanded"] == row["expanded_phase0"] + row["expanded_phase1"],
            ("phase counts", row["arm"]))


def gate_trace_check(rows, basis):
    first = rows["FULL_GATE"]
    for name in ("CUTOFF", "GATED_CUTOFF"):
        other = rows[name]
        require(first["audit_trace"] == other["audit_trace"] and first["plan"] == other["plan"],
                ("gate search trace", basis, name))
        first_trace = [(x["H2"], x["plan"], x["expansion_index"]) for x in first["trace"]]
        other_trace = [(x["H2"], x["plan"], x["expansion_index"]) for x in other["trace"]]
        require(first_trace == other_trace, ("gate incumbent trace", basis, name))


def check_case(spec, original, new, independent, watchdog, streams, args, active):
    case = spec["case"]
    active.update(case=case, stage="independent_oracles", state=None)
    require(0 < len(spec["old"]) <= 5, ("micro scope", case))
    oracle = new.ref.ReferenceOracle(spec, watchdog)
    optimum = oracle.suffix(oracle.initial())
    dp = independent.solve(spec, max_seconds=watchdog.remaining())
    require(dp["status"] == "PASS" and dp["optimum_H2"] == optimum,
            ("independent DP vs timed exhaustive", case, optimum, dp))
    require(independent.replay_plan(spec, dp["plan"], max_seconds=watchdog.remaining()) == optimum,
            ("independent DP plan", case))
    emit(streams["oracles"], dict(case=case, timed_exhaustive_H2=optimum,
         timed_exhaustive_states=len(oracle.memo), independent_dp=dp))

    exact = new.Context(spec, watchdog, False, basis="exact")
    radius = new.Context(spec, watchdog, False, basis="radius")
    old = original.Context(spec, watchdog, False)
    math_ctx = new.ref.Context(spec, watchdog)
    counters = dict(prefixes=0, phase0=0, phase1=0, terminal=0,
                    literal_full_checks=0, shortcut_checks=0, cutoff_checks=0,
                    integer_wait_prefixes=0, integer_wait_evaluations=0,
                    integer_wait_horizon_skips=0, old_exact_parity_prefixes=0,
                    solution_checks=0, method_alias_checks=0)
    locals_by_basis = {"exact": {}, "radius": {}}
    active["stage"] = "all_timed_prefixes"
    states = sorted(oracle.memo, key=lambda s:
                    (s.phase, s.oldmask, s.a_delivered, s.pos, s.t))
    waiting_considered = 0
    for s in states:
        watchdog.check()
        true = oracle.memo[s]
        active["state"] = state_dict(s)
        counters["prefixes"] += 1
        if s.phase == 2:
            counters["terminal"] += 1
            require(s.t == true, ("terminal oracle", case, state_dict(s), true))
            for basis in locals_by_basis:
                locals_by_basis[basis][s] = (s.t, s.t)
            emit(streams["prefixes"], dict(case=case, state=state_dict(s), oracle=true,
                 exact_base=s.t, exact_full=s.t, radius_base=s.t, radius_full=s.t))
            continue
        be, br, bo = exact.base(s), radius.base(s), old.base(s)
        fe, fr, fo = exact.full(s, be), radius.full(s, br), old.full(s, bo)
        require((be.value, be.B, be.qa, be.qb, be.gb, fe) ==
                (bo.value, bo.B, bo.qa, bo.qb, bo.gb, fo),
                ("old exact local parity", case, state_dict(s)))
        counters["old_exact_parity_prefixes"] += 1
        require(s.t <= br.value <= be.value <= fe <= true and
                br.value <= fr <= fe and fr <= true,
                ("local strength/admissibility", case, state_dict(s),
                 br.value, be.value, fr, fe, true))
        locals_by_basis["exact"][s] = (be.value, fe)
        locals_by_basis["radius"][s] = (br.value, fr)
        detail = dict(case=case, state=state_dict(s), oracle=true,
                      exact_base=be.value, exact_full=fe, radius_base=br.value, radius_full=fr)
        if s.phase == 1:
            counters["phase1"] += 1
            phase1_ref = new.reference_phase1_bound(math_ctx, s)
            require(be.value == br.value == fe == fr == phase1_ref,
                    ("common phase1", case, state_dict(s)))
        else:
            counters["phase0"] += 1
            radius_expected, radius_detail = math_ctx.bound(s, "RADIUS_PRECEDENCE")
            require((br.value, br.B, br.qa, br.qb, br.gb) ==
                    (radius_expected, radius_detail["B"], radius_detail["qa"],
                     radius_detail["qb"], radius_detail["G_qb"]),
                    ("independent radius threshold", case, state_dict(s)))
            literal_e = literal_union(math_ctx, s, be, watchdog)
            literal_r = literal_union(math_ctx, s, br, watchdog)
            require(fe == literal_e["full"] and fr == literal_r["full"],
                    ("unshortcutted full identity", case, state_dict(s), literal_e, literal_r))
            counters["literal_full_checks"] += 2
            for basis, base, full, literal in (("exact", be, fe, literal_e),
                                              ("radius", br, fr, literal_r)):
                if base.gb + spec["tau_a"] <= base.B:
                    require(full == base.value and
                            literal["raw"] == math_ctx.fa(base.B) + spec["tau_b"],
                            ("shortcut full identity", case, basis, state_dict(s)))
                    counters["shortcut_checks"] += 1
            if waiting_considered < args.waiting_prefixes:
                waiting_considered += 1
                horizon = max([br.B] + [a for _, a in literal_r["alpha"]]) - br.B
                if horizon <= args.waiting_max_ticks:
                    waited = literal_union(math_ctx, s, br, watchdog, integer_wait=True)
                    require(waited["raw"] == literal_r["raw"], ("finite events vs integer waiting", case, state_dict(s)))
                    counters["integer_wait_prefixes"] += 1
                    counters["integer_wait_evaluations"] += waited["events"]
                else:
                    counters["integer_wait_horizon_skips"] += 1
            detail.update(radius_B=br.B, exact_B=be.B,
                          radius_literal_raw=literal_r["raw"], exact_literal_raw=literal_e["raw"])
        for ctx, base, full in ((exact, be, fe), (radius, br, fr)):
            for upper in sorted({max(0, full-1), full, full+1, base.value, base.value+1}):
                for gated in (False, True):
                    ctx.gamma_cache.clear()
                    answer = ctx.cutoff(s, base, upper, gated)
                    require(answer == (full >= upper),
                            ("Boolean/full equivalence", case, ctx.basis, state_dict(s), upper, gated))
                    counters["cutoff_checks"] += 1
        emit(streams["prefixes"], detail)
    require(radius.stats()["skip_exact_quota"] == 0 and exact.stats()["radius_calls"] == 0,
            ("basis counter attribution", case))
    active.update(stage="pathmax_edges", state=None)
    pathmax = {}
    for basis, ctx in (("exact", exact), ("radius", radius)):
        edges, combinations = new.verify_pathmax_edges(ctx, oracle, locals_by_basis[basis], watchdog)
        pathmax[basis] = dict(edges=edges, channel_combinations=combinations)

    active["stage"] = "unlimited_policy_parity_and_optima"
    defaults, radii = {}, {}
    for arm in new.ARMS:
        watchdog.check(True)
        prior = original.solve(spec, arm, watchdog, audit=True, checkpoints=())
        default = new.solve(spec, arm, watchdog, audit=True, checkpoints=())
        rad = new.solve(spec, arm, watchdog, audit=True, checkpoints=(), basis="radius")
        compare_rows(prior, default, (case, arm, "old vs default exact"))
        for kind, row in (("old_v447", prior), ("v448_default_exact", default), ("v448_radius", rad)):
            check_solution(row, optimum, spec, independent, watchdog)
            emit(streams["solves"], dict(verification_variant=kind, **row))
            counters["solution_checks"] += 1
        require(default["bound_basis"] == "exact" and rad["bound_basis"] == "radius",
                ("basis metadata", case, arm))
        defaults[arm], radii[arm] = default, rad
    explicit = new.solve(spec, "ROUTE", watchdog, audit=True, checkpoints=(), basis="exact")
    compare_rows(defaults["ROUTE"], explicit, (case, "explicit/default exact"))
    check_solution(explicit, optimum, spec, independent, watchdog)
    emit(streams["solves"], dict(verification_variant="v448_explicit_exact", **explicit))
    counters["solution_checks"] += 1
    for name in ("RADIUS", "RADIUS_PAIR_LAZY", "RADIUS_PAIR_EAGER", "RADIUS_AWA"):
        arm, basis = new.METHOD_MAP[name]
        named = new.solve_method(spec, name, watchdog, audit=True, checkpoints=())
        require(basis == "radius" and named["method"] == name, ("method alias", name))
        compare_rows(radii[arm], named, (case, name))
        check_solution(named, optimum, spec, independent, watchdog)
        emit(streams["solves"], dict(verification_variant="v448_named_alias", **named))
        counters["solution_checks"] += 1
        counters["method_alias_checks"] += 1
    gate_trace_check(defaults, "exact")
    gate_trace_check(radii, "radius")
    profiled = new.solve(spec, "LAZY_ASTAR", watchdog, audit=True, checkpoints=(),
                         profile=True, basis="radius")
    # Compare policy semantics; profiled stats deliberately contain extra counters.
    require(semantic(profiled) == semantic(radii["LAZY_ASTAR"]), ("profile semantic parity", case))
    require(profiled["stats"]["quota_dp_labels"] == 0 and
            profiled["stats"]["radius_calls"] > 0, ("radius bypasses exact quota DP", case))
    check_solution(profiled, optimum, spec, independent, watchdog)
    emit(streams["solves"], dict(verification_variant="v448_radius_profile", **profiled))
    counters["solution_checks"] += 1
    closure_checks = new.independent_closure(spec, watchdog)
    return dict(status="PASS", case=case, seed=spec["seed"], m=len(spec["old"]),
                optimum_H2=optimum, counters=counters, pathmax=pathmax,
                closure_comparisons=closure_checks,
                gate_trace_equivalence_both_bases=True,
                elapsed_seconds=time.perf_counter()-watchdog.started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--case-seconds", type=float, default=30.0)
    parser.add_argument("--max-seconds", type=float, default=60.0)
    parser.add_argument("--waiting-prefixes", type=int, default=8)
    parser.add_argument("--waiting-max-ticks", type=int, default=4096)
    args = parser.parse_args()
    if args.offset < 0 or not 1 <= args.limit <= 4:
        parser.error("Use offset >=0 and 1..4 micro cases per fresh bounded run.")
    if not 0 < args.case_seconds <= 60 or not 0 < args.max_seconds <= 60:
        parser.error("Both time limits must be positive and at most 60 seconds.")
    if not 0 <= args.waiting_prefixes <= 32 or not 1 <= args.waiting_max_ticks <= 4096:
        parser.error("Invalid bounded integer-wait verification limits.")
    run = args.run if args.run.is_absolute() else HERE/args.run
    run = run.resolve()
    if run == HERE or HERE not in run.parents or run.exists():
        parser.error("Use a new descendant of V448; prior artifacts are never overwritten.")
    run.mkdir(parents=True, exist_ok=False)
    os.environ.update(TEMP=r"E:\CodexResearch-xi\temp", TMP=r"E:\CodexResearch-xi\temp",
                      PYTHONDONTWRITEBYTECODE="1")
    started = time.perf_counter()
    global_deadline = started + args.max_seconds
    active = dict(case=None, stage="hashes_and_imports", state=None)
    try:
        pins = check_pins()
        all_cases = json.loads(INPUTS.read_text(encoding="utf-8-sig"))
        require(len(all_cases) == 24 and all(3 <= len(s["old"]) <= 5 for s in all_cases),
                "Expected the frozen 24 micro cases with m3/m4/m5.")
        require(args.offset + args.limit <= len(all_cases), "Selected range exceeds frozen micro suite.")
        cases = all_cases[args.offset:args.offset+args.limit]
        write_json(run/"INPUTS.json", cases)
        protocol = dict(status="RUN_STARTED",scope="selected frozen micro cases only, no performance claims",
            offset=args.offset, limit=args.limit, total_frozen_micro_cases=24,
            case_seconds=args.case_seconds, max_seconds=args.max_seconds,
            waiting_prefixes=args.waiting_prefixes, waiting_max_ticks=args.waiting_max_ticks,
            input_sha256=pins["micro_inputs"], runner_sha256=digest(__file__),
            sources={name:dict(path=str(FILES[name]),sha256=value) for name,value in pins.items()},
            selected_cases=[s["case"] for s in cases], all_internal_policies_both_bases=True,
            proof_scope_m_max=5, main_results_read=False)
        write_json(run/"PROTOCOL.json", protocol)
        original = load("v448_check_original_solver", FILES["old_solver"])
        new = load("v448_check_new_solver", FILES["new_solver"])
        independent = load("v448_check_independent_dp", FILES["independent_dp"])
        summaries = []
        with gzip.open(run/"PREFIX_CHECKS.jsonl.gz","wt",encoding="utf-8") as prefix, \
                (run/"SOLVES.jsonl").open("w",encoding="utf-8") as solves, \
                (run/"ORACLES.jsonl").open("w",encoding="utf-8") as oracles, \
                (run/"CASE_COMPLETE.jsonl").open("w",encoding="utf-8") as completed:
            streams = dict(prefixes=prefix,solves=solves,oracles=oracles)
            for case in cases:
                watchdog = Budget(args.case_seconds, global_deadline)
                watchdog.check(True)
                result = check_case(case, original, new, independent, watchdog, streams, args, active)
                watchdog.check(True)
                emit(completed,result)
                summaries.append(result)
                print(json.dumps(dict(case=case["case"],status="PASS",
                                      elapsed_seconds=result["elapsed_seconds"])),flush=True)
        check_pins()
        require(time.perf_counter() < global_deadline, "Overall correctness limit reached before completion.")
        summary = dict(status="PASS",scope="selected micro batch; not authorization for performance",
            source_sha256=PINS["new_solver"],reference_sha256=PINS["new_reference"],
            micro_input_sha256=PINS["micro_inputs"],offset=args.offset,case_count=len(summaries),
            full_micro_suite_complete=(len(summaries)==24),cases=summaries,
            elapsed_seconds=time.perf_counter()-started)
        write_json(run/"SUMMARY.json",summary)
        hashes={p.name:digest(p) for p in run.iterdir() if p.is_file()}
        write_json(run/"OUTPUT_HASHES.json",hashes)
        write_json(run/"PROCESS_COMPLETE.json",dict(status="PASS",case_count=len(summaries),
                   offset=args.offset,elapsed_seconds=time.perf_counter()-started))
        return 0
    except BaseException as exc:
        failure=dict(status="FAIL",exception=type(exc).__name__,message=str(exc),
                     active=active,elapsed_seconds=time.perf_counter()-started,
                     traceback=traceback.format_exc(),partial_work_is_not_pass=True)
        write_json(run/"FAILURE.json",failure)
        write_json(run/"PROCESS_COMPLETE.json",dict(status="FAIL",exception=type(exc).__name__,
                   elapsed_seconds=time.perf_counter()-started))
        print(json.dumps(dict(status="FAIL",exception=type(exc).__name__,message=str(exc))),flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

