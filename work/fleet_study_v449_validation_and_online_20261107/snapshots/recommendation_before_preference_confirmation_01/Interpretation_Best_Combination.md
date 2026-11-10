# V449 interpretation and current joint-bound configuration

For the declared synthetic local H2 task, **RADIUS_PAIR_AWA_GATED is the current recommended configuration when the method must include the new joint bound**. It combines the inexpensive RADIUS quota basis, weighted anytime A* ordering (fixed weight 2), and a selective joint-bound rejection check at pop. It is the strongest balanced joint-bound option observed in this prespecified nine-method study. It is not a universal winner: the no-joint RADIUS_AWA baseline reaches 5% and 10% good-solution targets earlier in aggregate and on most cases. No method has been switched or deployed automatically.

The evidence consists of 100 fresh independent mother networks, 25 at each m=6/8/10/12, each with two capacity and two calendar conditions: 400 related scenarios. Nine methods were run three times each, yielding 10,800 returned calls, zero hard timeouts and zero missing calls. All 400 validation oracles completed exactly. The independent raw audit reports PASS with 222,406 CSV fields agreeing. The three repeats are technical repeats; the 400 variants are not 400 independent networks.

All times below are sums of per-case medians of three fully charged calls, in seconds. A proof-time comparison includes a case only when both methods prove optimal within one second in all three repeats. First-good targets are evaluated after search using optimum + fraction*(optimum-t0), and never supplied to the solver. All methods had zero cases whose common initial plan already met any of the 0%, 5% or 10% targets.

## Early quality comes first

All nine methods supplied feasible incumbents by 100 ms in all repeats of all 400 cases. The following counts require all three repeats to be optimal at the literal deadline; they are stronger than a median-optimal count.

| Method | Optimal by 100 ms | Optimal by 500 ms | Optimal by 1000 ms | All-three proof by 1 s |
|---|---:|---:|---:|---:|
| RADIUS | 337/400 | 397/400 | 400/400 | 400/400 |
| RADIUS_PAIR_EAGER | 326/400 | 394/400 | 400/400 | 400/400 |
| RADIUS_PAIR_LAZY | 343/400 | 398/400 | 400/400 | 400/400 |
| RADIUS_AWA | 370/400 | 400/400 | 400/400 | 400/400 |
| RADIUS_PAIR_AWA | 355/400 | 400/400 | 400/400 | 400/400 |
| RADIUS_PAIR_AWA_GATED | 372/400 | 400/400 | 400/400 | 400/400 |
| NO_BOUND | 269/400 | 368/400 | 400/400 | 400/400 |
| DP_ADAPTER | 300/400 | 399/400 | 400/400 | 400/400 |
| ROUTE | 185/400 | 230/400 | 284/400 | 284/400 |

Against RADIUS_AWA at 100 ms, the recommended method has only 2 lower, 396 equal and 2 higher case-median H2 values. At 500 and 1000 ms all 400 case-median values tie. The 372-versus-370 all-three hit count therefore does not establish broad quality dominance. The four non-ties are all at m=12 and are retained below.

| Case | Gated H2 | RADIUS_AWA H2 | Exact H2 |
|---|---:|---:|---:|
| v449_scale_main_s94502015_m12_tight_free | 269 | 252 | 252 |
| v449_scale_main_s94502019_m12_roomier_free | 175 | 184 | 175 |
| v449_scale_main_s94502019_m12_roomier_signal | 190 | 191 | 190 |
| v449_scale_main_s94502020_m12_tight_free | 238 | 235 | 232 |

Case-median 100-ms comparisons with the other declared baselines are more favorable, while all null and adverse results remain in the complete pair tables.

| Baseline | Gated wins / ties / losses at 100 ms | At 500 ms | At 1000 ms |
|---|---|---|---|
| RADIUS | 44 / 356 / 0 | 2 / 398 / 0 | 0 / 400 / 0 |
| RADIUS_AWA | 2 / 396 / 2 | 0 / 400 / 0 | 0 / 400 / 0 |
| DP_ADAPTER | 85 / 315 / 0 | 1 / 399 / 0 | 0 / 400 / 0 |
| NO_BOUND | 111 / 289 / 0 | 29 / 371 / 0 | 0 / 400 / 0 |
| ROUTE | 198 / 202 / 0 | 169 / 231 / 0 | 116 / 284 / 0 |

## First-good time and proof time are different outcomes

