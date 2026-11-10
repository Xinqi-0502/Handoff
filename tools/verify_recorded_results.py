#!/usr/bin/env python3
"""Recompute manuscript endpoints from frozen JSON/JSONL, without running the solver.

A replay of measurements is different from measuring new wall times or RAM.
This audit reads source records and writes JSON to stdout. It never edits a run.
"""
import argparse
from collections import Counter, defaultdict
from itertools import product
import json
from pathlib import Path
from statistics import median

V449 = "fleet_study_v449_validation_and_online_20261107"
V450 = "fleet_study_v450_full_baselines_memory_online_20261107"
AWA = "HZ_AWA_RADIUS"
PAIR = "HZ_AWA_RADIUS_PAIR_GATED"
ANA = "ANA_RADIUS"
SPECIAL = "RADIUS_PAIR_AWA_GATED"
METHODS = (AWA, PAIR, ANA, SPECIAL)
BUDGETS = (100, 500, 1000)
FRACTIONS = (0, 0.05, 0.10)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rows(path):
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def changed(candidate, baseline):
    return 100 * (candidate / baseline - 1)


def proof(row):
    return row["certified_optimal"] and row["elapsed_seconds"] <= 1


def first_time(row, target):
    return next(
        (event["seconds"] for event in row["trace"] if event["H2"] <= target),
        None,
    )


def quality(row, milliseconds):
    return min(
        (event["H2"] for event in row["trace"] if event["seconds"] * 1000 <= milliseconds),
        default=None,
    )


def pair_proof(groups, cases, candidate, baseline):
    common = [
        case for case in cases
        if all(proof(row) for method in (candidate, baseline) for row in groups[case, method])
    ]
    candidate_expanded = sum(median(row["expanded"] for row in groups[c, candidate]) for c in common)
    baseline_expanded = sum(median(row["expanded"] for row in groups[c, baseline]) for c in common)
    per_case = {
        case: tuple(median(row["elapsed_seconds"] for row in groups[case, method])
                    for method in (candidate, baseline))
        for case in common
    }
    candidate_seconds = sum(x for x, _ in per_case.values())
    baseline_seconds = sum(y for _, y in per_case.values())
    result = {
        "common_cases": len(common),
        "candidate_expanded": candidate_expanded,
        "baseline_expanded": baseline_expanded,
        "expanded_change_percent": changed(candidate_expanded, baseline_expanded),
        "candidate_proof_seconds": candidate_seconds,
        "baseline_proof_seconds": baseline_seconds,
        "proof_time_change_percent": changed(candidate_seconds, baseline_seconds),
        "candidate_faster": sum(x < y for x, y in per_case.values()),
        "ties": sum(x == y for x, y in per_case.values()),
        "candidate_slower": sum(x > y for x, y in per_case.values()),
    }
    return result, per_case


def require_repeats(groups, cases, methods, source):
    expected = set(product(cases, methods))
    require(set(groups) == expected, f"Unexpected scenario/method coverage in {source}")
    for key, group in groups.items():
        require(sorted(row["repeat"] for row in group) == [0, 1, 2],
                f"Missing/duplicate technical repeat in {source}: {key}")


