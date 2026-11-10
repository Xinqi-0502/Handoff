# Independent V450 online audit



PASS: 64 scenarios, 8 mothers, 1728 policy calls; 128 representative native replays, including 0 retained failures.



Every case remains in the tables. Any failed or missing plan representative makes its full case/arm/budget physical aggregate unknown; weights are never renormalized over survivors.

The primary physical quantity is policy-frequency-weighted representative replay J. It is not three independent native replications. The direct same-plan/same-activation subset is shown alongside its full denominator, never substituted for all scenarios.

Within-budget forecast quality excludes late fallback plans. Execution includes planning latency rounded up to 0.2 seconds. Forecast-to-actual reversals include both traffic-model error and activation-delay differences.

Truck handoff waiting is hub dwell minus the two 2-second transfers; SUMO waitingTime, dispatch activation delay, release command, first motion and hub departure are separate columns. Signal-stop exposure includes red OR yellow within45m, excludes planned stops, and is not pure red-light delay. Pedestrian15m proximity is exposure, not causal delay.

Every PASS replay has zero collision elements of any type in collisions.xml and no relevant collision/intermodal Warning or Error lines in captured sumo.log/stdout.log. This means no recorded collisions in the measured outputs; it is not a real-world safety guarantee. Failed replays retain recorded counts and missing-evidence flags.

Mother_Pairs.csv uses the mother as the independent unit; a mother mean is unknown if any planned condition is unknown. No statistical-power claim is made.

This is a single frozen decision epoch, not continuous rolling dispatch. No actual RAM bytes are supplied by these records.
