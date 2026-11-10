# Native process memory results

Coverage: 128/128 observations, 32 scenarios and 8 mothers. One fresh process per method/scenario; no repeat-variability estimate.

Primary endpoints are process lifetime peaks read immediately after solve; before-import and pre-solve current/peak baselines are retained in Observations.csv. PeakPagefileUsage is peak process commit, not physical pagefile writes. PrivateUsage is current private commit, not a peak field. Working set includes shared and private resident pages.

Common pre-solve module origins identical: True. Censored/failed observations: 0. Missing endpoints remain NA.

| Method | Native n | Peak working set median KiB | Peak commit median KiB | Pre-solve working set median KiB | Proof by 1 s | Literal optimum by 1 s |
|---|---:|---:|---:|---:|---:|---:|
| RADIUS_PAIR_AWA_GATED | 32 | 27042.00 | 19048.00 | 23924.00 | 32/32 | 32/32 known |
| HZ_AWA_RADIUS | 32 | 27236.00 | 19296.00 | 24022.00 | 32/32 | 32/32 known |
| HZ_AWA_RADIUS_PAIR_GATED | 32 | 27114.00 | 19126.00 | 24066.00 | 32/32 | 32/32 known |
| ANA_RADIUS | 32 | 27128.00 | 19128.00 | 24012.00 | 32/32 | 32/32 known |

Pairs use the identical case intersection and report their own denominator. Ratios of sums and medians of case ratios are distinct. The HZ pair comparison uses the same complete engine; other engine comparisons also include implementation/container choices.

Peak growth above baseline is supplemental and is not algorithm-private RAM. Peaks cannot be reset and include import/startup history. End-of-soft-run peaks include any soft overrun; they are not a maximum sampled only within the first second. These independently instrumented times are not substituted for V449 speed results. Frontier/cache counts are not RAM. This sample does not establish a general memory bound.

The separately labelled Diagnostic_Pilot CSV files retain native measurements for all nine original methods on the four fixed cost scenarios. Their denominator is four, with one process observation per method/case; they are not pooled with the 32-scenario main comparison or treated as broad performance confirmation.
