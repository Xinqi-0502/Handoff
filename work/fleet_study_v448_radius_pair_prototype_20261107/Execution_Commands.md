# V448 prepared commands (not executed by preparation)

All commands require the parent's later serialized launch decision. Input generation and AST/static checks do not authorize numerical work. Current micro/pilot completion must be checked from raw artifacts; planned path lists do not prove PASS.

The 24 explicitly selected single-case paths are stored in records/explicit_selected_check_run_paths.json: runs/check_micro_01_00 through runs/check_micro_01_23, matching run_micro_suite_v448.py --tag micro_01. Failed attempts remain preserved; any successful retry substitution must be explicit and must still cover every unique frozen case exactly once.

After all 24 selected raw checks complete and are accepted, assemble the source-bound gate:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 'E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\micro_gate_v448.py' --runs-json 'E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\records\explicit_selected_check_run_paths.json' --out 'E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\gates\micro_all_01'
```

Only after the complete source-matched gate and parent launch decision, run the four frozen pilot jobs under the corrected V447 v2 monitor. Use the parent's existing hidden PowerShell launcher; any new Start-Process must use -WindowStyle Hidden. The original monitor is not used.

```powershell
& 'E:\CodexResearch-xi\workspace\work\fleet_study_v447_random_high_load_20261107\monitor_v447_v2.ps1' `
  -ScriptPath 'E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\run_jobs_v448.py' `
  -RunnerArgs @('E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\records\pilot_jobs_01.json') `
  -WorkingDirectory 'E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107' `
  -LogDirectory 'E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\runs\monitor_pilot_01' `
  -IntervalSeconds 10
```

Jobs use the full blocks m6/m8/m10/m12 in pilot_m6_01/pilot_m8_01/pilot_m10_01/pilot_m12_01. Child-job normal return is not equivalent to every solve obtaining an optimal certificate; inspect each PROCESS_COMPLETE and raw censoring.

After the parent confirms completed data, run the read-only analysis into a new directory:

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 'E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\analysis_v448.py' --runs-json 'E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\records\explicit_selected_pilot_run_paths.json' --out 'E:\CodexResearch-xi\workspace\work\fleet_study_v448_radius_pair_prototype_20261107\analysis\pilot_01'
```

The analysis command performs no solver/oracle work, and does not modify selected source data. It does not measure actual RAM. All outputs and failure records stay on E.
