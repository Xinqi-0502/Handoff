# Deferred execution

This is code-only preparation. Full64 independent audit PASS must exist before rendering. The two-case pilot is rejected by cases/mothers/policy_calls guards. No outcomes were inspected during preparation; only pilot CSV headers and the audit writer schema were read.

After root releases the shared analysis/render window, use the final full64 independent analysis path. Example only; it does not imply that this directory already exists or that the audit has passed:

~~~powershell
$figureRoot = 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\figures\native_outcome'
$finalAnalysis = 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\online\analysis\main_02'
$env:TEMP = 'E:\CodexResearch-xi\temp'
$env:TMP = $env:TEMP
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:MPLCONFIGDIR = Join-Path $figureRoot 'render_native_01\_fontcache'
Set-Location -LiteralPath $figureRoot
$summaryHash = (Get-FileHash -LiteralPath (Join-Path $finalAnalysis 'SUMMARY.json') -Algorithm SHA256).Hash
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 (Join-Path $figureRoot 'plot_native_outcome_v450.py') --execute --analysis $finalAnalysis --summary-sha256 $summaryHash --out (Join-Path $figureRoot 'render_native_01')
~~~

The output directory must be new. Preserve any failure and rerun to a new suffix only after correcting documented issues. The automatic receipt stops at AUTOMATED_PASS_VISUAL_PENDING. Final delivery requires actual PNG and PDF-preview inspection and a separate visual QA receipt. No TIFF requirement was specified.

