# Online H2-to-J bridge: source-only proof and scope audit

2026-11-07. This is an independent source inspection and mathematical argument, not a new numerical test. No solver, simulator, benchmark, result aggregation or plotting was run. No frozen source was changed. No blocking mathematical error was found in the inspected bridge under the conditions below.

## 1. Scope and the travel lemma

The domain fixes epoch E=6, two receiving-vehicle choices, two hubs, one receiver/hub for both atomic incoming parcels, pickup order a then b, and the other vehicle's deterministic old-delivery route. At least one pending old delivery before pickup a is an additional domain restriction. Both committed first customers have completed at E. This is a restricted forecast-model domain, not unrestricted fleet dispatch.

For the receiver, 0<wa<wb<=Q and wa+wb>Q. GIVEN pickup a before b and no unloading/storage alternative, a must be delivered before receiving b: the two incoming parcels alone exceed capacity. This does not prove that choosing a before b is globally optimal or unavoidable in an unrestricted model.

Let d be the directed Floyd closure of MATRIX distance divided by vehicle speed. Every predictor leg satisfies

    T_pred(t,p,q) >= t+d(p,q).

PublicSignal.leg passes the MATRIX distance to traverse. Travel increments telescope to distance/speed; Crossing.traverse adds nonnegative signal waits; ShortForecast adds a nonnegative observation penalty and another nonnegative wait. Floyd closure can only decrease the direct duration. Diagnostic query logs do not change these values. This pointwise lower envelope does NOT require the predictor to be FIFO: the COARSE penalty is switched off beyond E+48. Static d has the directed triangle inequality, so removing other visits, services and waits gives optimistic witnesses for a forecast continuation.

## 2. The two-receipt relaxation

At a phase-zero prefix (branch,tokens,t,p,cost), let O be the remaining identified old parcels, L their total weight, sigma the service time and tau_a=tau_b the handoff duration. Define

    qa=max(0,L+wa-Q),              qb=max(0,L+wb-Q),
    v_o=t+d(p,o)+sigma+d(o,h),
    Rq=weighted threshold of v_o reaching quota q,
    R0=t+d(p,h),
    A=E+d_truck(depot,truck_hub),
    B=max(A,Rqa)+tau_a,
    ell_a=d(h,a)+sigma+d(a,h),
    H_R=max(B+ell_a, max(A,Rqb))+tau_b.

A is a static optimistic truck arrival, not its COARSE forecast. Let alpha_o=v_o+tau_a and E1(x)={o:alpha_o<=x}. Gamma_o(x) is x plus the shorter static hub loop visiting BOTH a and o, in either order, including BOTH services. Let T(x) be the weighted Gamma threshold on O minus E1(x), for quota max(0,qb-weight(E1(x))); zero quota uses x. Then

    H_raw=min over x in {B} union {alpha_o>=B}
                    [max(x+ell_a,T(x))+tau_b],
    H_PAIR=max(H_R,H_raw).

For any legal continuation, write x* for the first receipt completion and h2* for the second. The first quota and truck arrival imply B<=x*. Old parcels actually delivered before the first receipt belong to E1(x*). E1 can include additional parcels that cannot all be visited together, so it is an optimistic set, not a feasible route. For each old parcel delivered between receipts and outside E1, one of the two orders relative to mandatory delivery a is realized; thus Gamma_o(x*)<=h2*-tau_b. At least qb DISTINCT old weight has been removed by the second receipt, and the mandatory-a loop is complete. Hence the union covers qb without using one old identity twice, and its relaxed value at x* is at most h2*.

Between alpha events E1 and its residual quota are constant, while every static loop arrival is nondecreasing. Moving x* left to the preceding event or B cannot worsen the relaxed value. The finite-event minimum is therefore admissible. H_R is separately admissible by the first quota, mandatory-a loop and total old quota before the second receipt; their maximum is safe. The finite events exactly minimize the optimistic coverage relaxation, not the original joint route problem.

## 3. Objective bridge: each customer charged once

Let g_s contain the receiver-prefix customer-flow contribution, including BOTH already completed first customers at 2E. Let C_other be the other vehicle's fixed-route forecast completion sum, EXCLUDING its already completed first customer. V450 initial() and _old_cost() implement this partition. New releases are at E; old releases are zero. Before pickup a,

    J_R=g_s+C_other
        +sum pending old o [t+d(p,o)+sigma]
        +[B+d(h,a)+sigma-E]
        +[H_R+d(h,b)+sigma-E].

The pair bound replaces only H_R in the final bracket with H_PAIR. Therefore

    J_PAIR=J_R+H_PAIR-H_R
          <= J_forecast(any completion of this prefix).

Every completed or pending customer appears once; each new release time is subtracted once. Transfers and truck dwell are not added as extra objective terms. Mandatory-a service influences b's completion as well as a's completion, which is legitimate for a sum of completion times, not duplicate charging of a customer. C_other is exact for the same frozen predictor and fixed route, not necessarily for physical execution. After pickup a, the common continuation bound separately covers pending old deliveries, a if pending, and b via remaining quota/mandatory-a return. At a complete route, the ledger equals the forecast objective.

## 4. Continuous cutoff, local cache and Pathmax

For incumbent U, EPS=1e-8 and RAW local J_R, define

    D_H=H_R+U+EPS-J_R.

Rejecting J_PAIR>U+EPS is equivalent to H_PAIR>D_H. The Boolean hook asks whether some event satisfies the mandatory-a return deadline and enough distinct weight in E1 union eligible Gamma parcels OUTSIDE E1. If any event qualifies it cannot reject; if every event fails it rejects. The continuous adapter does not copy the offline integer-time minus-one cutoff.

