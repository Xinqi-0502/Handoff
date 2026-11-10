# V449 operational cost planning

This note uses already completed V448 observations only. No V449 solver or numerical check was run. The exact same random-input distribution does not guarantee the same timing on new seeds.

| m | Prior complete V448 block elapsed (s) | Old reference DP mean / max per case (s) | Arithmetic allowance for new 4-case cost block (s) |
|---|---:|---|---:|
| 6 | 1.326 | 0.003919 / 0.005041 | 8.14 |
| 8 | 3.900 | 0.025239 / 0.041996 | 8.99 |
| 10 | 25.236 | 0.151669 / 0.202150 | 16.00 |
| 12 | 70.679 | 0.781410 / 1.068180 | 29.29 |

The arithmetic sum for the four new cost blocks is 62.43 seconds; the analogous main arithmetic is 74.83 minutes. These are staffing illustrations, not measured V449 durations, statistical predictions, or time upper bounds.
The arithmetic carries the old means for six measured methods, uses old cold reference-DP duration as a proxy for the as-yet-unmeasured traced/initialized DP adapter, and reserves one full soft second for each of the two unmeasured weighted PAIR combinations. It adds one old oracle cost per case. Trace/greedy changes, different seeds, replay, gate checking, garbage collection, process scheduling, I/O and expansion overruns may change total cost. The JSON retains all components and raw-file hashes.

Four cost jobs use one mother and all four related conditions each, with nine methods once: 36 calls per job, 144 total. Inspect each complete scale block before continuing. These single observations may assess resource feasibility only; do not select a favorable method or seed from them. The reserved second cost mother remains unused and archived.
Main has 52 serial jobs (two mothers per job except the final single-mother block at each m), with 10,800 calls. The sum of nominal one-second allowances is three hours, before oracle/replay and overruns. Giving every validation oracle its full 15-second allowance adds 100 minutes over 400 cases. Neither figure is an actual-duration promise, because soft limits can overrun and many calls finish earlier.
The independent old DP maximum was already 1.068180 seconds on the small V448 m12 sample. A one-second DP baseline may be censored, and this must remain visible. Original exact ROUTE also overran one-second limits substantially. The 15-second watchdog is cooperative; it is not an operating-system hard kill. Use the existing monitored serialized launcher, stop on 60 C or failed temperature monitoring, preserve partial runs and do not automatically start main after cost.
The new input corpus and method set are already prespecified. Any operational budget amendment requires a new explicit protocol/version while retaining all affected data; no outcome-based trimming or favorable-case substitution is permitted.
