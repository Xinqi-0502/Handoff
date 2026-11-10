# Execution entry points

Use the existing V447 monitor for every numerical command. Parent/root owns the serial numerical window. All paths below are absolute. No memory solver run has been started by the preparer.

The completed narrow gate is:
`E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory\runs\safety_02\PROCESS_COMPLETE.json`
Its own runtime was 65.3861 s, the monitor returned PASS, and the last sensor reading was 42 C. The 16 MiB allocation increased private commit by 16,809,984 bytes. Failed safety_01 is retained.

## Metadata freeze (no solver)

Run freeze_memory.py with `--external-gate` set to the actual successful, source-matched published-engine gate record and `--safety-gate` set to the record above. The reviewed engine hash is `4d4286ad650f52264375bda90cf1a7c0c907eaa57df4396b58f959d7313b951c`. The freeze requires a new memory/freeze_01 directory and hashes every input/source/job; it does not solve or import a solver.

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory\freeze_memory.py' --external-gate $publishedGate --safety-gate 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory\runs\safety_02\PROCESS_COMPLETE.json'
```

`$publishedGate` is the actual path supplied by root after that gate completes, not a claimed existing PASS file.

## Wrapper gate

```powershell
& 'E:\CodexResearch-xi\workspace\work\fleet_study_v447_random_high_load_20261107\monitor_v447_v2.ps1' -ScriptPath 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory\run_memory_jobs.py' -RunnerArgs @('--execute','--jobs','E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory\freeze_01\correctness_jobs.json') -WorkingDirectory 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory' -LogDirectory 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory\runs\monitor_wrapper_01' -IntervalSeconds 10
```

After the wrapper returns PASS, assemble its raw evidence (no solving):

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory\run_memory_jobs.py' --execute --selected 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory\freeze_01\correctness_selected.json' --out 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\memory\gates\wrapper_all_01'
```

## Cost pilot, then separately approved main

Use the same monitor command with RunnerArgs jobs changed to `freeze_01\pilot_jobs.json` and fresh LogDirectory `runs\monitor_pilot_01` (36 observations). Main uses `freeze_01\main_jobs.json`, fresh `runs\monitor_main_01` (128 observations), and additionally requires the explicit source-matched cost approval. It never starts automatically when pilot finishes.

The runner supports `--run` for an explicitly authorized fresh retry output path while preserving the same frozen job and numerical settings. It never overwrites an existing run. Gate assembly uses an explicit selected-run list, requires exact declared case/method coverage, and hashes the raw evidence. All failed attempts remain on disk.
