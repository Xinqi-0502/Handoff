# Formula-level coverage and bounded originality conclusion

2026-11-07. No numerical run is reported here. Formal user-supplied papers, prior full-text audits and the current code are distinguished below. The claim is a narrow mechanism difference within inspected material, never a first-publication certificate.

## Exact candidate being compared

At a fixed receiver/hub with incoming order a then b, let O be identified old parcels, W its weight sum, Q capacity. The current experimental domain has wa<wb<=Q and wa+wb>Q, so a must be delivered before b is received. Define qa=max(0,W+wa-Q), qb=max(0,W+wb-Q). With FIFO earliest-arrival closure and nonnegative service, v_o is the earliest return to the hub after serving only old parcel o from the current state; Rq is its weighted order-statistic threshold. R0 is direct arrival. Let B=max(supplier ETA,Rqa)+tau_a and alpha_o=v_o+tau_a.

For a first-handoff completion x, E1(x)={o:alpha_o<=x}. Each second-stage threshold Gamma_o(x) is the minimum arrival of the two ordered hub loops visiting BOTH a and o, with both services. Fa(x) is the loop visiting a alone. The remaining quota is qrem(x)=max(0,qb-W(E1(x))). Its second-stage threshold uses only O\E1(x), so the same old identity never releases capacity twice. Combine that threshold with Fa(x), then add tau_b. Minimize over x in {B} union {alpha_o:alpha_o>=B}, and take max with the common independent lower bound.

The finite event set follows because E1 and qrem stay fixed between alpha events while FIFO makes all second-stage arrivals and their weighted threshold nondecreasing. This is exact for the stated optimistic coverage relaxation, not for the joint feasible route. Its upfront RADIUS threshold is polynomial and avoids the former exact subset-path DP. A per-item witness does not imply a route jointly serving all eligible old parcels.

For the cheap gate, xcap=max(B,Rqb+tau_a) makes E1 cover qb. Urel=Fa(xcap)+tau_b is an achievable value of the RELAXATION and hence an upper bound on its minimum. Urel<incumbent proves that evaluating the complete relaxation cannot prune; it is neither a feasible-plan incumbent nor a lower bound. The current integer-time Boolean cutoff uses deadline incumbent-tau_b-1; a continuous-time adapter must independently handle strictness and must not copy this subtraction blindly.

## Coverage matrix

| Source and exact location | Already present | What the inspected formulas do not establish |
|---|---|---|
| Hof--Schneider 2021, p.665 (32)--(46), p.675 Section4.1.1 | Nonempty receiving vehicle, service/replenishment order, supplier inventory and a partial-replenishment benchmark variant | A fixed atomic incoming parcel and current old-identity quota query; qrem after a shared first-handoff variable is not derived there |
| Hof, pp.663--664 (9)--(17), official AppendixB.4 p.11 | Synchronization by max of arrivals, transfer duration and supplier departure | The proposed FIFO route-conditioned finite-event minimization; the paper uses given arc travel times |
| Hof AppendixB.2--B.4, PDF pp.4--17 | Fixed-route segment loads, move evaluations, time-window surrogate, cycle filters | Admissible lower bound over unchosen old-delivery subsets; a move surrogate is not automatically a branch bound |
| Wei--Wang--Hu 2025, (9); (18)--(19),(30)--(33), Algorithm2 line26 | Time-dependent travel, truck/UGV route capacities, cross-echelon schedule adjustment and truck-to-UGV timing | No inspected state tracks this receiver's already-onboard old cargo through two atomic reloads; (32)--(33) concern satellite-to-first-UGV-customer timing, not the supplier's departure after this receiver's final handoff |
| Laborie2003, Section5.3.3, p.164 / PDFp.14, (2) | Resource deficit met by sorted earliest production events and cumulative weights | At fixed x the weighted threshold is directly analogous; the paper does not supply these forced-a road loops or this alpha-event projection |
| Muscettola2004, p.261 / PDFp.2, (1), Theorem2 | Single-count event identity, temporal resource envelope, maximum-weight closure/flow | Encoding resource identity is not new. No complete mapping to the route-conditioned disjunction across one shared x was established in the inspected text |
| Vidal et al., CIRRELT2013-22, Sections3.1--3.2, (9)--(15),(28)--(30) | Fixed-sequence resource/time profile concatenation and intermediate-time optimization | A profile for fixed sequences does not itself construct optional old-item coverage or the finite set of alpha events |
| Tolpin et al. IJCAI2013, Algorithm1 and Sections3.1--3.2 | Lazy evaluation and heuristic bypassing | The generic skip principle is prior art. The constructive Urel expression is the study-specific object still being compared |

Official primary sources: [Hof DOI](https://doi.org/10.1287/trsc.2020.1034), [Hof supplement](https://pubsonline.informs.org/doi/suppl/10.1287/trsc.2020.1034/suppl_file/trsc.2020.1034.sm1.pdf), [Wei DOI](https://doi.org/10.1016/j.tre.2024.103954), [Laborie DOI](https://doi.org/10.1016/S0004-3702(02)00362-4), [Muscettola primary](https://cdn.aaai.org/ICAPS/2004/ICAPS04-032.pdf), [Vidal author manuscript](https://www.cirrelt.ca/documentstravail/cirrelt-2013-22.pdf), [Tolpin primary](https://ijcai.org/proceedings/2013/0106.pdf).

## Evidence boundaries

The detailed prior comparisons are [V442 Hof formal audit](../../fleet_study_v442_fulltext_comparison_20261107/Hof_Formal_Formula_Audit.md), [V442 Wei formal audit](../../fleet_study_v442_fulltext_comparison_20261107/Wei_Formal_Formula_Audit.md), and [V443 targeted formula audit](../../fleet_study_v443_two_batch_departure_bound_20261107/Targeted_Prior_Art.md). V450 directly re-read Hof formal images pp.665--678 and Wei formal Algorithms3--4 images pp.17--18, plus previously extracted method text. Hof supplement formula locators reuse readable official text and the prior audit; this round does not claim newly verified rendered supplement pages.

The retained candidate is the joint construction: identity-preserving old-item ledger, one common first-handoff time, forced-a two-point FIFO witnesses, finite forward-event projection and the RADIUS-based cheap upper bound on that relaxation. Each ingredient has conventional antecedents. The inspected Hof/Wei algorithms do not provide this complete lower-bound query, but absence in two papers is not a global novelty proof. The shared-kernel comparison tests its empirical contribution without assigning AWA/ANA/Lazy framework improvements to the new bound.

The local target is H2 (second handoff completion, potentially supplier departure). It is not total customer delivery time. Incorporating it into customer-flow J requires a separately proved objective inequality; the online adapter must not use H2 as J or reuse unsafe clock dominance under a non-FIFO forecast.
