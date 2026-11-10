# V448 independent raw pilot audit

Status: PASS for independent arithmetic/coverage checks. Computed directly from four frozen pilot blocks MEASUREMENTS/ORACLES/PROTOCOL/CASE_COMPLETE/SUMMARY/PROCESS_COMPLETE, without importing the solver or analysis code. A prior CSV-only cross-check was used only as a secondary comparison; all values below were recomputed from original records.

Coverage: 448 OK observations, 0 hard timeouts, 0 missing; 32 scenarios from 8 mothers. All 32 independent oracles are exact. No initial plan is already optimal. Primary arms have 3 technical repeats; old exact ROUTE and RADIUS_PAIR_EAGER have 1 auxiliary observation.

The strict time/state population requires both arms to return an optimality certificate by 1 second in every expected repeat. Times and states are per-case medians for primary arms. Auxiliary contrasts remain descriptive. Values at 100/500/1000 ms are rebuilt from timestamps, and their comparisons include every scenario.

| Scope | Baseline | Eligible / all | Time C/B ms | Time ratio | Expanded C/B | State ratio | Time W/T/L |
|---|---|---:|---|---:|---|---:|---|
| ALL | RADIUS | 31/32 | 2542.749000/2988.252801 | 0.850915 | 5279/11022 | 0.478951 | [22, 0, 9] |
| ALL | RADIUS_AWA | 32/32 | 3385.768100/3887.793499 | 0.870871 | 7735/17682 | 0.437451 | [21, 0, 11] |
| ALL | NO_BOUND | 25/32 | 1016.571100/3079.318799 | 0.330129 | 2406/73496 | 0.032736 | [23, 0, 2] |
| ALL | ROUTE | 16/32 | 123.241400/926.363700 | 0.133038 | 398/576 | 0.690972 | [16, 0, 0] |
| ALL | RADIUS_PAIR_EAGER | 32/32 | 3385.768100/4174.867400 | 0.810988 | 7735/7735 | 1.000000 | [32, 0, 0] |
| signal | RADIUS | 16/16 | 1340.560800/1627.709200 | 0.823587 | 2591/5379 | 0.481688 | [12, 0, 4] |
| signal | RADIUS_AWA | 16/16 | 1340.560800/1664.112700 | 0.805571 | 2591/5836 | 0.443968 | [11, 0, 5] |
| signal | NO_BOUND | 12/16 | 411.365000/1209.216300 | 0.340191 | 1016/29534 | 0.034401 | [11, 0, 1] |
| signal | ROUTE | 8/16 | 58.600600/485.884100 | 0.120606 | 186/263 | 0.707224 | [8, 0, 0] |
| signal | RADIUS_PAIR_EAGER | 16/16 | 1340.560800/1705.522500 | 0.786012 | 2591/2591 | 1.000000 | [16, 0, 0] |
| m12 | RADIUS | 7/8 | 1662.014800/2006.766000 | 0.828206 | 2983/6083 | 0.490383 | [7, 0, 0] |
| m12 | RADIUS_AWA | 8/8 | 2505.033900/2912.380500 | 0.860133 | 5439/12482 | 0.435747 | [7, 0, 1] |
| m12 | NO_BOUND | 1/8 | 135.836900/679.620300 | 0.199872 | 110/13475 | 0.008163 | [1, 0, 0] |
| m12 | ROUTE | 0/8 | NA/NA | NA | None/None | NA | [0, 0, 0] |
| m12 | RADIUS_PAIR_EAGER | 8/8 | 2505.033900/3064.279000 | 0.817495 | 5439/5439 | 1.000000 | [8, 0, 0] |

| Scope | Baseline | 100 ms W/T/L/U | 500 ms W/T/L/U | 1000 ms W/T/L/U |
|---|---|---|---|---|
| ALL | RADIUS | [1, 31, 0, 0] | [0, 32, 0, 0] | [0, 32, 0, 0] |
| ALL | RADIUS_AWA | [1, 23, 8, 0] | [0, 31, 1, 0] | [0, 32, 0, 0] |
| ALL | NO_BOUND | [6, 26, 0, 0] | [6, 26, 0, 0] | [4, 28, 0, 0] |
| ALL | ROUTE | [10, 22, 0, 0] | [15, 17, 0, 0] | [15, 17, 0, 0] |
| signal | RADIUS | [1, 15, 0, 0] | [0, 16, 0, 0] | [0, 16, 0, 0] |
| signal | RADIUS_AWA | [1, 11, 4, 0] | [0, 16, 0, 0] | [0, 16, 0, 0] |
| signal | NO_BOUND | [4, 12, 0, 0] | [4, 12, 0, 0] | [2, 14, 0, 0] |
| signal | ROUTE | [6, 10, 0, 0] | [8, 8, 0, 0] | [8, 8, 0, 0] |
| m12 | RADIUS | [1, 7, 0, 0] | [0, 8, 0, 0] | [0, 8, 0, 0] |
| m12 | RADIUS_AWA | [1, 2, 5, 0] | [0, 7, 1, 0] | [0, 8, 0, 0] |
| m12 | NO_BOUND | [1, 7, 0, 0] | [6, 2, 0, 0] | [4, 4, 0, 0] |
| m12 | ROUTE | [1, 7, 0, 0] | [7, 1, 0, 0] | [8, 0, 0, 0] |

