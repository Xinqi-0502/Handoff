# Final memory artifact index

Status: measurements complete; primary analysis COMPLETE; independent raw audit PASS. No further memory observations are queued. The original 768-call preparation was prospectively reduced to the approved 128-call main cohort before algorithm memory observations. All original preparation snapshots and failures are preserved.

## Main evidence

- `analysis/main_01/Memory_Results.md`: process-memory endpoints and explicit baseline high-water clarification.
- `analysis/main_01/Interpretation_Addendum.md`: required attribution limit. The experiment does not establish algorithm-specific RAM savings; small raw peak differences are dominated by existing pre-solve maxima.
- `analysis/main_01/Observations.csv`: 128 rows, including before-import/pre-solve/post-solve native bytes, literal deadline quality, proof flags, process cost and scenario metadata.
- `analysis/main_01/Method_Summary.csv`: main four-method summaries over all 32 cases and each scale.
- `analysis/main_01/Paired_Cases.csv`, `Pair_Summary.csv`, `Pair_Summary_Proved_By_1s.csv`: per-case native comparisons and explicit all-native/common-on-time-proof denominators. All four methods proved the optimum by 1 second on all 32 cases in this measurement cohort.
- `analysis/main_01/Diagnostic_Pilot_Observations.csv`, `Diagnostic_Pilot_Method_Summary.csv`: nine original methods, four fixed cost scenarios each; separate from the 32-scenario main cohort.
- `analysis/main_01/Zero_Growth_Readback_01.json`: archived row-level zero-growth counts with source CSV hash and precise recipe.
- `analysis/main_01/Source_and_Raw_Hashes.json`: original analysis and raw evidence hashes; unchanged.
- `analysis/main_01/Addendum_Manifest_01.json`: preserved old report hash, new report/addendum hashes, unchanged CSV identity.

The independent audit is outside this directory at `E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\audit_code\memory\results\main_01`. It passed 428 additional scan-based replays of saved incumbent/oracle plans and 4,412 crosschecked primary-analysis fields. No optimization was rerun by that audit.

## Raw and protocol records

- `freeze_01/MANIFEST.json`: final source/input/job freeze, SHA256 `c9242a0fc7fec3571920cbf47c1d6c970b3be1aecc85048864c03a52cfb78c81`.
- `freeze_01/main_selected.json`: exact 32 selected run directories, `runs/main_00_01` through `runs/main_31_01`; each has four complete worker observations.
- Each run retains `PROTOCOL.json`, `ORACLES.jsonl`, `MEMORY.jsonl`, `CASE_COMPLETE.jsonl`, `SUMMARY.json`, `PROCESS_COMPLETE.json`, plus per-worker request/start/result/native-handle/after-report records and stdout/stderr.
- `runs/main_coordinator_01/PROCESS_COMPLETE.json`: all declared jobs returned normally.
- `runs/monitor_main_01/PROCESS_COMPLETE.json`: actual monitor PASS, child exit code zero, 2026-11-07 13:22:31.4506320 to 13:45:08.0694501 UTC. Last sensor 38 C; all main samples ranged from 38 to 43 C. Main monitor duration was about 22.61 minutes.
- `runs/safety_02/PROCESS_COMPLETE.json`, `gates/wrapper_all_01/GATE.json`: successful native-counter/lifecycle and 12-method wrapper gates.
- `analysis/cost_pilot_01/Cost_Run_Accounting.md` and `.json`, `Cost_Approval_01.json`: measured 36-call feasibility accounting and approval under the already authorized 45-minute threshold.
- `Memory_Protocol_01.md`, `Memory_Protocol_Amendment_02.md`, `Execution_Notes.md`: original protocol, prospective reduction and execution entry points.

## Implementation and exact scope

The eight frozen local measurement sources are `native_memory.py`, `owned_process.py`, `memory_common.py`, `memory_worker.py`, `check_memory_safety.py`, `run_memory.py`, `run_memory_jobs.py`, and `freeze_memory.py`. Their exact hashes, twelve upstream dependencies and full published engine hash are in the manifest. `analyse_memory.py` and `account_memory_cost.py` are postprocessing scripts and perform no solver run.

The main cohort is 32 related scenarios from eight mothers, four methods, one fresh process per method/scenario. There are no failed/censored main observations; 128 independent owned process lifecycles were matched, despite legitimate reuse of PID numbers (119 distinct PID values). All pre-solve import origins matched exactly. This sample provides no process-repeat variability estimate.

Endpoints are real Windows process counters, not RAM inferred from search/frontier counts. PeakWorkingSetSize includes shared resident pages; PeakPagefileUsage is peak process commit; PrivateUsage is current private commit. Peaks cannot be reset. In 32/32, 28/32, 30/32 and 28/32 observations respectively (frozen GATED, HZ_RADIUS, HZ_PAIR, ANA), the working-set high-water mark did not increase after the pre-solve baseline. Therefore do not claim that the small raw differences demonstrate algorithm RAM reduction. The local H2 worker is measured; SUMO, the whole fleet dispatcher, parent validation and system-wide memory are not.
