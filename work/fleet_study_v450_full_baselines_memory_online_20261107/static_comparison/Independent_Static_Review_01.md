# Source-only review of the fresh paired baseline comparison

2026-11-07. Reviewed run_fair_comparison.py and analyse_fair_comparison.py as currently saved, plus the memory adapter. No performance data were read or recomputed in this review.

Runner: the same1s soft/15s cooperative hard limit is passed to each arm; every solve creates its own Context and includes setup and greedy construction. Independent oracle and two plan replays occur outside solve and are not supplied to it. Injection uses the same frozen domain module. Method order is rotated deterministically. The new engine trace and nullable-certificate schema are compatible. The same-kernel HZ pair/no-pair comparison is the causal bound comparison; the frozen deployment engine is also an engineering comparison.

Required analysis hardening before declaring a final complete dataset:

1. Read and cross-check each PROTOCOL and CASE_COMPLETE, source/input hashes, split, method list, expected repetitions and requested input range. Verify the exact case×method×repeat matrix including hard-timeout records, not only successful-row repetition uniqueness. Reject duplicate/overlapping input cases across selected runs and unexpected cases/methods/repeats. PASS alone is not a full provenance proof.
2. Compute independent mothers from frozen selected INPUTS, not successful case rows, so an all-hard-timeout mother does not disappear. Explicitly report missing/hard-timeout cases by method. Keep failure rows in denominators without fabricating incumbents.
3. First-quality timing includes initialization. Separate initially optimal/already within5% or10% cases from actual search improvements. Recompute threshold targets and first hits from trace+independent opt; unknown oracle remains unknown.
4. Keep candidate/base direction explicit. itertools order makes HZ_AWA_RADIUS the lhs and HZ_AWA_RADIUS_PAIR_GATED the rhs. Its lhs percentage is baseline relative to candidate; it is not the candidate's reduction. Prefer an explicitly directed candidate-versus-baseline row in the final overview.
5. All-three-on-time proof subsets are correctly required for reported proof-time/expansion ratios. Preserve their identical denominator and report it beside every ratio. Overall expanded_end over timed-out cases is work consumption, not a solved-search efficiency ranking. Initial seed attainment and final optimality proof are different endpoints.
6. Add size/capacity/signal descriptive strata if final claims concern scale or pressure. A global total alone cannot establish those interactions. Technical repeats are not independent instances.

Memory compatibility: solve_selected passes the same module and watchdog correctly. validate_row handles remaining_bound=None with gap=None, independently replays plans in the parent after measurement, checks timer partition and permits goal-pop semantics. No source-level API blocker was found; this does not validate process-memory instrumentation at runtime.
