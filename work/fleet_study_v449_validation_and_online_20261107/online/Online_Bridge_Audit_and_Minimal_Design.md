# V449 online bridge: source audit, proof and minimal implementation

Prepared 2026-11-07. New source only; no solver, correctness enumeration or SUMO run was performed by this author during preparation. AST is a separate source check. This is a candidate for root review and monitored small gates, not completed runtime evidence.

## Actual old system and what is reused

* `work/fleet_study_v420_paired_20261104/fusion420.py:16–43`: two receivers A/B, two hub branches HE/HW; the old legal plan has one incoming i and one X. `branch_pool` forces at least one pending old delivery before X. `lengths` fixes the other receiver's route.
* `fusion420.py:103–139`: all four branches, a common greedy witness, at most six complete forecasts per branch (24 total). Selection minimizes `pred['J']`. The elapsed-time assertion is a post-hoc <1 second assertion, not an interrupting deadline. Fixed 24 forecasts is not an equal wall-time protocol.
* `work/fleet_study_v419_signal_pedestrian_traffic_20261104/model_turn2.py:129–143` (the active override; its ancestor is `work/fleet_study_v410_traffic_budget_policy_20261104/policy.py:66–88`): forecast J is sum of all old absolute completion times plus incoming completion minus its release E. Handoff/truck waiting are separate recorded quantities. The present extension uses exactly the same customer-flow definition with two releases, J=sum(old C)+C_a+C_b−2E.
* `work/fleet_study_v420_paired_20261104/native420.py:55–133`: persistent SUMO process, 0.2 s steps, physical parking arrivals, 4 s delivery, 2 s synchronized transfer, zero collisions/teleports, complete all customer jobs. `research420.py:21–38,64–97` freezes the shared observed prefix, seals decisions, then replays each distinct plan. `audit420.py:get` independently audits physical stops, loads and completion events.
* `work/fleet_study_v415b_executor_audit_20261104/schedule.py:StopController` pins stops to the intended route occurrence. Reused unchanged via an augmented token-to-site dictionary; this matters on repeat visits to the same hub.
* `work/fleet_study_v420_published_baseline_20261104/paper_oropt.py:select_plans` is imported unchanged. Its 3/2/1-stop Or-opt neighborhood accepts our objective/feasibility callbacks. This is the existing freight adaptation, not a new replication of every component of its source paper. Our common domain keeps the other route fixed, so its attempted changes to that route are rejected equally by the common legal predicate.
* `work/fleet_study_v439_online_route_bridge_20261107/bridge_model.py:139–156,205–225,317–340` already established the safe pattern of exact forecast prefix clocks plus static optimistic future completion bounds. Its single-new-order domain cannot exercise the new two-batch relation.

The installed native executable is `D:\traffic-coop-research\.venv\Lib\site-packages\sumo\bin\sumo.exe`; existence was read-verified. Old V420 `runs/smoke_02/prefix/INPUT.json:48` records the same path. `work/fleet_study_v408_rolling_transfer_traffic_20261104/source/reused_road_sumo.py:64–88` discovers it and records package/binary versions and hashes without installation. The new native executor retains that discovery and provenance.

## Important clock restriction

`work/fleet_study_v419_signal_pedestrian_traffic_20261104/coarse.py:23–32` adds a 2/4 s observed traffic penalty until E+48, then removes it. That rule has not been proved FIFO and can create a downward jump. We do not propagate a lower-bound clock through it, apply earliest-time dominance, or use its predicted ETA as a lower bound on physical SUMO travel.

Exact candidate/prefix clocks continue to use the original COARSE forecast. The bound uses a directed free-flow distance closure d at 8 m/s and a separate truck closure at 6 m/s; positive services/transfers remain. The closure satisfies directed triangle inequalities and every forecast leg has at least that free-flow duration. Thus deleting visits and waits is an optimistic relaxation even when the original forecast is non-FIFO. No new traffic calibration is implied.

## Frozen minimal domain

The branch selects one of A/B and HE/HW. Both atomic new orders are assigned to this receiver and hub in order a then b. The other receiver executes its fixed `lengths` route. Both goods are on the truck at E, and the truck stays at the hub until the last transfer finishes. wa=3, wb=4, capacities retain A=6/B=5; wa<wb<=Q and wa+wb>Q imply a must be delivered before b can be received. All ten old jobs, both new jobs, and both small vehicles remain in the objective and native execution.

