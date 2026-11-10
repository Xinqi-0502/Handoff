# Independent memory measurement proposal

Prepared 2026-11-07; no memory experiment or new algorithm run has been performed. Search-label counts are computational-work indicators and cannot be converted into bytes or called actual RAM savings.

## Planning-only measurement: recommended first stage

Use a separate instrumented run, with one fresh Python worker for each case × arm × technical repetition. Import the identical frozen online sources, load the identical snapshot, and then measure a single solve. Match method order, inputs, wall/forecast limits and run exclusions to the frozen online protocol. Do not reuse a process across arms, because Python allocator retention and process-lifetime peak counters would bias later arms. Do not mix these instrumented times into ordinary timing summaries.

The existing read-only helper `work/fleet_study_v444_selective_two_batch_20261107/native_process_memory.py:snapshot` already uses the Windows GetProcessMemoryInfo API and exposes bytes. It does not need installation or global settings. Reuse its implementation after a source pin and a small own-process API smoke test, not a copied new API binding.

Record immediately after imports/input setup, immediately before solve, immediately after solve, and before worker exit:

* WorkingSetSize: resident working-set bytes at that instant; includes shareable/image pages in the process scope.
* PeakWorkingSetSize: process-lifetime peak resident working-set bytes, including imports/startup. This is a native observed peak, not peak search-state storage.
* PrivateUsage: current private committed bytes; it is not resident physical RAM.
* PeakPagefileUsage: retain under the Windows API's exact counter name; do not rename it RAM or Python heap.

Primary memory output should be absolute process peak and exact scope. Also show the pre-solve peak and `max(0,post_peak−pre_peak)` as an explicitly censored incremental indicator. If startup/import peak dominates, a zero increment means the counter did not resolve a larger later peak; it does not establish equal algorithm memory or zero memory cost. The earlier V444 native pilot showed this limitation and must not be hidden.

Optional tracemalloc in an additional mode can capture Python-tracked peak allocations from just before context creation through result construction, including bound caches/DP state. It excludes native SUMO, interpreter/library allocations outside tracing, and OS memory. Report it separately from resident/private counters. Sampling or tracing overhead means the elapsed time from this mode is diagnostic only.

## Whole physical replay: a distinct resource scope

The actual native workflow includes the Python online worker and its SUMO child. Reuse the reviewed kill-on-close Job ownership wrapper so monitoring never attaches to unrelated processes. A future metrics extension can query that owned Job before its handle closes. Windows Job peak committed-memory counters are not physical resident RAM; confirm the chosen API's exact semantics and run a controlled child-allocation smoke test before using them.

If using periodic process-memory sampling, record PID, process start identity, timestamp and per-process counters at a predeclared frequency. SUMO and Python must be separate columns. Summed working sets may double-count shared pages, so label the sum precisely rather than claiming unique machine RAM. The maximum sampled value is a sampled peak and can miss short bursts. Process exit, inaccessible reads and missed samples are missingness, not zero. Do not change the monitored algorithm budget to compensate for overhead based on observed results.

A full native replay often dominates memory independently of which dispatcher selected the plan. Therefore planning-only memory is the appropriate method-storage comparison; whole-job resource use answers a different system question. Neither can be substituted for the other.

## Required independent gate and reporting

Before any measurement: pin the helper and sources; verify struct/API invariants (positive working set, peak>=current, byte units); test that a controlled allocation is reflected, release behavior does not violate peak monotonicity, and only the owned worker is observed. For Job scope also test normal exit, timeout and host termination including a child/grandchild. Run no large workload until process ownership and the 60 C/fail-closed external monitor both pass.

Preserve per-case raw counters, baselines, missing flags and process identity. Aggregate technical repetitions within each case first, then pair methods on the same cohort; publish coverage and wins/ties/losses. Any memory claim must state measurement scope and uncertainty. No memory-gain conclusion is currently supported by the bridge's label counts or its preparation files.
