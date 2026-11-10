# Current recommended combination and evidence

The recommended tested configuration that retains the proposed joint bound is **RADIUS_PAIR_AWA_GATED**: a low-cost independent RADIUS bound orders a weight-2 anytime search, and the two-batch capacity-coupled bound is evaluated at a popped candidate before expansion. The joint check uses an unweighted admissible bound for pruning. It does not replace the search priority with the complete joint bound.

## Completed confirmation

The frozen design contains 100 new independent mother networks and 400 paired capacity/signal scenarios, with 6, 8, 10 or 12 old orders. Nine configurations received three technical repeats under the same one-second budget, objective, input and initial feasible plan. All 10,800 calls returned. All 400 validation optima were obtained. The 24-case exhaustive correctness gate passed. An independent audit recomputed raw records and matched 222,406 reported fields.

The objective is the second handoff completion time H2 in a local fixed-receiver, fixed-hub, two-atomic-batch subproblem. The model uses deterministic FIFO travel functions. This confirmation is not a whole-fleet or real-city service experiment.

## Main controlled comparison

The closest attribution control is RADIUS_AWA. Both configurations use the same low-cost ordering and weight. The additional joint check is enabled only in the proposed configuration.

| Metric | RADIUS_AWA | RADIUS_PAIR_AWA_GATED |
|---|---:|---:|
| Sum of case-median proof time, seconds | 23.3074068991 | 18.2604883991 |
| Sum of case-median completed expansions | 258,496 | 118,799 |
| Scenarios with all three proofs within 1 second | 400/400 | 400/400 |
| Scenarios optimal in all three repeats by 100 ms | 370/400 | 372/400 |
| First 5% target time, sum of case medians, seconds | 7.9658200011 | 8.0311586004 |
| First 10% target time, sum of case medians, seconds | 6.9172121005 | 7.1427625997 |

Proof time decreased by 21.6537% and completed expansions by 54.0422%. The proposed configuration was faster in 361/400 scenario comparisons. Aggregating each mother's four paired conditions, it was faster in 94/100 mothers and slower in six.

The early-solution tradeoff is different. At 100 ms, comparing case-median solution values gives two wins, 396 ties and two losses. The first 5% and 10% target times increased by 0.8202% and 3.2607%, respectively. These targets are defined afterward as optimum + fraction * (optimum - t0), and were never supplied to the solver. None of the common initial solutions already met these targets. Plain RADIUS_AWA remains the appropriate comparison when the sole priority is the earliest acceptable approximate solution.

All sums use each scenario's median over three repeated calls. They are not the sum of all 1,200 measured calls and are not a guarantee about any new instance.

## Traffic-signal subset

In the 200 signal-enabled scenarios, covering the same 100 mothers under two capacity conditions, proof time changed from 11.7344062997 to 9.1718101000 seconds, a 21.8383% reduction. Expansions changed from 118,820 to 54,215, a 54.3722% reduction. There were 176 faster and 24 slower scenario comparisons. The 100 ms solution-quality comparison gave one win, 199 ties and no losses. These are search-computation benefits under the specified signal model, not measured reductions in road congestion or customer delivery delay.

## Mechanism and deployment cost

Eagerly adding the joint bound to ordinary RADIUS search reduced expansions but increased proof-time totals from 24.1880137988 to 27.2273165995 seconds. Lazy evaluation reduced the total to 21.3782912000 seconds. The gated weighted configuration reduced it to 18.2604883991 seconds. The joint information supplies the additional pruning. Its net speed benefit depends on controlling evaluation overhead with an established search policy.

The recommended configuration saved 24.5060% proof time against ordinary RADIUS, 70.5025% against NO_BOUND, and 65.1696% against the timed topological DP implementation on all 400 common completed scenarios. Against old exact ROUTE, the valid common set contains only 284 scenarios: proof-time totals were 58.1501140008 versus 4.0619390995 seconds, while expansions were 25,950 versus 25,984. The low-cost method was faster there despite slightly more expansions. Old ROUTE completed on time in 284/400 scenarios, so this conditional timing comparison must retain its denominator.

