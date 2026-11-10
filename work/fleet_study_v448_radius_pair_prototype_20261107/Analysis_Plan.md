# V448 read-only analysis plan

Prepared before pilot analysis. No solver, oracle, checker, gate assembly, benchmark, or data analysis is executed by this preparation. The script imports only the Python standard library and writes only a new descendant of V448/analysis. It does not import numerical sources or modify inputs, runs, or solver files.

## Frozen coverage and units

The frozen INPUTS.json has 32 scenarios from 8 independent mother instances: m = 6, 8, 10, 12, two mothers per scale, each crossed with two capacities and signal off/on. These are 32 related scenarios, not 32 independent networks. Technical repeats are not extra independent instances.

Primary methods RADIUS, RADIUS_PAIR_LAZY, RADIUS_AWA, and NO_BOUND each have 3 observations per scenario (384 calls). Auxiliary RADIUS_PAIR_EAGER and old exact ROUTE each have 1 diagnostic observation per scenario (64 calls), for 448 planned calls. Auxiliary tables remain separate from the three-repeat primary comparisons. All NO_BOUND calls are retained.

The public names are mapped to the frozen internal policy and basis. RADIUS_PAIR_LAZY uses the new radius-based PAIR bound with the published Lazy A* policy adapted to this model; it is not a claim that Lazy A* itself is new. Old exact ROUTE uses the exact quota base.

## Analysis definitions

1. Literal equal-budget quality uses only incumbent improvements with trace seconds <= 0.1, 0.5, or 1.0 seconds. A method's case median is defined only when all three primary repeats have a feasible incumbent by that cutoff. Per-repeat values and availability counts are retained. Candidate vs RADIUS, RADIUS_AWA and NO_BOUND is WIN/TIE/LOSS when both case medians exist, otherwise UNKNOWN. All 32 cases remain in every comparison denominator. Unknown observations are not assigned infinity or classified as losses.
2. Strict paired completion time includes a case only if both methods certify optimality in all three repeats with total elapsed <= 1 second. Use the median of total elapsed per case. Report BOTH_THREE_ON_TIME / CANDIDATE_ONLY / BASELINE_ONLY / NEITHER for all 32 cases, the eligible denominator, faster/tied/slower counts, median case ratio and ratio of summed case medians. This conditional cost cannot be presented as unconditional speed. Setup, initial plan, and all bounds are charged.
3. End-of-soft-run values and literal-budget values remain distinct. An expansion or initialization that finishes late does not receive within-budget quality or proof credit. The conservative proof cutoff uses final elapsed, not a guessed earlier proof time. First known-optimum hit is a post-hoc trace statistic and differs from proof. Unknown oracle values leave regret and first-optimum fields missing. Ratio denominators equal to zero yield null/NA, never an infinite or invented improvement.
4. Hard timeouts have no recovered incumbent and no solver component times. Their external call seconds are recorded separately. Missing, fatal, rejected, or partial records remain visible. A source is complete only with the full 112-call block, eight unique oracle/case-completion records, correct attempted-call journal, matching summary and completion status, and no fatal/rejected artifact. PASS_WITH_CENSORING is complete accounting, not success for every solve.
5. Report all cases, and descriptive strata by m, capacity, signal, mother seed, and m/capacity/signal. No p-values, significance claims, seed selection, or fitting is performed. Crossed variants from one mother remain related.

## Source and clock checks

The analyzer checks the frozen input SHA, complete method/repeat schedule, per-case input SHA, seed/m/Q/signal/capacity, public/internal method mapping, protocol budgets and source pins, unprofiled status, oracle identity, trace cutoff values, timer nesting and phase expansion accounting. It reconstructs literal cutoff values rather than trusting a stored summary. Source raw files, explicit run selection, source pins, input and analysis script are recorded in Analysis_Manifest.json.

setup_seconds + initial_seconds + search_seconds partitions elapsed_seconds. root_bound_seconds is nested in search and must not be added to that sum. This pilot is unprofiled: detailed quota/Gamma timers are not available here. Oracle computation and plan replay are outside measured solve time and are not supplied as incumbents.

The only recorded spatial indicators are peak_frontier and final cache-entry counts. peak_frontier is a heap-entry count that may include stale entries; it is not a byte measurement. There is no native process RAM or tracemalloc measurement in this frozen pilot. No actual-memory decrease may be claimed, and no additional memory experiment is introduced.

## Outputs and completeness

All_Calls.csv contains every planned call, including absent or hard-timeout slots. Primary_Case_Summary.csv and Primary_Budget_Quality.csv preserve three-repeat summaries and values. Auxiliary_Single_Observation_Cases.csv and Auxiliary_Single_Observation_Quality.csv are explicitly single observations. Paired_On_Time_Certificate_Time.csv and Paired_Budget_Quality.csv contain every candidate/baseline/case pairing. The three strata CSV files show coverage, time eligibility, and quality outcomes. Summary.md/JSON, Source_Status.json, Analysis_Manifest.json and ANALYSIS_COMPLETE.json retain accounting and provenance.

COMPLETE means all selected source blocks are complete, including explicitly recorded censoring. PROVISIONAL_INCOMPLETE_OR_FAILED_SOURCES prevents a partial analysis from being mistaken for full coverage. Invalid schema or provenance raises and leaves a new analysis FAILURE.json. A later complete analysis must use a new output path.

The explicit path JSON files are planned selections, not evidence of completed or successful runs. They must not be interpreted as a 24-case correctness PASS or a completed pilot. A retry requires an explicit whole-run selection decision and preservation of all old attempts. Do not change a selection file already bound by a successful gate; use a new version and gate if needed.
