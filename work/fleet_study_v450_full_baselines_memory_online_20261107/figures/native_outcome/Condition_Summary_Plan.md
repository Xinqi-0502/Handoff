# Deferred all-condition summary

Status: source prepared only. No pilot effect was inspected or used to select conditions. The complete Cartesian product offset {0,24} x people {0,10} x slow {0,2} is retained at budgets {10,50,200} ms. Each of the 24 cell/budget combinations contains all eight mothers. Both actual customer-flow J and truck handoff waiting are reported, yielding 48 summary rows, with unfavorable effects and unknowns retained.

The output mean requires all eight pairs in a cell. W/T/L/U use the existing 1e-6-second audit tolerance; unknown physical pairs never become zero or survivor-renormalized means. Cross-arm execution equality and within-arm stability are separate descriptive columns and never change the outcome denominator.

After the full64 independent audit PASS and explicit root release, use the same --analysis and --summary-sha256 as the native figure, and a fresh output directory:

~~~powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 '.\summarize_native_conditions.py' --execute --analysis $finalAnalysis --summary-sha256 $summaryHash --out '.\conditions_main_01'
~~~

Run from figures/native_outcome with process-local TEMP/TMP on E. This stdlib-only script does no optimization, simulation, graphics or profile measurement. It reads final audited tables, checks all-cell reconciliation to the figure's overall values and writes separate tables/prose. Existing figures and frozen numerical sources are untouched.