| Endpoint versus RADIUS_AWA | Gated seconds | Baseline seconds | Gated change | Gated earlier / later cases | Gated faster / slower mothers |
|---|---:|---:|---:|---|---|
| First 0% gap | 10.815402 | 11.571597 | -6.53% | 192 / 208 | 61 / 39 |
| First 5% gap | 8.031159 | 7.965820 | +0.82% | 100 / 300 | 29 / 71 |
| First 10% gap | 7.142763 | 6.917212 | +3.26% | 62 / 338 | 6 / 94 |
| Optimality proof | 18.260488 | 23.307407 | -21.65% | 361 / 39 | 94 / 6 |

All four rows use all 400 common cases and all 100 mothers. Mother-level comparison sums the four paired-condition case medians within each mother; no case is excluded. The 6.53% aggregate reduction in first-optimum time coexists with 192 earlier and 208 later cases, so it is not a per-case stable first-optimum improvement. The 5% and 10% target times are 0.82% and 3.26% slower overall; they are later on 300 and 338 cases, respectively. At the mother level, the corresponding first-good sums are slower on 71 and 94 of 100 mothers. When merely obtaining a good solution as early as possible is the only objective and inclusion of the new bound is optional, RADIUS_AWA remains a serious alternative.

Among the four joint-bound combinations, the gated weighted combination has the smallest summed first-good times and proof time in this study. This is a scoped recommendation among prespecified configurations, not a claim that selecting it after viewing these results provides a second independent confirmation of a preselected winner.

## Proof cost with explicit common denominators

| Baseline | Common cases / planned | Common mothers | Gated / baseline seconds | Time change | Gated / baseline expanded | Expansion change | Gated faster / slower cases |
|---|---:|---:|---|---:|---|---:|---|
| RADIUS | 400/400 | 100 | 18.260488 / 24.188014 | -24.51% | 118799 / 256484 | -53.68% | 330 / 70 |
| RADIUS_AWA | 400/400 | 100 | 18.260488 / 23.307407 | -21.65% | 118799 / 258496 | -54.04% | 361 / 39 |
| DP_ADAPTER | 400/400 | 100 | 18.260488 / 52.426911 | -65.17% | 118799 / 6603208 | -98.20% | 300 / 100 |
| NO_BOUND | 400/400 | 100 | 18.260488 / 61.905280 | -70.50% | 118799 / 2878192 | -95.87% | 386 / 14 |
| ROUTE | 284/400 | 75 | 4.061939 / 58.150114 | -93.01% | 25984 / 25950 | +0.13% | 284 / 0 |
| RADIUS_PAIR_LAZY | 400/400 | 100 | 18.260488 / 21.378291 | -14.58% | 118799 / 113560 | +4.61% | 326 / 74 |
| RADIUS_PAIR_AWA | 400/400 | 100 | 18.260488 / 22.745960 | -19.72% | 118799 / 111442 | +6.60% | 372 / 28 |

The central controlled weighted-policy comparison is RADIUS_AWA versus RADIUS_PAIR_AWA_GATED: 23.307407 to 18.260488 seconds, a 21.65% reduction, and 258,496 to 118,799 completed expansions, a 54.04% reduction. Proof time is lower on 361/400 paired conditions and on 94/100 mothers after summing each mother's four conditions. The six slower mothers and 39 slower conditions remain in the evidence.

DP and NO_BOUND are meaningful counterchecks, not omitted weak results: the gated method is slower than DP on 100/400 proof comparisons and slower than NO_BOUND on 14/400, despite lower aggregate times. The old exact ROUTE comparison has only 284 common on-time cases from 75 mothers. On that subset, gated expansions increase slightly from 25,950 to 25,984 (+0.13%) while time falls. This demonstrates that replacing expensive exact quota work with a cheaper basis is not the same claim as reducing states against every baseline. The old ROUTE end-of-run total of 33,901 expansions over all 400 cases is truncated and cannot be called superior search efficiency.

## Scale and traffic-calendar conditions

| Scale versus RADIUS_AWA | Cases / mothers | Proof-time change | Expansion change | Gated faster / slower cases |
|---|---:|---:|---:|---|
| m6 | 100 / 25 | -5.41% | -38.67% | 67 / 33 |
| m8 | 100 / 25 | -17.92% | -52.81% | 96 / 4 |
| m10 | 100 / 25 | -19.30% | -51.93% | 98 / 2 |
| m12 | 100 / 25 | -22.82% | -55.06% | 100 / 0 |

