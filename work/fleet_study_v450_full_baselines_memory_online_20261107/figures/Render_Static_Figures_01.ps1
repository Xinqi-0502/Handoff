param([string]$OutputName = 'render_static_01')
$ErrorActionPreference = 'Stop'
$figureRoot = 'E:\CodexResearch-xi\workspace\work\fleet_study_v450_full_baselines_memory_online_20261107\figures'
$researchPython = 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if ($OutputName -notmatch '^render_static_[0-9]{2}$') { throw 'Use a fresh versioned render_static_XX directory.' }
$env:TEMP = 'E:\CodexResearch-xi\temp'
$env:TMP = $env:TEMP
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:MPLCONFIGDIR = Join-Path (Join-Path $figureRoot $OutputName) '_fontcache'
$env:NATURE_FIGURE_CONFIG = Join-Path $figureRoot 'nature_figure_config.json'
Set-Location -LiteralPath $figureRoot
& $researchPython -B -X utf8 (Join-Path $figureRoot 'render_and_audit_static_v450.py') --out (Join-Path $figureRoot $OutputName)
if ($LASTEXITCODE -ne 0) { throw 'Figure workflow failed. Preserve this output directory and inspect FAILURE.json.' }
Write-Output 'Automatic checks finished; actual PDF/PNG inspection remains required before visual PASS.'

