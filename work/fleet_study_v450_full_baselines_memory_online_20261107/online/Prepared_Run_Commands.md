# Prepared execution commands

No command in this note has been executed by preparation. The input generation alone is complete: INPUTS_64_01.json and MICRO_INPUTS_01.json. All solver/native work remains gated and root-scheduled. Use new output suffixes after any failed attempt; never overwrite an earlier run.

```powershell
$R = 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\online'
$PY = 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$MON = 'E:\CodexResearch-xi\workspace\work\fleet_study_v447_random_high_load_20261107\monitor_v447_v2.ps1'
```

The first online numerical command, after independent static clearance and the separate published-engine correctness gate, is:

```powershell
& $MON -Python $PY -ScriptPath "$R\job_host_online_v450.py" -WorkingDirectory $R -LogDirectory "$R\monitor\micro_gate_01" -RunnerArgs @('--python',$PY,'--script',"$R\check_online_v450.py",'--args-json',"$R\records\micro_gate_args_01.json",'--out',"$R\hosts\micro_gate_01",'--timeout-seconds','900')
```

All arguments are already saved as JSON string arrays under records. Invoke the same owned host and monitor pattern with these stages in order:

| Stage | Worker script | Arguments JSON | Suggested host/monitor suffix | Outer timeout |
|---|---|---|---|---:|
| Small exact correctness | check_online_v450.py | micro_gate_args_01.json | micro_gate_01 | 900 s |
| Two fixed native prefixes | prepare_online_v450.py | pilot_prefix_args_01.json | pilot_prefix_01 | 900 s |
| Four physical latency/invariant checks | native_gate_v450.py | native_gate_args_01.json | native_gate_01 | 900 s |
| Fixed two-scenario policy/native cost pilot | run_online_v450.py | pilot_args_01.json | pilot_01 | 1800 s |
| Separate optional instrumented profile | profile_online_v450.py | profile_args_01.json | profile_01 | 900 s |
| All64 native prefixes, only after advancement | prepare_online_v450.py | full_prefix_args_01.json | full_prefix_01 | 1800 s |
| All64 policy/native expansion, only after advancement | run_online_v450.py | full_args_01.json | full_01 | 14400 s |

The outer owned-process timeout covers Python plus SUMO descendants and does not alter 10/50/200-ms per-policy budgets or the1800-s simulated native horizon. It is a safety ceiling, not a prediction of runtime. Root must determine practical batch cost from the fixed pilot before the full expansion. The existing temperature monitor checks every10s, stops at60C or monitoring failure, and owns only the new Job-host child.

A direct Python command for read-only review of the gate interface is equivalent to:

```powershell
& $PY -B -X utf8 "$R\check_online_v450.py" check --inputs "$R\MICRO_INPUTS_01.json" --out "$R\gates\micro_01"
```

Use the monitored owned-host version for actual execution. A PASS requires the nested worker, host and monitor receipts; a stdout line alone is not completion evidence. Source changes invalidate the gates. The main source closure includes every online-root .py file, so put later independent audit scripts under online/analysis or a separate audit_code directory.