Signal-on contains 200 scenarios from all 100 mothers (two capacities each), not 50 independent mothers. On this subset, gated versus RADIUS_AWA proof time is 9.171810 versus 11.734406 seconds (-21.84%); completed expansions are 54,215 versus 118,820 (-54.37%). It is faster on 176 conditions and slower on 24; aggregating the two capacities within each mother gives 95 faster and 5 slower mothers. Its 100-ms case-median quality is 1 win, 199 ties and 0 losses; 500/1000-ms values all tie.

The paired signal-off controls use the same 100 mothers and two capacities: proof time falls from 11.573001 to 9.088678 seconds (-21.47%), and expansions from 139,676 to 64,584 (-53.76%). The 100-ms quality comparison is 1 win, 197 ties and 2 losses. These paired calendar conditions support a computational comparison under synthetic FIFO time dependence. They do not measure physical customer flow time, native SUMO deployment, traffic prediction error or real-world delivery gains.

## What the joint information contributes, and what deployment costs

| Controlled comparison | Common cases | Expansion change | Proof-time change |
|---|---:|---:|---:|
| RADIUS_PAIR_EAGER vs RADIUS | 400 | -55.72% | +12.57% |
| RADIUS_PAIR_LAZY vs RADIUS | 400 | -55.72% | -11.62% |
| RADIUS_PAIR_LAZY vs RADIUS_PAIR_EAGER | 400 | +0.00% | -21.48% |
| RADIUS_PAIR_AWA vs RADIUS_AWA | 400 | -56.89% | -2.41% |
| RADIUS_PAIR_AWA_GATED vs RADIUS_AWA | 400 | -54.04% | -21.65% |

In the same unweighted best-first framework, adding the complete joint bound reduces expansions from 256,484 to 113,560 (-55.72%), but increases total time from 24.188014 to 27.227317 seconds (+12.57%). This is direct evidence that stronger information alone does not guarantee lower computational cost. Lazy deployment retains the same aggregate expansion count and reduces proof time to 21.378291 seconds, 11.62% below RADIUS and 21.48% below eager deployment.

Within weighted A*, full numeric PAIR reduces expansions to 111,442 (-56.89% versus no-joint AWA) but reduces proof time by only 2.41%, and is slower on 236/400 cases. Gated PAIR expands more nodes than full numeric PAIR (118,799 versus 111,442), yet has lower proof time. Its recorded phase-0 pop checks total 207,440 and direct joint rejections total 97,194 (sums of case medians); these are actual check/rejection counters rather than a rejection count inferred from a difference of total expansions.

The defensible mechanism statement is that the specific two-batch joint necessary condition reduces search, while net computational benefit depends on when its extra work is performed. Individual-radius thresholds, quota dynamic programming, FIFO closure, Pathmax, Lazy A*, weighted anytime A*, and generic selective checking are existing components. Their use is not claimed as wholly original. The candidate contribution remains the specific joint relaxation/union construction under the documented assumptions; these experiments are not a complete formula-level novelty proof against all literature.

## Reuse and limits

Recommended_Configuration_01.json selects RADIUS_PAIR_AWA_GATED with the frozen radius basis, fixed weight 2, the existing prune-only joint check, a one-second soft budget and the original fully charged common initializer. It records RADIUS_AWA as the no-joint alternative for earliest good-solution service. It performs no automatic switching, changes no measured code, and contains no oracle-derived runtime stopping threshold. The 5%/10% targets are evaluation-only because a runtime generally does not know the exact optimum. The previous pending draft is preserved.

No actual process RAM or Python allocation bytes were measured. Frontier/cache/DP-label counts have different units and cannot establish byte savings. DP_ADAPTER is this study's standard topological DP implementation; its long-budget oracle shares source and is not independent validation of that same DP. The small separate exhaustive gate and frozen-reference plan replays supply its cross-checks. Published-policy adaptation is distinct from reproducing a complete published freight-routing system.

Source artifacts: analysis/scale_main_01 (complete official CSVs); analysis/independent_scale_main_01 (PASS independent raw audit); Interpretation_Evidence_01.json (normalized comparisons and CSV hashes); Mother_Stability_01.json (all mother-level sums); figures/scale_main_01 (preserved first-render collision failure) and the subsequent corrected figure version. Nothing from an adverse method, condition, seed or failure was removed.
