# V449 cost-run accounting

All 144 calls returned across the four fixed blocks; no hard timeout or fatal source failure. All 16 validation oracles were exact. The blocks took 20.182961 seconds in total. This is 4 independent cost mothers with 16 related scenarios and one observation per method/case.

| Method | Calls | Sum elapsed (s) | Median elapsed (s) | Max elapsed (s) | Max soft overrun (s) | Missing H2 at 100/500/1000 ms |
|---|---:|---:|---:|---:|---:|---|
| DP_ADAPTER | 16 | 2.156507 | 0.045808 | 0.570693 | 0.000000 | 0/0/0 |
| NO_BOUND | 16 | 2.159776 | 0.059390 | 0.557070 | 0.000000 | 0/0/0 |
| RADIUS | 16 | 0.748770 | 0.019928 | 0.186107 | 0.000000 | 0/0/0 |
| RADIUS_AWA | 16 | 0.701773 | 0.020751 | 0.144110 | 0.000000 | 0/0/0 |
| RADIUS_PAIR_AWA | 16 | 0.669126 | 0.020378 | 0.145712 | 0.000000 | 0/0/0 |
| RADIUS_PAIR_AWA_GATED | 16 | 0.550532 | 0.014658 | 0.124080 | 0.000000 | 0/0/0 |
| RADIUS_PAIR_EAGER | 16 | 0.865849 | 0.019671 | 0.229568 | 0.000000 | 0/0/0 |
| RADIUS_PAIR_LAZY | 16 | 0.671723 | 0.015737 | 0.174301 | 0.000000 | 0/0/0 |
| ROUTE | 16 | 7.948928 | 0.390137 | 1.168104 | 0.168104 | 0/0/0 |

Per-scale/method accounting and raw-file hashes are in Cost_Run_Accounting.json. These single observations assess the feasibility of executing the frozen protocol; no algorithm quality ranking or winner selection is made from them. All nine methods, the main seeds, one-second budget and three repeats remain unchanged. The unused second cost mothers remain archived.
All setup, initial planning and solver work use the frozen clock definition; serialization, post-hoc oracle and replay costs contribute to block elapsed but not algorithm elapsed. Soft overruns remain charged and visible. Missing early incumbents would remain missing, never replaced with the later result. No actual process RAM or allocation bytes were measured.
