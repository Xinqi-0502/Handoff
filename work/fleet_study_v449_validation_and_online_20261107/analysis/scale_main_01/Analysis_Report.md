# V449 frozen nine-method confirmation analysis

Source status: **COMPLETE**. 10800 returned calls, 0 hard timeouts and 0 missing calls out of 10,800 planned calls.
The design contains 100 independent random mother networks and 400 related capacity/signal scenarios. Each method has three technical repeats. No single universal winner is selected.

Early feasible quality is the primary view. The table counts scenarios with all three incumbents available at the literal deadline, and all three equal to the known optimum. Missing data and unknown optima are not converted to success.

| Method | 100 ms feasible / optimal | 500 ms feasible / optimal | 1000 ms feasible / optimal | All 3 proofs within 1 s |
|---|---:|---:|---:|---:|
| RADIUS | 400/400 / 337/400 | 400/400 / 397/400 | 400/400 / 400/400 | 400/400 |
| RADIUS_PAIR_EAGER | 400/400 / 326/400 | 400/400 / 394/400 | 400/400 / 400/400 | 400/400 |
| RADIUS_PAIR_LAZY | 400/400 / 343/400 | 400/400 / 398/400 | 400/400 / 400/400 | 400/400 |
| RADIUS_AWA | 400/400 / 370/400 | 400/400 / 400/400 | 400/400 / 400/400 | 400/400 |
| RADIUS_PAIR_AWA | 400/400 / 355/400 | 400/400 / 400/400 | 400/400 / 400/400 | 400/400 |
| RADIUS_PAIR_AWA_GATED | 400/400 / 372/400 | 400/400 / 400/400 | 400/400 / 400/400 | 400/400 |
| NO_BOUND | 400/400 / 269/400 | 400/400 / 368/400 | 400/400 / 400/400 | 400/400 |
| DP_ADAPTER | 400/400 / 300/400 | 400/400 / 399/400 | 400/400 / 400/400 | 400/400 |
| ROUTE | 400/400 / 185/400 | 400/400 / 230/400 | 400/400 / 284/400 | 284/400 |

Pair_Quality_Summary.csv reports all 36 method pairs at 100/500/1000 ms, including wins, ties, losses, unknown cases and asymmetric availability. Case_Quality.csv preserves every case and all repeat values. Quality comparisons use the median only when all three values exist.

Pair_Time_Summary.csv separates proof time from first 0%, 5% and 10% relative-duration-gap targets. Each time comparison uses only scenarios where BOTH methods achieved the specified event within one second in ALL THREE repeats; the remaining left-only, right-only and neither counts stay visible. Targets use opt + fraction*(opt - t0), derived after search. Ratios use paired case medians, never pooled calls. Zero denominators are NA. Initial-target counts identify targets already met by the common initializer; these are not search improvements. Expanded sums and their ratio use the same eligible pair subset, rather than all-case work totals.

Late improvements and certificates remain in end-of-run records but receive no credit at earlier cutoffs. Hard timeouts have no recovered incumbent; their duration is not treated as solver elapsed or proof time. Returned soft-overrun values are retained separately. Incomplete source blocks make the report provisional.

Case_Work_And_Proof.csv and Work_And_Proof_Summary.csv distinguish elapsed/setup/initial/search/root timing, phase-specific completed expansions, joint rejection counts and available work counters. Root timing is nested within search; it must not be added again. Detailed profiling was disabled, so absent internal DP/closure counters are NA.

No process RAM or Python allocation bytes were measured. Peak heap entries (including stale labels), closure/cache entries, and DP structural-label counts are storage proxies with different meanings. The DP closure caches full arrival vectors; search closures cache scalar queries. These counts do not establish an actual memory saving.

DP_ADAPTER is this study's standard complete topological DP implementation. Its reference oracle shares recurrence/network source; it is not independently validated by that same source. Separate small exhaustive checks and frozen-reference plan replay provide the cross-checks. Lazy A* and weighted anytime A* are published search-policy adaptations to this local model, not reproductions of a complete published freight dispatcher. The joint bound is supplied by this study.

This confirmation concerns synthetic local two-handoff H2 optimization. It supplies no whole-fleet SUMO or real-world delivery benefit by itself. Signal/capacity variants are paired conditions, not additional independent mother networks. No p-values or extrapolated success probabilities are reported.

Source_Status.json and Provenance.json retain explicit selection, source/raw hashes, incomplete/failure evidence and accounting. All measured sources and input files are read only.