## Executed online bridge

The new bound was connected to the original customer-flow objective by strengthening only the second new parcel's completion-time term. Both atomic incoming parcels use the same receiver and hub within each of four branches. The other receiver's fixed route remains in the planning domain. Native SUMO execution recomputes all old and new deliveries and both handoffs, and allows the truck to leave only after the second handoff.

Both a 24-forecast protocol and a fixed 50 ms protocol were executed: 72 policy calls and 12 native replay runs overall. Each distinct selected scenario-plan was replayed once within its protocol. Independent event, inventory, parked-transfer and source/hash audits passed. The four diagnostic settings share one mother instance. This is frozen-prefix two-batch execution, not a continuously rolling multi-building dispatcher.

PAIR produced eight strictly stronger checks per setting but zero additional cuts. It retained the same states, plans and actual service outcomes as RADIUS. Its time totals increased by 3.1499% at 24 forecasts and 3.2129% at 50 ms. The proposed extra relation therefore has no demonstrated online service benefit in this diagnostic set. The retained Or-opt comparison also showed that a better forecast objective can yield a worse executed result. These outcomes are preserved.

## Simulation evidence and boundaries

A separate public San Pablo Dam exercise used observed passage-time data, day-1 parameter selection and day-2 evaluation. Five revised runs and a retained insufficient-horizon failure were audited. The held-out mean segment RMSE changed from 426.827624 to 394.477062 seconds. One segment improved and two worsened. The absolute error remains large, so this exercise does not establish successful physical calibration of the delivery network. The source uses ordinal-row matching, excludes explicitly logged nonpositive observed segment differences from scoring only, preserves all vehicles, and conditions each day on its observed boundaries.

The current delivery scenarios remain synthetic. Their evidence supports controlled within-model comparisons and checked handoff execution. Further deployment claims require relevant observed traffic data and scenario calibration.

Lazy A* and Anytime Weighted A* are published search policies adapted to the common model. RADIUS and ROUTE are internal bound controls. DP is a separately timed implementation of standard dynamic programming, and its validation oracle shares that DP lineage. Separate small exhaustive tests and plan replay provide the cross-checks. The study has not reproduced a complete recent multi-vehicle freight dispatcher under this model. Selecting a winning configuration is performance evidence, not proof of exhaustive originality.

No actual process-memory bytes were measured in this confirmation. Label and cache counts must not be presented as RAM savings.

## Evidence files

- Formal results: `analysis/scale_main_01/Analysis_Report.md` and its source CSV files.
- Independent raw audit: `analysis/independent_scale_main_01/PROCESS_COMPLETE.json`.
- Frozen design and source identity: `Scale_Protocol.md`, `Scale_Source_Manifest.json`.
- Online results: `online/Online_Bridge_Results_01.md`, `online/Online_Deadline_Results_01.md`.
- Public validation: `validation/san_pablo_dam/analysis/public_02_01/Independent_Validation_Report.md`.
- Simulation and baseline scope: `literature/Simulation_Validity_Statement.md`, `literature/Baseline_Identity_and_Contribution.md`.
- Raw, failed and historical attempts remain in this versioned E-drive directory. No existing research data were deleted.
## Confirmed selection priorities and figures

The user confirmed that either earlier good solutions or lower computation at equal solution quality is acceptable. The selected joint-bound configuration is justified by the second criterion with its proof endpoint stated explicitly. The first-good 5% and 10% delays remain part of the recommendation. There is no combined score or hidden automatic switching.

Three figures were generated directly from the verified analysis CSVs. The corrected set is `figures/scale_main_02`: `Figure_01_Budget_Quality.pdf`, `Figure_02_Conditional_Proof_Cost.pdf`, and `Figure_03_Coverage_And_Search_Work.pdf`. PNG versions, source CSVs and explanatory captions accompany them. The first rendering's layout failure remains archived. The corrected third figure was visually inspected, and its legend no longer overlaps axis text. Figure data were not changed to fix layout.