"""Read-only evidence gate for all 24 frozen V448 micro correctness cases.

API: current_sources() -> {filename: SHA256}; validate_gate(path) -> gate dict.
validate_gate accepts GATE.json or its directory and rechecks original evidence.
Missing files fail when an API is called; importing this module reads no artifacts
and imports no solver. The nine measurement sources are frozen at assembly time.

CLI (future explicit invocation only):
  python -B micro_gate_v448.py --runs-json records/selected_checks.json --out gates/micro_all_01
Selection JSON is a path array or {"runs": [paths]}; paths are absolute or relative
to V448. Only selected PASS attempts count. Old failed attempts remain untouched.
No correctness run, numerical solver, or performance authorization is performed.
"""
from pathlib import Path
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import traceback

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "fleet_study_v447_random_high_load_20261107"
CHECKER_SHA = "beec4805585dbf8224cad60a2fd107b73e2ec80cae4df199166b4ed0e074eb73"
SOURCE_PATHS = {name: HERE / name for name in (
    "selective_v448.py", "reference_v448.py", "check_v448.py", "instances_v448.py",
    "run_v448.py", "run_jobs_v448.py", "micro_gate_v448.py")}
SOURCE_PATHS.update({name: PARENT / name for name in
                     ("independent_dp_v447.py", "instances_v447.py")})
PIN_PATHS = dict(old_solver=PARENT / "selective_v447.py",
    old_reference=PARENT / "reference_v447.py", new_solver=HERE / "selective_v448.py",
    new_reference=HERE / "reference_v448.py", independent_dp=PARENT / "independent_dp_v447.py",
    micro_inputs=PARENT / "instances" / "micro_01" / "INPUTS.json")
ARMS = ("NO_BOUND", "ROUTE", "PAIR_EAGER", "LAZY_ASTAR", "FULL_GATE", "CUTOFF",
        "GATED_CUTOFF", "AWA_ROUTE", "AWA_PAIR", "AWA_GATED")
ALIASES = {"RADIUS": "ROUTE", "RADIUS_PAIR_LAZY": "LAZY_ASTAR",
           "RADIUS_PAIR_EAGER": "PAIR_EAGER", "RADIUS_AWA": "AWA_ROUTE"}
RAW_FILES = {"INPUTS.json", "PROTOCOL.json", "SUMMARY.json", "CASE_COMPLETE.jsonl",
             "SOLVES.jsonl", "ORACLES.jsonl", "PREFIX_CHECKS.jsonl.gz"}


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def current_sources():
    """Hash all required measurement sources now; absent sources are errors."""
    return {name: digest(path) for name, path in SOURCE_PATHS.items()}


def resolved(path):
    path = Path(path)
    return (path if path.is_absolute() else HERE / path).resolve()


def descendant(path):
    require(HERE in path.parents, f"Path must be a descendant of V448: {path}")
    return path


class Evidence:
    def __init__(self):
        self.hashes = {}

    def read(self, path):
        path = Path(path).resolve()
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        old = self.hashes.setdefault(str(path), sha)
        require(old == sha, f"Evidence changed while reading: {path}")
        return data

    def json(self, path):
        return json.loads(self.read(path).decode("utf-8-sig"))

    def rows(self, path, compressed=False):
        data = self.read(path)
        if compressed:
            data = gzip.decompress(data)
        return [json.loads(line) for line in data.decode("utf-8-sig").splitlines() if line.strip()]

    def unchanged(self):
        for path, expected in self.hashes.items():
            require(digest(path) == expected, f"Evidence changed before gate: {path}")


def checker_pins(evidence):
    path = HERE / "check_v448.py"
    data = evidence.read(path)
    require(hashlib.sha256(data).hexdigest() == CHECKER_SHA, "Unreviewed checker version")
    tree = ast.parse(data.decode("utf-8-sig"))
    values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "PINS" for t in n.targets)]
    require(len(values) == 1 and set(values[0]) == set(PIN_PATHS), "Checker pin schema mismatch")
    pins = values[0]
    for name, path in PIN_PATHS.items():
        actual = hashlib.sha256(evidence.read(path)).hexdigest()
        require(actual == pins[name], f"Checker source/input changed: {name}")
    return pins


