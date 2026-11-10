# Root static review and launch record

The root reviewer inspected Scale_Protocol.md, all six pinned V449 scale sources, the DP adapter and explicit schedules before execution. The review checked nine-arm mappings, shared timed initial plans, source hashes, separation of oracle information from measured solves, conservative interrupted-DP certificates, literal deadline accounting and complete independent-mother scheduling.

The 24-case adapter gate passed (GATE SHA256 508bf6724af92f0657ecf9f72b79db961933c819558744b7999efd74608d5e5f). The gate verifies correctness and accounting, not comparative performance. All four cost blocks completed, totaling 144 calls and 16 cases. Source and algorithm settings remain frozen. These cost calls are not confirmation data.

The seven-arm description in Research_Run_Contract.md is superseded by Protocol_Design_Amendment_01.md, which was frozen before numerical results. Nine arms will be reported, including both prespecified weighted joint-bound configurations. No adaptive switch or tuned parameter has been invented after observing the confirmation set.

The user has previously said an optimal solution is not required. The recommendation will therefore distinguish early solution quality from proof cost, not silently select proof time as the only criterion. A pending optional preference question does not affect this frozen comparison. The best measured combination is not a claim of universal superiority or novelty of its published search policy.

All numerical jobs run serially on E with the existing fail-closed 60 C monitor. Existing sources, data, failures and junctions remain intact. Native SUMO subprocess execution additionally requires a tested owned-process Job Object, because terminating a Python parent alone is insufficient to stop descendants.