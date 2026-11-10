# V448 exploratory pilot: interpretation of completed evidence

The radius-based PAIR candidate reduced completed-search/proof cost in this small pilot, while it did not improve the final 1-second objective over the two primary radius baselines. The anytime baseline often found the optimum sooner. These are distinct outcomes.

The frozen analysis finished COMPLETE: 32 scenarios, 8 independent mothers, 448/448 returned observations, no hard timeout or missing record, and 32 exact independent-DP oracle values. The four selected blocks have matching source pins and no fatal/rejected artifact. No solver was run for this analysis. The analysis source SHA256 is 1377a7161e94f09a5dd3806bb1cfcdb9a7e9b07e8f008cfeb3f8e6472c384166. Full provenance is in Analysis_Manifest.json.

## Primary proof and completion-time comparisons

Candidate = RADIUS_PAIR_LAZY. Each primary method has three technical repeats per scenario. The time comparison includes a scenario only if both methods certify optimality within the literal 1-second total elapsed limit in all three repeats. Ratios use sums of case medians; excluded pair states remain reported.

| Baseline | Both three on time / 32 | Candidate only | Baseline only | Neither | Candidate faster / slower | Candidate / baseline sum of case medians (s) | Relative change |
|---|---:|---:|---:|---:|---|---|---:|
| RADIUS | 31 | 1 | 0 | 0 | 22 / 9 | 2.542749 / 2.988253 | -14.91% |
| RADIUS_AWA | 32 | 0 | 0 | 0 | 21 / 11 | 3.385768 / 3.887793 | -12.91% |
| NO_BOUND | 25 | 7 | 0 | 0 | 23 / 2 | 1.016571 / 3.079319 | -66.99% |

Candidate and RADIUS_AWA each had 96/96 within-deadline proof observations. RADIUS had 94/96; its two late proofs came from one m12 tight/free scenario (s9492001), and all 96 final results were certified. The maximum RADIUS overrun was 14.224 ms. Candidate and RADIUS_AWA had no overrun. No method had an initialization overrun.

The joint-bound information and its evaluation policy must be distinguished. Across all 32 returned case summaries, candidate expanded 7,735 nodes versus RADIUS 17,118 and RADIUS_AWA 17,682 (54.81% and 56.25% fewer). All these final primary results were certified, including the two late RADIUS observations. These are node counts, not CPU-equivalent work. Candidate versus AWA changes both the bound and queue policy, so that comparison is not a pure formula ablation.

## Literal equal-budget quality and first optimum

All 32 scenarios had three feasible observations at every declared cutoff. Entries below are candidate wins / ties / losses; smaller H2 is better.

| Baseline | 100 ms | 500 ms | 1,000 ms |
|---|---|---|---|
| RADIUS | 1 / 31 / 0 | 0 / 32 / 0 | 0 / 32 / 0 |
| RADIUS_AWA | 1 / 23 / 8 | 0 / 31 / 1 | 0 / 32 / 0 |
| NO_BOUND | 6 / 26 / 0 | 6 / 26 / 0 | 4 / 28 / 0 |

First attaining the known optimal H2 is different from proving it. Across all 32 cases, sums of three-repeat median first-optimum times were 3.299998 s for candidate, 3.813062 s for RADIUS, and 1.813339 s for RADIUS_AWA. Candidate reached that target earlier in 22 cases and later in 10 versus RADIUS, but earlier in only 6 and later in 26 versus AWA. Thus the AWA comparison supports reduced total proof/completion cost, not faster acquisition of the optimal incumbent. Oracle targets were used only after the solves.

Examples retain both directions:

- Positive: v448_radius_pilot_s9492002_m12_roomier_signal, 100 ms: candidate H2 = 191, RADIUS = 353, RADIUS_AWA = 198; oracle = 191.
- Negative: v448_radius_pilot_s9492001_m12_tight_free, 500 ms: candidate H2 = 333, RADIUS_AWA = 243; oracle = 243. All three candidate repeats later certified within 1 second.
- Strong short-budget counterexample: v448_radius_pilot_s9492001_m12_roomier_signal, 100 ms: candidate H2 = 368 versus AWA = 193, with oracle = 193.

