# V449 online bridge: forecast24 independent results audit

Status: **independent raw audit PASS**. The audit reread all36 policy records, eight native scenario/plan replays, input/source receipts, event logs, complete compressed traces and trip records. It independently reconstructed loads, customer costs, physical parking intervals, truck release, canonical trace hashes and exact compressed-file hashes. All three execution layers report PASS. No solver, predictor or simulator was imported or rerun.

Two earlier analysis-reader attempts are preserved: the first expected monitor `status` instead of `Status`; the second hashed Windows CRLF text bytes instead of the native recorder's canonical JSON+LF stream. The successful fresh attempt03 checks each record's LF/CRLF representation, hashes the canonical stream, and separately hashes the compressed file. Neither issue required changing research sources or raw results.

## What the completed bridge establishes

The original customer-flow objective is connected to two atomic handoffs and actual native SUMO execution. All ten old customers and both new customers, both small vehicles, capacity checks, physical 2-second transfers and 4-second customer service remain in the execution. The supplier truck stays after a and departs only after b. This is a frozen-prefix two-batch execution bridge, not a continuously arriving-order, multiple-building rolling-dispatch system.

There are four related scenarios from one mother seed420511, with offsets0/24 and slow-background settings0/2; pedestrians are zero. Three policy timing repetitions do not create new orders. The 36 policy records select eight distinct scenario/plan pairs, each physically replayed once. This is diagnostic evidence, not independent confirmation of general benefit.

## The proposed extra bound has no observed online benefit here

RADIUS and PAIR select exactly the same plan in all four scenarios, have the same forecast and actual J, and expand respectively33,33,31,31 search prefixes. Both consume only five complete forecasts per scenario and exhaust the search with a forecast-optimality certificate, well below the shared cap of24. The initial witness is improved by search; the final equality is not merely an initially optimal seed.

PAIR performs21,21,19,19 phase-zero checks. Eight checks per scenario give a strictly stronger lower bound, but **zero checks produce an additional cut**. Stronger numerical values therefore do not establish an effective search mechanism on this cohort. PAIR adds work while the common solver already proves the optimum after relatively few expansions. No actual service benefit, truck-wait benefit or reduction in search states can be assigned to PAIR in this bridge.

## Per-scenario prediction and actual customer-flow objective

All objective values are customer-seconds, lower is better. R/P means the identical RADIUS and PAIR results.

| Scenario | Method | Forecast J | Actual SUMO J | Old-customer flow | New a flow | New b flow |
|---|---|---:|---:|---:|---:|---:|
| offset0, slow0 | R/P |1253.07000|1495.8|864.4|281.2|350.2|
| offset0, slow0 | Or-opt |1375.06125|1451.4|919.8|137.2|394.4|
| offset0, slow2 | R/P |1253.07000|1495.8|864.4|281.2|350.2|
| offset0, slow2 | Or-opt |1375.06125|1451.4|919.8|137.2|394.4|
| offset24, slow0 | R/P |1125.48000|1225.0|780.6|120.6|323.8|
| offset24, slow0 | Or-opt |1207.06125|1307.8|816.8|120.6|370.4|
| offset24, slow2 | R/P |1125.48000|1278.0|785.4|122.2|370.4|
| offset24, slow2 | Or-opt |1207.06125|1314.2|821.6|122.2|370.4|

Actual components are recomputed from `RESULT.json.completed`: old releases are zero, each new release is6 seconds, and ticks are divided by5. No constant contribution for the other vehicle is substituted into actual J.

The forecast ranks R/P better than Or-opt in all four scenarios, but actual execution reverses that ranking in both offset0 scenarios: R/P is44.4 customer-seconds worse. At offset24 it is82.8 and36.2 better. Thus a better certified forecast plan need not deliver better actual service. This is predictor error / objective ranking evidence, not a failure of the forecast lower-bound admissibility proof. It prevents a claim that the new pair bound improves traffic service.

## Supplier timing, reconstructed from events

Wait excludes the two 2-second transfer services. Dwell includes those4 seconds. Last handoff equals the recorded truck-release time, and is not last customer delivery.

