# Independent V449 main-result audit: prepared, not executed

Source: `independent_main_audit_v449.py` (263 lines), AST-only PASS. SHA256:
`2d79bdd1c021f0c7befa702b45ea93d1c06c3d1cc89dbf5b788f85275a1b6153`.

No running main measurement, oracle or CSV was read by this preparation. The script imports only standard-library modules, never the solver or official analysis. It requires an explicit execution flag and completion receipts for all52 selected blocks. It must run only after root confirms the timing batch and official analysis are complete.

Future command:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\audit_code\independent_main_audit_v449.py' --execute --selected 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\records\explicit_selected_scale_main_runs_01.json' --analysis 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\analysis\scale_main_01' --out 'E:\CodexResearch-xi\workspace\work\fleet_study_v449_validation_and_online_20261107\analysis\independent_scale_main_01'
```

The output must be fresh. Failed audit attempts must be retained and retried into a new output folder. This checker intentionally requires the complete10800-call matrix; it does not issue a final PASS for incomplete source blocks.

It independently reconstructs literal100/500/1000ms incumbent quality, all-three optimality and proof coverage, first0/5/10% duration-gap attainment and common initial targets. The target comparison uses `100*(H2-opt)<=pct*(opt-t0)` rather than trusting stored target values. It computes every36-method pair on identical all-three on-time eligibility, with time and completed-expansion case medians, common sums and side-only/missing coverage. Exact first-hit expansion indices remain distinct from completed-expansion counts; a partial DP expansion is kept separate.

It cross-checks official per-case quality/proof/first-good CSVs and aggregate quality/time/state summaries, including initial-target attribution. The DP recurrence and its oracle share source; agreement is not relabeled independent algorithm validation. No solver is rerun, and no actual RAM values or labels-to-bytes conversion are produced. Raw/source hashes are checked before and after the audit and retained.
