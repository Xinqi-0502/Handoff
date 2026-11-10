# San Pablo Dam bounded calibration-transfer protocol

Status: PREPARED; no traffic simulation run by the preparing agent. Existing SUMO 1.27.1 and netconvert binaries were found at `D:\traffic-coop-research\.venv\Lib\site-packages\sumo\bin`. Only `sumo --version` was executed.

## Sources and small download

The [official tutorial](https://eclipse.dev/sumo/docs/Tutorials/Calibration/San_Pablo_Dam.html) and [upstream directory](https://github.com/eclipse-sumo/sumo/tree/32b8df574b9976dda12d9ccc5e6332b2ae9ff98e/tests/complex/tutorial/san_pablo_dam) define the source. Commit: `32b8df574b9976dda12d9ccc5e6332b2ae9ff98e`. Twenty-four files total 324119 bytes, including the fourteen measurement files, configurations, helper scripts and project LICENSE/NOTICE. `Upstream_Manifest.json` records every URL and SHA256. Originals remain in `upstream` and are never modified.

Project NOTICE declares EPL-2.0 with the stated GPL secondary-license route for source; original observation files carry no separate dataset-specific CC license. Preserve the source notices and tutorial attribution. Do not label the survey data CC0 or invent a separate permission statement. The tutorial identifies real passage observations collected on two November 1997 days; our implementation uses their supplied day1/day2 identifiers.

## Observation and clock model

Each observation file contains one `HH:MM:SS` passage time per vehicle, with no explicit vehicle ID. The upstream tutorial implicitly matches vehicles by line order. We retain this assumption explicitly: row index j becomes SUMO vehicle ID j, and its simulated detector events are matched by that ID, not by XML output order. Day 1 has 2298 rows per available station; day 2 has 2293. Station 5 is absent on day 1, station 6 on day 2. Common evaluation segments are therefore 1→2, 2→3 and 3→4. Whole-second observations remain whole-second measurements; no higher empirical precision is invented.

All times are seconds after midnight. Begin is the minute boundary preceding the first station-1 observation; end is the last station-8 observation plus 900 s. Station-1 times supply desired departures, not guaranteed realized insertion times. Insertion delay is explicitly reported; segment travel time uses actual detector-to-detector times. Every requested vehicle must arrive and cross every required detector exactly once for an error summary to be accepted.

## Frozen controlled comparison

Exactly three candidate values, **tau = 1.2, 1.5 and 1.8 s**, are simulated on day 1. The 1.5-s candidate is the official runner's starting baseline, not a claim about the SUMO factory default. All other vehicle values remain fixed at the tutorial start: maxSpeed 22 m/s, accel 2 m/s², decel 2 m/s², length 5 m, sigma 0.5 and minGap 2.5 m. Same network, generated routes, seed 23423 and 1-s step length apply across candidates. No optimizer or adaptive parameter search is used.

For segment k and all N observed rows, compute RMSE_k = sqrt(mean((T_sim-T_obs)^2)); the primary selection criterion is the unweighted mean of the three segment RMSEs. Also retain segment MAE and signed bias and every matched residual. Choose the smallest day-1 criterion; exact numeric ties prefer tau=1.5, then smaller tau. The selection record is written and hashed **before** any day-2 run.

On day 2 run only the baseline and the locked winner. If winner=baseline, reuse its one held-out run. Thus the workflow performs four or five traffic simulations, never more than five. No day-2 result changes parameters, candidate sets, segment selection or acceptance rules. Report held-out RMSE change, including zero or deterioration. The source bundle has not supplied a domain-wide acceptance threshold; successful workflow completion is not automatically satisfactory empirical agreement.

## Boundary conditioning and explicit adaptations

Each day's observed station-1 times supply inflow. Its station-7/8 times generate an outflow variable speed sign exactly following the original runner's 337.5/(t8-t7) rule, including its changed-time filter and omission of the final index. This is **conditional observed-boundary transfer**, not an independent prediction of all day-2 traffic. Evaluation uses upstream common segments and does not score the boundary pair used to construct the VSS.

The 337.5-m VSS numerator and the two-edge network coordinates are retained from upstream without claiming they establish a new surveyed geometry. The geometry is a simplified corridor, not a signalized urban delivery network.

The official optimizer is not invoked. The old `validate.py` reads one-second interval lines by string position and appends once for positive counts; this adaptation uses `instantInductionLoop` enter events with explicit vehID, as documented by [SUMO](https://eclipse.dev/sumo/docs/Simulation/Output/Instantaneous_Induction_Loops_Detectors.html). It prevents output-order matching and aggregation from silently losing vehicles. It is consequently not a bitwise reproduction of the old tutorial score.

Automatic gridlock teleporting is disabled (`time-to-teleport=-1`) and collision warnings invalidate the run. No safety-mode override is applied. Unfinished TripInfo is written and its population checked. A run with missing crossings, missing/unfinished vehicles, duplicate IDs, nonpositive travel times, collision/teleport warnings, nonzero exit or timeout is retained as a failure, never converted to a successful calibrated score.

## Execution after static review, under the external temperature monitor

Working directory: `E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107`.

```powershell
$env:TEMP='E:\CodexResearch-xi\temp'
$env:TMP=$env:TEMP
$env:PYTHONDONTWRITEBYTECODE='1'
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 validation/san_pablo_dam/run_public_validation.py --execute --out validation/san_pablo_dam/runs/cross_day_01
```

The source verifies all downloaded/input hashes and requires the observed SUMO version. Each subprocess has at most 45 s and the whole execution at most 300 s. The output directory must be fresh on E. The user workspace's external temperature monitor and 60°C stop rule remain required; do not run this concurrently with formal timed solver comparisons. No package installation is required.

Archive per-run commands/stdout/stderr, generated XML, event and TripInfo files, per-vehicle residual CSV, per-segment metrics, pre-heldout selection, summary and output hashes. `PROCESS_COMPLETE=PASS` denotes workflow completion only. Report actual calibration/holdout errors and physical agreement limits separately.

## Remaining limits

The experiment is a bounded reproducibility and cross-day transfer exercise on two days, one stochastic seed and one corridor. A favorable result does not validate traffic signals, delivery truck/robot behavior, building service or our synthetic road network. A negative result must remain visible. Structural handoff and signal tests are separate deliverables. The frozen delivery benchmarks must not be rerun or retrospectively relabeled as calibrated using these parameters.

## Execution containment amendment

Every created executable (version probe, netconvert and SUMO) is assigned at process creation to a private Windows Job Object with KILL_ON_JOB_CLOSE, using STARTUPINFOEX JOB_LIST. The noninherited job handle closes if the monitored Python parent is terminated. Timeout/error cleanup terminates and waits only for this owned job; no unrelated processes are enumerated or killed. The prior script/protocol/preparation manifest are retained. No traffic parameter or held-out selection rule changed. This mechanism is statically prepared, not yet runtime-verified by this agent.

## Pre-simulation observation-quality amendment

Raw station sequences are nondecreasing and the complete daily counts agree, but ordinal matching yields four nonpositive scored segment differences on day 1 and five on day 2. The day-2 downstream boundary also has one negative difference. These are input-quality observations found before any simulated result; they are not removed from the source files. Raw_Observation_QC.json and .csv preserve the exact day, zero-based ordinal row, station pair, original seconds, difference and treatment.

All 2,298 day-1 and 2,293 day-2 demand vehicles remain. A scored segment uses only strictly positive observed travel-time differences, independently for that segment. Eligible counts for segments 1-2, 2-3 and 3-4 are respectively 2298, 2297, 2295 on day 1 and 2293, 2289, 2292 on day 2. Every run preserves all matched records and a score-eligibility field; excluded records are not given fabricated errors. RMSE/MAE/bias use the reported eligible denominator. The unweighted mean of the three segment RMSEs remains the fixed training selection criterion.

For the one invalid day-2 boundary difference (ordinal row 94), no VSS update is emitted, retaining the preceding valid speed. The procedure fails if an invalid update occurs before any valid update. The upstream rule selecting changed station-7 times and omitting the last row remains. Exactly the same pre-specified quality rule applies to all candidates and both days; day 2 never selects parameters.

This is ordinal-row matching, not verified observed vehicle identity: the raw files contain passage clocks but no explicit vehicle IDs. Simulated IDs provide exact simulation bookkeeping only. This quality amendment is an additional departure from literal upstream reproduction. It supports a bounded public-tutorial validation conditional on the observed daily boundaries, not empirical calibration of the synthetic delivery network.

Pre-amendment script/protocol/preparation manifests and the original static check are preserved; Observation_QC_Changes.diff records the code change.

## Execution readiness receipt

The shared Windows executor passed three controlled, non-SUMO lifecycle cases in lifecycle_checks/check_03: normal return, timeout, and abrupt termination of its own Python host. Handles confirmed termination of both the owned child and grandchild in the latter two cases. No process enumeration or unrelated termination was used. Two earlier test failures are retained: a 10-second outer startup allowance expired in check_01; check_02 confirmed normal exit and expected timeout but could not observe the grandchild readiness file before the short timeout. The final check uses a lightweight sleeping child and longer startup allowance. The executor function and validation source did not change between these checks. This is execution-containment evidence, not traffic-model validation.