At xcap=max(B,Rqb+tau_a), E1 already covers qb. Hence max(H_R,xcap+ell_a+tau_b) upper-bounds H_PAIR. If this value<=D_H, further work can safely be skipped. It is an upper bound on a RELAXATION minimum, not a lower bound, physical feasible-plan cost or incumbent update.

published_online_v450.Domain.raw_bounds caches only raw local J bounds, keyed by the complete immutable State. extra_prune supplies raw_lower(s) and ignores stored_lower. This is essential: adding H_PAIR-H_R to an inherited Pathmax floor can double-count alternative lower-bound information. The safe numeric combination is max(parent_floor,J_PAIR), not parent_floor+(H_PAIR-H_R).

Pathmax itself is safe without forecast FIFO: every child completion is also a parent completion, so a valid parent lower bound is valid for every child completion. The propagated value is unweighted, never a weighted queue key or a relaxation upper bound. Dominance keys contain branch, complete token sequence, clock, position and cost; an earlier clock does not dominate a different later-clock prefix. Certificates use live unweighted bounds. This argument uses exact arithmetic; source-level fixed floating-point tolerances and the common downward 1e-7 guard are not a machine-verified real-arithmetic proof.

## 5. Online interpretation and physical scope

A precise description is **traffic-conditioned forecast search using a static free-flow joint capacity-release relaxation**. Traffic enters frozen observations, predicted prefix clocks, the fixed other-route forecast, greedy incumbents and subsequent predictions. The online Gamma functions themselves are x plus static constants. The broader FIFO time-dependent construction in the literature matrix is not evidence that this adapter implements that general case.

The proved inequality concerns the frozen FORECAST objective and the restricted domain. It does not establish a lower bound on actual SUMO J, an actual-optimal oracle, or global full-fleet optimality. Forecast error and physical activation delay can change arrivals; even C_other need not lower-bound physical cost.

Same-kernel gated PAIR adds a safe pop-time rejection while keeping the common radius queue-scoring channel. Its direct mechanism is avoiding subtrees that cannot improve the current forecast incumbent. It does not guarantee a different/better final route, less wall time, or better physical customer service.

Native activation is E+ceil(cpu_seconds*5)/5 with 0.2-second steps. Conditional on identical snapshot, network, demand, seed/runtime/controller, complete selected plan AND activation tick, the deterministic native execution is identical. Sub-tick CPU savings can leave actual J unchanged; different selected plans or activation ticks can matter. This is a conditional implementation statement, not an inference about the currently running cohort's outcomes.

## 6. Originality boundary and source anchors

Formula_Coverage_Matrix separates conventional weighted resource thresholds, identity accounting, route profiles, lazy evaluation and published search from the specific shared-x/forced-a/old-identity union. This note supplies the separate objective inequality requested there. It neither establishes first publication nor extends the matrix's inspected-paper coverage. The potentially distinctive object is the concrete coupled relaxation and its objective-specific adapter; Pathmax, AWA/ANA/Lazy, generic skipping and metric closure are not new contributions.

Source anchors, at inspection:

- V449 online_model.py:73 closure; :98 legal transitions; :142 forecast objective; :174 H2; :202 customer-wise J.
- V450 online_model_v450.py:64 other-route ledger; :70 prefix ledger; :136 cutoff; :229 search domain; :258 full-state key.
- V450 published_online_v450.py:16 raw cache; :27 shared lower bound; :30 pair hook; :47 adapter.
- V419 coarse.py:23 ShortForecast; :27 observation penalty.
- V419 model_turn2.py:103 waits; :117 traversal.
- V410 policy.py:36 waiting; :63 MATRIX leg.
- V450 native_online_v450.py:19 simulate; :23 activation; :33 seed/step configuration.
- V450 literature/Formula_Coverage_Matrix.md: explicit local-H2 scope and H2-to-J requirement.

Absolute source paths and inspection hashes follow. These identify files inspected, not a new runtime gate.

- E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\online\online_model.py
  SHA256: 31d5521a1424608b6f0654744fbb7e0cfc83978071dd0ec96e4b83993a76fb06

- E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\online\online_model_v450.py
  SHA256: 30f4fc0037a17c5cab646970c82d09aa4e8e0d72490f5920525e0d61d734051f

- E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\online\published_online_v450.py
  SHA256: 6243ff17e9aab4539fbfb6ac2ce21e6fca92203e7b2c7b94d4cb587b45d7dba5

- E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\baseline_replication\published_search_v450.py
  SHA256: 4d4286ad650f52264375bda90cf1a7c0c907eaa57df4396b58f959d7313b951c

- E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\online\native_online_v450.py
  SHA256: 3efeade4e8e8be761f4003e88e4186504fc4a203c50768c6d1baec47fbe5b8a0

- E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\literature\Formula_Coverage_Matrix.md
  SHA256: 4767166734f80ec306842408f4eb1dddd031492182dbb59ad0cf0582e57dbbc5

- E:\CodexResearch-xi\workspace\work\fleet_study_v419_signal_pedestrian_traffic_20261104\coarse.py
  SHA256: 0bc24da6f43bbe7943662c5f7486f7b03a5b1252eac2c4fd2277d5a5d18dc31c

- E:\CodexResearch-xi\workspace\work\fleet_study_v419_signal_pedestrian_traffic_20261104\model_turn2.py
  SHA256: c566526fc95137d8b4aa3e2872b5ec42ee30b870146afa017b772609a11b6a6f

- E:\CodexResearch-xi\workspace\work\fleet_study_v410_traffic_budget_policy_20261104\policy.py
  SHA256: 1935cee1702c05504910112869d4f7fd7dc1d179be2901062e00efbcc6199fa5
