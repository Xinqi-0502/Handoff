# Interpretation addendum: native peaks are dominated by the pre-solve baseline

The native-memory experiment is complete and independently audited, but it does not establish an algorithm-specific RAM reduction from the joint lower bound. All 128 observations are genuine Windows process-counter measurements, not frontier/cache proxies. All four methods produced and proved the optimum within 1 second in all 32 paired scenarios, with no failed/censored observation and an identical common import bundle.

## Direct high-water evidence

| Method | No new working-set peak after baseline | No new peak-commit mark after baseline | Pre-solve peak WS median, KiB | Post-solve peak WS median, KiB |
|---|---:|---:|---:|---:|
| RADIUS_PAIR_AWA_GATED | 32/32 | 30/32 | 27,042 | 27,042 |
| HZ_AWA_RADIUS | 28/32 | 26/32 | 27,202 | 27,236 |
| HZ_AWA_RADIUS_PAIR_GATED | 30/32 | 27/32 | 27,110 | 27,114 |
| ANA_RADIUS | 28/32 | 26/32 | 27,102 | 27,128 |

Each zero-growth count was obtained before the analysis window closed by filtering the 32 rows for a method and checking `observed_growth_PeakWorkingSetSize == 0`, equivalently equality of the two saved lifetime peaks. Peak-commit counts use the corresponding PeakPagefileUsage field. The source is Observations.csv; its hash and the exact column recipe are retained in Zero_Growth_Readback_01.json. These statements do not depend on rounding the displayed medians.

The full same-engine HZ pair has a raw median case ratio of 0.9958201093 for peak working set and 0.9904822408 for peak process commit. Raw working-set ratios are lower in 23 cases and higher in nine. These small descriptive differences cannot be causally assigned to the joint bound because most observations never exceeded their pre-solve lifetime maximum. Against ANA, HZ_PAIR has a working-set median case ratio of 1.0008092277, with 15 lower and 17 higher observations; this negative/mixed result remains in the tables.

PeakWorkingSetSize includes resident shared and private pages. PeakPagefileUsage denotes peak process commit, not physical paging-file writes. PrivateUsage is the current private commit snapshot, not a peak; its values are secondary descriptions and are not substituted for the prespecified peak endpoints. Baseline subtraction is not algorithm-exclusive RAM. A smaller search-state count remains a separate work metric.

## Scope and integrity

The main sample contains eight mothers, four related capacity/signal variants per mother, m=6/8/10/12, and one fresh process per method/scenario. It is not 32 independent networks and provides no process-repeat variance estimate. The four-method main sample is separate from the four-scenario nine-method cost diagnostics. The latter preserve old ROUTE's two deadline failures (only 2/4 within-deadline optima/proofs), rather than removing them or pooling their smaller denominator into the main table.

The measurement is for the local fixed-receiver/two-handoff H2 search worker. It does not measure full-fleet or SUMO RAM. Imports, source/input verification and model setup contribute to the worker lifetime peak; replay and reference-oracle validation run in the parent after the endpoint. Soft-return peaks include any overrun; they are not a sampled maximum restricted to exactly the first second. Here every main observation proved optimal by the deadline.

The independent audit at `audit_code/memory/results/main_01` passed 428 scan-based plan replays and 4,412 primary-analysis field checks. All 128 owned process lifecycles were matched. Windows reused some PID numbers; 119 distinct PID values do not mean processes or caches were reused.

No new measurement, solver, replay audit or numerical analysis was run to write this addendum. It corrects interpretation of already computed and preserved data. The defensible conclusion is that substantial or stable algorithm-specific RAM savings have not been established; computational work and speed findings must be assessed separately.