def confirmation(root):
    run = root / "static_comparison/runs/main_01"
    specs = {spec["case"]: spec for spec in read_json(run / "INPUTS.json")}
    oracles = {
        row["case"]: row["result"]["optimum_H2"]
        for row in rows(run / "ORACLES.jsonl") if row["result"]["status"] == "PASS"
    }
    require(len(specs) == 256 and set(specs) == set(oracles), "Confirmation input/oracle coverage")
    networks = defaultdict(list)
    for case, spec in specs.items():
        networks[spec["seed"]].append(case)
    require(len(networks) == 64 and all(len(ids) == 4 for ids in networks.values()),
            "Confirmation design coverage")
    groups = defaultdict(list)
    for row in rows(run / "MEASUREMENTS.jsonl"):
        case = row["case"]
        require(row["status"] == "OK", f"Unrecovered confirmation measurement: {case}")
        require(row["oracle_H2"] == oracles[case], f"Independent optimum mismatch: {case}")
        require(row["H2"] >= oracles[case] and
                (not row["certified_optimal"] or row["H2"] == oracles[case]),
                f"Invalid certificate: {case}")
        require(row["expanded"] == row["expanded_phase0"] + row["expanded_phase1"],
                f"Expansion accounting mismatch: {case}")
        require(row["trace"][-1]["H2"] == row["H2"], f"Trace final value mismatch: {case}")
        for ms in BUDGETS:
            require(quality(row, ms) == row["literal_quality"][str(ms)], f"Quality trace mismatch: {case}")
        groups[case, row["method"]].append(row)
    require_repeats(groups, specs, METHODS, run)
    paired, times = pair_proof(groups, specs, PAIR, AWA)
    require((paired["common_cases"], paired["candidate_expanded"], paired["baseline_expanded"],
             paired["candidate_faster"], paired["candidate_slower"]) == (255, 77362, 170932, 233, 22),
            "Primary paired proof endpoints differ from manuscript")
    require(round(paired["proof_time_change_percent"], 2) == -27.17, "Proof-time result differs")
    require(round(paired["expanded_change_percent"], 2) == -54.74, "Expansion result differs")
    complete_networks = [cases for cases in networks.values() if all(case in times for case in cases)]
    improvements = sum(sum(times[c][0] for c in cases) < sum(times[c][1] for c in cases)
                       for cases in complete_networks)
    require((len(complete_networks), improvements) == (63, 60), "Network aggregation differs")
    by_method = {
        method: {
            "all_repeats_optimal_at_ms": {
                str(ms): sum(all(quality(r, ms) == oracles[c] for r in groups[c, method]) for c in specs)
                for ms in BUDGETS
            },
            "all_repeats_certified_within_one_second": sum(
                all(proof(r) for r in groups[c, method]) for c in specs),
        }
        for method in METHODS
    }
    expected = {
        AWA: (223, 255, 256, 255), PAIR: (227, 256, 256, 256),
        ANA: (207, 251, 256, 255), SPECIAL: (232, 256, 256, 256),
    }
    for method, observed in by_method.items():
        endpoints = (*observed["all_repeats_optimal_at_ms"].values(),
                     observed["all_repeats_certified_within_one_second"])
        require(endpoints == expected[method], f"Appendix Table B2 differs: {method}")
    first = {}
    for fraction in FRACTIONS:
        summed = {}
        for method in METHODS:
            case_times = []
            for case, spec in specs.items():
                optimum = oracles[case]
                target = optimum + fraction * (optimum - spec["t0"])
                hits = [first_time(row, target) for row in groups[case, method]]
                require(all(t is not None and t <= 1 for t in hits), f"Missing first target: {case}")
                case_times.append(median(hits))
            summed[method] = sum(case_times)
        first[str(fraction)] = {
            "sum_case_median_seconds": summed,
            "pair_change_percent": changed(summed[PAIR], summed[AWA]),
        }
    require([round(result["pair_change_percent"], 2) for result in first.values()] == [-7.96, 2.82, 4.07],
            "Figure 2 first-target endpoints differ")
    by_scale = {str(m): pair_proof(groups, [c for c, spec in specs.items() if len(spec["old"]) == m],
                                  PAIR, AWA)[0] for m in (6, 8, 10, 12)}
    relations = Counter(
        (x > y) - (x < y) for x, y in (
            (median(quality(row, 100) for row in groups[c, PAIR]),
             median(quality(row, 100) for row in groups[c, AWA])) for c in specs
        )
    )
    require(dict(relations) == {-1: 6, 0: 249, 1: 1}, "100 ms case-median comparison differs")
    return {
        "source": "V450 static_comparison/runs/main_01/{INPUTS,ORACLES,MEASUREMENTS}",
        "cases": len(specs),
        "independent_networks": len(networks),
        "formal_calls": sum(map(len, groups.values())),
        "pair_vs_awa": paired,
        "pair_vs_ana": pair_proof(groups, specs, PAIR, ANA)[0],
        "pair_vs_specialized_pair": pair_proof(groups, specs, PAIR, SPECIAL)[0],
        "figure_1_by_old_orders": by_scale,
        "figure_2_first_target": first,
        "appendix_table_B2": by_method,
        "complete_networks_faster": improvements,
        "complete_networks_compared": len(complete_networks),
        "100_ms_case_median_pair_lower_equal_higher": [relations[i] for i in (-1, 0, 1)],
    }


