"""Run the archived search code or replay an archived SUMO plan from a fresh checkout."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PureWindowsPath
import sys
import time

sys.dont_write_bytecode = True

V448 = "fleet_study_v448_radius_pair_prototype_20261107"
V449 = "fleet_study_v449_validation_and_online_20261107"
V450 = "fleet_study_v450_full_baselines_memory_online_20261107"
DEFAULT_NATIVE = "native_0006_s4509001_n8_q12_o0_p10_f2_829a8d41da_t31"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_module(name, path, source=None):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    if source is None:
        spec.loader.exec_module(module)
    else:
        exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def local_path(root, archived):
    """Resolve only archive-workspace paths from the frozen Windows manifests."""
    recorded = PureWindowsPath(archived)
    components = recorded.parts
    require(
        components[:4] == ("E:\\", "CodexResearch-xi", "workspace", "work"),
        f"Unexpected historical path: {archived}",
    )
    target = root.joinpath(*components[3:]).resolve()
    require(target.is_relative_to(root / "work"), f"Path leaves work: {archived}")
    return target


def verify_file(path, digest):
    require(sha(path) == digest, f"SHA-256 mismatch: {path}")


def verify_paths(root, mapping):
    resolved = {}
    for archived, digest in mapping.items():
        path = local_path(root, archived)
        verify_file(path, digest)
        resolved[str(path)] = digest
    return resolved


def static_smoke(root, out, start, stop):
    baseline = root / "work" / V450 / "baseline_replication"
    checker = load_module("portable_static_checker", baseline / "check_published_search_v450.py")
    checker.sources()
    domain, oracle, published = checker.modules()
    fixtures = checker.toy_checks(published)
    specs = checker.read(checker.MICRO)
    stop = 4 if stop is None else stop
    require(0 <= start < stop <= len(specs), "Invalid micro case range.")
    records = []
    for case in specs[start:stop]:
        reference = domain.ref.ReferenceOracle(case, domain.Watchdog(30))
        optimum = reference.suffix(reference.initial())
        dp = oracle.solve(case, max_seconds=30)
        require(dp["status"] == "PASS" and dp["optimum_H2"] == optimum, case["case"])
        ctx = domain.Context(case, domain.Watchdog(30), False, basis="radius")
        value, plan = ctx.greedy()
        initial = (value, tuple(plan))
        for method in checker.METHODS:
            row = checker.run_method(published, domain, case, method, None)
            checker.check_result(domain, oracle, case, row, optimum, None, initial)
            require(row["H2"] == optimum and row["certified_optimal"], case["case"])
            records.append({"case": case["case"], "method": method, "oracle_H2": optimum, "result": row})
    result = {"status": "PASS", "cases": stop - start, "calls": len(records), "fixtures": fixtures, "records": records}
    write_json(out / "STATIC_SMOKE.json", result)
    return {"status": result["status"], "cases": result["cases"], "calls": result["calls"]}


def formal_static(root, out, start, stop):
    """Use the original V450 runner with fresh output and path-only archive adapters."""
    work = root / "work"
    folder = work / V450 / "static_comparison"
    runner_path = folder / "run_fair_comparison.py"
    manifest_path = folder / "Frozen_Source_Manifest.json"
    original = read_json(manifest_path)
    verify_paths(root, original["files"])
    scale_manifest = read_json(work / V449 / "Scale_Source_Manifest.json")
    verify_paths(root, scale_manifest["sources"])
    v450_gate_path = local_path(root, original["gate"])
    v450_gate = read_json(v450_gate_path)
    require(v450_gate["status"] == "PASS" and len(set(v450_gate["case_ids"])) == 24, "Invalid V450 gate.")
    verify_paths(root, v450_gate["sources"])
    verify_paths(root, v450_gate["evidence_sha256"])

    v448_gate_path = work / V448 / "gates" / "micro_all_01" / "GATE.json"
    verify_file(v448_gate_path, scale_manifest["parent_V448_gate_sha256"])
    v448_gate = read_json(v448_gate_path)
    v448_done = read_json(v448_gate_path.parent / "PROCESS_COMPLETE.json")
    require(
        v448_gate["status"] == v448_done["status"] == "PASS"
        and v448_gate["cases"] == v448_done["cases"] == 24
        and v448_done["gate_sha256"] == sha(v448_gate_path),
        "Invalid V448 gate.",
    )
    selection = v448_gate["selection"]
    verify_file(local_path(root, selection["path"]), selection["sha256"])
    verify_paths(root, v448_gate["evidence_sha256"])

    source = runner_path.read_bytes()
    fixed_temp = rb"os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',PYTHONDONTWRITEBYTECODE='1')"
    require(source.count(fixed_temp) == 1, "The frozen runner's temporary-directory line changed.")
    source = source.replace(fixed_temp, b"sys.dont_write_bytecode=True")
    runner = load_module("portable_formal_runner", runner_path, source)
    checker = load_module(
        "portable_formal_checker", work / V450 / "baseline_replication" / "check_published_search_v450.py"
    )

    def verify_runner_sources():
        require(read_json(manifest_path) == original, "Formal source manifest changed.")
        return {**original, "files": verify_paths(root, original["files"]), "gate": str(v450_gate_path)}

    def verified_modules():
        domain, oracle, _ = checker.modules()
        helper = load_module("portable_formal_helper", work / V448 / "run_v448.py")
        return domain, oracle, helper

    runner.check_sources = verify_runner_sources
    runner.load_modules = verified_modules
    # The archived driver uses ROOT here only to constrain the output directory.
    runner.ROOT = out.parent
    options = [str(runner_path), "main", "--run", str(out), "--start", str(start)]
    if stop is not None:
        options += ["--stop", str(stop)]
    saved_argv = sys.argv
    try:
        sys.argv = options
        runner.main()
    finally:
        sys.argv = saved_argv
    return read_json(out / "PROCESS_COMPLETE.json")


def native_replay(root, out, case_name, execute):
    online = root / "work" / V450 / "online"
    manifest = read_json(online / "Online_Source_Manifest_03.json")
    verify_paths(root, manifest["sources"])
    require(Path(case_name).name == case_name and case_name.startswith("native_"), "Expected an archived native case name.")
    archived = online / "runs" / "full_02" / case_name
    sys.path.insert(0, str(online))
    try:
        native = load_module("portable_native_replay", online / "native_online_v450.py")
        saved_audit = read_json(archived / "AUDIT.json")
        audited = native.audit_trace(archived)
        audited = json.loads(json.dumps(audited, allow_nan=False))
        differing_fields = sorted(key for key in audited.keys() | saved_audit.keys() if audited.get(key) != saved_audit.get(key))
        require(not differing_fields, f"Saved trace audit differs in: {differing_fields}")
        result = {
            "status": "PASS",
            "archived_case": case_name,
            "archived_trace_sha256": audited["trace_sha256"],
            "saved_trace_audit_matches": True,
        }
        if execute:
            inputs = read_json(archived / "INPUT.json")
            _, _, runtime = native.native.discover_runtime()
            expected_packages = inputs["runtime"]["packages"]
            require(runtime["packages"] == expected_packages, f"Use the archived SUMO package versions {expected_packages}.")
            rerun = native.simulate(inputs["snapshot"], inputs["plan"], out / "native_replay", inputs["planning_seconds"])
            fields = (
                "status", "completed", "all_customers", "J_customer_seconds", "handoff_a_seconds",
                "last_handoff_seconds", "truck_wait_excluding_transfer_seconds", "activation_seconds",
                "collision_ticks", "teleports",
            )
            differences = [field for field in fields if rerun[field] != audited[field]]
            result.update(
                status="FAIL" if differences else "PASS",
                differing_outcomes=differences,
                trace_sha256_matches=rerun["trace_sha256"] == audited["trace_sha256"],
                replay_trace_sha256=rerun["trace_sha256"],
                simulation_packages=runtime["packages"],
            )
        write_json(out / "NATIVE_REPLAY_CHECK.json", result)
        require(result["status"] == "PASS", f"Native outcome differs: {result.get('differing_outcomes')}")
        return result
    finally:
        sys.path.remove(str(online))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Repository root containing work/ (defaults to the parent of this script's directory).")
    parser.add_argument("--out", type=Path, required=True, help="A new directory outside the frozen work/ tree.")
    parser.add_argument("--formal-static", action="store_true", help="Retime the original 256-case study with three repeats and the archived 1 s policy deadline.")
    parser.add_argument("--skip-static", action="store_true", help="Only audit or replay a native case.")
    parser.add_argument("--start", type=int, default=0, help="First static case index, inclusive.")
    parser.add_argument("--stop", type=int, help="Last static case index, exclusive; defaults to 4 for smoke and 256 for formal static.")
    native_options = parser.add_mutually_exclusive_group()
    native_options.add_argument("--native", action="store_true", help="Audit the archived trace and rerun the saved plan in SUMO.")
    native_options.add_argument("--audit-native", action="store_true", help="Recompute the archived trace audit without starting SUMO.")
    case_options = parser.add_mutually_exclusive_group()
    case_options.add_argument("--native-case", default=DEFAULT_NATIVE, help="Directory name under V450 online/runs/full_02.")
    case_options.add_argument("--native-all", action="store_true", help="Audit or replay all 128 archived formal native cases.")
    args = parser.parse_args()
    root = args.archive.resolve(strict=True)
    out = args.out.resolve()
    require((root / "work" / V450).is_dir(), "Archive must contain the frozen work tree.")
    require(not out.is_relative_to(root / "work"), "Write the rerun outside the frozen work tree.")
    require(not out.exists(), f"Output directory already exists: {out}")
    require(not (args.skip_static and args.formal_static), "--skip-static and --formal-static conflict.")
    require(not args.skip_static or args.native or args.audit_native, "Choose a native action when skipping static.")
    require(not args.native_all or args.native or args.audit_native, "--native-all requires --native or --audit-native.")
    started = time.perf_counter()
    results = {}
    if args.formal_static:
        results["formal_static"] = formal_static(root, out, args.start, args.stop)
    else:
        out.mkdir(parents=True, exist_ok=False)
        if not args.skip_static:
            results["static_smoke"] = static_smoke(root, out, args.start, args.stop)
    if args.native_all:
        saved = read_json(root / "work" / V450 / "online" / "runs" / "full_02" / "PHYSICAL.json")
        names = [entry["folder"] for entry in saved]
        require(len(names) == len(set(names)) == 128 and all(entry["status"] == "PASS" for entry in saved),
                "Expected 128 distinct completed archived physical replays.")
        native_results = []
        for name in names:
            require(Path(name).name == name and name.startswith("native_"), "Invalid archived case name.")
            case_output = out / "native_checks" / name
            case_output.mkdir(parents=True, exist_ok=False)
            native_results.append(native_replay(root, case_output, name, args.native))
        results["native"] = {"status": "PASS", "cases": len(native_results), "reexecuted": args.native}
    elif args.native or args.audit_native:
        results["native"] = native_replay(root, out, args.native_case, args.native)
    report = {"status": "PASS", "elapsed_seconds": time.perf_counter() - started, "checks": results}
    write_json(out / "REPLAY_SUMMARY.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
