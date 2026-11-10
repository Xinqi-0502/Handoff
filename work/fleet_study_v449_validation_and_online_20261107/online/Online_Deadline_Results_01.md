# V449 50-millisecond online deadline: independent results audit

Status: **independent raw audit PASS**. All36 policy records and four native scenario/plan replays were independently checked against raw input/source identities, literal trace timestamps, deadline and overrun fields, physical event loads, full parking traces, trip completion and hashes. No solver, predictor or SUMO was rerun. Earlier analysis-reader failures are preserved under attempts01/02; the successful fresh audit is attempt03, with no changes to numerical sources or results.

The 50ms deadline was frozen before outcomes and measured from before setup. Literal deadline outputs are distinct from late final outputs. On these four related scenarios / one mother, all36 policy records have a valid incumbent by50ms; all final results are available before that deadline and all recorded overruns are zero. This is not a tight-budget stress result. Four distinct selected scenario/plans were replayed in native SUMO and the existing native audits all passed.

All three arms select the same plan in every scenario. Forecast J is1253.07 for the two offset0 cases and1125.4800000013333 for the two offset24 cases. Actual customer-flow J is1495.8,1495.8,1225.0,1278.0 in `(offset0,slow0),(offset0,slow2),(offset24,slow0),(offset24,slow2)` order. All old/new and truck timing components therefore coincide between arms and equal the R/P rows in `Online_Bridge_Results_01.md`.

| Scenario | RADIUS median ms | PAIR median ms | Or-opt median ms | R/P forecasts | Or-opt forecasts | R/P expanded | Extra PAIR cuts |
|---|---:|---:|---:|---:|---:|---:|---:|
| offset0, slow0 |10.9585|11.0899|28.6914|5|183|33|0|
| offset0, slow2 |11.0716|11.1603|30.5923|5|183|33|0|
| offset24, slow0 |11.0328|11.6319|30.4173|5|180|31|0|
| offset24, slow2 |11.0183|11.6154|30.6055|5|180|31|0|

RADIUS and PAIR finish exhaustive forecast-optimality proofs before the deadline in all12 repetitions per arm. Or-opt reaches the same independently known forecast optimum but supplies no global optimality certificate; do not report all three methods as proving optimality. It terminates under its search policy. The larger number of Or-opt forecasts is permitted in this wall-budget protocol: it must not be compared to its24-call result as though only the proposed bound changed.

PAIR still has eight strictly stronger bound checks per scenario, zero extra cuts, the same expansion counts, and slightly higher case-median time than RADIUS. There is no measured extra solution-quality, actual-service or search-state benefit from PAIR here. Both bounded tree methods' shorter completion times than Or-opt are a method/policy comparison, not proof that the proposed extra relation caused the difference.

The raw source is `online/runs/wall50ms_native_01`, separately sealed from `forecast24_native_01`. Three timing repetitions are technical repeats; the four traffic settings share seed420511. This bridge is frozen-prefix two-batch native execution, not a continuously rolling multi-building system. No actual RAM conclusion follows from the state counts. Final independent tables and raw/source hashes are archived under `online/analysis/independent_bridge_03`.


## Final independent quantitative checks

All36 calls return before50ms; the maximum observed elapsed is31.121100ms, and there are no missing literal incumbents, late final improvements or recorded overruns in this cohort. RADIUS and PAIR each expand128 prefixes and use20 full forecasts across the four case representatives. PAIR again has80 checks,32 stronger values and zero extra cuts. Or-opt uses726 forecasts in total under this wall-time protocol; these are not cap24 runs.

The sum of four case-median times is44.081200ms for RADIUS,45.497500ms for PAIR and120.306500ms for Or-opt. PAIR/RADIUS=1.032129, a3.21% descriptive overhead. PAIR/Or-opt=0.378180 compares different search policies and does not isolate the new relation. Forecast quality and actual service are tied in all4 cases. Actual J totals5494.6 customer-seconds for every arm. RADIUS/PAIR each provide12 on-time proof records; Or-opt attains the independently known optimum but provides no global proof certificate.

Final evidence: `analysis/independent_bridge_03/wall50ms_cases.csv`, `wall50ms_native_events.csv`, `Independent_Aggregates.json`, `Audit_Source_Hashes.json`, `Audit_Manifest.json` and `PROCESS_COMPLETE.json`. No empirical traffic-service or memory benefit from PAIR is established here.
