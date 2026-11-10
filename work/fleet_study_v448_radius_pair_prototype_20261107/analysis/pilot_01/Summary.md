# V448 exploratory pilot analysis

Data completeness: **COMPLETE**. 448 OK, 0 hard-timeout and 0 missing calls out of 448 planned calls.
The design has 8 independent mother instances and 32 related capacity/signal scenarios. Three repeats are technical timing repeats, not independent instances.
Primary methods have three repeats per scenario; RADIUS_PAIR_EAGER and old exact ROUTE have one diagnostic observation each and are tabulated separately. All primary NO_BOUND observations are retained.

## Strict paired completion time

A scenario enters a time comparison only when both methods obtained an optimality certificate in all three repeats with total elapsed time at most 1 second. The table uses each case median; other pair states remain in the denominator. These are selected completed-pair costs, not unconditional speed.

| Baseline | Eligible / 32 | Candidate only | Baseline only | Neither | Faster / tied / slower | Ratio of sums |
|---|---:|---:|---:|---:|---|---:|
| RADIUS | 31 / 32 | 1 | 0 | 0 | 22 / 0 / 9 | 0.850915 |
| RADIUS_AWA | 32 / 32 | 0 | 0 | 0 | 21 / 0 / 11 | 0.870871 |
| NO_BOUND | 25 / 32 | 7 | 0 | 0 | 23 / 0 / 2 | 0.330129 |

## Literal equal-budget quality

H2 at each cutoff uses only improvements timestamped by that cutoff. The case comparison uses a median only when all three repeats have a feasible incumbent; missing observations remain UNKNOWN, not a loss or an infinite imputation. Lower H2 is better. The raw per-repeat values and availability are retained.

| Baseline | Budget ms | Win / tie / loss / unknown (32) |
|---|---:|---|
| RADIUS | 100 | 1 / 31 / 0 / 0 |
| RADIUS | 500 | 0 / 32 / 0 / 0 |
| RADIUS | 1000 | 0 / 32 / 0 / 0 |
| RADIUS_AWA | 100 | 1 / 23 / 8 / 0 |
| RADIUS_AWA | 500 | 0 / 31 / 1 / 0 |
| RADIUS_AWA | 1000 | 0 / 32 / 0 / 0 |
| NO_BOUND | 100 | 6 / 26 / 0 / 0 |
| NO_BOUND | 500 | 6 / 26 / 0 / 0 |
| NO_BOUND | 1000 | 4 / 28 / 0 / 0 |

## Interpretation limits

A late final improvement or late proof never receives credit at the 1-second cutoff. First known-optimum hit is distinct from proof of optimality. Unknown oracle optima leave regret and first-target fields missing; zero duration denominators produce NA ratios.
Hard timeouts have no recovered incumbent and no solver component timers. Their external call seconds are kept separately. Failed or partial sources remain visible and prevent a COMPLETE status. No case or failed attempt is silently discarded.
Setup + initial + search partition total elapsed. Root-bound time is nested inside search and must not be added again. This unprofiled pilot does not record detailed quota/Gamma CPU time.
Actual process RAM and Python allocation bytes were not measured. peak_frontier counts heap entries, possibly including stale entries; cache sizes count final entries. Neither is a memory-byte measurement or evidence of reduced actual memory.
This is an exploratory synthetic FIFO-model pilot, not a large-sample confirmation, SUMO execution, or real customer-benefit study. No significance tests or win-based filtering are used.
