# V448 frozen exploratory low-cost PAIR pilot

Status: PREPARED, NOT RUN. This protocol does not authorize an automatic launch. Root will decide after the V447 formal main/recovery work is complete, the exact V448 source has passed all 24 frozen micro cases, and the approved v2 temperature supervisor has passed its smoke check.

## Question and fixed model

Test whether retaining the two-batch union condition with weighted individual-via radius quotas offers a useful cost/quality tradeoff relative to a cheap independent radius bound, published AWA* with that radius bound, and no proposed bound. This is an exploratory cost/mechanism pilot, not a new large-sample confirmation. It cannot establish global originality, city-fleet gains, SUMO effects or real-world transport benefits.

The domain remains one receiver and hub, atomic incoming a before b, positive services, load-independent FIFO movement with waiting, and objective second-handoff completion H2. Phase-1 continuation, Pathmax, feasible actions, initial plan, dominance/reopening, tie rules and existing queue policies remain shared. The V448 exact/radius source is unchanged by preparing this pilot.

## Frozen inputs and experimental units

Generate exactly eight independent new mother networks: two each for m=6,8,10,12. Seeds are 9480000 + 1000*m + i, i=1,2. Each mother has the same two capacity and two signal treatments as V447, producing exactly 32 related scenarios. Split and case names begin v448_radius_pilot. Seeds and distributions are fixed without consulting formal performance.

instances_v448.py imports only the frozen V447 input-generator implementation, pinned by SHA256. It uses the same random coordinates, directed road costs/calendars, positive unequal cargo weights and services, Q=L or ceil(1.25L), wa=0.6L and wb=0.8L. Structural connectivity, capacities and exact treatment pairing were checked during input generation; no shortest-path solver, bound, oracle or benchmark was executed.

The frozen file is instances/pilot_01/INPUTS.json:
b459e02e4173e07787b47e905de193842fc05e4f7c4738315de044a588b7afa1.

The independent count is eight mothers, two per scale. Neither 32 related scenarios nor 448 timed calls is an independent sample count. All seeds and all four treatments remain, including unfavorable, null, censored and failed cases.

## Methods and repetitions

| Role | Public method | Internal policy | Phase-0 basis | Repeats per scenario |
|---|---|---|---|---:|
| Primary baseline | RADIUS | ROUTE | radius | 3 |
| Primary candidate | RADIUS_PAIR_LAZY | LAZY_ASTAR | radius plus union | 3 |
| Primary published-policy baseline | RADIUS_AWA | AWA_ROUTE, w=2 | radius | 3 |
| Primary engineering baseline | NO_BOUND | NO_BOUND | state clock only | 3 |
| Auxiliary information/evaluation ablation | RADIUS_PAIR_EAGER | PAIR_EAGER | radius plus union | 1 |
| Auxiliary earlier implementation reference | ROUTE | ROUTE | exact quota path | 1 |

The PAIR formula is supplied by this research; Lazy A* and AWA* are published search policies, not new search algorithms. Auxiliary one-observation costs must not be presented as three-repeat median speed results. Beating only exact-quota ROUTE would not establish practical superiority; the cheap RADIUS and NO_BOUND controls remain primary.

Each scenario has 4*3+2*1=14 serial solves, giving 448 calls over 32 scenarios. For each primary repetition, rotate the four methods by (global case index + repeat) modulo four. Across each complete eight-case scale block, each primary occupies every execution position equally often. Run the two auxiliaries afterward, reversing their order by case parity. Every call gets a fresh Context and caches.

## Resource and measurement policy

Freeze soft wall time at 1000 ms, solver watchdog at 15 seconds and independent-DP cap at 15 seconds. No budget/size/seed tuning is enabled in the runner. Four jobs each contain one complete scale block of eight scenarios and 112 calls. The nominal sum of fully consumed one-second soft allowances is 448 seconds; this is not a duration upper bound. Expansion overruns, verification, oracles, setup/output work and resource interruptions add cost. The root may decide not to launch; completed data and failures must never be discarded based on wins.

All Context construction, greedy planning, root/later bound work and search/certificate work remain inside each solver's elapsed clock. The inherited root timer is nested in search/total and must not be added again. profile=False, audit=False and checkpoints=() prevent profiling and node-snapshot overhead. This pilot does not measure Python allocations or native process RAM.

Compute the independent structural-DP oracle once per case, outside timed solves, and use it only to validate outcomes and lower certificates afterward. Neither its objective, plan nor cache is passed into a solver or its initial plan. Censored oracles mean unknown optimum, not zero regret.

Record raw improvement traces, expanded/phase counts, final H2, lower certificate/gap, total/setup/initial/search/root times, overruns and known oracle values. Reconstruct literal 100/500/1000 ms H2 only from trace entries at or before each cutoff. A late improved solution is not an in-budget answer. Conservative in-budget certification additionally requires end certification and elapsed<=1000 ms.

A solver watchdog exception records HARD_TIMEOUT with no recovered incumbent, trace or component statistics. Missing values remain unknown. Verification exceptions are separate fatal failures and retain the rejected result before stopping dependent jobs. Soft-budget uncertified runs remain valid censored observations. Source/identity/certificate or plan failures stop the batch. All attempts and partial folders remain on E.

## Required micro gate

Use check_v448.py only on the frozen V447 micro24 inputs, reusing them for correctness rather than independent performance evidence. micro_gate_v448.py accepts an explicit selection of successful fresh check folders; it validates hashes, raw evidence, no overlapping case selection and exactly the frozen 24-case coverage. It checks the current solver/reference/checker and measurement-source hashes. A single selected-case PASS is insufficient.

The measurement runner calls validate_gate before any solver or oracle. The intended aggregate gate path is gates/micro_all_01/GATE.json. See Gate_Assembly_Notes.md. No aggregate gate has been created during preparation.

## Prepared commands, not executed

After all required micro checks pass, root may explicitly assemble their evidence:

    python -B micro_gate_v448.py --runs-json records/selected_micro_checks_01.json --out gates/micro_all_01

The selected-runs JSON must be filled from actual completed check folders; no success is predeclared.

Only after the full gate and root's launch decision, under monitor_v447_v2.ps1:

    python -B run_jobs_v448.py records/pilot_jobs_01.json

The job list points to fresh runs/pilot_m6_01, pilot_m8_01, pilot_m10_01 and pilot_m12_01. It never reads V447 main-result folders. Separate analysis should retain all cells, compare primary three-repeat case medians only where appropriate, report completion and literal-budget quality with their full denominators, and keep related capacity/signal variants grouped by mother. The pilot is exploratory regardless of whether results are favorable.

