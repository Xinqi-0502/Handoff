# V450 native memory protocol, version 1

Status: implementation prepared; no algorithm memory observation has been run. The counter/lifecycle attempts are separate plumbing checks and retain failures. The unchanged V449 solver timing results remain authoritative for speed; these memory-profile timings are not pooled with them.

## Estimand and process boundary

The primary endpoints are Windows `GetProcessMemoryInfo(PROCESS_MEMORY_COUNTERS_EX)` lifetime `PeakWorkingSetSize` and `PeakPagefileUsage`, in bytes, sampled immediately after the selected solver returns and before result serialization or any correctness replay. `WorkingSetSize`, `PagefileUsage`, and `PrivateUsage` are also retained. Working set includes resident shared and private pages. Pagefile/PrivateUsage represent process commit, not actual disk writes. The OS lifetime peaks cannot be reset.

Each observation starts a fresh hidden process in an owned Windows Job. The before-solve baseline follows identical common imports, request/input parsing and garbage collection. Solver Context construction, its own caches, common greedy initial plan and all bound/search work occur after that baseline and inside the frozen solve clock. A separate model-setup peak is not claimed. Peak growth above the before-solve lifetime peak is only a supplemental description, not algorithm-private memory or a bound on it.

A pre-import read, after-result-serialization read, and parent-owned process-handle reads at start/exit are separately retained. Post-exit unavailable counters remain NA. The primary endpoint is the immediate post-solve sample, not an optional shutdown counter. Oracle, exhaustive reference, plan replay and derived outcome validation run only in the controller after measurement. No oracle result, plan or cache reaches a solver worker.

## Inputs and methods

The prespecified sample consists of the first two mothers at each m=6/8/10/12 in the frozen V449 main input order, with all four capacity/signal variants: original indexes 0:8, 100:108, 200:208 and 300:308. This yields 8 mothers and 32 correlated scenarios. The index rule does not consult outcomes. This is a posthoc memory sample, not another independent efficacy confirmation.

The original design is nine frozen V449 methods × 32 cases × 2 fresh observations = 576, followed by three complete published-policy implementations × 32 × 2 = 192, total 768. The three additions are HZ_AWA_RADIUS, HZ_AWA_RADIUS_PAIR_GATED and ANA_RADIUS. All twelve methods import the same frozen complete module bundle, including the published engines, before the baseline snapshot. Published policy and domain-bound contributions are separately named; this is not a replication of an entire urban-freight paper.

All solve calls use 1000 ms soft budget, 15 s cooperative hard watchdog, fresh context/caches, and the same greedy initial plan. The parent gives each owned process a 60 s total limit including Windows startup/import/serialization. Soft overruns, hard-solver timeouts, hard-process timeouts and initialization beyond a deadline remain distinct. A missing memory endpoint or incumbent is never filled with zero or a late result.

Method order rotates by scenario index and repetition. Two repeats are technical process repeats, not independent instances. All parameters and input IDs are fixed before observations.

## Gates and bounded cost pilot

1. Counter/lifecycle plumbing: a dedicated 16 MiB committed/touched allocation checks native commit growth and nondecreasing lifetime peaks; normal-exit callback and an owned timeout check the narrow additions to the previously tested V449 Job helper. `safety_01` failed because the 8 s timeout preceded the descendant readiness marker; it is preserved. `safety_02` uses 40 s, below the deliberate 120 s sleep, and still requires actual known worker/descendant exit. No solver is involved.
2. Existing frozen V448/V449 correctness gates and a source-matched complete-published-engine gate must pass before the memory manifest can freeze.
3. The memory wrapper checks original micro indexes 0,8,16 (one m3/m4/m5 case), all 12 methods once in fresh workers. The controller compares independent full timed-prefix enumeration with topological DP, validates every actual incumbent plan through two replay implementations, checks shared initial identity, trace times, final objective and nullable unweighted certificates, and validates positive native endpoints. These three wrapper cases supplement the prior complete 24-case algorithm gates; they do not replace them.
4. The cost pilot uses indexes 0,8,16,24 of the 32 selected scenarios (one fixed tight/free case per scale), nine original methods once: 36 observations. It measures startup, import, solver, validation and total operational costs. It does not select methods or cases by memory/quality wins.
5. Main measurement requires a separate source-matched cost approval record. If actual process cost requires a reduction, preserve this original design and freeze a prospective amendment before examining method-memory comparisons. The root has noted a possible four-method priority cohort; it is not silently substituted here.

A normal counter process took roughly 10 s in the first plumbing attempt, so solver-only V449 arithmetic is not a reliable duration forecast. The actual 36-observation pilot will determine the operational budget. No speculative speed or memory gain is promised.

## Evidence and interpretation

Each run retains protocol, exact source/input hashes, every request, stdout/stderr, native snapshots, raw solver result, parent validation, literal 100/500/1000 ms incumbent quality and on-time proof flags. Unknown or incomplete values remain NA. Three-way timer sums are checked separately; `root_bound_seconds` and nested bound timers are not added again.

Memory comparisons must identify sample/paired denominator, technical repeat aggregation and deadline completion. End-of-soft-run peaks can reflect different work beyond 1 s; literal outcome fields expose this. This protocol does not measure a sampled maximum restricted to exactly the first second. No heap, frontier or cache count is relabelled RAM; no tracemalloc is used. Results establish Windows process memory in this environment, not a general memory-complexity guarantee.

All outputs, failures and temporary files stay on E. The existing monitor enforces the 60 C fail-closed policy and E-drive identity. Owned Job termination never enumerates or kills unrelated process names. No installed runtime is moved.
