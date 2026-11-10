# Baseline identity and contribution

**V449 includes two published complete heuristic-search policies adapted to the same local model. It does not reproduce a complete published truck-robot routing algorithm or establish comparison with the strongest contemporary freight solver.** This note identifies methods and attribution; it reports no new performance result.

**Lazy A*.** Tolpin, Beja, Shimony, Felner and Karpas, “Towards Rational Deployment of Multiple Heuristics in A*,” IJCAI 2013: [formal PDF](https://ijcai.org/proceedings/2013/0106.pdf), p.2, Algorithm 1 and section 3.1. The implementation evaluates the cheap bound first, evaluates the expensive bound when needed at OPEN selection, and reinserts if priority rises. It includes the paper's OPEN bypasses; the root evaluates both bounds. Our adaptation adds a feasible initial incumbent, goal-on-generation updates, incumbent pruning, timed-label bookkeeping, reopening and stable serial ties. This is **Lazy A* with OPEN bypassing**, not the paper's probability/cost-based Rational Lazy A*.

**Anytime Weighted A*.** Hansen and Zhou, *Anytime Heuristic Search*, JAIR 28 (2007), 267-297: [DOI](https://doi.org/10.1613/jair.2096), [formal PDF](https://jair.org/index.php/jair/article/download/10489/25135), Algorithm 1, p.5/printed 271; convergence/certificates, pp.6-7. Fixed weight 2 gives priority g+2h=2B-t-t0, where B is an absolute H2 lower bound. The implementation continues after improvements, updates generated goals and reopens improved labels. Pruning/certificates use **unweighted B**, not weighted priority. Stable serial ties differ from the paper's experimental convention. Weight 2 is one frozen configuration, not a tuned family or an automatic factor-two guarantee at arbitrary interruption. ARA* is not implemented.

| V449 method | Identity and supplied information |
|---|---|
| RADIUS_PAIR_LAZY | Published Lazy A* policy with this study's radius basis and full PAIR bound |
| RADIUS_AWA | Published Anytime Weighted A*, weight 2, with common radius bound |
| RADIUS_PAIR_AWA | Same weighted policy; full numeric PAIR also changes priority |
| RADIUS_PAIR_AWA_GATED | Weighted common-radius priority plus selective PAIR cutoff; not ordering-equivalent to full-numeric PAIR |
| RADIUS_PAIR_EAGER | Eager best-first maximum-bound control with the same new PAIR information |
| RADIUS / ROUTE | Internal searches using radius thresholds / original exact quota-route bound; not published freight-method identities |
| DP_ADAPTER | This study's standard complete topological DP implementation on the finite event graph |
| NO_BOUND | Unheuristic engineering check, not the sole or strongest baseline |

All methods optimize **H2, completion of the second handoff**, for one fixed receiver, one hub and ordered handoffs. They share travel inputs, capacity/service rules, initialization rule and charged timing scope. FIFO travel with waiting supports earlier-arrival dominance; improved labels remain reopenable. Heuristic arms retain a common continuation bound and standard forward Pathmax ([Zhang et al., IJCAI 2009](https://ijcai.org/proceedings/2009/0111.pdf), p.2, rule (a)). These improvements are not the proposed mechanism. DP uses a complete recurrence without proposed-bound/incumbent pruning and certifies only after full traversal. Its oracle shares recurrence/network source; independent small exhaustive checks and frozen-reference replay supply additional validation.

The candidate contribution is the **route-conditioned shared-release necessary condition across two handoffs, finite first-handoff event projection, and specific constructive U_rel certificate**. Individual weighted thresholds, cumulative resource accounting, branch-and-bound, lazy evaluation and generic heuristic bypass are established tools. U_rel is an upper bound on the relaxation optimum, not a feasible delivery incumbent or a lower-bound certificate. The low-cost variant substitutes individual weighted thresholds for exact quota-route evaluation, trading strength for evaluation cost.

Results must separate bound information, evaluation cost and search ordering. Full PAIR versus the common bound within one policy examines information; lazy versus eager PAIR examines evaluation policy. Gated versus full-numeric AWA does not isolate evaluation cost because priorities differ. Equal expansions exclude internal bound work and are not equal computational cost. These comparisons support transparent **published-policy adaptations**, not full freight-method reproduction, a universal strongest-baseline claim or worldwide originality.

Evidence: [V445 formal-source audit](../../fleet_study_v445_capacity_coupling_20261107/Anytime_Baseline_and_Novelty_Audit.md), [V446 common-bound audit](../../fleet_study_v446_common_continuation_20261107/Baseline_Strength_Audit.md), [V447 design note](../../fleet_study_v447_random_high_load_20261107/Evidence_Design_Note.md), [V448 implementation notes](../../fleet_study_v448_radius_pair_prototype_20261107/code_notes.md), [V449 mapping](../scale_sources_v449.py). Archived formal PDFs were consulted; Tolpin's PDF title is “Towards.” No new search or numerical run was needed.
