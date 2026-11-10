# Independent public-data validation audit

The revised public-data workflow completed 5 traffic runs. Raw detector XML, original ordinal observation rows, complete trip populations, recorded metric arithmetic and output hashes independently matched the saved results. This PASS means workflow and arithmetic consistency, not a universal traffic-calibration acceptance criterion.

Day-1 mean-of-segment-RMSE scores were tau=1.2: 188.985605 s; tau=1.5: 318.826229 s; tau=1.8: 358.079868 s. The frozen minimum-score rule selected tau=1.2 s. The baseline is the official tutorial runner's initial tau=1.5 s, not a claim about the simulator's factory default. No held-out day selected tau.

On day 2 the baseline mean segment RMSE was 426.827624 s and the selected candidate was 394.477062 s. The signed change (selected minus baseline) was -32.350562 s. A negative value is improvement; a zero or positive value is retained. These are observed-boundary, ordinal-matching errors from a small three-candidate screen; they do not identify globally optimal parameters.

| Day | Tau (s) | Segment | Eligible / total | Excluded | RMSE (s) | MAE (s) | Bias (s) |
|---:|---:|:---:|---:|---:|---:|---:|---:|
| 1 | 1.2 | 1-2 | 2298 / 2298 | 0 | 276.621739 | 201.986136 | 200.465265 |
| 1 | 1.2 | 2-3 | 2297 / 2298 | 1 | 137.119292 | 96.237923 | 89.355712 |
| 1 | 1.2 | 3-4 | 2295 / 2298 | 3 | 153.215783 | 114.484723 | 108.626736 |
| 1 | 1.5 | 1-2 | 2298 / 2298 | 0 | 597.101391 | 477.679343 | 477.545374 |
| 1 | 1.5 | 2-3 | 2297 / 2298 | 1 | 158.956698 | 120.549726 | 115.987262 |
| 1 | 1.5 | 3-4 | 2295 / 2298 | 3 | 200.420598 | 150.350122 | 145.117033 |
| 1 | 1.8 | 1-2 | 2298 / 2298 | 0 | 669.834377 | 543.300265 | 543.107402 |
| 1 | 1.8 | 2-3 | 2297 / 2298 | 1 | 184.009690 | 138.789700 | 136.076900 |
| 1 | 1.8 | 3-4 | 2295 / 2298 | 3 | 220.395537 | 170.220436 | 169.344932 |
| 2 | 1.5 | 1-2 | 2293 / 2293 | 0 | 855.684389 | 663.012381 | 659.201208 |
| 2 | 1.5 | 2-3 | 2289 / 2293 | 4 | 194.658630 | 149.345540 | 149.003914 |
| 2 | 1.5 | 3-4 | 2292 / 2293 | 1 | 230.139852 | 181.594524 | 179.806671 |
| 2 | 1.2 | 1-2 | 2293 / 2293 | 0 | 745.781020 | 536.861884 | 528.179250 |
| 2 | 1.2 | 2-3 | 2289 / 2293 | 4 | 198.250829 | 146.416204 | 146.313355 |
| 2 | 1.2 | 3-4 | 2292 / 2293 | 1 | 239.399337 | 181.414184 | 179.608469 |

All 2298 day-1 and 2293 day-2 demand vehicles were retained and arrived in each corresponding run. The end summaries reported no collisions, teleports, discarded vehicles or remaining vehicles. Scoring excludes only nonpositive raw differences separately for each segment. Day-1 denominators are 2298/2297/2295; day-2 denominators are 2293/2289/2292. The complete matched CSVs retain excluded raw rows without fabricated errors. The raw files contain no explicit vehicle IDs; simulated IDs support bookkeeping and do not establish actual observed identity.

Within each day, demand records, boundary speed inputs, network, detector configuration, seed and simulation settings were identical across candidates, with tau the only vehicle-parameter change. Day-specific measured inflow and downstream speed boundaries are conditioning inputs. The held-out measurements are therefore not an unconstrained forecast of a new city network.

The original attempt ended with 119 unfinished day-1 tau=1.2 vehicles and remains a failed/censored artifact. The single approved amendment extended the same final drain allowance from 900 to 7200 seconds for every candidate/day, using completeness evidence before any error-driven selection. No further horizon tuning was performed. Actual historical traffic runs include that failed attempt in addition to the 5 completed revised runs.

This is a separate San Pablo Dam tutorial adaptation. It does not calibrate the delivery network, traffic signals, parcel demand, robots or elevator behavior. Its errors and any transfer failure remain part of the evidence.

Automatic XML-schema validation is not claimed here. Any simulator warning that SUMO_HOME was unavailable and automatic XML validation disabled is retained in Independent_Audit.json; parsing, conservation and numerical comparisons do not substitute for schema validation.

Sources: [raw summary](E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\validation\san_pablo_dam\runs\public_02\Summary.json), [frozen v2 protocol](E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\validation\san_pablo_dam\Frozen_Protocol_v2.json), [selection before held-out runs](E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\validation\san_pablo_dam\runs\public_02\Selection_Before_Heldout.json), [retained first failure](E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\validation\san_pablo_dam\analysis\public_01_failure\Failure_Audit.md), [official tutorial](https://eclipse.dev/sumo/docs/Tutorials/Calibration/San_Pablo_Dam.html). Independent_Segment_Metrics.csv and Independent_Audit.json contain the unrounded recalculations.
