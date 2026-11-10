# Independent interpretation of the full-search comparison

2026-11-07. The primary and independent analyses agree on all 1,024 case-method summaries (22,528 mapped field checks) and 78 directed paired comparisons. The raw audit verified 256 scenarios from 64 independently generated mother instances, four related capacity/signal variants per mother, four methods and three technical repetitions: 3,072 returned calls and no hard timeouts. All 256 independent oracle values are known. Sources: [raw audit](../main_01/Independent_Audit.json), [cross-table check](Crosscheck.json), [primary summaries](../../../static_comparison/analysis/main_01/Paired_Summary.csv).

## Main mechanism comparison

Candidate: **HZ_AWA_RADIUS_PAIR_GATED**. The no-PAIR comparator uses the identical complete Hansen--Zhou engine, weighted priority, common RADIUS/continuation bounds, initialization, caches and Pathmax. Thus this pair isolates the added safe Boolean bound pruning more directly than a comparison between two different code architectures.

| Baseline | Identical common on-time proof subset | Expanded labels, candidate / baseline | Change in summed expanded labels | Sum of case-median proof times, candidate / baseline | Time change |
|---|---:|---:|---:|---:|---:|
| HZ_AWA_RADIUS | 255 / 256 | 77,362 / 170,932 | -54.74% | 16.8885 / 23.1884 s | -27.17% |
| ANA_RADIUS | 255 / 256 | 77,362 / 159,966 | -51.64% | 16.8885 / 22.0530 s | -23.42% |

Each eligible scenario requires all three repetitions of BOTH methods to prove optimality within 1 s. These are ratios of sums over the same subset, not medians of per-case percentages. All three candidate observations were faster than all three baseline observations in 175 / 255 cases against HZ and 159 / 255 against ANA; the reverse occurred in 2 and 5 cases, respectively, with 78 and 91 overlapping timing ranges. These descriptive observations are not significance tests. [Directed proof table](../main_01/Directed_Proof_Pairs.csv)

## Scale and mother-level consistency

| Old parcels | Common scenarios per baseline | Label reduction vs HZ | Time reduction vs HZ | Label reduction vs ANA | Time reduction vs ANA |
|---|---:|---:|---:|---:|---:|
| 6 | 64 | 44.80% | 12.24% | 39.79% | 8.93% |
| 8 | 64 | 50.54% | 22.05% | 45.28% | 15.78% |
| 10 | 64 | 55.04% | 25.19% | 49.92% | 18.57% |
| 12 | 63 | 55.16% | 28.24% | 52.75% | 25.38% |

The four related variants are not four independent samples. Grouping them by mother and requiring all four to belong to the common proof subset leaves 63 complete mothers and one partial mother. All 63 complete mothers have fewer expanded labels than either baseline. Their four-variant summed median times favor the candidate in 60 / 63 mothers against HZ and 57 / 63 against ANA. The remaining 3 and 6 are slower. At m=6, time is worse for 3 / 16 mothers against HZ and 5 / 16 against ANA. The partial m=12 mother remains in the exported table with its three eligible variants and is excluded only from the complete-mother consistency counts. This is empirical consistency within the fixed generator, not a statistical or asymptotic scaling theorem. [Mother-level rows](Mother_Paired_Deltas.csv), [consistency summary](Mother_Consistency_Summary.csv)

## Anytime quality and retained negative findings

At 100 ms, comparison of the three-repeat median incumbent gives candidate win/tie/loss counts of **6 / 249 / 1** against HZ and **31 / 213 / 12** against ANA, with all 256 scenarios observable. All-three-repeat optimal-incumbent counts at 100 ms are 227 for the candidate, 223 for HZ and 207 for ANA. By 1 s, all four methods have attained the independent optimum in every repetition of all 256 scenarios: there is no final incumbent-quality difference at that deadline. Proof completion remains 256 / 256 for both gated implementations versus 255 / 256 for each no-PAIR published baseline. Finding the optimum and proving it are different outcomes. [Literal quality pairs](../main_01/Directed_Literal_Quality_Pairs.csv), [method coverage](../main_01/Independent_Method_Summary.csv)

The candidate reaches the exact optimum 7.96% sooner in summed case-median first-hit time than HZ, but reaches the looser 5% and 10% duration-relative thresholds **2.82% and 4.07% later**. Against ANA, first-hit changes are -37.40%, -29.03% and -0.27% for exact, 5% and 10% targets. All comparisons include 256 scenarios with all three repetitions reaching the target within 1 s. No common initial plan is already optimal or within either target, so these figures represent actual search improvement rather than immediately successful initialization. This is still not uniform anytime dominance: the 100 ms losses and slower early loose-threshold attainment must remain visible. [First-good pairs and initial strata](../main_01/Initial_Strata_First_Good_Pairs.csv)

The generic same-kernel gated implementation expands exactly the same total 82,923 labels as the frozen specialized RADIUS_PAIR_AWA_GATED implementation across all 256 scenarios, yet takes **18.18% more** summed case-median proof time (17.6830 versus 14.9630 s). The generic version is slower in 63 / 64 complete mother groups. This is an engineering-overhead comparison, not evidence against admissibility or an extra benefit of the new mathematical bound. It supports retaining the specialized deployment version while using the identical generic kernel for the clean mechanism ablation.

## Scope

The two published baselines are complete AWA and ANA search-policy reimplementations with explicit domain adaptations, not complete Hof/Wei freight-system reproductions. The proposed contribution is the two-handoff bound and cheap skip, not the published search policies. The experiment minimizes H2, the second handoff completion time; it does not directly measure total customer flow time. Loads concern old-order counts and capacity pressure. Roads use known synthetic FIFO signal calendars, not measured congestion, SUMO vehicle queues or a calibrated city. Online J results, process RAM and public calibration evidence must remain separate. No global originality claim follows from these numerical findings. [Baseline/source audit](../../../literature/Published_Baseline_Implementation_Audit.md), [formula-level coverage](../../../literature/Formula_Coverage_Matrix.md)
