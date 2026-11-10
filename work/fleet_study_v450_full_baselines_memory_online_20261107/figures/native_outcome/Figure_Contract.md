# Native-outcome figure contract — preparation only

Question: does adding the shared-quota gate to the same published AWA* engine change realized customer-flow J and supplier handoff waiting under each of the three predeclared planning budgets?

One two-panel figure, with distinct roles: panel a shows the realized customer objective; panel b shows supplier handoff waiting. Candidate HZ_AWA_PAIR_GATED minus HZ_AWA_RADIUS. Every 10, 50 and 200 ms budget is retained, including zero and unfavorable effects. Both panels display signed mean paired changes in seconds, with a zero reference. Customer-flow J is the sum of customer completion-minus-release durations, not H2. Truck handoff waiting excludes the two transfer services; it is not SUMO waitingTime.

Population: all 64 prespecified scenarios, eight independent mothers with eight related offset/pedestrian/slow-vehicle conditions per mother. Exactly the same cases at all budgets. Each case outcome is the policy-frequency-weighted representative native replay, using the existing audit's three policy repetitions and selected representative plans/activation times. It is not a mean of three independent native replications.

At each budget, W/T/L/U counts use candidate-minus-baseline differences and the audit's 1e-6 second tolerance. W means lower, L means higher, U means an unknown paired physical outcome. The full-64 mean is plotted only when all 64 pairs are known. Otherwise the mean is NA; no survivor renormalization. All counts remain visible. No confidence intervals or tests are inferred from the 64 related scenarios. No favorable subset, direct-only subset, proof-completion filter or budget selection is allowed.

Source gate: require the full64 independent audit PASS receipt and its SUMMARY SHA256 supplied explicitly at execution; cases=64, mothers=8, policy_calls=1728. Read Case_Budget_Results.csv, Pair_Cases.csv and Pair_Summary.csv; verify case/budget/method coverage and independent cross-table arithmetic. Preserve full source CSV copies and SHA256 hashes. Reject the two-case pilot by construction. No solver, simulator or analysis module imports.

Visual contract: Python/matplotlib, white, 183 x 115 mm, equal plotting rectangles, independent symmetric y ranges (different outcomes), lower-case a/b labels; teal lower, orange higher, neutral zero. 8 pt labels, minimum 5 pt exported text. One PNG at 600 dpi, editable SVG and PDF, exact per-case/aggregate plotted CSVs, captions and provenance. No AI images.

QA: source check; final-layout alignment <=1.5 pt; PDF font >=5 pt; collision/clipping check; PDF preview and PNG physical-size check; actual visual inspection before PASS. No TIFF is required by this artifact contract. Preserve failed attempts, use fresh output directories.

This is a frozen single decision epoch in a synthetic SUMO setup. It does not establish continuous rolling dispatch, calibrated delivery-network traffic, real-world safety, causal pedestrian delays, or performance on a complete published freight problem. Existing static figures and all frozen online sources remain unchanged. Preparation is source/AST only; no render, aggregation or measurement run until root explicitly releases the window after full64 audit PASS.

