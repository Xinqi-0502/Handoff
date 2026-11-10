# V448 bounded micro correctness plan

Status: runner prepared, not executed. The root agent will schedule serialized validation after approval. No V447 formal result or scenario is changed or selected using outcomes.

## Frozen inputs and commands

The input is the frozen V447 instances/micro_01/INPUTS.json: 24 related scenarios, six independent micro mothers, m3/m4/m5, each with paired capacity and signal treatments. This is reused correctness coverage, not new independent performance evidence.

One default batch covers one case:

    python -B check_v448.py --run runs/check_micro_00_01 --offset 0 --limit 1

For subsequent cases increment offset (0 through 23) and always use a fresh run folder. The caller should use the installed runtime and an E working directory, for example:

    C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\check_v448.py --run runs/check_micro_00_01 --offset 0 --limit 1 --case-seconds 30 --max-seconds 60

The script accepts 1..4 cases per batch; both per-case and overall limits are capped at 60 seconds. Exhausting a limit records FAIL, preserves partial files and blocks success. It is safe to split into smaller fresh batches. The command is documentation only and was not run during preparation.

## Per-case checks

1. Build the timed exhaustive suffix oracle with no proposed bound. Compare its root optimum with the independently written topological structural DP. Independently replay the DP plan.
2. For every reachable timed prefix, compare new exact local base/full values with the original V447 Context. Check radius independent values against the frozen reference RADIUS_PRECEDENCE implementation. Verify s.t <= base_R <= base_E <= full_E <= true suffix optimum and base_R <= full_R <= full_E. No unsupported full_R>=base_E relation is asserted.
3. Both bases' full bounds are compared against a literal union-event loop that does not call production full/cutoff or apply any early-return shortcut. Every qualifying gb+tau_a<=B shortcut is checked against that full expression and its mandatory-a raw value.
4. Test Boolean cutoff/full equivalence for both gated and ungated modes at the full-bound boundary and independent-base boundary. Clear the production Gamma cache before each Boolean comparison. Common phase-1 values are checked independently.
5. For the first eight phase-0 prefixes in the prespecified order (more remaining old items first, then structural fields/time), compare the radius finite-event minimum with every integer x from B_R through the last alpha event. Thus the root is considered before low-quota terminal-near prefixes. A declared horizon cap of 4096 ticks prevents an accidental large waiting loop; skipped horizons are explicitly counted. This waiting check is a bounded supplement, whereas local admissibility/full identity cover every prefix.
6. Verify parent-to-child Pathmax safety with the exhaustive suffix values for both bases, including positive event time, nonnegative remaining heuristic, parent validity at each child, and inherited max validity.
7. For every one of the ten internal search policies, run original V447/default-exact V448/radius V448 with no soft cutoff, under the case watchdog. Check original/default-exact semantic traces, objective, final plan, expansion/pruning counters and non-timing common statistics. Validate all objectives/certificates and independently replay every final plan. Check explicit exact agrees with the default for ROUTE.
8. Check each of the four named public radius aliases against its internal-policy radius result. Verify FULL_GATE/CUTOFF/GATED_CUTOFF have the same search and incumbent trace within each basis. Verify profile-enabled radius Lazy A* retains the unprofiled semantic trace and performs zero quota-DP labels.
9. Recheck the unchanged closure with the independent Bellman-Ford implementation, and check timer nesting and phase-count sums.

A complete selected case performs 36 bounded correctness solves, not performance replications. The policies are unchanged; the purpose is to catch basis routing, shortcut, queue/certificate and accounting mistakes. There is no timing comparison or win-based acceptance criterion.

## Recorded evidence and blocking behavior

Each run writes selected INPUTS.json, PROTOCOL.json (all source/input hashes and limits), compressed per-prefix checks, SOLVES.jsonl, ORACLES.jsonl, CASE_COMPLETE.jsonl, SUMMARY.json, OUTPUT_HASHES.json and PROCESS_COMPLETE.json. Exceptions and limits also write FAILURE.json with the active case/stage/prefix and traceback. Existing run directories are rejected.

PASS means only the selected micro batch passed. No individual batch claims all24 coverage. Before any later performance gate, combine the per-batch completed case identities and verify exactly the frozen 24 cases are covered with identical source/input pins and no unresolved failure. Failed attempts remain preserved; a later corrected version requires a new source hash and fresh runs.

The source and input files are hash-checked before and after a batch. Main-result folders are not used. Exact/radius clocks, all costs and later practical benefits remain unmeasured until a separately authorized experiment.

