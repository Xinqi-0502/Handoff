# Independent V449 main-results audit

**PASS — independent arithmetic and source-provenance audit of the frozen raw records.** This audit did not import the production solver or the official analysis, rerun any search, or modify any raw result. It verified 222,406 fields against the official CSV outputs. The evidence is 400 related scenarios from 100 mother instances, 9 methods, 3 technical repetitions, 10,800 returned measurements, 400 exact oracle results, and all 52 explicitly selected source blocks. There were no hard-timeout or missing calls. The 400 scenarios and the technical repetitions are not 400 or 1,200 independent mother instances.

## Evidence and audit scope

- Independent source: `../../audit_code/independent_main_audit_v449.py`, SHA256 `2d79bdd1c021f0c7befa702b45ea93d1c06c3d1cc89dbf5b788f85275a1b6153`.
- Completion receipt: `PROCESS_COMPLETE.json`; frozen inputs, sources, raw evidence and official CSV hashes: `Audit_Source_Hashes.json`.
- Raw-source coverage: `Block_Coverage.json`; independent full results: `Independent_Coverage.csv`, `Independent_Pair_Time.csv`, `Independent_Pair_Quality.csv`, `Independent_First_Good_Cases.csv`, and `Independent_DP_Counts.csv`.
- Official output cross-checked: `../scale_main_01`. All 36 unordered method comparisons and their recorded strata were retained, including adverse results.

Checks included the full case/method/repetition matrix, common initialization, source and input identities, trace timestamps and costs, returned certificate arithmetic, literal deadlines, three-repetition case aggregation, common-eligible denominators, first 0/5/10-percent targets, and DP work fields. The target test was independently evaluated as `100*(H2-optimum) <= percentage*(optimum-t0)`.

This is independent verification of saved evidence and arithmetic, not a fresh independent validation of the optimization algorithm. The reference oracle and DP_ADAPTER use related DP source, so their agreement alone is not an independent correctness proof. The pre-existing small correctness gates provide a separate evidence layer. No measured RAM bytes exist in these formal records; labels, caches and queue lengths must not be reported as RAM.

## Literal time-budget solution quality and proof coverage

Each entry below counts scenarios for which **all three repetitions** had reached the exact optimum within the stated literal deadline. The final column counts all-three-repetition optimality certificates returned within the full 1-second budget. The `all3_proof` field repeated on the independent coverage CSV's different `ms` rows is this full-budget measure, not a new certificate measurement at each earlier deadline.

| Method | Optimum by 100 ms | Optimum by 500 ms | Optimum by 1 s | Proof by 1 s |
|---|---:|---:|---:|---:|
| RADIUS | 337 | 397 | 400 | 400 |
| RADIUS_PAIR_EAGER | 326 | 394 | 400 | 400 |
| RADIUS_PAIR_LAZY | 343 | 398 | 400 | 400 |
| RADIUS_AWA | 370 | 400 | 400 | 400 |
| RADIUS_PAIR_AWA | 355 | 400 | 400 | 400 |
| RADIUS_PAIR_AWA_GATED | 372 | 400 | 400 | 400 |
| NO_BOUND | 269 | 368 | 400 | 400 |
| DP_ADAPTER | 300 | 399 | 400 | 400 |
| ROUTE (old exact-quota bound) | 185 | 230 | 284 | 284 |

No scenario had an exact-optimal common initializer in all three repetitions. All eight methods other than old ROUTE reached and proved the optimum within 1 second on all 100 m12 scenarios; old ROUTE did so on 0/100. This is a result for this frozen distribution and budget, not a general claim that those methods always finish or that all RADIUS-based variants are equally useful at earlier deadlines.

