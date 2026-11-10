# Freight ALNS reconstruction scope and outstanding components

2026-11-07. The formal papers are available; missing author code alone is not grounds for saying reconstruction is impossible. Current completed code implements full published AWA/ANA search loops with a common domain adapter. No full Hof or Wei metaheuristic has been implemented or timed in this directory.

## Hof and Schneider: algorithm is substantially specified

Primary: *Intraroute Resource Replenishment with Mobile Depots*, Transportation Science55(3), 660--686 (2021), [DOI](https://doi.org/10.1287/trsc.2020.1034). User PDF SHA256 61c9069d9a4a463908b6434d8f1559d794f960122b1526699cc15e5967f20ded; archived in V442. This round directly read formal PDF physical pages6--19 (printed665--678). The official supplement supplies detailed move evaluation. The publisher supplement landing lists the appendix PDF; this bounded search did not retrieve an author source-code archive. That is an access finding, not evidence that code never exists.

| Required complete component | Formal definition | Reconstruction status |
|---|---|---|
| Full hybrid loop | Figure2 p.666; ALNS or path relinking, local search, elite update, SA, reset/diversify, penalty update | Not implemented; pseudocode available |
| Initialization and transfers | Section3.2 p.667; customer seeds by latest window, cost insertion; Figure3 best transfer insertion on infeasible segments | Not implemented; adapt fixed atomic cargo ownership explicitly |
| Cycle exclusion | Section3.3 pp.667--668 successor sets | Not implemented; necessary with interacting mobile-depot routes |
| Local search | Section3.4 p.668 randomized relocation, first improvement, transfer cleanup | Not implemented |
| Destroy families | Sections3.5--3.5.1 pp.669--671: TV/SV route, segment, random, cluster/MST, relatedness, worst, neighbor graph, waiting time | Not implemented; Tables3 compatibility/scopes required, not just one remove/insert move |
| Repair families | pp.671--672: greedy, GRASP, regret2/3/4, paired TV/SV transfer insertion and task order | Not implemented |
| Route selection/evaluation | Section3.5.2 p.672: random/cost/distance/efficiency/waiting/transfer-density; diversification and noise variants | Not implemented |
| Adaptation | Section3.5.3 p.673: separate roulette vectors, component score/frequency, reaction update, visited-solution memory | Not implemented |
| Path relinking | Section3.6 pp.673--675, Figure6; all elite guides, common-arc preservation, missing transfer handling, truncated path | Not implemented |
| Penalties and acceptance | p.667 four violations; p.675 Section3.7 exponential SA; cooling/reset/diversification | Not implemented |
| Efficient move evaluator | Official AppendixB.2--B.4 | Available formal text; reconstruction and invariance checks still required |

Table5 p.678 gives a usable fixed parameter set: no-improvement limit omega=2000 for VRPTWMD or500 for the 2E benchmark; reset mu=200; removal interval[.01,.1]; scores6,9,3; reaction .8; update interval20; neighbor/worst/related random exponents2,2,3; relatedness weights1,2,4; GRASP .05; diversification .7; noise[.9,1.1]; elite size10; relinking fraction .7; penalty initial10/min.1/max10000/update1.1 and consecutive feasible/infeasible counts2; SA deterioration .01, cooling span100, diversification after2 resets. The algorithm has multiple adaptation channels and transfer scopes; their omitted variants cannot be silently declared irrelevant.

A faithful framework adapter is possible after implementing this checklist. Its objective must be replaced by the study's H2 or J, static travel replaced by the declared FIFO evaluator, and fixed onboard cargo/atomic a-b precedence enforced. Those are material model changes. In a one-receiver/two-handoff subproblem many fleet/transfer operators become unavailable; a complete reduced-domain implementation would still not reproduce the full fleet benchmark. Exact objective evaluation could replace the appendix surrogate if documented, but its computational cost and search trajectory would differ. The 1s cap is also a new external stopping rule, not Table5's original termination.

## Wei, Wang and Hu: complete IMOALNS entails a population method

Primary: Transportation Research PartE194 (2025),103954, [DOI](https://doi.org/10.1016/j.tre.2024.103954). DOI year2024 is not publication year. Formal user PDF SHA256 6a3bae188a2a7bb7da95230a88b82c78cdfbb6e46072af323cd8dd9df66b68ef,36pages. Required components are 3D-KNN clustering (Section4.1/Algorithm1), improved Clarke--Wright initialization and truck-satellite window feedback (Section4.2/Algorithm2), population generation, all four destroy and four repair operators (Section4.3.1--2), adaptive scoring (Algorithm3,p.17), multiobjective SA (Algorithm4,p.18), and nondominated sorting/crowding selection (Section4.3.5/Figure8). Table6 sets T0=1000, population200, gmax200, cooling .9. None is currently implemented as a complete package here. Data availability says on request; the inspected article does not provide an author code link.

Several printed details require declared interpretation rather than a silent correction: regret expression/sign and max-selection; Algorithm3's probability formula includes a multiplying n, its reject branch also scores omega3, and selection-count divisions need a zero-count rule; Algorithm4 distinguishes domination, incomparable candidates and SA. Big-M/time/load typography concerns recorded in V442 are not proof that the authors' actual program is invalid. A source-faithful rebuild must freeze how these ambiguities are handled and independently validate it. Collapsing multiple objectives to H2/J removes nondominance/crowding behavior and is a material adaptation, not the original experiment.

## Present decision

Use the two complete generic published search methods now, with the explicitly isolated same-kernel pair-bound contrast. Keep full freight ALNS reconstruction as a separately scoped implementation stage with the above component checklist and declared objective/domain changes. Do not label a small LNS, generic ALNS library, weighted queue alone, or unfinished operator subset as a complete Hof/Wei reproduction. Conversely, do not claim the papers' complete algorithms cannot be reconstructed merely because official source was not retrieved.
