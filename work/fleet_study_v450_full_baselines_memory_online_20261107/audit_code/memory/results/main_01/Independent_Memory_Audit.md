# Independent V450 memory audit



PASS: 128 planned observations, 32 scenarios, eight independent mother instances; four methods and one fresh process per method/scenario.

This audit imports only the standard library. It checks source/input/job hashes, the complete matrix, owned process lifecycle and native endpoints, controller validation evidence, saved exact-oracle inequalities, and an additional independent scan-based FIFO replay of every available incumbent plan. It performs no optimization or simulator run.

Primary endpoints remain separate: PeakWorkingSetSize is the lifetime resident working-set peak (including shared pages); PeakPagefileUsage is peak process commit; PrivateUsage is current private commit. Baseline snapshots are retained. Their difference is not algorithm-exclusive RAM.

All-native pairs and common-on-time-proof pairs have separate denominators in Independent_Pair_Summary.csv, including m, Q, capacity-regime, signal and joint strata. Censored solver results keep any genuine available native endpoint; missing endpoints remain null. Optional post-exit counters are never substituted for the post-solve primary endpoint.

One process observation per method/case does not estimate process-repeat variability. Lifetime peaks include startup/import history and any soft overrun. Instrumented timing is not substituted for the separate timing study. Micro correctness and the four-scenario cost pilot are not pooled into this main cohort.

Primary-analysis comparison: PASS.

Independent replay verifies saved plans; the saved exact-oracle status is checked, not independently re-proved by a new exhaustive search.