def selection(root):
    run_paths = sorted((root / "runs").glob("scale_main_m*/MEASUREMENTS.jsonl"))
    groups = defaultdict(list)
    networks = set()
    cases = set()
    for path in run_paths:
        for row in rows(path):
            require(row["outcome"] == "OK", f"Missing selection measurement in {path}")
            cases.add(row["case"])
            networks.add(row["seed"])
            groups[row["case"], row["method"]].append(row)
    require((len(cases), len(networks)) == (400, 100), "Selection design coverage")
    methods = sorted({method for _, method in groups})
    require(len(methods) == 9, "Selection method coverage")
    require_repeats(groups, cases, methods, root)
    comparisons = [
        ("RADIUS_PAIR_EAGER", "RADIUS", 400, -55.72, 12.57),
        ("RADIUS_PAIR_LAZY", "RADIUS", 400, -55.72, -11.62),
        ("RADIUS_PAIR_AWA", "RADIUS_AWA", 400, -56.89, -2.41),
        (SPECIAL, "RADIUS_AWA", 400, -54.04, -21.65),
        (SPECIAL, "RADIUS_PAIR_AWA", 400, 6.60, -19.72),
        (SPECIAL, "NO_BOUND", 400, -95.87, -70.50),
        (SPECIAL, "ROUTE", 284, 0.13, -93.01),
    ]
    compared = {}
    for candidate, baseline, n, expanded, elapsed in comparisons:
        result, _ = pair_proof(groups, sorted(cases), candidate, baseline)
        require((result["common_cases"], round(result["expanded_change_percent"], 2),
                 round(result["proof_time_change_percent"], 2)) == (n, expanded, elapsed),
                f"Appendix Table B1 differs: {candidate}/{baseline}")
        compared[f"{candidate} / {baseline}"] = result
    require(compared[f"{SPECIAL} / NO_BOUND"]["candidate_slower"] == 14,
            "Selection unpruned per-case regression count differs")
    return {
        "source": "V449 runs/scale_main_m*/MEASUREMENTS.jsonl",
        "cases": len(cases),
        "independent_networks": len(networks),
        "technical_calls": sum(map(len, groups.values())),
        "appendix_table_B1": compared,
    }


def memory(root):
    files = sorted((root / "memory/runs").glob("main_[0-9][0-9]_01/MEMORY.jsonl"))
    raw = defaultdict(list)
    keys = set()
    for path in files:
        for row in rows(path):
            require(row["status"] == "OK", f"Unrecovered formal memory observation: {path}")
            key = (row["case"], row["method"])
            require(key not in keys, f"Duplicate formal memory observation: {key}")
            keys.add(key)
            raw[row["method"]].append(row)
    require(set(raw) == set(METHODS) and all(len(x) == 32 for x in raw.values()),
            "Formal memory coverage")
    table = {}
    for method, observations in raw.items():
        resident = "PeakWorkingSetSize"
        commit = "PeakPagefileUsage"
        table[method] = {
            "observations": len(observations),
            "peak_working_set_median_KiB": median(
                row["post_solve"]["counters_bytes"][resident] for row in observations) / 1024,
            "peak_commit_median_KiB": median(
                row["post_solve"]["counters_bytes"][commit] for row in observations) / 1024,
            "peak_working_set_did_not_exceed_startup": sum(
                row["post_solve"]["counters_bytes"][resident] == row["pre_solve"]["counters_bytes"][resident]
                for row in observations),
        }
    expected = {AWA: (27236, 19296, 28), PAIR: (27114, 19126, 30),
                ANA: (27128, 19128, 28), SPECIAL: (27042, 19048, 32)}
    for method, values in table.items():
        require(tuple(values.values())[1:] == expected[method], f"Appendix Table B3 differs: {method}")
    return {"source": "V450 memory/runs/main_[00-31]_01/MEMORY.jsonl",
            "fresh_process_observations": len(keys), "appendix_table_B3": table}


