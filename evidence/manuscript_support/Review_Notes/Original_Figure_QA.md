# Compact manuscript figure QA

Status: **PASS under the explicit conference-template contract**. All three actual PNGs and all three PDF-rendered previews were inspected. Values, sample counts, two-panel alignment, axes, loss directions and zero results remain readable. No visible clipping or text collision was found. PDF text checks confirm only Times New Roman families and a minimum of 8.5 pt; all automated collision checks report zero failures and warnings.

Insert the final files at **16.0 cm width**: Fig. 1 height 5.5 cm, Fig. 2 height 4.5 cm, and Fig. S1 height 5.0 cm. Do not shrink them further. PNG is 300 dpi, with matching editable PDF and SVG. The main text uses Figs. 1 and 2; the native outcome figure belongs in the appendix/supplement.

The original-source CSVs are copied unchanged under source_data, with original absolute locations and hashes in Source_Manifest.json. Every plotted value is cross-checked against the existing independently audited source tables. The native caption retains the 10 ms NO_PLAN_BY_DEADLINE counts (192/192 gated, 191/192 baseline) and explains late common-initial-plan fallback. It does not call those results plans produced within 10 ms.

The skill source validator only accepts its default font families and rejected the template's explicitly required Times New Roman. The render_01 failure and raw finding are preserved. The documented single font exception follows the user's conference template; the replacement checks verify the installed font file, actual Matplotlib font resolution, every PDF text-span family and the effective 8.5 pt floor. Other quality checks were not weakened. The 160 mm width and 300 dpi PNG also follow explicit user requirements rather than the skill's 183 mm / 600 dpi defaults. Eight white bar labels intentionally sit within the teal bars and remain legible; the collision audit accepts their containment.

No new experiment, optimization or SUMO run was performed. Earlier experiment and figure sources are unchanged. The final flat files are byte-identical copies of render_02 exports, and the full captions and insertion notes accompany them.
