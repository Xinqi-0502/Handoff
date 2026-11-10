# V450 static figure contract

Status: PREPARED ONLY. No rendering, solver execution or new statistical analysis is authorized by this preparation step. Render only after the root agent releases the serial workload window.

## Evidence and scientific question

Figure 1 asks: within the common cohort that both methods proved optimal within one second in all three technical repetitions, does the shared-quota gate reduce search work, and does this reduction translate into total proof-time savings at each tested order count? Panel a supplies search-work evidence (expanded labels); panel b supplies the distinct realized-cost evidence (elapsed time, including common initialization and bound work). The two panels form one quantitative grid. They do not establish asymptotic complexity.

Figure 2 asks: does faster optimality proof imply faster discovery of a usable solution? The four endpoints retain the measured tradeoff: time to a 5% gap and to a 10% gap increases slightly, while time to the optimum and its proof decreases. These are descriptive aggregate ratios; they are not significance claims.

Both figures compare HZ_AWA_RADIUS_PAIR_GATED with HZ_AWA_RADIUS in the same independent Hansen–Zhou AWA* engine. The published search policy, priority, initial plan, RADIUS bound, continuation bound, Pathmax, model and one-second budget are common. The added shared-quota gate is the variable. This does not reproduce a complete published freight-routing system.

## Cohort, arithmetic and limits

- Formal sample: 256 scenarios from 64 independent mother instances; 16 mothers per m in {6, 8, 10, 12}; four related capacity/signal variants per mother. Three repetitions are technical timing repetitions, not independent instances.
- Figure 1: common on-time proof pairs are 64/64, 64/64, 64/64 and 63/64 scenarios, respectively. The single m=12 exclusion remains explicit. A baseline index of 100 is used. Each plotted index equals 100 times the sum of candidate case values divided by the sum of baseline case values, using exactly the same eligible cases. Each time value is the median of three repetitions before summation. Expanded-label values are deterministic per completed case.
- Figure 2: a signed change is 100*(candidate time sum / baseline time sum - 1). First-within-5%, first-within-10%, and first-optimum endpoints each have 256 eligible scenarios. Proof has 255. Both arms must meet the endpoint on time in all three repetitions. Endpoint cohorts must not be silently pooled.
- Solution gap is (H2-H2*)/(H2*-t0), where H2 is second-handoff completion and H2* is the independent optimum. It is not a ratio of absolute clock times. No initial plan meets any of the displayed quality thresholds.
- No confidence intervals, p values, fitted complexity curves, or timing-noise claims are introduced. Ratios of sums are not averages of per-case percentages. Expanded labels exclude internal lower-bound work.
- The road model uses known FIFO signal calendars on synthetic networks. Order count is not traffic density. The plots do not show customer-delivery flow time, calibrated urban traffic, process memory, or online-system performance.
- Fixed input tables are the independently recomputed proof/first-good tables, accompanied by the primary-analysis and cross-check PASS receipts. The copied CSV bytes, original paths and SHA256 hashes are retained.

## Visual and export parameters

Python/matplotlib only; reuse the existing E-drive plotting libraries. No AI-generated graphics or existing figure artwork.
Figure 1: 183 by 104 mm, two equal plotting panels, shared 0–115 index range, horizontal baseline 100, discrete bars at four m values; each x label states eligible n / 64.
Figure 2: 183 by 100 mm, one horizontal-bar panel, common zero reference, x range -35 to +11 percent; orange for slower and teal for faster; every endpoint label states eligible n.
White canvas, Arial with DejaVu Sans fallback; 8 pt body and tick text, 9 pt panel titles, 8 pt bold lower-case panel labels, minimum exported text 5 pt. Teal #167D9A and orange #B96B35; neutral grey reference lines. No error bars or visual uncertainty symbols.
Exports: editable SVG (text retained), TrueType PDF, 600 dpi PNG, exact plotted-point CSVs, captions and a hash manifest. Physical dimensions are fixed without bbox_inches='tight'.

## Required QA

Before export: source validator; after final canvas layout, strict panel alignment at 1.5 pt tolerance, including panel-label placement for Figure 1. Figure 2 is explicitly single-panel.
After export: PDF effective-font audit with 5 pt minimum; collision/clipping audit with QA overlay; page size, non-empty raster and SVG text checks; PDF-to-PNG previews.
Automated FAIL or NOT AUDITABLE blocks completion. Warnings remain available for explicit review. All final PDFs and PNGs must be inspected at final physical size, by panel and as a whole. No visual PASS before actual inspection. Failed output directories are preserved; reruns use a fresh versioned directory.

## Source and execution boundary

The preparation manifest pins this contract, the plot and QA source, copied source CSVs, completion receipts, cross-check receipt and skill QA helpers. The renderer checks the pins before importing plotting libraries. Temporary files, font cache, Python bytecode policy and outputs stay on E. It does not import or call a solver.