def replay_values(raw, summary):
    deliveries = {}
    releases = {}
    transfers = {}
    starts = {}
    truck_arrival = None
    for tick, action, actor, job, *_ in raw["events"]:
        if action == "delivery":
            require(job not in deliveries, f"Duplicate completed job: {job}")
            deliveries[job] = tick
        elif action == "release":
            releases[job] = tick
        elif action == "beginX":
            starts[job] = tick
        elif action == "transfer":
            transfers[job] = tick
        elif action == "arrive" and actor == "T" and job == "Xa":
            truck_arrival = tick
    require(len(deliveries) == 18 and deliveries == raw["completed"], "Physical delivery coverage")
    require(set(starts) == set(transfers) == set(releases) == {"a", "b"}, "Two handoffs and releases required")
    require(truck_arrival is not None, "Physical truck arrival is missing")
    flow = sum(tick - releases.get(job, 0) for job, tick in deliveries.items()) / 5
    dwell_ticks = transfers["b"] - truck_arrival
    service_ticks = sum(transfers[job] - starts[job] for job in transfers)
    wait = (dwell_ticks - service_ticks) / 5
    require(abs(flow - summary["J_customer_seconds"]) < 1e-8, "Native flow summary differs")
    require(abs(wait - summary["truck_wait_excluding_transfer_seconds"]) < 1e-8, "Native wait summary differs")
    require(raw["collision_ticks"] == 0 and raw["teleports"] == 0, "Native collision or teleport")
    return flow, wait


