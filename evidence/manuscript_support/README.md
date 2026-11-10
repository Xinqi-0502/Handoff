# Supporting materials

This package accompanies A Joint Capacity-Release Lower Bound for Two-Stage Urban Freight Handoffs.

## Included material

Figure_Source_Data contains every CSV copied unchanged from the manuscript figure-data directory. The three fig*_points.csv files contain the plotted values; the other CSVs retain corroborating summaries and paired observations. File_Hashes.json protects their identity.

Figure_Code/redraw_figures.py is a portable Python/Matplotlib reproduction of Figures 1, 2 and S1. It reads only this package, verifies CSV hashes and checks plotted values against the bundled summaries.

Table_Source_Data/Selection_400 contains design-stage summaries for 400 related scenarios from 100 mother instances. These selected the method; they are not independent confirmation. Confirmation_256 contains four-method confirmation tables for 256 scenarios from 64 new mothers, including case medians. Process_Memory_32 contains separate actual-process observations and summaries for 32 scenarios and 128 fresh processes; startup/import peaks remain included and do not establish algorithmic memory savings. Online_64 contains native customer outcomes, deadlines, common-engine comparisons and a separate instrumented profile for 64 conditions from eight order instances on one SUMO network.

Manuscript_Claim_Evidence.json includes the manuscript evidence review, provenance labels and copied-file SHA-256 values. Archive labels refer to sources retained separately and are not runnable filesystem dependencies. Review_Notes/Original_Figure_QA.md records the original figures' completed visual/PDF QA. test_render is a local figure reproduction, not another experiment. SHA256SUMS lists relative-path checksums, excluding itself.

## Redraw

Use Python 3.10 or newer and Matplotlib with its normal dependencies. From this package directory:

    python -m pip install -r Figure_Code/requirements.txt
    python Figure_Code/redraw_figures.py --out Recreated_Figures

The output directory must not exist. Existing outputs are never overwritten. The --data option accepts a copy of the complete Figure_Source_Data directory. Outputs are editable PDF/SVG and 300-dpi PNG at 160 mm width, with heights 55,45,50 mm.

Times New Roman is used when available. No licensed font is bundled. If absent, DejaVu Serif is used and typography differs. Matching data and fonts alone do not guarantee identical files across Matplotlib/FreeType versions; PDF/SVG metadata can differ. Reproduction_Test.json records the actual runtime and decoded-pixel comparison with the manuscript PNGs.

## Interpretation

Times are sums of per-scenario medians of technical repetitions. Proof-time pairs require both methods to certify within the deadline in all three repetitions; their eligible denominator can differ from all-scenario solution-quality summaries. Variants of one mother are related, not independent demand replicates. Negative and null effects are retained.

Online outcomes are policy-frequency-weighted representative native replays, not averages of three independent SUMO runs. The 10 ms endpoint mainly executed late common-initialization fallbacks. Same-engine physical outcomes tie at every budget. Separate profile times must not be pooled with formal performance timings. Expanded labels are not memory bytes.

## Scope limit

This is a compact figure/table and summary-evidence package, NOT the complete raw research archive. It does not claim to reproduce optimization, timing or simulation experiments from scratch. Full order inputs, frozen solver/simulator sources, per-call traces, oracle records, native logs, monitoring and failure records are retained separately by the author. This package does not substitute for that archive.

Copied data are byte-for-byte unchanged. No new solver, simulator or performance experiment was run to prepare this package.

## Recorded reproduction check

All three PNGs are decoded-pixel identical to the manuscript figures in the recorded test: Python 3.12.14, Matplotlib 3.11.2, Times New Roman. See Reproduction_Test.json. This test only redraws existing data; it does not rerun the study.