Early losses remain material. At 100 ms, LAZY versus AWA had **1 win, 358 ties and 41 losses**; at 500 ms it had 0 wins, 398 ties and 2 losses. AWA_GATED versus AWA had 2 wins, 396 ties and 2 losses at 100 ms, and all ties at 500 ms and 1 second. LAZY versus RADIUS had 6 wins, 391 ties and 3 losses at 100 ms, followed by all ties at 500 ms and 1 second. These compare returned objective values, not just optimum-coverage counts.

## Search reduction and proof cost

The following totals sum one median over the three repetitions for each case in the **same 400-case set where both compared methods proved optimality within 1 second**. They are aggregate workload measures, not confidence intervals or independent-sample tests.

| Method | Sum of case-median proof elapsed time (s) | Sum of completed expansions |
|---|---:|---:|
| RADIUS | 24.188013799 | 256,484 |
| RADIUS_PAIR_EAGER | 27.227316599 | 113,560 |
| RADIUS_PAIR_LAZY | 21.378291200 | 113,560 |
| RADIUS_AWA | 23.307406899 | 258,496 |
| RADIUS_PAIR_AWA_GATED | 18.260488399 | 118,799 |
| NO_BOUND | 61.905279799 | 2,878,192 |
| DP_ADAPTER | 52.426910599 | 6,603,208 |

The EAGER/LAZY comparison separates two conclusions: the shared-capacity bound reduced the search, while its eager evaluation was more expensive overall than RADIUS. LAZY retained the same aggregate expansions and reduced elapsed proof cost. The AWA_GATED result also improves proof cost versus the matched AWA baseline, but comparisons between differently ordered queues cannot be described as a pure bound-evaluation ablation. DP expansions represent its own structural states; their counts are not interchangeable with branch-and-bound label operations, and its complete measured time remains the appropriate practical comparison.

Old ROUTE requires a separate eligible denominator. On the 284 jointly on-time cases, LAZY and ROUTE used 4.532351899 and 58.150114001 seconds, with 22,067 and 25,950 expansions. AWA_GATED and ROUTE used 4.061939099 and 58.150114001 seconds, with 25,984 and 25,950 expansions. Thus the latter large timing advantage is not an expansion advantage on that subset. The remaining 116 ROUTE cases stay visible in the all-case deadline table; they are not silently dropped from quality reporting.

## First useful solution is a different outcome

On the common 400 cases, AWA_GATED versus AWA had a smaller sum of case-median first-exact-optimum times (10.815401899 versus 11.571596900 seconds), but reached that target earlier in only 192 cases and later in 208. At the 5-percent target, its totals were 8.031158600 versus 7.965820001 seconds and it was earlier in 100 cases, later in 300. At the 10-percent target, its totals were 7.142762600 versus 6.917212100 seconds and it was earlier in 62 cases, later in 338. Target totals include initial solutions meeting the target; the independent tables retain those initializer flags. Faster proof does not imply universally earlier good incumbents.

## Interpretation boundary

These results support a scoped computational claim: the inexpensive two-batch capacity association can reduce search, and selective/lazy use can reduce the full cost of proving optimality on these frozen instances. They do not establish global novelty, performance on arbitrary orders or networks, continuous online fleet dispatch, or traffic-service improvement. The formal 400-scenario cohort must remain separate from the earlier 32-scenario development pilot and the four-scenario, one-mother native SUMO bridge diagnostic.

The separate online raw audit passed at `../../online/analysis/independent_bridge_03`. It found zero extra PAIR cuts, identical PAIR/RADIUS plans and actual customer objectives, and slightly higher PAIR elapsed time under both forecast-count and 50-ms budgets. The OR_OPT forecast/physical ranking reversals were retained. That successful execution connection does not add evidence of practical service benefit for PAIR in the current online diagnostic.

**Final disposition:** evidence and arithmetic PASS; report the proof-cost gains together with the EAGER overhead, early-quality losses, old-ROUTE deadline failures, denominator restrictions, correlated experimental units, DP-reference dependence, and absence of actual RAM measurements. No numerical source, frozen input, or raw result was changed by this audit.