This is a real enlargement of the original one-order model, not a claim that the unchanged old model already had two handoffs. It does not search across separate receivers or separate hubs for a/b, split batches, arbitrary replenishment, truck next-building sequences, multiple rolling replans or indoor robot geometry. In a future broader domain, unmatched branches must retain a common safe bound rather than be silently dropped. The current branch guard fails closed if its atomic/capacity assumptions do not hold.

Inputs are the lexical first four snapshots of the sealed V420 archive, selected without new outputs. a retains the original incoming destination MW/ME; b uses the other destination. These are four related diagnostic settings from one old seed, not four independent new instances or a confirmation study. `check_online.py prepare` preserves archive provenance and writes a fresh file; it does not solve.

## Why a second-handoff bound safely bounds original J

For a prefix with exact forecast time t, receiver position p, and old remaining load L, let qa=max(0,L+wa−Q), qb=max(0,L+wb−Q). For each remaining old item o define

`r_o = t + d(p,o) + s_o + d(o,h)`.

Let R(q) be the weight-q quantile of r_o (R(0)=t+d(p,h)). Let the optimistic truck arrival be `A=E+d_truck(T,Th)`, and `B=max(A,R(qa))+tau_a`. This B is a lower bound on the post-first-handoff clock. Let `F_a(x)=x+d(h,a)+s_a+d(a,h)`.

Common second-handoff lower bound:

`Hbase = max(F_a(B), max(A,R(qb))) + tau_b`.

For first-handoff posttime x, `E1(x)={o:r_o+tau_a<=x}`. Only outside-E1 items contribute to the remaining quota `max(0,qb−weight(E1))`; each such item's necessary post-first two-delivery loop is the minimum of h-a-o-h and h-o-a-h, with both services. Its weighted threshold is T(x). The pair bound is

`Hpair=max(Hbase, min_x [max(F_a(x),T(x))+tau_b])`.

Only x=B and the alpha_o=r_o+tau_a events at or above B need evaluation. Between events the eligible set is unchanged and every loop increases with x; equality belongs to E1. Both stages share the same old-item ledger. This is the V448 RADIUS+PAIR relaxation specialized to a static optimistic projection, not a full PDPTW oracle.

For each common completion lower bound e_j, the proposed J bound replaces only b's term:

`LB_J = completed_flow + fixed_other_forecast_cost + sum_remaining_old(e_o) + (e_a−E) + (max(e_b_common,Hpair+d(h,b)+s_b)−E)`.

At phase zero e_a=B+d(h,a)+s_a, and e_b_common uses Hbase. Afterwards both arms use the same direct/remaining-weight-quota and forced-a-return continuation bound. At a terminal prefix the bound equals forecast J.

Proof: Every completion of a fixed prefix has a first-handoff clock x>=B. Each old item released before that event belongs to E1(x). If an old item is released later before b is received, deleting other visits yields one of the two a/o loops, so its necessary completion-to-hub time is no greater than the real second-handoff time. The union weight necessary for qb therefore enforces the threshold. The truck and receiver synchronization waits can only increase actual completion. Hence Hbase<=Hpair<=H2 for every completion. FIFO is needed only for the optimistic relaxation (here static), not the COARSE predictor. Finally every individual e_j is <= its own completion C_j under the SAME feasible plan. Summing these termwise inequalities is valid even when the relaxed terms reuse resources. It would be invalid to add an extra H2 objective term to an already complete J bound. No item is counted twice in the J sum or twice within the two-stage quota ledger.

`fixed_other_forecast_cost` is exact only for the deliberately separable planning forecast and the fixed other route. In native traffic, either vehicle can affect the other; actual evaluation therefore recomputes every delivery and never treats that other-vehicle contribution as a constant. The bound certifies the frozen forecast objective, not native/real-world J.

## Implemented controls and gates

New source: `online_model.py`, `native_two_batch.py`, `check_online.py`, `run_online.py`.

RADIUS and PAIR share the same four witnesses, exact transitions, candidate domain, RADIUS priority, tie rules, round-robin branch policy and terminal forecast calls. PAIR adds only its extra pop-time J lower-bound check. RADIUS does not calculate the pair event projection. No signed or earliest-arrival dominance is used. All setup, greedy construction, closure construction, prefix legs, bounds and full forecasts are timed and counted. Existing Or-opt is a separate external-method comparison, not the pure information ablation.

