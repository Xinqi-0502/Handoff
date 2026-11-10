# V448 micro gate assembly contract

Prepared source only; no numerical solver, checker, gate assembly, or absent result was invoked. Python AST PASS. Current helper SHA256: `2d8875a347f89fdca3f8eab6dc9052a2596bab86e00c4730c9d67f3e8d0dfe00`.

Historical helper SHA256 before the cutoff-accounting correction: `ce267a259821d4b5ec422c1f45c4d521548a000b974f2dbb2f52aceb97cc6192`. This historical fingerprint is retained for provenance and is not the current helper.

API: `current_sources()` returns a filename-to-SHA256 dictionary for seven local sources (selective, reference, checker, instances, run, run_jobs, micro_gate) and the parent independent_dp/instances sources. Missing sources raise when called, not on import. No source imports or hash reads occur at import.

`validate_gate(path)` accepts GATE.json or its directory. It checks the successful completion marker and gate hash, explicit selection-file hash, all nine current source identities, all six checker pins, and all original evidence again. It returns the validated gate dictionary or raises. Gate validation does not run solvers.

Future CLI: `python -B -X utf8 micro_gate_v448.py --runs-json records/explicit_selected_check_run_paths.json --out gates/micro_all_01`. The selection is an array of paths or an object with a runs array. Relative paths resolve from V448. Gate output must be a new V448 descendant; old failed attempts and previous gates are never deleted or overwritten.

The selected PASS attempts may be successful retries. Each selected attempt must have PROCESS_COMPLETE PASS and no FAILURE, matching original output hashes, checker BEEC version, six pinned artifacts, full selected input, protocol, summary and case-completion records. Selected ranges may hold 1..4 cases, but the union must equal exactly all 24 frozen cases, without duplicate cases or run paths. Failed/partial attempts remain preserved outside the selected gate.

Coverage checks include every case's 36 solution validations, 4 named aliases, both bases, nonempty phase-0/phase-1/terminal/full/cutoff/parity/pathmax/closure checks and complete raw solve/oracle/prefix matrices. Aggregate shortcut and integer-wait checks must be nonempty. Waiting checks remain the frozen prefix sample (8 candidate prefixes, horizon limit 4096), not exhaustive waiting tests at every state. No performance claim or permission is encoded by the correctness gate.

The helper binds measurement-source hashes at assembly time. Those files need not have existed when earlier raw checks were generated; solver/reference/checker identities must nevertheless match the checked pinned versions. Later changes to any of the nine measurement sources invalidate the gate and require a new explicitly assembled gate. Changing solver/checker pin identities also requires compatible new correctness evidence.

Failure during assembly writes FAILURE.json and PROCESS_COMPLETE FAIL. Preflight failures before a new output directory exists raise without creating a successful gate. Original research evidence and numerical sources are read only.

Cutoff accounting is reconstructed from every raw nonterminal prefix and both base/full pairs: two gated modes times the size of {max(0,full-1),full,full+1,base,base+1}. The two bases may have different boundary-set sizes; divisibility by four is not assumed. This static pre-run correction changes only evidence accounting, not solver or checker behavior.
