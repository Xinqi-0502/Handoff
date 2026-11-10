# Independent memory audit: prepared, not executed

The audit is stdlib-only and imports no solver, measured worker, native-memory helper or primary analysis module. Its only executable work after authorization is saved-file validation, arithmetic and independent feasible-plan replay. It never solves an optimization problem or launches a child measurement process.

Checks:
- The amended 32 scenarios / eight mothers / four methods / one observation matrix, exact frozen selection, original V449 subset, rotation, completion counts, source/input/job/gate hashes and common import origins.
- Each owned child REQUEST, STARTED, RESULT, native handle lifecycle and AFTER_REPORT_MEMORY. A repeated PID value is recorded rather than automatically rejected: Windows may reuse PIDs after a previous process has exited; each independent lifecycle must still be proven by its request and owned-handle artifacts.
- Before-import, pre-solve and post-solve counters, bytes/current/peak invariants and monotonic lifetime peaks. The primary endpoint is the worker post-solve snapshot before validation/serialization; optional exit counters never replace it.
- Parent validation assertions, common initial plan, saved independent-oracle inequalities, trace strict improvement, timer/certificate identities and literal deadline quality. Every available incumbent and saved optimum plan is replayed with a separate handwritten O(n^2) FIFO shortest-arrival scan. Saved optimum status is not re-proved by a new search.
- PeakWorkingSetSize, PeakPagefileUsage and current PrivateUsage are distinct. Peak growth is retained only as a diagnostic; baseline subtraction is not algorithm-exclusive RAM.
- Raw-byte paired sums/ratios, case ratios and lower/equal/higher counts, separately for all available native pairs and common proof within one second. Strata include m, Q, capacity regime, signal and their declared joint conditions. Failed/censored records are retained; unknown endpoints stay null.
- Optional comparison with primary Observations, Method_Summary, Pair_Summary and Pair_Summary_Proved_By_1s CSVs. Micro and cost-pilot evidence is checked only as source provenance, not pooled into main memory outcomes.

No runtime or result PASS is claimed. AST parsing is the only executed check so far. Root owns the serial execution window; finish measurement and online correctness work first.

## Prepared command (do not launch during measurements)

The primary memory analysis must already exist for --compare. Use a fresh audit output directory. Preserve any failed attempt.

~~~powershell
$env:TEMP = 'E:\CodexResearch-xi\temp'
$env:TMP = $env:TEMP
$env:PYTHONDONTWRITEBYTECODE = '1'
Set-Location -LiteralPath 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107'
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 'audit_code\memory\audit_memory_raw_v450.py' --execute --selected 'memory\freeze_01\main_selected.json' --compare 'memory\analysis\main_01' --out 'audit_code\memory\results\main_01'
~~~

Without --execute the script exits before reading result evidence. Without --compare it can produce an independent audit while marking the primary-table comparison NOT_REQUESTED; such a run is not a completed cross-analysis comparison.