def online(root):
    run = root / "online/runs/full_02"
    calls = list(rows(run / "RESULTS.jsonl"))
    physical = read_json(run / "PHYSICAL.json")
    require(len(calls) == 1728 and len(physical) == 128, "Formal online coverage")
    outcomes = {}
    for item in physical:
        key = item["case"], item["signature"], item["activation_tick"]
        require(key not in outcomes and item["status"] == "PASS", f"Bad native replay: {key}")
        # Historical folder names are leaves. Do not resolve an embedded path outside the run.
        folder = item["folder"]
        require(Path(folder).name == folder and folder.startswith("native_"), f"Invalid replay folder: {folder}")
        raw = read_json(run / folder / "RESULT.json")
        audit = read_json(run / folder / "AUDIT.json")
        require(audit["status"] == "PASS" and raw["activation_tick"] == item["activation_tick"],
                f"Native audit or activation mismatch: {key}")
        outcomes[key] = replay_values(raw, item)
    cohorts = defaultdict(dict)
    keys = set()
    for call in calls:
        case, arm, rep = call["case"], call["arm"], call["rep"]
        if arm == "HZ_AWA_PAIR_GATED":
            arm = PAIR  # Normalize the historical online spelling for the output.
        ms = round(call["budget_seconds"] * 1000)
        key = (case, arm, ms, rep)
        require(key not in keys, f"Duplicate formal online call: {key}")
        keys.add(key)
        require((case, call["executed_signature"], call["activation_tick"]) in outcomes,
                f"No archived native execution for: {key}")
        if arm in (AWA, PAIR):
            cohorts[case, arm, ms][rep] = call
    cases = sorted({c["case"] for c in calls})
    require(len(cases) == 64 and len({c["seed"] for c in calls}) == 8, "Online design coverage")
    by_budget = {}
    for ms in (10, 50, 200):
        elapsed = {AWA: 0.0, PAIR: 0.0}
        expanded = Counter()
        init_overruns = Counter()
        flow = {AWA: 0.0, PAIR: 0.0}
        wait = {AWA: 0.0, PAIR: 0.0}
        proved = Counter()
        common_proofs = 0
        for case in cases:
            case_calls = {arm: cohorts[case, arm, ms] for arm in (AWA, PAIR)}
            require(all(set(r) == {0, 1, 2} for r in case_calls.values()), "Missing online repeat")
            for rep in range(3):
                a, b = (case_calls[arm][rep] for arm in (AWA, PAIR))
                require(a["executed_signature"] == b["executed_signature"]
                        and a["activation_tick"] == b["activation_tick"],
                        f"Physical execution differs for {case}, {ms} ms, repeat {rep}")
            all_proved = {
                arm: all(row["certified_forecast_optimal_by_deadline"] for row in group.values())
                for arm, group in case_calls.items()
            }
            paired_proof = all(all_proved.values())
            common_proofs += paired_proof
            for arm, group in case_calls.items():
                measurements = list(group.values())
                proved[arm] += all_proved[arm]
                if paired_proof:
                    elapsed[arm] += median(row["elapsed_seconds"] for row in measurements)
                expanded[arm] += median(row["counts"]["expanded"] for row in measurements)
                init_overruns[arm] += sum(row["stop_reason"] == "initialization_overrun" for row in measurements)
                for row in measurements:
                    j, w = outcomes[case, row["executed_signature"], row["activation_tick"]]
                    flow[arm] += j / 3 / len(cases)
                    wait[arm] += w / 3 / len(cases)
        result = {
            "cases_with_identical_executed_signatures_and_ticks": len(cases),
            "common_all_repeat_proofs": common_proofs,
            "all_repeat_proof_counts": dict(proved),
            "case_median_expansion_totals": dict(expanded),
            "initialization_overrun_calls": dict(init_overruns),
            "mean_customer_flow_seconds": flow,
            "mean_truck_wait_seconds": wait,
        }
        if ms in (50, 200):
            result["expansion_change_percent"] = changed(expanded[PAIR], expanded[AWA])
            result["proof_time_change_percent"] = changed(elapsed[PAIR], elapsed[AWA])
            require(round(result["expansion_change_percent"], 2) == -2.70, f"Online expansion comparison differs at {ms}")
            expected = (63, 5.57) if ms == 50 else (64, 2.87)
            require((common_proofs, round(result["proof_time_change_percent"], 2)) == expected,
                    f"Online proof comparison differs at {ms}")
        if ms == 10:
            require((init_overruns[PAIR], init_overruns[AWA]) == (192, 191), "10 ms overrun counts differ")
        if ms == 50:
            require(abs(flow[PAIR] - 2416.040625) < 1e-7 and abs(wait[PAIR] - 264.0875) < 1e-7,
                    "50 ms physical aggregates differ")
        by_budget[str(ms)] = result
    return {
        "source": "V450 online/runs/full_02/{RESULTS.jsonl,PHYSICAL.json,native_*/RESULT.json}",
        "cases": len(cases), "policy_calls": len(calls), "native_replays": len(outcomes),
        "budget_ms": by_budget,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="Checkout root containing the work directory")
    args = parser.parse_args()
    root = args.root.resolve()
    result = {
        "status": "PASS",
        "scope": "Recomputed from archived traces, result events and native memory counters. No new solve or simulation.",
        "selection": selection(root / "work" / V449),
        "confirmation": confirmation(root / "work" / V450),
        "memory": memory(root / "work" / V450),
        "online": online(root / "work" / V450),
    }
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