def check_case_summary(row, spec, waiting_prefixes):
    require(row["status"] == "PASS" and row["case"] == spec["case"]
            and row["seed"] == spec["seed"] and row["m"] == len(spec["old"]), "Case summary identity")
    require(row["gate_trace_equivalence_both_bases"] is True, "Missing gate trace check")
    c = row["counters"]
    for key, value in c.items():
        require(type(value) is int and value >= 0, f"Invalid check count: {key}")
    for key in ("prefixes", "phase0", "phase1", "terminal", "literal_full_checks",
                "cutoff_checks", "old_exact_parity_prefixes", "solution_checks", "method_alias_checks"):
        require(c[key] > 0, f"Empty required check: {key}")
    require(c["prefixes"] == c["phase0"] + c["phase1"] + c["terminal"], "Prefix accounting")
    require(c["old_exact_parity_prefixes"] == c["phase0"] + c["phase1"], "Old exact parity coverage")
    require(c["literal_full_checks"] == 2 * c["phase0"], "Literal full bound coverage")
    require(c["solution_checks"] == 36 and c["method_alias_checks"] == 4, "Policy/alias coverage")
    require(c["cutoff_checks"] % 4 == 0, "Cutoff channel count")
    require(c["integer_wait_prefixes"] + c["integer_wait_horizon_skips"] ==
            min(waiting_prefixes, c["phase0"]), "Waiting sample accounting")
    require(c["integer_wait_evaluations"] >= c["integer_wait_prefixes"], "Waiting evaluation count")
    require(row["closure_comparisons"] > 0, "Empty closure check")
    require(set(row["pathmax"]) == {"exact", "radius"}, "Pathmax basis coverage")
    for channel in row["pathmax"].values():
        require(channel["edges"] > 0 and channel["channel_combinations"] == 4 * channel["edges"],
                "Empty/incomplete pathmax checks")
    require(row["pathmax"]["exact"] == row["pathmax"]["radius"], "Pathmax edge coverage differs")