Interpretation: LAZY reduces total time on the strict common-completion population, but does not improve 1-second H2 over RADIUS/AWA (all ties). Against AWA it has eight worse case-median solutions at 100 ms and one at 500 ms; these negatives remain in the table and Negative_Examples.csv. NO_BOUND is a real primary three-repeat control: it has 25/32 all-repeat on-time proof cases and 28/32 all-repeat optimal incumbents at 1 second; the candidate has 32/32 for both. Its two faster completed cases are retained, and its m12 time comparison has only one eligible case, so that ratio cannot describe all eight m12 cases.

Old exact ROUTE has only 16/32 on-time proofs and 17/32 optimal incumbents by 1 second. Its m12 subset has 0/8 on-time proofs and 0/8 optimal incumbents; hence no m12 strict completion-time ratio exists. Its eight m12 runs each finish only one search expansion before the soft limit check, consistent with costly quota-bound evaluation; this is a diagnostic observation, not proof that the new pair condition alone creates the improvement. The old ROUTE single observations are not a timing-stability replication.

All-scenario sums of returned elapsed time include late/unproved soft-stop work. They are saved separately in Raw_Recomputed_Coverage.csv and must not be called strict completed-instance speed. H2 optimal incumbent acquisition is distinct from proof. Signal subset ratios are descriptive: comparing signal/free ratios is not a causal test that added signals increase the method benefit.

This 32-scenario/8-mother pilot is exploratory, distinct from the 400-scenario/100-mother V447 formal experiment. NO_BOUND and independent-DP counterevidence from V447 must not be overwritten by this smaller pilot. No SUMO/road-density/actual customer-completion claim follows; H2 is second-handoff completion. Bound-internal computation is excluded from expanded-state counts.

Selected negative examples:
- {"case": "v448_radius_pilot_s9492001_m12_tight_signal", "baseline": "RADIUS_AWA", "budget_ms": 100, "candidate_H2": 368, "baseline_H2": 260, "negative": "literal_quality"}
- {"case": "v448_radius_pilot_s9492001_m12_roomier_free", "baseline": "RADIUS_AWA", "budget_ms": 100, "candidate_H2": 333, "baseline_H2": 183, "negative": "literal_quality"}
- {"case": "v448_radius_pilot_s9492001_m12_roomier_signal", "baseline": "RADIUS_AWA", "budget_ms": 100, "candidate_H2": 368, "baseline_H2": 193, "negative": "literal_quality"}
- {"case": "v448_radius_pilot_s9492002_m12_tight_signal", "baseline": "RADIUS_AWA", "budget_ms": 100, "candidate_H2": 353, "baseline_H2": 243, "negative": "literal_quality"}
- {"case": "v448_radius_pilot_s9492002_m12_roomier_free", "baseline": "RADIUS_AWA", "budget_ms": 100, "candidate_H2": 324, "baseline_H2": 187, "negative": "literal_quality"}
- {"case": "v448_radius_pilot_s9492001_m12_tight_free", "baseline": "RADIUS_AWA", "budget_ms": 500, "candidate_H2": 333, "baseline_H2": 243, "negative": "literal_quality"}

First-optimum acquisition tradeoff (independently recomputed from raw traces, not from saved first-hit fields): candidate sum of per-case median first-hit times = 3.299998400 s, AWA = 1.813339000 s, ratio 1.819846 on all 32 cases; candidate is earlier/tied/later in 6/0/26 cases. Thus faster final proof does not imply faster first optimal solution. Initial plans are nonoptimal in all 32 cases, independently checked against exact oracles. The first-hit oracle is used only after the run for assessment, not as a search incumbent. Full per-case values and missing-target coverage are retained in First_Optimal_Tradeoff.csv and First_Optimal_Aggregates.csv.

Cost-attribution cross-check: the completed V447 instrumented m12 pilot summary (analysis/profile_pilot_m12_01/Profile_Summary.md) reports 24 observations over eight variants of two mothers. LAZY median quota time is 5013.571 ms versus pair evaluation 6.338 ms (instrumented elapsed 5077.612 ms); EAGER reports quota 4948.510 ms versus pair 33.899 ms; ROUTE reports quota 4971.822 ms and no pair calls. These recorded component medians support a common exact-quota-DP bottleneck in that instrumented pilot. This audit read and checked the summary/case table, not a new profiling run or a reaggregation of profile raw records. Profile times are separate from formal timing, their components overlap as documented, and truncation may alter completed work. They do not attribute every V448 gain to the pair construction or establish a causal cross-instance speed comparison.
