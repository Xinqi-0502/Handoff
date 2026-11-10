# Baseline identity and contribution

**V449 includes two published complete heuristic-search policies adapted to the same local model. It does not reproduce a complete published truck-robot routing algorithm or establish comparison with the strongest contemporary freight solver.** This is a source/implementation identity note; it reports no new performance result.

## Published sources and actual adaptations

**Lazy A*.** Tolpin, Beja, Shimony, Felner and Karpas, *Towards Rational Deployment of Multiple Heuristics in A**, IJCAI 2013: [official full text](https://ijcai.org/proceedings/2013/0106.pdf), PDF p.2, Algorithm 1 and section 3.1. The archived formal PDF was read, including sections 3.2-4 on heuristic bypassing and Rational Lazy A*. The implemented policy evaluates the cheap bound first, evaluates the expensive bound when needed at OPEN selection, and reinserts when its priority rises. It includes the paper's OPEN bypasses, avoiding an unnecessarily weak version. The root evaluates both bounds. Our implementation adds a feasible initial incumbent, goal-on-generation updates, incumbent pruning, complete timed-label bookkeeping and reopening. Stable serial ties are declared implementation choices. **It is Lazy A* with OPEN bypassing, not the paper's probability/cost-based Rational Lazy A*.**

**Anytime Weighted A*.** Hansen and Zhou, *Anytime Heuristic Search*, JAIR 28 (2007), 267-297, [DOI 10.1613/jair.2096](https://doi.org/10.1613/jair.2096), [formal PDF](https://jair.org/index.php/jair/article/download/10489/25135): Algorithm 1, PDF p.5/printed 271; convergence and error bounds, pp.6-7/272-273. The implementation uses fixed weight 2, continues after improvements, updates generated goals and reopens improved labels. For absolute completion bound B at clock t, g=t-t0, h=B-t and priority=g+2h=2B-t-t0. Pruning and frontier certificates use the **unweighted** B, not the weighted queue head. Stable serial ties differ from the paper's experimental tie convention. Weight 2 is one frozen configuration, not a tuned family or a universal factor-two guarantee at arbitrary interruption. ARA* is not implemented.

| V449 method | Identity and information supplied |
|---|---|
| RADIUS_PAIR_LAZY | Published Lazy A* policy; this study's cheap radius basis and full PAIR bound |
| RADIUS_AWA | Published Anytime Weighted A*, weight 2; common radius bound |
| RADIUS_PAIR_AWA | Same published weighted policy; full numeric PAIR also changes priority |
| RADIUS_PAIR_AWA_GATED | Weighted common-radius priority plus this study's selective PAIR cutoff; not ordering-equivalent to the previous row |
| RADIUS_PAIR_EAGER | Eager best-first maximum-bound control using the same new PAIR information |
| RADIUS / ROUTE | Internal common searches using respectively individual-radius thresholds / the original exact quota-route bound; not named published freight methods |
| DP_ADAPTER | This study's standard complete topological DP implementation on the finite event graph, not a reproduced freight-paper algorithm |
| NO_BOUND | Deliberately unheuristic engineering check; not the sole or strongest baseline |

## Shared model and attribution boundary

All methods solve the restricted fixed-receiver, same-hub, ordered two-handoff objective H2: completion of the second handoff. They share the input travel model, capacity/service rules, feasible initialization rule and charged timing scope. FIFO travel and allowed waiting justify earlier-arrival dominance at the same structural state; improved labels remain reopenable. Heuristic arms use the common continuation bound and forward Pathmax, rather than dropping useful information after the first handoff. Standard Pathmax is prior work ([Zhang et al., IJCAI 2009](https://ijcai.org/proceedings/2009/0111.pdf), p.2, rule (a)); these common improvements are not the new contribution. DP uses its own complete recurrence without proposed-bound/incumbent pruning and certifies optimality only after full traversal. Its oracle shares recurrence/network source, so that oracle alone is not independent DP validation; separate small exhaustive checks and frozen-reference replay are the additional checks.

The proposed contribution is narrower: the route-conditioned shared-release necessary condition across two handoffs, its finite first-handoff event projection, and the specific constructive U_rel certificate for avoiding an unhelpful cutoff evaluation. Individual radius thresholds, cumulative resource accounting, generic branch-and-bound, lazy evaluation and generic heuristic bypass are established tools. U_rel bounds the **relaxation optimum from above**; it is neither a feasible delivery incumbent nor a lower-bound certificate. The low-cost implementation replaces exact quota-route evaluation with individual weighted thresholds, trading bound strength for evaluation cost.

Thus results must separate **bound information**, **evaluation cost**, and **published search-policy ordering**. A full-PAIR versus common-bound comparison within the same policy isolates information; lazy versus eager PAIR examines evaluation policy; gated AWA does not isolate cost from full-numeric AWA because their priorities differ. Equal expansions exclude internal bound work and do not imply equal computational cost. No worldwide originality or full freight state-of-the-art claim follows from these adaptations.

Evidence trail: [V445 formal-source audit](../../fleet_study_v445_capacity_coupling_20261107/Anytime_Baseline_and_Novelty_Audit.md), [V446 common-bound audit](../../fleet_study_v446_common_continuation_20261107/Baseline_Strength_Audit.md), [V447 design note](../../fleet_study_v447_random_high_load_20261107/Evidence_Design_Note.md), [V448 implementation notes](../../fleet_study_v448_radius_pair_prototype_20261107/code_notes.md), and [V449 method mapping](../scale_sources_v449.py). The V444 archived formal Tolpin PDF resolves its title as “Towards”; no new literature search or numerical run was needed.
