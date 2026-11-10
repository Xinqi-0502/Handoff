# V449 CSV figure contract and preparation

Status: source only, AST checked; matplotlib has not been imported and no CSV analysis or figure rendering was executed. Rendering is deferred until the parent confirms main-run completion, authorizes the formal analysis, and authorizes plots. Numerical sources remain frozen.

The task explicitly selects Python/matplotlib. No backend preference command or global setting is changed during the measured benchmark. All eventual outputs, temporary configuration and failure records stay on E. Installed packages may be reused without installation; a missing selected-backend dependency must stop rendering rather than trigger a different plotting backend.

## Scientific questions and planned evidence

The outcome is deliberately not assumed before results exist.

- Figure 1 asks how finite-budget feasible quality changes with scale. Four scales retain all nine methods. The upper panels show all-three-repeat optimal hits out of 100 planned related scenarios; lower panels show median relative regret and actual available n. These are complementary coverage and quality roles. Unknown data, zero regret and zero denominators remain distinct.
- Figure 2 asks whether proof-cost ratios are supported by a substantial common subset. Three predeclared joint-bound strategies (lazy, full weighted, gated weighted) are compared with Radius, Radius AWA, DP and Exact Route. Global and each-scale points annotate n/N, so two common cases can never visually imply 100. Ratios and expanded sums use identical eligible subsets. Source CSV preserves common mothers and initial-optimal counts.
- Figure 3 asks whether proof coverage and search work agree. All 400 planned cases per method enter the coverage categories. Total, pre-handoff and post-handoff expansion distributions retain every case with three returned counts. Work is end-of-soft-run completed expansion count, not CPU equivalence, proof-time subset work or measured memory. Hard/missing repeats are not assigned zero expansions.

Archetype: quantitative comparison grids. These are report/research figures, not yet journal-submission assets. No particular publisher compliance or novelty claim is implied. Figures 1/3 are 12.6 x 8.8 inches; Figure 2 is 13.3 x 9.2 inches, allowing nine method names and denominator annotations to remain legible. The PDF is vector with editable text; PNG is a 300-dpi review copy. Minimum source font size is 7.5 pt, followed by a 5-pt exported-glyph audit. No p-values, invented confidence intervals or probability claims are drawn. Counts reflect 100 independent mothers and 400 paired scenarios, with three technical repeats.

## Sources and future CLI

The script reads only these formal analysis CSV files: Case_Work_And_Proof.csv, Quality_Summary.csv and Pair_Time_Summary.csv. It does not import analysis or solver modules, read raw benchmark JSON, rerun optimization or infer memory bytes. It cross-checks 400 x 9 case coverage, scale counts, the three-repeat accounting, conditional proof denominators, and paired elapsed/expanded sums. It requires the analysis supplement that includes initial_H2 and same-eligible expanded sums (analysis SHA 2f0258d1e4fb914fa875fd56ab2683690ec1efe62cbf0cd0f4cdea82f999d2bc).

Future command, only after explicit parent authorization:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\plot_scale_v449.py' --analysis 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\analysis\scale_main_01' --out 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\figures\scale_main_01'
```

If the primary runtime lacks matplotlib or a PDF-audit dependency, --library-root may name an existing compatible package directory. That option adds the directory only for this process and its audit subprocesses. No dependency is installed automatically. Rendering must not begin while numerical benchmark timings are being measured.

Each figure saves PNG, PDF and a source CSV. Figure 3 source CSV retains all 3600 case/method rows and includes phase counts and joint-pop counters. Input CSV and plotting-source hashes are recorded in PROVENANCE.json. Output must be a new child of V449/figures; failures stay in FAILURE.json and PROCESS_COMPLETE.json and require a new retry directory.

## Deferred QA

Before any export, the script calls require_matplotlib_panel_alignment with the final drawn layout, 1.5-pt tolerances and explicit colorbar exclusions. It then runs exported-PDF text-size and collision audits. An audit error stops delivery; WARN findings still require visual review. The process status is RENDERED_PENDING_VISUAL_REVIEW, never a claim of visual/publication readiness. Every final PNG/PDF panel and assembled figure must be inspected at its intended physical size before the parent delivers it. No QA result is currently claimed: only Python AST was checked during preparation.

If runtime QA finds a layout issue, preserve that failed output and revise only the plotting source for a fresh output directory; do not change results, exclude losing methods or alter denominators. The skill's source-validation audit and final PDF audits are deferred with rendering. First-good targets achieved by the common initial plan remain identified in analysis and must not be described as search improvements.
