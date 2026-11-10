# V449 scale-analysis preparation

Status: source prepared and AST checked; neither the analysis nor any additional numerical run was executed by this preparation step. The main protocol remains fixed at nine methods, three repeats, one-second soft budget, 100 independent mothers and 400 paired scenarios. Cost results are accounted separately in Cost_Run_Accounting.md/json and do not select methods, seeds or budgets.

## Explicit selection and future command

The file records/explicit_selected_scale_main_runs_01.json names all 52 frozen main blocks. It is a planned selection, not evidence that those runs exist or passed. If a block fails, preserve it and record an explicit full-block replacement in a new selection file; do not select successful individual calls or use a latest-directory scan.

After the parent authorizes analysis of completed data:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\analysis_scale_v449.py' --selected 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\records\explicit_selected_scale_main_runs_01.json' --out 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\analysis\scale_main_01'
```

The output directory must be new and below V449/analysis. The script imports only Python standard-library modules and does not import any solver. It never writes numerical source or input files. A failure is saved in FAILURE.json and PROCESS_COMPLETE.json; a retry must use a new output directory. Source identity errors stop analysis. Partial records inside a selected range remain as MISSING slots and yield a provisional status, provided the protocol/input identity and full selected range coverage can be established. A missing protocol cannot establish range identity and therefore stops analysis rather than guessing.

## Frozen descriptive views

1. Early quality at literal 100, 500 and 1000 milliseconds is the primary comparison. Every one of the 400 scenarios is retained for all nine methods. A case median exists only when all three repeated incumbents exist by that deadline. Pairwise H2 comparisons need no oracle. Unknown optima produce no regret or optimality-success claim.
2. First-good targets are oracle_H2 + fraction*(oracle_H2 - t0), with fractions 0, 0.05 and 0.10. These are post-hoc evaluation targets, never solver inputs. The first trace entry reaching each target supplies its actual recorded time and expansion index. No late target is credited to an earlier deadline.
3. Proof time is a separate endpoint: all three returned certificates must be exact AND each complete solver elapsed time must be at most one second. Pairwise time ratios are restricted to scenarios where both methods satisfy the same all-three on-time condition. The common, left-only, right-only and neither counts are always reported. Neither means the required event was not established in both methods; it can include missing calls or unknown oracle targets, not only algorithmic failure. Target summaries separately record known-oracle counts.
4. All 36 unordered method pairs are produced in frozen method order. WIN means the left method has lower H2 or lower eligible event time. Reporting must identify left/right explicitly. A ratio of sums of paired case medians and a median of per-case ratios are distinct fields. Zero denominator ratios are NA; their number is reported. No p-values or probability claims are computed.
5. Global, m=6/8/10/12, signal, capacity, m-by-signal, m-by-capacity and full m/capacity/signal strata are descriptive. Each stratum reports its distinct mother count. Capacity and signal variants are related observations; 400 scenarios are not 400 independent networks. Technical repeats are not new mothers.

## Cost, work and space

Elapsed/setup/initial/search timings and root-bound time are preserved. Root-bound time is nested in search, so adding it again would double-count. Expanded means completed nonterminal expansions; first-target expansion_index names the expansion during which the incumbent appeared, and a DP interruption can leave one partially completed expansion. DP partial_expansions stays separate. Heap pops, stale labels, and Lazy A* reevaluations are not silently called expansions.

Peak frontier is a heap-entry count and can include stale entries. DP structural labels and closure-vector entries use different units from scalar search closure entries. Missing proxy fields remain NA. The protocol measured neither actual process RAM nor Python allocation bytes. No sum or ratio of these proxies may be presented as bytes saved. Detailed profiling was disabled, so absent internal quota/closure statistics are not imputed as zero. Final work summaries concern each run's actual completed work, including overrun, and do not claim identical CPU effort at equal expansion count.

Hard watchdog failures have no recovered incumbent and no solver component times; the external watchdog duration stays separate. They are retained in the 10,800-call denominator, never assigned zero time or an invented initial plan. Soft overruns and late certificates remain visible in end-of-run summaries, but cannot improve literal-deadline quality or proof coverage.

## Evidence scope and provenance

The analyzer checks the 12 frozen source hashes, frozen main input hash, per-row input identity, method/basis/repeat/order, gate hash and 24-case scope, all completion journals, oracle ledger, certificate identities, timer partition and literal trace evaluations. It records raw/source hashes before aggregation and checks raw/source stability again afterwards. Common initial values/plans and certified final values are cross-checked across methods within each scenario. A run's PASS_WITH_CENSORING is accounting completion, not a claim that every call proved optimal.

DP_ADAPTER is a standard complete topological DP implemented in this study. Its 15-second reference oracle shares the recurrence/network source; that same-source agreement is not independent validation of the DP comparator. Separate small full-prefix exhaustive tests and reference plan replay supply the cross-checks. AWA and Lazy A* are published-policy adaptations; the particular two-batch joint bound remains this study's supplied heuristic, not a formula attributed to those papers.

No single universal best method is selected automatically. Early quality/first-good and proof cost are distinct user objectives. Full joint-bound information and its eager, lazy, weighted or gated deployment strategies must be interpreted separately. These synthetic local H2 experiments alone do not establish whole-fleet SUMO or real-world delivery improvements.

## Reporting supplement before main analysis

Initial 0/5/10% target flags/counts now distinguish targets already achieved by the common initializer. The paired time summary records these flags inside its actual eligible subset. A first-good time on such a case measures initializer availability, not a search-quality improvement. Proof rows use initial optimality for this attribution. Paired expansion sums and ratios use exactly the same eligible common subset as the time ratio; all-case work totals must not be divided to describe a conditional proof-time comparison. Previous analysis source B3C64155 is preserved in snapshots/analysis_before_initial_target_01; this adds descriptive fields only and changes no algorithm, input, budget or target.
