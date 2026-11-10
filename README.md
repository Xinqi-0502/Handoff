# Handoff research reproduction archive

This repository accompanies *A Joint Capacity-Release Lower Bound for Two-Stage Urban Freight Handoffs* by Xinqi Wei. It contains the manuscript, original program inputs and run records, synthetic traffic networks, solver and simulation code, independent checks, reports, and the data and code behind the figures. The sequence below follows the evidence used in the paper.

| Stage | Location | Contents |
| --- | --- | --- |
| Manuscript | [paper](paper) | Word, PDF, manuscript source, figures and final evidence review |
| Correctness and prototype | [V448](work/fleet_study_v448_radius_pair_prototype_20261107) | Independent reference, micro cases, bounds, gates and pilot records |
| Method selection | [V449](work/fleet_study_v449_validation_and_online_20261107) | 400 scenarios, 10,800 policy calls, frozen choices, selection and stress analyses |
| Independent confirmation | [V450 static comparison](work/fleet_study_v450_full_baselines_memory_online_20261107/static_comparison) | 256 new scenarios, 3,072 timed calls, instances, solver traces and oracle values |
| Baselines and independent audit | [V450 audit](work/fleet_study_v450_full_baselines_memory_online_20261107/audit_code) | AWA/ANA checks, data audit and results with per-case pairing |
| Process memory | [V450 memory](work/fleet_study_v450_full_baselines_memory_online_20261107/memory) | 128 Windows observations, process checks and trial accounting |
| Online execution | [V450 online](work/fleet_study_v450_full_baselines_memory_online_20261107/online) | 1,728 calls, 128 distinct native SUMO replays, profiling, plans, trajectories, gates and failures |
| Final result index | [V450 evidence index](work/fleet_study_v450_full_baselines_memory_online_20261107/FINAL_EVIDENCE_INDEX_01.json) and [report](work/fleet_study_v450_full_baselines_memory_online_20261107/Research_Evidence_Report_01.html) | Recorded file hashes and links to the underlying results |
| Figure and table review | [Manuscript support](evidence/manuscript_support) | Figure input CSVs, redraw code, table data and claim-to-evidence map. Figure S1 is historical and is absent from the current paper. |

The earlier `work/fleet_study_*` directories supply runtime modules and network inputs pinned by the static and online source manifests. Failed attempts, deadline misses and null outcomes are part of the archive. `RELEASE_INVENTORY.json` records copied file checksums and any excluded items. Locally downloaded literature snapshots are represented by their bibliographic references and retrieval manifests.

## 1. Verify the archived evidence

Use Python 3.11 or later. Run commands from the repository root.

```sh
python tools/verify_inventory.py
python tools/verify_recorded_results.py --root .
```

The archival comparison uses per-scenario medians from three repeats. The confirmation cohort contains 256 scenarios. AWA and PAIR both completed all three proofs within one second in 255 of them. On this shared subset, the expansion totals are 170,932 and 77,362, and summed median proof times are 23.188373599783517 and 16.888535799109377 seconds. The archival verifier checks results from frozen data. Fresh process timing and deadline membership depend on the machine and load.

## 2. Run the solver and inspect a saved simulation trace

Choose a new output path for each invocation. `repro_runs/` is ignored by Git.

```sh
python tools/replay_smoke.py --archive . --out repro_runs/solver_micro
python tools/replay_smoke.py --archive . --out repro_runs/static_48 --formal-static --stop 4
python tools/replay_smoke.py --archive . --out repro_runs/trace_audit --skip-static --audit-native
```

The micro replay checks exact objectives, certificates and graph-policy fixtures against independent references. The timed command runs the first four confirmation cases with the archived four arms and three repeats. Omit `--stop 4` and choose a fresh output directory to retime all 256 cases. Read the resulting call status and certificate before aggregating timings.

## 3. Replay the physical simulation

Create a separate Python environment. The native run used Eclipse SUMO 1.27.1 and matching TraCI and sumolib. Install the archived versions where they are available for your operating system.

```sh
python -m pip install -r requirements-sumo.txt
python tools/replay_smoke.py --archive . --out repro_runs/native_saved_plan --skip-static --native
```

The replay uses the archived snapshot, plan and planning latency. This isolates physical execution from timing the online planner on another machine. `--native-case` accepts another `native_*` directory name from `work/fleet_study_v450_full_baselines_memory_online_20261107/online/runs/full_02/`. Add `--native-all` to either `--native` or `--audit-native` to process all 128 formal native executions.

## 4. Regenerate the paper figures

```sh
python -m pip install -r requirements-figures.txt
python evidence/manuscript_support/Figure_Code/redraw_figures.py --out repro_runs/figures
```

Use Figures 1 and 2 for the current paper. The historical Figure S1 is regenerated from the archived source data for comparison.

## Full historical protocols

The original programs and their documented commands are preserved. See [Execution_Commands.md](work/fleet_study_v448_radius_pair_prototype_20261107/Execution_Commands.md), [Scale_Protocol.md](work/fleet_study_v449_validation_and_online_20261107/Scale_Protocol.md), and [Execution_Contract.md](work/fleet_study_v450_full_baselines_memory_online_20261107/Execution_Contract.md). V450 records the original online command arrays in `online/records/*_args_02.json`. Those receipts retain absolute paths from the original Windows machine. For a full legacy run, interpret those paths relative to a scratch copy of this archive and use fresh output directories. Check frozen source bytes against the stored SHA-256 values before relocating paths.

To benchmark the online policies again on a new Windows machine, recreate the micro gate, pilot prefixes, native gate, and full prefixes in that order. The original commands below are expressed with paths relative to the checkout. Use a new directory for `$Run`, check each exit code, and keep the new timing results separate from the archived results.

```powershell
$Online = Join-Path (Get-Location) "work/fleet_study_v450_full_baselines_memory_online_20261107/online"
$Run = Join-Path (Get-Location) "repro_runs/online_01"
python -B "$Online/check_online_v450.py" check --inputs "$Online/MICRO_INPUTS_01.json" --out "$Run/micro"
python -B "$Online/prepare_online_v450.py" prefix --inputs "$Online/INPUTS_64_01.json" --out "$Run/pilot_prefix" --pilot
python -B "$Online/native_gate_v450.py" --prefixes "$Run/pilot_prefix" --gate "$Run/micro" --out "$Run/native_gate"
python -B "$Online/prepare_online_v450.py" prefix --inputs "$Online/INPUTS_64_01.json" --out "$Run/full_prefix"
python -B "$Online/run_online_v450.py" --definitions "$Online/INPUTS_64_01.json" --prefixes "$Run/full_prefix" --gate "$Run/micro" --native-gate "$Run/native_gate" --out "$Run/full" --native
```

The release check retimed four static confirmation cases and replayed a native saved plan. The full online pipeline above is the archived protocol for a new run.

The Windows peak-memory study uses the Windows process counters and fresh processes. The same raw counters can be recomputed on other platforms. Fresh native timings are environment dependent. The traffic-network experiments are synthetic. The preserved San Pablo tutorial validation is a separate upstream fixture, with its original LICENSE, NOTICE, and source commit, and does not calibrate the paper's synthetic network.
