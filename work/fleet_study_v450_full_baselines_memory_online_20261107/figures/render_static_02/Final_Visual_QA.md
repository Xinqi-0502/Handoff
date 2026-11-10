# Final visual QA — PASS

2026-11-07. Both actual 600 dpi exported PNGs and both previews rendered from the exported PDFs were inspected, including each Figure 1 panel and each complete canvas. Physical export sizes are 183 x 104 mm and 183 x 100 mm. No clipping, text overlap, obscured values or ambiguous positive/negative signs were found.

Figure 1: equal panel rectangles and aligned panel labels pass the strict 1.5 pt gate; reference 100 is visible; values and n=64/64,64/64,64/64,63/64 are legible. Figure 2: the two positive timing changes remain visible; each endpoint carries its distinct n=256 or n=255. The text distinguishes first attainment from optimality proof. No error bars or inferential claim is implied.

Both PDFs have a measured minimum font size of 7 pt, above the 5 pt contract. Both collision audits are auditable with zero FAIL and zero WARN. Figure 2's multi-panel alignment is correctly NOT APPLICABLE because it is a single panel. SVG text remains editable.

The source validator has one non-blocking format warning: no TIFF export. The agreed deliverables are PDF, SVG and 600 dpi PNG, with no target-journal TIFF requirement. This warning is explicitly accepted for the agreed contract; no journal submission compliance is claimed.

The retained render_static_01 failure was two light grid strokes crossing Figure 1 value labels. Revision 02 removed nonessential grid strokes in both figures and corrected distinct QA-log filenames. Data, arithmetic, axis limits, cohort selection, captions and figure dimensions did not change. The two plotted-point CSVs are byte-identical between attempts. Source snapshots and Render_QA_Changes_02.diff preserve the amendment.

No frozen experiment, analysis or raw file changed. Rendering and the independent memory audit have both terminated; no plot, solver, SUMO or analysis child process remains active from this agent.