def collect(selected_runs):
    """Validate persisted output only; never invokes any solver/checker function."""
    sources = current_sources()
    evidence = Evidence()
    pins = checker_pins(evidence)
    specs = evidence.json(PIN_PATHS["micro_inputs"])
    require(len(specs) == 24 and len({s["case"] for s in specs}) == 24
            and all(3 <= len(s["old"]) <= 5 for s in specs), "Frozen 24-case input schema")
    expected_sources = {k: dict(path=str(PIN_PATHS[k]), sha256=v) for k, v in pins.items()}
    paths = [descendant(resolved(path)) for path in selected_runs]
    require(paths and len(set(paths)) == len(paths), "Empty or duplicate selected run paths")
    summaries = {}
    totals = Counter()
    for run in paths:
        require(run.is_dir() and not (run / "FAILURE.json").exists(), f"Missing/failed selected run: {run}")
        done = evidence.json(run / "PROCESS_COMPLETE.json")
        protocol = evidence.json(run / "PROTOCOL.json")
        summary = evidence.json(run / "SUMMARY.json")
        inputs = evidence.json(run / "INPUTS.json")
        rows = evidence.rows(run / "CASE_COMPLETE.jsonl")
        output_hashes = evidence.json(run / "OUTPUT_HASHES.json")
        require(RAW_FILES <= set(output_hashes), "Incomplete original output hash manifest")
        for name, sha in output_hashes.items():
            require(Path(name).name == name and name not in (".", ".."), "Unsafe output manifest entry")
            require(hashlib.sha256(evidence.read(run / name)).hexdigest() == sha,
                    f"Original output hash mismatch: {run / name}")
        require(done["status"] == summary["status"] == "PASS", "Selected run did not pass")
        offset, limit = protocol["offset"], protocol["limit"]
        require(type(offset) is int and type(limit) is int and offset >= 0 and 1 <= limit <= 4
                and offset + limit <= 24, "Selected range invalid")
        selected_specs = specs[offset:offset + limit]
        ids = [s["case"] for s in selected_specs]
        require(protocol["total_frozen_micro_cases"] == 24 and protocol["selected_cases"] == ids
                and inputs == selected_specs, "Selected case/input identity mismatch")
        require(protocol["runner_sha256"] == CHECKER_SHA and protocol["sources"] == expected_sources
                and protocol["input_sha256"] == pins["micro_inputs"], "Protocol source identity")
        require(protocol["all_internal_policies_both_bases"] is True
                and protocol["proof_scope_m_max"] == 5 and protocol["main_results_read"] is False,
                "Checker verification scope mismatch")
        require(protocol["waiting_prefixes"] == 8 and protocol["waiting_max_ticks"] == 4096,
                "Frozen waiting-check settings required")
        require(0 < protocol["case_seconds"] <= 60 and 0 < protocol["max_seconds"] <= 60,
                "Micro check budget out of scope")
        require(done["offset"] == summary["offset"] == offset
                and done["case_count"] == summary["case_count"] == limit, "Completion range mismatch")
        require(summary["source_sha256"] == pins["new_solver"]
                and summary["reference_sha256"] == pins["new_reference"]
                and summary["micro_input_sha256"] == pins["micro_inputs"], "Summary source identity")
        require(rows == summary["cases"] and [r["case"] for r in rows] == ids, "Case completion mismatch")
        for row, spec in zip(rows, selected_specs):
            require(row["case"] not in summaries, "Repeated case across selected retries")
            check_case_summary(row, spec, protocol["waiting_prefixes"])
            summaries[row["case"]] = row
            totals.update(row["counters"])

        solve_rows = evidence.rows(run / "SOLVES.jsonl")
        oracle_rows = evidence.rows(run / "ORACLES.jsonl")
        prefix_rows = evidence.rows(run / "PREFIX_CHECKS.jsonl.gz", compressed=True)
        require(all(r["case"] in ids for r in solve_rows + oracle_rows + prefix_rows), "Foreign case in raw rows")
        for case in ids:
            row = summaries[case]
            optimum = row["optimum_H2"]
            sols = [r for r in solve_rows if r["case"] == case]
            matrix = Counter((r["verification_variant"], r["arm"]) for r in sols)
            expected = Counter((variant, arm) for variant in
                ("old_v447", "v448_default_exact", "v448_radius") for arm in ARMS)
            expected.update([("v448_explicit_exact", "ROUTE"), ("v448_radius_profile", "LAZY_ASTAR")])
            expected.update(("v448_named_alias", arm) for arm in ALIASES.values())
            require(matrix == expected and len(sols) == row["counters"]["solution_checks"], "Raw solve coverage")
            aliases = {r["method"]: r["arm"] for r in sols if r["verification_variant"] == "v448_named_alias"}
            require(aliases == ALIASES, "Raw method alias coverage")
            for s in sols:
                require(s["H2"] == optimum and s["certified_optimal"] is True
                        and s["certified_gap"] == 0, "Raw solve optimum/certificate mismatch")
                if s["verification_variant"].startswith("v448_"):
                    expected_basis = "exact" if s["verification_variant"] in (
                        "v448_default_exact", "v448_explicit_exact") else "radius"
                    require(s["bound_basis"] == expected_basis, "Raw solve bound basis mismatch")
            oracles = [r for r in oracle_rows if r["case"] == case]
            require(len(oracles) == 1, "Raw oracle coverage")
            oracle = oracles[0]
            require(oracle["timed_exhaustive_H2"] == optimum
                    and oracle["independent_dp"]["status"] == "PASS"
                    and oracle["independent_dp"]["optimum_H2"] == optimum, "Independent oracle identity")
            prefixes = [r for r in prefix_rows if r["case"] == case]
            phases = Counter(r["state"]["phase"] for r in prefixes)
            c = row["counters"]
            require(len(prefixes) == oracle["timed_exhaustive_states"] == c["prefixes"]
                    and phases == Counter({0: c["phase0"], 1: c["phase1"], 2: c["terminal"]}),
                    "Raw prefix coverage")
            require(len({json.dumps(r["state"], sort_keys=True) for r in prefixes}) == len(prefixes),
                    "Repeated prefix state")
            for r in prefixes:
                require(r["state"]["t"] <= r["radius_base"] <= r["exact_base"] <= r["exact_full"] <= r["oracle"]
                        and r["radius_base"] <= r["radius_full"] <= r["exact_full"], "Stored prefix inequality")
    require(set(summaries) == {s["case"] for s in specs}, "Exactly all 24 cases must be covered")
    require(totals["shortcut_checks"] > 0 and totals["integer_wait_prefixes"] > 0,
            "Empty aggregate shortcut or integer-wait verification")
    evidence.unchanged()
    require(current_sources() == sources, "Measurement sources changed during gate validation")
    return dict(schema_version=1, gate_kind="V448_FROZEN_MICRO", status="PASS",
                full_micro_suite_complete=True, cases=24, independent_mothers=len({s["seed"] for s in specs}),
                sources=sources, checker_sha256=CHECKER_SHA, checker_pins=pins,
                input_sha256=pins["micro_inputs"], selected_runs=[str(p) for p in paths],
                evidence_sha256=evidence.hashes, case_ids=[s["case"] for s in specs],
                case_summaries=[summaries[s["case"]] for s in specs], counters=dict(totals),
                integer_wait_is_prefix_sample=True, no_solver_run_by_assembler=True,
                performance_claims=False)


