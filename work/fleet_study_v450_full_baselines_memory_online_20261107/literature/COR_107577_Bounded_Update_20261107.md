# Bounded update: COR 2026, 107577

2026-11-07. Status: **PARTIAL_PRIMARY_BODY / NO_COMPLETE_FULLTEXT**. This is a source-inspection update, not a novelty clearance or numerical result.

Reference: [Comparing four MILP formulations for the time-dependent inventory routing problem with FIFO-compliant travel times](https://doi.org/10.1016/j.cor.2026.107577), Computers & Operations Research 194 (2026), 107577. [Publisher record](https://www.sciencedirect.com/science/article/pii/S0305054826001954); [author preprint record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6205942).

## Access and actual reading scope

Eight narrowly targeted queries were used. Search-index extracts attributed to the publisher/DOI supplied parts of §§3.1, 3.3.1–3.3.3, 3.4–3.5 and 4.1, including the discussion of equation (33) and Proposition 4. Direct publisher/DOI and SSRN retrieval failed; the publisher PDF endpoint returned a cache miss. The existing-browser attempt stopped at initialization with a kernel-assets/path error, before accessing a tab. No credentials were requested.

No complete PDF, algorithm images, complete constraint block, proof, or appendix was inspected. PDF page numbers therefore remain **unverified**; section/equation identifiers below are the available locators. An indexed excerpt is not a complete formal article, even when it contains equations. The query/access log records the exact limits.

## What was actually located

| Locator | Inspected content | Relevance to this study |
|---|---|---|
| §3.1; §3.3.2 | FIFO travel-time transformation and breakpoint departure-time variables. | Temporal breakpoints and FIFO modelling have precedents; this alone does not identify the old-item quota construction. |
| §3.3.1, discussion of Algorithms 2–4 | Generate time-reachable vertices, remove vertices lacking a return route to the supplier, then generate admissible time-indexed arcs. Algorithm images were unavailable. | Closest visible pruning component: reachability/return feasibility. Its full rules remain unverified. |
| §3.5 | The example reports period/client inventory and replenishment quantities. | These visible quantities do not establish a matching two-atomic-reload old-item ledger. |
| §4.1, equation (33) and Proposition 4 | Big-M departure-time propagation and relative LP-relaxation strength among formulations. | A formulation-strength result is a different object from a conditional two-handoff query. The proof was not inspected. |

## Exact comparison target and unresolved test

The current candidate is the following **joint construction**, not FIFO, threshold selection, or generic pruning alone:

1. Identified old parcels O retain their identities across two atomic incoming orders at one receiver/hub.
2. One common first-handoff completion x determines E1(x). The remainder qrem(x)=max(0,qb-W(E1(x))) is filled only from O\E1(x); an old identity cannot release capacity twice.
3. Second-stage thresholds use FIFO loops visiting both incoming order a and each candidate old parcel, including service.
4. Minimize the optimistic bound over the forward event set {B} union {alpha_o >= B}.
5. The constructive value Urel=Fa(max(B,Rqb+tau_a))+tau_b upper-bounds the minimum of that relaxation. It can certify that an expensive check cannot prune; it is neither a feasible-plan incumbent nor a lower bound.

A direct equivalence finding would require an inspected formula or proposition mapping all of these elements, including the common x and the role/direction of Urel. Merely having departure variables, inventory conservation, FIFO profiles, a MILP representation, or a return-feasibility filter is insufficient to establish algorithmic identity.

**Conclusion:** no direct formula match was established in the inspected fragments. The missing method/algorithm material prevents a claim that the complete article lacks such a match. Retain this entry as an unresolved partial-text comparison, not evidence of global originality. No additional recent resource/profile paper was promoted to a direct challenger from these bounded searches; no broader absence claim follows.

The established ingredient-level precedents and exact current definitions remain in [Formula_Coverage_Matrix.md](Formula_Coverage_Matrix.md). Generic resource accounting, weighted thresholds, profile composition and heuristic bypassing remain prior art; the limited candidate contribution is their particular route-conditioned construction. No frozen code, input, measured result, or figure source changed.

