# Simulation validity statement

**The public calibration tutorial is reproducible, but the present exercise does not establish acceptable traffic accuracy or calibrate the delivery network.** A separate San Pablo Dam adaptation completed five revised SUMO runs and passed independent raw-output arithmetic and population checks. Its held-out absolute errors remain large. The delivery scenarios therefore remain synthetic.

## Observed evidence and controls

The public source is SUMO's [San Pablo Dam calibration tutorial](https://eclipse.dev/sumo/docs/Tutorials/Calibration/San_Pablo_Dam.html), pinned locally to an upstream commit. SUMO 1.27.1 was reused. Only the car-following headway parameter tau varied: 1.2, 1.5 and 1.8 s on day 1. The 1.5 s baseline is the tutorial runner's starting value, not an assertion about factory defaults. Within each day, demand, network, downstream speed input, other vehicle parameters, seed, time step, detectors and scoring rules were identical. The selection was saved before day-2 evaluation; only the baseline and selected candidate were evaluated on day 2.

Day-1 mean-of-three-segment RMSEs were 188.985605, 318.826229 and 358.079868 s respectively, selecting tau=1.2 s. On day 2 the same aggregate decreased from 426.827624 to 394.477062 s, a change of -32.350562 s, approximately -7.58%. This aggregate is an unweighted average of segment RMSEs, not pooled RMSE and not a delivery-performance measure.

| Held-out segment | Baseline RMSE (s) | Selected RMSE (s) | Direction |
|:---:|---:|---:|:---|
| 1-2 | 855.684389 | 745.781020 | Improved, still large |
| 2-3 | 194.658630 | 198.250829 | Worsened |
| 3-4 | 230.139852 | 239.399337 | Worsened |

The aggregate improvement is concentrated in the first segment; two segments worsened. A favorable percentage therefore does not establish calibration success. There was one held-out day and no prespecified domain-specific traffic-accuracy acceptance threshold.

## Verified and unverified layers

- **Verified in this public exercise:** original input/output hashes; independent reconstruction of detector passage differences and RMSE/MAE/bias; identical within-day controls except tau; training-only selection; complete arrival of all 2,298 day-1 and 2,293 day-2 demand vehicles in every revised run. Recorded collision/teleport warnings were absent and terminal counters were zero.
- **Observation limitations:** timestamps are matched by ordinal row, not verified observed vehicle identities. Segment-wise eligible counts are 2298/2297/2295 on day 1 and 2293/2289/2292 on day 2. Nonpositive raw differences are retained but excluded from the corresponding score; no demand vehicle is deleted. One invalid day-2 downstream difference produces no speed update, retaining the preceding valid speed. Day-specific observed inflow and downstream conditions are supplied, so this is conditional transfer rather than an unconstrained forecast.
- **Preserved failure:** the first attempt stopped with 119 unfinished vehicles. A single uniformly applied drain-horizon amendment changed the final allowance from 900 to 7200 s, based on completeness before examining error scores. The failed attempt remains archived; it is not counted among the five successful revised runs.
- **Not verified by this exercise:** local-city demand or driving behavior; synthetic delivery-road accuracy; signals, freight interactions, indoor robots or elevators; full-fleet delivery benefits. SUMO warned that automatic XML validation was disabled because SUMO_HOME was unavailable; XML parsing and output checks are not represented as schema-validation proof.

[FHWA's calibration guidance](https://www.fhwa.dot.gov/publications/research/operations/13026/007.cfm) treats calibration as comparison with observed conditions and cautions against unexamined transfer between settings. SUMO's [Berlin example](https://eclipse.dev/sumo/docs/Tutorials/Calibration/Berlin.html) demonstrates the additional observed geometry, traffic inputs and speed/congestion comparisons needed for a local claim. Ault and Sharon's [formal RESCO paper](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/file/f0935e4cd5920aa6c7c996a5ee53a70f-Paper-round1.pdf), sections 4.1 and 4.3, pp. 7-9, likewise separates synthetic implementation checks from broader comparative evidence and cautions about transfer. These sources support keeping structural correctness, controlled algorithm comparisons and empirical scenario validity separate.

The defensible paper description is: **controlled synthetic delivery experiments, supplemented by a separately documented public-data calibration-transfer exercise with mixed segment outcomes and substantial remaining error.** A local calibration claim would require relevant measured counts/travel times or queues, a declared acceptance criterion, frozen training choices and independent dates or sites.

Evidence: [independent report](../validation/san_pablo_dam/analysis/public_02_01/Independent_Validation_Report.md), [all segment metrics](../validation/san_pablo_dam/analysis/public_02_01/Independent_Segment_Metrics.csv), [raw audit](../validation/san_pablo_dam/analysis/public_02_01/Independent_Audit.json), [retained failure](../validation/san_pablo_dam/analysis/public_01_failure/Failure_Audit.md), [frozen revised protocol](../validation/san_pablo_dam/Frozen_Protocol_v2.json).
