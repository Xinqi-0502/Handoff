# V449 50-millisecond online deadline result (provisional independent audit)

Status: completed raw policy records, chosen plans and native completion/transfer events have been independently read; the additional full trace/hash audit is deferred during formal timing. No final independent-audit PASS is claimed. The analysis-only monitor `status`/`Status` error and correction are recorded separately; numerical sources and results are unchanged.

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

The raw source is `online/runs/wall50ms_native_01`, separately sealed from `forecast24_native_01`. Three timing repetitions are technical repeats; the four traffic settings share seed420511. This bridge is frozen-prefix two-batch native execution, not a continuously rolling multi-building system. No actual RAM conclusion follows from the state counts. Final independent integrity details will be appended only after the deferred audit runs.
