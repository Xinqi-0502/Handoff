# Native-outcome figure and condition summary: final QA

Status: **PASS**. The actual PNG and the PDF-rendered preview were both inspected. Both panels have readable titles, axes, zero markers and W/T/L/U labels; no visible overlap or clipping was found. The PDF has a 7 pt minimum text size, and the automated collision audit has no findings. The source warning about no TIFF is accepted because the requested export set is PNG/PDF/SVG. No uncertainty interval is implied: all 64 observed paired changes are exactly zero, and the related scenarios are not treated as 64 independent networks.

At each of 10, 50 and 200 ms, both actual customer-flow J and truck handoff waiting have mean change 0 seconds and W/T/L/U = 0/64/0/0. All eight predeclared condition cells retain all eight mothers: each of the 48 condition/budget/metric rows has mean change 0 seconds and W/T/L/U = 0/8/0/0. The 384 per-case metric differences are exactly zero, not merely within the equality tolerance.

The figure and condition CSVs reconcile, and their per-case CSV files are byte-identical. Execution identity counts are recorded in the separate JSON receipt and CSV. Within-arm stability, cross-arm equality and the audit's direct subset remain different definitions; none filters the outcome denominator. This is frequency-weighted representative replay for a single synthetic dispatch epoch. It does not demonstrate a customer-outcome improvement, a calibrated delivery network or continuous dispatch.

The existing automated output manifests remain unchanged. This additive receipt records final visual review. No optimization or SUMO run was performed during reporting.
