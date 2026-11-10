"""Serialize all 24 frozen micro cases in one thermally supervised process.

Run with Python -B run_micro_suite_v448.py --tag micro_01.  A tag must be
fresh.  This coordinator does not launch child processes or performance runs.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import re
import sys
import time
import traceback

P = Path(__file__).resolve().parent
CHECKER = P / "check_v448.py"
EXPECTED_CHECKER_SHA = "beec4805585dbf8224cad60a2fd107b73e2ec80cae4df199166b4ed0e074eb73"
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def put(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify_frozen(check, frozen, pins):
    require(sha(__file__) == frozen["coordinator_sha256"], "Coordinator changed during suite")
    require(Path(check.__file__).resolve() == CHECKER, "Unexpected checker module path")
    require(sha(CHECKER) == frozen["checker_sha256"], "Checker changed during suite")
    require(check.check_pins() == pins, "Pinned sources or input changed during suite")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="micro_01")
    args = parser.parse_args()
    if not re.fullmatch("[a-z0-9_]+", args.tag):
        raise ValueError("Invalid tag")
    journal = P / "records" / ("check_suite_" + args.tag)
    runpaths = [P / "runs" / f"check_{args.tag}_{i:02d}" for i in range(24)]
    # Reject every old path before creating even a suite journal.
    if journal.exists() or any(path.exists() for path in runpaths):
        raise ValueError("Fresh suite journal and all 24 fresh run folders required")
    frozen = dict(coordinator_sha256=sha(__file__), checker_sha256=sha(CHECKER))
    require(frozen["checker_sha256"] == EXPECTED_CHECKER_SHA, "Unreviewed checker version")
    import check_v448 as check
    pins = check.check_pins()
    verify_frozen(check, frozen, pins)
    allcases = read(check.INPUTS)
    require(len(allcases) == 24 and len({s["case"] for s in allcases}) == 24,
            "Expected 24 distinct frozen micro cases")
    require(all(3 <= len(s["old"]) <= 5 for s in allcases), "Expected m3/m4/m5 micro cases")
    expected_sources = {name: dict(path=str(check.FILES[name]), sha256=value)
                        for name, value in pins.items()}
    journal.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    complete = []
    active = None
    try:
        put(journal / "PROTOCOL.json", dict(
            **frozen, source_sha256=frozen["coordinator_sha256"],
            input_sha256=pins["micro_inputs"], sources=expected_sources,
            cases=[s["case"] for s in allcases], runs=[str(p) for p in runpaths],
            case_seconds=30, max_seconds_per_case_run=60, waiting_prefixes=8,
            waiting_max_ticks=4096, serial_same_process=True,
            numerical_suite_not_started_when_protocol_written=True))
        for i, run in enumerate(runpaths):
            active = dict(offset=i, case=allcases[i]["case"], run=str(run))
            verify_frozen(check, frozen, pins)
            saved_argv = sys.argv
            try:
                sys.argv = [str(CHECKER), "--run", str(run), "--offset", str(i),
                            "--limit", "1", "--case-seconds", "30", "--max-seconds", "60",
                            "--waiting-prefixes", "8", "--waiting-max-ticks", "4096"]
                if check.main() != 0:
                    raise RuntimeError(f"Correctness case {i} failed; dependent work stopped")
            finally:
                sys.argv = saved_argv
            verify_frozen(check, frozen, pins)
            summary = read(run / "SUMMARY.json")
            protocol = read(run / "PROTOCOL.json")
            done = read(run / "PROCESS_COMPLETE.json")
            require(not (run / "FAILURE.json").exists(), "Child failure record exists")
            require(summary["status"] == done["status"] == "PASS", "Incomplete or failed case")
            require(summary["case_count"] == done["case_count"] == 1
                    and summary["offset"] == done["offset"] == i, "Case coverage mismatch")
            require(protocol["offset"] == i and protocol["limit"] == 1
                    and protocol["total_frozen_micro_cases"] == 24
                    and protocol["selected_cases"] == [allcases[i]["case"]], "Protocol case mismatch")
            require(protocol["runner_sha256"] == frozen["checker_sha256"]
                    and protocol["sources"] == expected_sources
                    and protocol["input_sha256"] == pins["micro_inputs"], "Protocol source mismatch")
            require((protocol["case_seconds"], protocol["max_seconds"],
                     protocol["waiting_prefixes"], protocol["waiting_max_ticks"]) == (30, 60, 8, 4096),
                    "Child verification budget mismatch")
            require(summary["source_sha256"] == pins["new_solver"]
                    and summary["reference_sha256"] == pins["new_reference"]
                    and summary["micro_input_sha256"] == pins["micro_inputs"], "Summary source mismatch")
            require(read(run / "INPUTS.json") == [allcases[i]], "Selected input mismatch")
            rows = [json.loads(line) for line in (run / "CASE_COMPLETE.jsonl").read_text(
                encoding="utf-8").splitlines() if line.strip()]
            require(rows == summary["cases"] and len(rows) == 1
                    and rows[0]["case"] == allcases[i]["case"], "Case completion identity mismatch")
            for name, digest in read(run / "OUTPUT_HASHES.json").items():
                require(sha(run / name) == digest, f"Child output changed: {name}")
            complete.extend(rows)
            with (journal / "CASE_PROGRESS.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(dict(**active, **frozen, status="PASS",
                    protocol_sha256=sha(run / "PROTOCOL.json"))) + "\n")
            gc.collect()
        require(len(complete) == 24 and [s["case"] for s in complete] ==
                [s["case"] for s in allcases], "Full suite case coverage mismatch")
        verify_frozen(check, frozen, pins)
        gate = dict(status="PASS", full_micro_suite_complete=True, cases=24,
                    independent_mothers=len({s["seed"] for s in allcases}),
                    source_pins=expected_sources, **frozen, input_sha256=pins["micro_inputs"],
                    runs=[str(p) for p in runpaths], case_summaries=complete,
                    seconds=time.perf_counter() - started, integer_wait_is_prefix_sample=True,
                    performance_claims=False)
        put(journal / "PASS.json", gate)
        put(journal / "PROCESS_COMPLETE.json", dict(status="PASS", cases=24, seconds=gate["seconds"]))
        print(json.dumps(dict(status="MICRO_SUITE_PASS", cases=24, seconds=gate["seconds"])), flush=True)
    except BaseException as exc:
        fail = dict(status="FAIL", completed_cases=len(complete), active=active,
                    error=repr(exc), traceback=traceback.format_exc(),
                    seconds=time.perf_counter() - started)
        put(journal / "FAILURE.json", fail)
        put(journal / "PROCESS_COMPLETE.json", fail)
        raise


if __name__ == "__main__":
    main()