`check_online.py check` independently enumerates legal routes/actions and forecast clocks, tests prefix-set equality, each exact prefix state/time/cost, base<=pair<=true minimum J, Hbase<=Hpair<=true minimum H2, terminal equality and plan forecasts. It checks all three cap24 plans, their shared initial witness, and unlimited RADIUS/PAIR optimality against enumeration. The reference does not call production actions, bounds or solver. The forecast leg itself is shared and is not an independent traffic-model validation.

The native extension uses the original scene and route-occurrence controller. Both transfers require physical simultaneous parking and capacity. Truck departure is explicitly held until b. The independent event auditor reconstructs each load, 4 s delivery interval, 2 s transfer interval, all old/new completions, unchanged prefix hash, and continuous truck parking between handoffs. It verifies the final sum-flow metric and zero collisions/teleports. This is the actual connection to SUMO; it must pass at runtime before being claimed operational.

Separate protocols: (1) forecast24: six full evaluations per branch; (2) wall: a literal deadline measured from before setup, with only trace incumbents available by the deadline eligible for native replay. Full-expansion overrun is recorded, never counted as on-time. The common mandatory witness construction can overrun a very small budget; if no witness is available then the literal result is missing, not an oracle/default imputation. Policy timing runs before native replay. Technical repeats and repeated plans are not independent data. Each unique selected plan is replayed once from the exact same frozen native prefix.

## Root-run commands after independent static clearance

All commands run in this online directory with Python `-B -X utf8` and E-local temporary directories, under the existing 60 C/fail-closed supervisor when numerical work begins. Do not run concurrently with the main V449 timing study.

1. `python -B -X utf8 check_online.py prepare --out INPUTS_01.json`
2. `python -B -X utf8 check_online.py check --inputs INPUTS_01.json --out gates/check_01`
3. Only after gate PASS: `python -B -X utf8 run_online.py --inputs INPUTS_01.json --gate gates/check_01 --out runs/forecast24_native_01 --mode forecast24 --repeats 3 --native`
4. Freeze a wall budget before outcomes, then separately: `python -B -X utf8 run_online.py --inputs INPUTS_01.json --gate gates/check_01 --out runs/wall_native_01 --mode wall --wall-seconds 0.05 --repeats 3 --native`.

0.05 seconds is an exposed implementation default, not a scientifically justified final budget; root must freeze the planned budget before comparative outcomes. The small gate is required before any native run. New output paths must be fresh. Failure files are preserved. Gate input/source hashes and PROCESS_COMPLETE are mandatory; all local Python and loaded research-dependency source files plus network/leg data are hashed. No claim of success is made by preparation alone.

## Native process ownership and memory boundary

Do not launch native replay directly as the monitor's child. `job_host_online.py` is a thin wrapper around the one existing Windows Job Object implementation in `validation/san_pablo_dam/run_public_validation.py:owned_windows_process`. It verifies an explicitly supplied SHA before importing that helper. The monitor must own this host; the host atomically starts the online worker inside a kill-on-close Job and all SUMO descendants inherit membership. Killing the host therefore closes the non-inherited Job handle and terminates only this owned process tree. No native call occurs during module import.

Host CLI after helper lifecycle clearance:
`python -B -X utf8 job_host_online.py --python <absolute-python.exe> --script <absolute-online/run_online.py> --args-json <absolute-frozen-string-array.json> --out <fresh-E-host-log-dir> --helper-sha256 <final-public-helper-SHA> --timeout-seconds <frozen-cap>`.

The argument-array file must use absolute INPUTS/gate/output paths because the worker CWD is the fresh E host-log directory. The public-helper source is also included in the online gate's source hash closure, so subsequent changes invalidate that gate. Root must supply its final hash after the helper's separately planned normal/timeout/host-killed lifecycle tests. No such lifecycle test was run by this author.

The bridge currently records search counts and timing, not actual RAM. A future separate instrumented run can read peak committed memory of the owned process Job (or sampled private/working-set bytes per PID with an explicit sum definition), reporting Python and SUMO scopes separately. Native-library/JVM or OS caches must not be called Python allocations. Such measurement needs its own API/ownership smoke test and a common sampling frequency; it must not be silently inserted into the uninstrumented timing arm. No label-count-to-byte conversion or memory saving is claimed here.
