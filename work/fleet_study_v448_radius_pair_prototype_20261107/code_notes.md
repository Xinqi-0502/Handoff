# V448 implementation notes

Status: prepared and AST/static checked only. No solver, oracle, timing, or numerical correctness run has been executed for V448. V447 sources and its formal 400 scenarios/results remain untouched; this preparation reads only frozen sources and the micro-input file.

## Scope and API

selective_v448.py is a fork of frozen V447 with a fixed Context basis, either exact (default) or radius. reference_v448.py is byte-identical to V447 reference_v447.py, including the m<=12 validator.

    Context(spec, watchdog, profile=False, *, basis="exact")
    solve(spec, arm, watchdog, wall_ms=None, profile=False, audit=False,
          _context_factory=None, node_limit=None, checkpoints=NODE_CHECKPOINTS,
          *, basis="exact")
    solve_method(spec, method, watchdog, **kwargs)

The old positional solve arguments remain in their original order. Invalid basis names are rejected. A custom three-argument context factory still works with the default exact basis for existing policy fixtures; pairing a custom factory with radius is rejected explicitly, preventing silent basis omission.

| Public method | Internal search policy | Phase-0 basis |
|---|---|---|
| RADIUS | ROUTE | radius |
| RADIUS_PAIR_LAZY | LAZY_ASTAR | radius |
| RADIUS_PAIR_EAGER | PAIR_EAGER | radius |
| RADIUS_AWA | AWA_ROUTE, weight 2 | radius |
| Original ARMS names | Same original policy | exact |

All ten internal policies remain available with solve(..., basis="radius"), including the gate variants. The four tabled radius methods are the explicit public aliases. Every result records arm (internal policy), bound_basis, and method. Do not pool an internal ROUTE/radius row with exact ROUTE.

The inherited solver CLI remains exact-only. Its old correctness/gate code is retained for source continuity; it does not validate the new radius variant. Use the separately prepared check_v448.py for V448 micro validation. Neither a static pass nor a partial selected-case correctness pass authorizes performance runs.

## Mathematical change

Only phase-0 base() selects its quota-return values differently. Exact mode calls the unchanged quota_pair. Radius mode calls radius_pair, which computes each remaining old item's individual via-hub time, sorts those values once, and obtains both indivisible weighted thresholds Rqa/Rqb in one pass. Zero quota returns the direct earliest hub arrival, not zero. The shared formulas for B, independent base, alpha/Gamma, union events, early-release eligibility, and Boolean cutoff are retained.

Base.gb is now documented as either exact Gqb or radius Rqb. The same gb+tau_a<=B condition is valid in radius mode by individual-union saturation; it is not a common feasible path witness. The numerical return is unchanged. Its count is separately recorded as skip_radius_union_saturation, while skip_exact_quota remains reserved for the exact basis.

No new Base payload, per-state via cache, global quota cache, shared full-state bound cache, local DP cutoff, mask compression, network change or domain change was added. Later alphas() calls retain their original logic and reuse only the existing Network scalar closure cache. The same one-list/two-threshold radius calculation is used by ordinary RADIUS and every radius joint policy.

The exact quota_pair, Network class, Base data structure, mandatory continuation, alpha/Gamma computations, queue_priority, policy fixtures and Pathmax edge verifier were checked for AST identity where listed in Static_Preparation.json. Exact default semantic equivalence remains to be numerically verified. Small configuration/counter overheads exist in the new version; no wall-time identity with V447 is asserted.

## Accounting

All radius work occurs inside ordinary base evaluation and therefore inside search/total time; root evaluation is included in the inherited root timer. The code does not move precomputation outside the solve timer.

New counters: radius_calls and skip_radius_union_saturation. In profile mode: radius_ns and radius_individual_via_items. These are separate from quota_dp_labels and quota_ns. radius_ns is nested within base_ns, and root_bound_seconds is nested within search_seconds and elapsed_seconds; do not add nested timers together.

The constructor still builds the size-2^m mask-weight table. Removing the phase-0 exact quota DP does not make the whole solver polynomial or remove all exponential allocations. No process RAM, Python-allocation reduction or speedup has been measured.

## Validation preparation

check_v448.py is import-safe and only performs numerical work when explicitly invoked. It uses the frozen V447 micro24 inputs, the original V447 solver, the new V448 solver and the separate V447 structural-DP oracle/replay, all pinned by hashes. It never reads V447 main-result folders. The default is one m3/m4/m5 micro case, with a fresh 30-second per-case and 60-second overall budget. See Correctness_Plan.md for commands and coverage.

The preparation helper is source authoring plus AST comparison only. Its first expected-hash literal contained an extra character and failed before source copying. Preparation_Attempt_01.json preserves this non-numerical preparation failure. The corrected helper succeeded. No runtime failure or correctness pass is implied.

Core solver SHA256: f955dcb082a1e8fb4e683741a657c433209202f313571c07174d9ab15de42a6c.
Reference SHA256: 9810d96023a7710329d34a42f5c831687ea73e09fbfb42968fe4c660366a7416.
Source_Changes.diff records the source change from V447. Static_Preparation.json records the checked unchanged components. Final file hashes are recorded in Freeze_Manifest.json after static review.

