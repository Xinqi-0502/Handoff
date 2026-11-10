# Native-memory cost accounting

Actual completed cost pilot: 36 calls; summed case-run duration 376.639 s. Main workload remains 128 calls over 32 paired scenarios.

The prespecified arithmetic projection is 24.79 minutes. This uses the slowest observed non-solver process overhead plus the common 1 s budget, observed main-method overrun and parent case residual. It is not a future-runtime guarantee.

| Method | Calls | Censored | Sum process seconds | Median | Maximum |
|---|---:|---:|---:|---:|---:|
| RADIUS | 4 | 0 | 41.448 | 10.371 | 10.404 |
| RADIUS_PAIR_EAGER | 4 | 0 | 41.458 | 10.355 | 10.450 |
| RADIUS_PAIR_LAZY | 4 | 0 | 41.389 | 10.342 | 10.404 |
| RADIUS_AWA | 4 | 0 | 41.429 | 10.351 | 10.430 |
| RADIUS_PAIR_AWA | 4 | 0 | 41.356 | 10.330 | 10.403 |
| RADIUS_PAIR_AWA_GATED | 4 | 0 | 41.335 | 10.337 | 10.368 |
| NO_BOUND | 4 | 0 | 41.974 | 10.373 | 10.929 |
| DP_ADAPTER | 4 | 0 | 41.603 | 10.331 | 10.666 |
| ROUTE | 4 | 0 | 43.382 | 10.829 | 11.444 |

Cost was inspected to check execution feasibility. No method/input/budget was selected or changed from memory/quality wins. Solver durations here are from separate memory runs and are not formal speed evidence.
