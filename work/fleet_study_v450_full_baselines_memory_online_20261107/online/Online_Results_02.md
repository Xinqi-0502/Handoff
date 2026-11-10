# V450 online results: complete single-epoch connection, no incremental service benefit

The shared-quota check is active in the implemented online J search, but this cohort does not demonstrate a practical gain from adding it. Against the same Hansen–Zhou AWA engine without PAIR, all 64 scenarios have identical executed plans and activation ticks at each of the three budgets. Customer-flow J, every old/new completion outcome and truck handoff waiting are consequently unchanged. At 50/200 ms the check removes 170 case-median expansions (2.70%), while common on-time proof cost is higher. This is a completed null outcome, not an unfinished integration test.

## Cohort and verification

The frozen cohort has eight mother seeds and eight matched offset/pedestrian/slow-vehicle conditions per mother: 64 related scenarios, not 64 independent traffic networks. Every scenario contains two small delivery vehicles with eight old parcels each and two new atomic parcels. The main comparison changes only the Boolean PAIR hook in the same complete published AWA engine, with the same initializer, J objective, priority, raw-bound cache, Pathmax, candidate domain and budget. Auxiliary RADIUS, ROUTE and complete ANA searches run at 50 ms.

All 1,728 policy calls and 128 distinct case/plan/activation representative replays completed; the independent raw audit passed all 576 case/arm/budget aggregates. Each replay completed all 18 customers. All-type collision XML and captured warning/error logs were checked: no recorded collisions or relevant collision/intermodal warnings were found in these outputs. This does not establish real-world safety. The microgate, two native prefixes, four latency/handoff checks and full source-hash checks also passed.

## Same-engine causal comparison

Values below are PAIR minus its same-engine RADIUS control. Expanded totals are sums of within-case medians over three technical repetitions; at 50 ms they describe all-case work, while at 200 ms both arms prove every case within the deadline. Proof-time comparisons use the same cases on both sides and require all three repetitions to prove on time.

| Budget | Actual J W/T/L | Mean J delta (s) | Mean handoff-wait delta (s) | Expanded: control → PAIR | Extra cuts | Common on-time proof cases | Proof-time sums: control → PAIR (ms) | Change |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 ms | 0/64/0 | 0.0 | 0.0 | 0 → 0 | 0 | 0/64 | NA | NA |
| 50 ms | 0/64/0 | 0.0 | 0.0 | 6304 → 6134 | 170 | 63/64 | 1511.637 → 1595.830 | +5.57% |
| 200 ms | 0/64/0 | 0.0 | 0.0 | 6304 → 6134 | 170 | 64/64 | 1569.166 → 1614.223 | +2.87% |

All eight mother-level average differences are zero at every budget. Cross-arm executed signature plus activation tick match in all 192 paired technical calls at each budget. The 64-case direct-replay subset is therefore the entire main comparison, not a selected survivor subset. There are zero strict forecast/actual ranking reversals in the 768 saved same-budget pair rows in this cohort; that does not imply forecast accuracy. At 50/200 ms, actual J exceeds the forecast by 469.860 seconds per case on average. The earlier V449 diagnostic ranking reversal and zero-cut result remain separate evidence and are not overwritten.

## Deadline and activation limits

At 10 ms, PAIR has 192/192 NO_PLAN_BY_DEADLINE calls and the control 191/192. Both have zero expansions and execute the common late initializer. No case has all three on-time initial plans; their executed-forecast ties must not be called valid within-budget quality ties. At 50/200 ms both main arms supply all 192 plans on time. PAIR proves all three repetitions for 64/64 cases at 50 ms, versus 63/64 for its control; at 200 ms both prove 64/64. This one 50-ms certificate-coverage difference accompanies slower aggregate common-case proof time and no service difference.

For all 64 scenarios the common initial plan is strictly improved in the longer-budget runs, so the null service effect is not explained by an already-optimal initializer. Planning latency is charged to execution, but every one of the 1,728 calls activates at tick 31 (6.2 seconds): the 0.2-second simulator step maps their measured latency differences to the same physical delay. Raw latency, overrun and quantization increments remain in the records.

## Absolute realized outcomes and auxiliary baselines

Each outcome is a policy-frequency-weighted representative replay, with the number of represented policy repetitions divided by three. It is not an average of three independent SUMO runs. The full absolute sums and means for every arm/budget are in Absolute_Outcome_Totals.csv; the table below shows per-scenario means across all 64. Old flow is the sum over 16 old customers, whereas a and b are individual new-customer flow times.

