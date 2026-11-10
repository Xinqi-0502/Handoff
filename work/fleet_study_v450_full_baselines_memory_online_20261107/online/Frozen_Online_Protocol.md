# V450 online protocol: prepared, not executed

This new E-only stage follows V449's negative native diagnostic without changing or superseding it. V449's four related scenarios had identical PAIR/RADIUS plans and actual J, zero extra PAIR cuts, and approximately 3% higher PAIR planning time. Stronger numerical bounds were not actual additional cuts. V450 is prepared to test a larger, predeclared workload; it does not promise improvement.

## Cohort, objective and model scope

Use new mother seeds 4509001 through 4509008, each crossed with signal offset 0/24, pedestrian count 0/10, and slow-traffic setting 0/2. There are 64 related scenarios from eight mothers. Offset 0 is still signalized. The traffic setting changes two slow vehicles in addition to the common background vehicle; it is not a general traffic-volume or real-congestion calibration. No case, retry, seed or budget may be retained based on its result.

Each vehicle A/B begins with eight old parcels of total weight 12 and capacity 12. The first committed parcel has weight 1 and finishes at t=6; therefore each decision state has seven pending old parcels with weight 11, and the already completed first deliveries contribute 12 customer-seconds to J in total. The incoming atomic parcels a/b weigh 8/10. Their combined weight18 exceeds capacity12, so delivery of a before accepting b is forced. The original customer-flow objective is J=sum(completion minus release), with old release0 and both new releases6. Both vehicles' full old demand remains in the objective and in native execution.

Four common branches select receiver A/B and hub HE/HW; both incoming parcels use that same receiver/hub and handoff order a then b. The other receiver follows a deterministic nearest-next old route, identical across methods. This remains a restricted branch domain, not a global assignment over arbitrary receivers and hubs. Forecast and actual physical objectives are reported separately. An exact fixed-other-route forecast contribution is not treated as a fixed physical SUMO contribution.

**This stage is one frozen decision epoch. It is not a complete continuous-order or multi-building rolling dispatcher.** A future two-epoch continuation must rebuild the second state from actual remaining cargo, completion events and vehicle positions, retain traffic without restart, and record release-to-safe-replanning-barrier delay. It is not implemented or claimed by this source version; root explicitly prioritized the larger single-epoch gate and native pilot first.

## Frozen arms and budgets

Primary arms use the same independent complete Hansen-Zhou AWA kernel, weight2, same feasible initializer, same domain, same OPEN/archive, same actual-parent Pathmax, same full timed-state identity key, and same base RADIUS heuristic:

- HZ_AWA_RADIUS: common heuristic, false extra-prune hook.
- HZ_AWA_PAIR_GATED: same priority and stored-bound channel, with one additional safe Boolean pair rejection at pop.

Both run at 10, 50 and 200 milliseconds. RADIUS, old exact-quota ROUTE, and complete ANA_RADIUS run at 50 milliseconds as auxiliary comparisons. The internal custom weighted kernel is only a small correctness cross-check, not a main causal comparison. AWA and ANA are complete published search-loop adaptations to this restricted objective/domain, not reproductions of a complete freight-paper experiment. ANA keeps its distinct goal-pop and OPEN rekey policy.

There are three timing repetitions, with a predeclared cyclic arm/budget order. Full cohort size is 64*9 arm-budget cells*3 = 1728 policy calls; the fixed cost pilot has two conditions from seed4509001 (offset0/24, pedestrians10, slow traffic2), hence54 policy calls. These are technical repetitions, not independent mother instances. Cold module import is excluded, as a resident dispatcher assumption; context creation, closures, common initialization, all search/bound calculations, certificate and adapter return are included in measured planning elapsed time.

The initializer is common and feasible. Initial exact optimality is known only where a certificate or a strict improvement identifies its status; unknown cases must remain unknown. The 24 micro states also have independent enumerated exact targets. A policy must not receive those oracle plans or costs.

## Same-objective lower bound and selective rejection

The lower bound is on J, not on H2 directly. Completed first and prefix customer flow is g_J. Pending old customers receive independent free-flow completion bounds; the fixed other receiver contributes its exact common forecast cost. The two new terms each subtract release6 once. Only b's earliest completion is strengthened from H_base+d(h,b)+service to H_pair+d(h,b)+service. Thus

`J_pair = J_radius + H_pair - H_base`.

The first/second handoff formulas use the same old-parcel ledger, wa+wb>Q, a common hub and fixed order. Static directed free-flow shortest-path closure is optimistic under the exact COARSE prefix forecast. COARSE itself is not assumed FIFO: no earlier-clock dominance or signed static dominance is used. The full identity key contains branch, tokens, exact time, position and accumulated customer flow. A common 1e-7 downward arithmetic guard protects real-valued lower bounds in the published adapter.

AWA orders by `g_J + 2*(stored_LB_J-g_J)`; only unweighted admissible bounds certify/prune. The parent bound remains admissible for each actual child because the child's completions are a subset of the parent's completions, even when the predictor is non-FIFO. The joint hook does not change this stored priority channel.

