# Published baseline identity and complete-loop implementation

Prepared 2026-11-07. This document records source-level implementation, not a claim that a runtime gate or performance comparison has passed. The authoritative runtime status is the separately assembled 24-case gate. New code is [published_search_v450.py](../baseline_replication/published_search_v450.py).

## Actual methods and comparison meaning

| Method | Complete search policy | Domain heuristic | Added study pruning |
|---|---|---|---|
| HZ_AWA_RADIUS | Independent implementation of Hansen--Zhou Anytime Weighted A*, fixed w=2 | Common weighted individual-via RADIUS and phase-1 continuation | None |
| HZ_AWA_RADIUS_PAIR_GATED | Identical HZ kernel, data structures, initialization, queue and Pathmax | Identical common heuristic and cache | Phase-0 Boolean PAIR cutoff at pop, with constructive relaxation-upper skip |
| ANA_RADIUS | Independent implementation of the complete printed ANA* loop | Identical common heuristic and cache | None |
| RADIUS_PAIR_AWA_GATED | Previously frozen specialized V448 deployment implementation | RADIUS plus Boolean PAIR | Deployment reference; engine overhead differs |

The central causal comparison is the first two rows. Comparing the specialized deployment implementation with the generic published engines also measures representation, numeric checks, bookkeeping and cache costs. It cannot isolate the proposed bound. The study contributes neither the weighted search policy nor the generic idea of avoiding an expensive heuristic evaluation.

## Primary-source mapping

**Hansen and Zhou (2007), Anytime Heuristic Search**, JAIR 28, 267--297, [DOI 10.1613/jair.2096](https://doi.org/10.1613/jair.2096). Algorithm 1 is PDF p.5 / printed p.271; goal-on-generation is explicitly discussed on p.270. The implementation preserves weighted OPEN ordering, strict cost-improvement reopening, continuation after better solutions, admissible unweighted generation/pop pruning, and the frontier error certificate. Sections 2.3.1--2.3.2 separate termination and error bounds. Their convergence statement assumes finite branching, positive minimum edge cost and nonnegative admissible h. Our finite event-state domain supplies termination even when an artificial root or other edge has zero cost; that is a domain-specific finite-state argument, not an assertion that the original positive-edge assumption is met verbatim.

**van den Berg, Shah, Huang and Goldberg (2011), ANA*: Anytime Nonparametric A***, [author paper](https://goldberg.berkeley.edu/pubs/ana-aaai-2011-vdberg-shah-goldberg.pdf), Figure 1 and Section 3, PDF pp.2--3. The policy selects maximum e=(G-g)/h, reopens strict improvements, updates G on goal extraction, then recomputes every surviving OPEN key and removes labels with g+h>=G. The accumulated E is the minimum selected e; the paper's theorem bounds G/G* by the selected maximum potential. Our principal certificate is independently computed from the unweighted frontier, not E. E is retained as a diagnostic, with null for infinity.

The [author ANA page](https://goldberg.berkeley.edu/ana/) links the [CMU software page](https://www.cs.cmu.edu/~maxim/software.html), which points to SBPL. The archived official [ANAplanner.cpp](https://github.com/sbpl/sbpl/blob/4d654845aa3b92aa1b4282a342e9011bac95aeb9/src/planners/ANAplanner.cpp) is pinned at commit 4d654845aa3b92aa1b4282a342e9011bac95aeb9. Functions get_e_value, UpdateSuccs, ImprovePath and Reevaluatefvals confirm h=0 handling, successor improvement, goal selection and global heap rebuilding. This C++ version uses integer-cast keys and also assigns G from the generated goal value inside ImprovePath. Our implementation follows the printed Figure 1 using floating potential keys and goal-pop updates. It is not a compiled SBPL binary reproduction. No source was copied into the Python engine.

## Complete-loop audit and declared adaptations

| Obligation | Implementation / condition |
|---|---|
| OPEN and reopen | Independent heap and live-label map; immutable plans; strict domain-proved dominance replaces worse open labels and can reopen expanded keys |
| Selection | HZ g+2h; ANA maximum potential. Stable insertion serial breaks equal keys; original benchmark tie behavior is not asserted |
| Feasible incumbent | Same fresh common greedy solution and full setup cost for every arm; published nil/infinite initial incumbent replaced by this finite seed |
| H2 objective | g=t-t0, h=absolute_LB-t. Queue therefore uses 2*absolute_LB-t-t0; objective and certificate restore t0 |
| Domain and phase-1 bounds | Frozen V448 transitions, FIFO closure, RADIUS thresholds and common continuation; these are study-supplied, not source-paper heuristics |
| Forward Pathmax | Child cumulative lower bound is max(local,parent); applied to all published arms, never substitutes a weighted key for a certificate |
| Duplicate contract | Local FIFO domain uses same discrete key and earlier arrival. Online J/non-FIFO approximation must use full exact identity, not earlier-clock dominance |
| ANA h=0 | Infinite potential for an improving candidate; non-improving labels are pruned. This matches the sign convention in official get_e_value |
| Pruning | Only admissible cumulative lower>=incumbent; gated hook is an explicitly added study extension, phase0 only |
| Stop | Soft wall checked between completed expansions; entire initialization and atomic overrun charged. Hard interruption is an exception, not a fabricated feasible row |
| Certificate | min(incumbent, every live unweighted lower); exhaustion or equality certifies the model optimum. Initial overrun uses conservative root g; no claim of proof merely from a feasible seed |
| Trace | HZ updates during successor generation (completed=N-1); ANA updates on goal pop (completed=N). Actual timestamps distinguish timely and late results |

The imported frozen Context is a common problem adapter, not the previous solver. Neither independent engine calls sp.solve. The gate compares all four arms with the same initialization, a separate exhaustive timed-prefix oracle and an independent topological DP, double-replays every improving plan, and tests three soft limits. Handwritten graphs specifically exercise reopen, ANA global rekey priority reversal, goal-pop versus generated-goal reporting, weighted-key behavior and Pathmax. See [gate source](../baseline_replication/check_published_search_v450.py); execution is delegated to the root runner.

These are complete published **search-policy reimplementations with disclosed adapters**. They are not a reproduction of Hof--Schneider's freight ALNS-PR system, Wei et al.'s multiobjective population algorithm, the authors' original benchmark results, or a real urban deployment.