def validate_gate(path):
    """Verify a completed gate, current source identities, and every selected raw artifact."""
    path = resolved(path)
    gatefile = path / "GATE.json" if path.is_dir() else path
    require(gatefile.name == "GATE.json", "Expected GATE.json or its directory")
    directory = descendant(gatefile.parent)
    require(not (directory / "FAILURE.json").exists(), "Gate failure record exists")
    gate = json.loads(gatefile.read_text(encoding="utf-8-sig"))
    done = json.loads((directory / "PROCESS_COMPLETE.json").read_text(encoding="utf-8-sig"))
    require(done["status"] == "PASS" and done["cases"] == 24
            and done["gate_sha256"] == digest(gatefile), "Incomplete or modified gate")
    selection = gate["selection"]
    selection_path = Path(selection["path"])
    require(digest(selection_path) == selection["sha256"], "Selection manifest changed")
    selected = json.loads(selection_path.read_text(encoding="utf-8-sig"))
    selected = selected["runs"] if isinstance(selected, dict) else selected
    require(isinstance(selected, list) and [str(resolved(p)) for p in selected] == gate["selected_runs"],
            "Selection identities differ from gate")
    reconstructed = collect(selected)
    for key, value in reconstructed.items():
        require(gate.get(key) == value, f"Gate no longer matches evidence: {key}")
    return gate


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-json", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    selection_path = resolved(args.runs_json)
    out = descendant(resolved(args.out))
    require(not out.exists(), "Fresh gate directory required; preserve earlier attempts")
    selection_bytes = selection_path.read_bytes()
    selected = json.loads(selection_bytes.decode("utf-8-sig"))
    selected = selected["runs"] if isinstance(selected, dict) else selected
    require(isinstance(selected, list) and selected and all(isinstance(p, str) for p in selected),
            "Selection must contain explicit run path strings")
    out.mkdir(parents=True, exist_ok=False)
    try:
        gate = collect(selected)
        selection_sha = hashlib.sha256(selection_bytes).hexdigest()
        require(digest(selection_path) == selection_sha, "Selection manifest changed during assembly")
        gate.update(created_utc=datetime.now(timezone.utc).isoformat(),
                    selection=dict(path=str(selection_path), sha256=selection_sha))
        write_json(out / "GATE.json", gate)
        write_json(out / "PROCESS_COMPLETE.json", dict(status="PASS", cases=24,
                   gate_sha256=digest(out / "GATE.json")))
        print(json.dumps(dict(status="PASS", cases=24, gate=str(out / "GATE.json"))), flush=True)
        return 0
    except BaseException as exc:
        failure = dict(status="FAIL", error=repr(exc), traceback=traceback.format_exc(),
                       no_solver_run_by_assembler=True)
        write_json(out / "FAILURE.json", failure)
        write_json(out / "PROCESS_COMPLETE.json", failure)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