## Scale and signal descriptions

The m12 stratum contains only two independent mothers and eight related scenarios. Candidate and AWA certified in all 24 observations; RADIUS certified on time in 22/24, and NO_BOUND in 5/24. Candidate versus RADIUS had seven common all-three-on-time cases and was faster in all seven: 1.662015 versus 2.006766 s summed case medians (-17.18%). Candidate versus AWA had eight common cases, seven faster and one slower: 2.505034 versus 2.912380 s (-13.99%). m12 candidate/AWA quality was 1/2/5 at 100 ms, 0/7/1 at 500 ms, and 0/8/0 at 1 second. Candidate/RADIUS quality was 1/7/0 at 100 ms and all eight tied thereafter.

| Signal stratum | Comparison | Common time pairs | Sum-of-case-medians relative change |
|---|---|---:|---:|
| On (16 scenarios) | Candidate / RADIUS | 16 | -17.64% |
| On (16 scenarios) | Candidate / AWA | 16 | -19.44% |
| Off (16 scenarios) | Candidate / RADIUS | 15 | -11.64% |
| Off (16 scenarios) | Candidate / AWA | 16 | -8.03% |

At 100 ms, candidate/AWA quality was 1/11/4 with signals and 0/12/4 without signals. At 500 ms the signal group tied all 16 cases; the free group had 15 ties and one loss. These are descriptive, prespecified strata of related variants. They do not prove that traffic signals cause a performance gain.

## NO_BOUND and single-observation diagnostics

NO_BOUND remains a relevant countercheck. It had 77/96 on-time proof observations and 25/32 cases with all three proofs on time; 28/32 case medians had the optimum at 1 second. Candidate had all 32. However, on two m6 tight variants of mother s9486001, NO_BOUND completed faster despite many more expansions: free 4.4192 versus 4.6564 ms (261 versus 32 expansions), signal 4.1960 versus 5.1232 ms (257 versus 36 expansions). Smaller search does not guarantee lower cost.

Old exact ROUTE is auxiliary with one observation per scenario. It certified within 1 second in 16/32 cases, and its 1-second incumbent was optimal in 17/32. On m12 it had no on-time certificate and no optimal 1-second incumbent in any of eight cases. Each m12 run completed only one parent expansion, yet elapsed time was 1.247-1.576 s; total root-bound time was 3.122449 s within 10.882008 s total elapsed across those eight observations. Its maximum soft overrun was 575.898 ms. Root time is nested, and later child-bound work is also charged. This exposes costly exact-quota work and coarse expansion-boundary budget checks; it does not establish that the exact bound is ineffective as information. A single observation and unequal completion status do not support a stable speed ratio.

RADIUS_PAIR_EAGER is also auxiliary with one observation per scenario. All 32 completed within 1 second. Its total expansion count was the same 7,735 as the candidate's case-median sum, while full PAIR evaluations summed to 36,976 versus 14,090. This supports the expected reduction in full-bound evaluations under lazy evaluation on these cases. Its single-observation total elapsed (4.174867 s) must remain separate from the candidate's three-repeat median total (3.385768 s); this is not the primary repeated-time comparison. No new search-policy novelty is claimed.

## Evidence boundary

This is an exploratory cost/mechanism pilot on eight new, unscreened synthetic mother networks, not a 100-mother confirmation. Crossed capacity/signal scenarios and technical repetitions are not independent experimental units. No inputs or methods were selected by wins, and negative outcomes remain in the tables. Published search policies were adapted to a shared two-handoff model; the results do not demonstrate superiority to state-of-the-art freight dispatch systems.

Only frontier/cache entry counts were recorded. No process RAM or Python allocation-byte experiment was performed, so actual memory savings are unmeasured. The task objective is the model's second-handoff completion H2; there is no SUMO execution, global-dispatch outcome, or customer-benefit evidence in this pilot. The original V447 formal data and all numerical sources remain unchanged.

The independent read-only crosscheck of original measurements and oracle records is archived in ../independent_pilot_audit_01/Independent_Pilot_Audit.md. Numerical primary tables remain in this directory; this note adds interpretation without changing them.