For an incumbent U and local common J bound B_J, the extra strict rejection translates to H_pair > H_base+U+EPS-B_J. Its Boolean finite-event test scans B and old-release breakpoints alpha_o>=B. It counts each old parcel once in E1 union the eligible two-visit loops, and tests sufficient old weight jointly with the forced a loop. A cheap upper bound on this relaxation, `max(H_base,max(B,R_b+tau_a)+loop_a+tau_b)`, can skip the expensive test if it already passes the translated threshold. This is an upper bound on a relaxation only: it is never a feasible incumbent, never a lower bound, and is never propagated. The additional hook does not prune equal-cost ties; common published-kernel incumbent pruning retains the original algorithm's tie policy.

## Planning latency and native execution

Customer releases remain at t=6. Small vehicles finish their committed first delivery and remain parked while planning runs. The supplier is dispatched only when the chosen plan activates. Background vehicles, traffic signals and pedestrians continue advancing throughout this simulated planning interval. Activation is `6+ceil(measured_planning_seconds/0.2)*0.2`. Save raw elapsed time, activation tick, rounded delay and the nonnegative quantization increment. The 0.2-second step can hide substep timing differences; no precision beyond it is claimed.

If no complete incumbent action sequence was available by the literal budget, record `NO_PLAN_BY_DEADLINE` and keep within-budget J/plan null. For service continuity, the late mandatory common initializer is executed as an explicitly marked fallback after the full measured planning time. It is never counted as an on-time solution. All fallback/failure cases remain in the denominator. Late returned improvements are not used to replace the common fallback.

All policy timing ends before physical replay. For every distinct selected plan within each case/arm/budget's three repetitions, replay the repetition with median elapsed time among repetitions of that plan (lower middle for two, then repetition ID). Preserve every distinct plan. Exact deduplication across selections requires identical case, plan signature and activation tick. Replays do not create new independent traffic observations, and the physical output is not claimed to be the median of repeated native outcomes.

The truck remains physically at the selected hub after handoff a, then leaves immediately after the final b transfer. Customer delivery, last transfer, physical truck release and final fleet arrival are distinct events. The horizon is1800 simulation seconds. A horizon failure retains raw trace, completed/unfinished customers and failure record; incomplete physical J is not filled with zero or silently excluded.

Native evidence records every old/new completion, transfer/load/service intervals, the truck dwell and wait excluding transfer, trip duration/waiting/timeLoss, collisions, teleports, and full pedestrian/signal trajectories. Exposure summaries count stopped approaches under the actual next movement's red/yellow signal, crosswalk occupancy after activation, and pedestrian/vehicle proximity within15m. Proximity is exposure, not proof that a pedestrian caused delay. Report zero actual exposures even when a setting requested pedestrians.

## Gates and ownership

1. Deterministically generate definitions and 24 fixed micro states (3 unseen micro mothers, 3/4 old parcels, Q12/16, offsets0/24). This is preparation, not a numerical result.
2. The independent full-route reference checks every micro prefix, J clocks/costs, terminal equality, RADIUS/ROUTE/PAIR admissibility, the Boolean cutoff, common parent-bound inheritance, unlimited results from all three published-domain methods, common initializers and node0 behavior. Run only after independent static review.
3. Prepare the two fixed pilot native prefixes under the shared thermal monitor.
4. Native gate replays each pilot prefix's common initializer with fixed synthetic delays0.05/0.21 seconds. These four replays test controller/activation invariants and are not policy performance observations.
5. Only after both gates PASS run the fixed pilot, preserving all methods and budgets. Advancement to all64 depends on correctness and operational cost, not on a favorable effect.

Every output is a fresh folder. Both gates hash the full source closure, including the published engine, old immutable dependencies and network files. A source change requires a new gate. Use the V449 frozen owned-process helper by exact SHA and the existing temperature monitor: monitor -> V450 Job host -> worker -> SUMO. Never launch native SUMO outside this owned process tree. The shared helper and old V449 sources are not modified.

Detailed profile mode is separate and disabled in formal timing. It measures common bound time, inclusive pair-hook time and exclusive pair-hook time after subtracting internal bound overlap. Raw query/cut/queue counts remain available in main timing. No native or Python RAM bytes are measured by this online runner; separate fresh-process memory measurement is required for a RAM claim.

## Reporting rules

Primary physical outcomes are actual all-customer J, old/new customer flow, truck waiting/dwell, service completion and deadline coverage. Retain predicted/actual ranking reversals. Report all64 scenario rows and mother-level paired summaries, traffic strata, wins/ties/losses and unknowns. Main same-engine ablation isolates the additional check; ANA/ROUTE comparisons change the search policy or base heuristic and cannot isolate that single mechanism. Do not pool this cohort with V449's four diagnostics or static-order benchmarks. Neither this synthetic junction nor the separate public-road validation makes it a calibrated delivery digital twin.