| Scenario | Method | Truck arrival | Wait excluding transfers | Total dwell | Last handoff / release |
|---|---|---:|---:|---:|---:|
| offset0, slow0/2 | R/P |13.2|315.2|319.2|332.4|
| offset0, slow0/2 | Or-opt |95.0|201.0|205.0|300.0|
| offset24, slow0 | R/P |95.6|147.4|151.4|247.0|
| offset24, slow0 | Or-opt |95.6|183.8|187.8|283.4|
| offset24, slow2 | R/P |97.2|171.8|175.8|273.0|
| offset24, slow2 | Or-opt |97.2|183.8|187.8|285.0|

## Dispatch computation under the common forecast cap

Values are medians of three technical repetitions in milliseconds; setup, closures, common witnesses, exact prefix legs, bounds and complete forecasts are charged. Process import time and native replay are not included in these dispatch times.

| Scenario | RADIUS ms | PAIR ms | Or-opt ms | R/P full forecasts | Or-opt full forecasts | R/P expanded | Extra PAIR cuts |
|---|---:|---:|---:|---:|---:|---:|---:|
| offset0, slow0 |12.0361|12.3521|13.4599|5|24|33|0|
| offset0, slow2 |11.5937|11.8422|12.9058|5|24|33|0|
| offset24, slow0 |11.4374|11.9281|12.9251|5|24|31|0|
| offset24, slow2 |11.3814|11.7893|12.4638|5|24|31|0|

PAIR's case medians are slightly slower than RADIUS in each case. These short timings and one mother do not support a broad timing claim. Or-opt's stored `expanded=0` is a tree-counter incompatibility, not zero algorithmic work; compare its forecast calls/time rather than that field. Fewer full forecasts are not by themselves less total prediction work because prefix forecasting is also performed and timed.

## Source and interpretation limits

Raw run: `online/runs/forecast24_native_01` (`RESULTS.jsonl`, `PHYSICAL.json`, per-native `INPUT.json`, `RESULT.json`, `AUDIT.json` and compressed traces). Frozen input: `online/INPUTS_01.json`, SHA dee7a76550e766903375dfb96d6c0d48f0285000403baa7366c52d122f438a94. Gate SHA f125b3735cf347ac45a8c2152200495071abcf51e6a3a0a8c887f972ca8a9fdf. Final independent CSVs and the complete raw/source hash inventory are in `online/analysis/independent_bridge_03`.

RADIUS versus PAIR isolates the extra capacity relation because candidate domain, initial witnesses and common ordering agree. Or-opt changes the search policy as well as evaluation pattern and is the existing restricted freight adaptation of a published method. This cohort does not validate cross-receiver assignment, different hubs for the two batches, the truck's next building, indoor robots, continuing online orders, or real-world traffic calibration. No actual memory measurement was taken.

Next work is conditional: a prespecified new cohort or larger order count can test whether additional cuts appear, and independent traffic-model validation can test the forecast-ranking problem. Neither greater complexity nor more traffic is promised to produce benefit. Preserve this zero-gain cohort unchanged.


## Final independent quantitative checks

One deterministic solve per scenario (technical repeats first summarized within case): RADIUS and PAIR each expand128 prefixes and use20 full forecasts across four scenarios. PAIR evaluates80 extra phase-zero checks,32 of which are strictly stronger, and makes zero additional cuts. The sum of case-median dispatch times is46.448600ms for RADIUS,47.911700ms for PAIR and51.754600ms for Or-opt: PAIR/RADIUS=1.031499, a3.15% measured overhead here. This small, one-mother comparison is descriptive.

PAIR versus Or-opt wins forecast J in4/4 scenarios but wins actual J in2/4 and loses in2/4. Actual totals are5494.6 versus5524.8 customer-seconds (ratio0.994534); that small aggregate masks the two44.4-second losses and is not evidence of PAIR-specific benefit, since RADIUS is identical. The independent audit confirms all36 literal outputs are available, maximum dispatch elapsed13.518200ms, and every reported native objective equals the sum of its old/new customer components.

Final evidence: `analysis/independent_bridge_03/forecast24_cases.csv`, `forecast24_native_events.csv`, `Independent_Aggregates.json`, `Audit_Source_Hashes.json`, `Audit_Manifest.json` and `PROCESS_COMPLETE.json`. The raw run and all gated source files remain unchanged.