| Arm | Budget | J (customer-s) | Old flow sum (s) | New a flow (s) | New b flow (s) | Truck handoff wait (s) |
|---|---:|---:|---:|---:|---:|---:|
| ANA_RADIUS | 50 ms | 2416.040625 | 1770.115625 | 252.115625 | 393.809375 | 264.087500 |
| HZ_AWA_PAIR_GATED | 10 ms | 2752.996875 | 2130.165625 | 240.209375 | 382.621875 | 254.040625 |
| HZ_AWA_PAIR_GATED | 50 ms | 2416.040625 | 1770.115625 | 252.115625 | 393.809375 | 264.087500 |
| HZ_AWA_PAIR_GATED | 200 ms | 2416.040625 | 1770.115625 | 252.115625 | 393.809375 | 264.087500 |
| HZ_AWA_RADIUS | 10 ms | 2752.996875 | 2130.165625 | 240.209375 | 382.621875 | 254.040625 |
| HZ_AWA_RADIUS | 50 ms | 2416.040625 | 1770.115625 | 252.115625 | 393.809375 | 264.087500 |
| HZ_AWA_RADIUS | 200 ms | 2416.040625 | 1770.115625 | 252.115625 | 393.809375 | 264.087500 |
| RADIUS | 50 ms | 2416.040625 | 1770.115625 | 252.115625 | 393.809375 | 264.087500 |
| ROUTE | 50 ms | 2729.861458 | 2106.510417 | 240.095833 | 383.255208 | 253.922917 |

At 50 ms, PAIR, its same-engine control, ordinary RADIUS and ANA all realize exactly the same J and handoff outcomes. PAIR is better than old ROUTE in 63 cases and tied in one; the aggregate J reduction is 11.50%. That advantage is also achieved without PAIR and cannot be assigned to the new capacity relation. ROUTE has no cases with all three on-time optimality certificates (six individual calls prove), and its small expanded count reflects limited work under its expensive bound, not superior efficiency. Ordinary RADIUS is faster than PAIR in this cohort and uses a different search priority/container, so it is a counterexample to broad speed-superiority claims rather than a pure PAIR ablation.

The lower total J is accompanied by a tradeoff: the 50-ms optimized plans have mean truck handoff wait 264.0875 s, compared with 253.922917 s for ROUTE and 254.040625 s for the 10-ms initializer. New a/b also complete later on average; the total-J improvement comes from reduced old-customer flow. The original sum-of-customer-flow objective does not directly minimize truck waiting. Within the main same-engine comparison these quantities all tie.

## Separate check-cost diagnostic

The additional profile used all 64 frozen prefixes, two arms and 50 ms, after the complete formal run. It is separate from formal timing/quality: timers can change work completed before the budget.

| Instrumented arm | PAIR calls | Upper-check skips | Event checks | Loop queries | Extra cuts | Exclusive PAIR time (ms) | Share of total instrumented elapsed |
|---|---:|---:|---:|---:|---:|---:|---:|
| HZ_AWA_RADIUS | 0 | 0 | 0 | 0 | 0 | 0.0000 | 0.00% |
| HZ_AWA_PAIR_GATED | 5309 | 4337 | 1300 | 1702 | 170 | 80.9517 | 4.40% |

PAIR skips 81.69% of its 5,309 checks through the cheap upper test. Its exclusive cost is 80.9517 ms in total, about 15.25 microseconds per invocation, and 44/64 instrumented cases have positive rejection counts (range 0–12). Common raw-bound cache queries/hits/entries and common-bound costs are retained in Profile_Costs.csv; the cache is an ordinary shared optimization, not a claimed contribution. The instrumented candidate expands 6,127 states, whereas the formal case-median total is 6,134: these runs are deliberately not pooled. The observed small search reduction does not repay the added checking cost in the formal comparison.

## Physical evidence and remaining scope

Among the 128 representative replays, 126 record stopped red-or-yellow approach exposure, 64 record an occupied crosswalk after activation, and 48 record vehicle/pedestrian proximity within 15 m. These are observed exposures, not estimates of causal signal or pedestrian delay. Truck release commands coincide with the last b handoff in every replay; actual first motion follows 0.6–4.0 seconds later. Handoff waiting is hub dwell minus the two two-second transfer services. SUMO waitingTime/timeLoss and dispatch activation delay are separate quantities.

This is a frozen single decision epoch with live SUMO execution, not continuous rolling dispatch. Both new parcels share one receiver and hub within each branch; cross-receiver splits and multiple new hubs are outside this candidate domain. The deterministic road scenario is not a locally calibrated real-world freight network. Independent mothers number eight; technical repetitions and 64 related conditions are not independent demand samples. Online RAM bytes were not measured. These restrictions and the null incremental physical result remain part of the conclusion.

Evidence: analysis/full_02/Independent_Online_Audit.md; analysis/interpretation_02/Summary.json, Main_Same_Engine.csv, Arm_Budget_Summary.csv, Absolute_Outcome_Totals.csv, Profile_Costs.csv and Profile_Phases.csv; raw runs/full_02; profiles/full_01. All quantities were extracted after completion without changing measurements.
