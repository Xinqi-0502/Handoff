# Native figure revision 02: deadline interpretation

The original render_native_01 and plotting source remain unchanged. Revision 02 adds an on-figure 10 ms late-common-initial-plan-fallback notice and a portable caption with independently audited counts: shared-quota gate 192/192, RADIUS alone 191/192 NO_PLAN_BY_DEADLINE repetitions. The figure does not describe these executed fallback outcomes as plans obtained on time at 10 ms.

No metric, cohort, plotted number, condition table or experimental result changes. The points() function is AST-identical. The revised renderer verifies the exact annotation counts against the copied Case_Budget_Results.csv before drawing. Only new source, new preparation metadata and a fresh render_native_02 are created. No solver or simulator is called.
