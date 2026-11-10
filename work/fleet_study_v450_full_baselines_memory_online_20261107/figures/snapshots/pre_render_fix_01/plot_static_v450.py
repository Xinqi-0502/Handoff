"""V450 static evidence figures. No solver imports; audited CSVs only."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME = Path(r"E:\CodexResearch-xi\workspace\research_outputs\ICTEC2027_Analysis_Figures_Extended_20261106\_Plot_Runtime")
SKILL = Path(r"C:\Users\admin\.codex\skills\nature-figure\scripts")
CANDIDATE = "HZ_AWA_RADIUS_PAIR_GATED"
BASELINE = "HZ_AWA_RADIUS"
SIZES = (6, 8, 10, 12)
TEAL = "#167D9A"
ORANGE = "#B96B35"
GREY = "#6B6B6B"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def verify_preparation():
    prep = json.loads((ROOT / "Preparation_Manifest.json").read_text(encoding="utf-8-sig"))
    if prep["status"] != "PREPARED_AST_ONLY":
        raise ValueError("Unexpected preparation state")
    for item in prep["pinned_files"]:
        if sha(item["path"]) != item["sha256"]:
            raise ValueError("Frozen source or evidence hash mismatch: " + item["path"])
    for item in prep["source_csvs"]:
        if sha(item["original_path"]) != item["sha256"] or sha(ROOT / item["copy_path"]) != item["sha256"]:
            raise ValueError("CSV provenance mismatch")
    for name in ("primary_complete.json", "independent_complete.json", "crosscheck_complete.json", "Crosscheck.json"):
        if json.loads((ROOT / "source_data" / name).read_text(encoding="utf-8-sig"))["status"] != "PASS":
            raise ValueError("Require completed primary analysis and independent cross-check")
    cross = json.loads((ROOT / "source_data" / "Crosscheck.json").read_text(encoding="utf-8-sig"))
    if cross["case_rows"] != 1024 or cross["independent_mothers"] != 64 or cross["related_variants_per_mother"] != 4:
        raise ValueError("Unexpected audited cohort")
    return prep

def number(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError("Non-finite plotted value")
    return value

def one(rows, **fields):
    selected = [r for r in rows if all(r.get(k) == str(v) for k, v in fields.items())]
    if len(selected) != 1:
        raise ValueError(("Expected exactly one selected source row", fields, len(selected)))
    return selected[0]

def points():
    proof = read_csv(ROOT / "source_data" / "Directed_Proof_Pairs.csv")
    first = read_csv(ROOT / "source_data" / "Initial_Strata_First_Good_Pairs.csv")
    scale_points = []
    for m, expected_n in zip(SIZES, (64, 64, 64, 63)):
        row = one(proof, stratum="m", value=m, candidate=CANDIDATE, baseline=BASELINE)
        if int(row["common_on_time_proved"]) != expected_n or int(row["all_cases"]) != 64:
            raise ValueError("Changed scale cohort")
        for metric, candidate_key, baseline_key, change_key in (
            ("expanded_labels", "candidate_expanded_sum", "baseline_expanded_sum", "expansion_change_percent"),
            ("proof_time_seconds", "candidate_time_sum", "baseline_time_sum", "time_change_percent"),
        ):
            c, b = number(row, candidate_key), number(row, baseline_key)
            if b <= 0:
                raise ValueError("Non-positive reference denominator")
            index = 100 * c / b
            if not math.isclose(index - 100, number(row, change_key), abs_tol=1e-9):
                raise ValueError("CSV derived field disagrees with source sums")
            scale_points.append(dict(figure="Fig1", panel="a" if metric == "expanded_labels" else "b",
                m=m, metric=metric, candidate=CANDIDATE, baseline=BASELINE, eligible_cases=expected_n,
                available_cases=64, independent_mothers=16, related_variants_per_mother=4,
                candidate_sum=c, baseline_sum=b, relative_index_percent=index,
                change_percent=index-100, aggregation="ratio of sums; per-case median of three times",
                source_csv="Directed_Proof_Pairs.csv"))
    endpoint_points = []
    for key, label, fraction in (("first_5_percent", "First gap \u22645%", "0.05"),
                                 ("first_10_percent", "First gap \u226410%", "0.1"),
                                 ("first_optimum", "First optimum", "0.0")):
        row = one(first, stratum="all", value="all", candidate=CANDIDATE, baseline=BASELINE,
                  fraction=fraction, initial_group="all")
        if int(row["common_all3_reached"]) != 256 or int(row["group_cases"]) != 256:
            raise ValueError("Changed first-attainment cohort")
        initial = one(first, stratum="all", value="all", candidate=CANDIDATE, baseline=BASELINE,
                      fraction=fraction, initial_group="initial_good")
        if int(initial["group_cases"]) != 0:
            raise ValueError("Figure contract requires no initially qualifying plans")
        c, b = number(row, "candidate_seconds"), number(row, "baseline_seconds")
        change = 100*(c/b-1)
        if not math.isclose(change, number(row, "time_change_percent"), abs_tol=1e-9):
            raise ValueError("First-attainment arithmetic mismatch")
        endpoint_points.append(dict(figure="Fig2", endpoint=key, label=label, candidate=CANDIDATE,
            baseline=BASELINE, gap_fraction=float(fraction), eligible_cases=256, available_cases=256,
            candidate_seconds_sum=c, baseline_seconds_sum=b, time_change_percent=change,
            source_csv="Initial_Strata_First_Good_Pairs.csv"))
    row = one(proof, stratum="all", value="all", candidate=CANDIDATE, baseline=BASELINE)
    if int(row["common_on_time_proved"]) != 255 or int(row["all_cases"]) != 256:
        raise ValueError("Changed proof cohort")
    c, b = number(row, "candidate_time_sum"), number(row, "baseline_time_sum")
    endpoint_points.append(dict(figure="Fig2", endpoint="proof", label="Optimality proof",
        candidate=CANDIDATE, baseline=BASELINE, gap_fraction="", eligible_cases=255, available_cases=256,
        candidate_seconds_sum=c, baseline_seconds_sum=b, time_change_percent=100*(c/b-1),
        source_csv="Directed_Proof_Pairs.csv"))
    return scale_points, endpoint_points

def export(fig, out, name, panel_count):
    from audit_panel_alignment import require_matplotlib_panel_alignment
    fig.canvas.draw()
    # Final layout gate is enforced before any publishable export.
    require_matplotlib_panel_alignment(fig, json_out=out/(name+".alignment.json"),
        overlay_svg=out/(name+".alignment.svg"), tolerance_pt=1.5,
        gutter_tolerance_pt=1.5, require_panel_labels=(panel_count > 1), strict=True)
    fig.savefig(out/(name+".svg"))
    fig.savefig(out/(name+".pdf"))
    fig.savefig(out/(name+".png"), dpi=600)

def draw_scale(rows, out, plt):
    from matplotlib.transforms import ScaledTranslation
    fig, axes = plt.subplots(1, 2, figsize=(183/25.4, 104/25.4), sharey=True)
    fig.subplots_adjust(left=.10, right=.97, bottom=.25, top=.76, wspace=.24)
    fig.suptitle("Shared-quota gate: search work and proof time", y=.955, fontsize=10, fontweight="bold")
    fig.text(.5, .885, "Same AWA* engine | AWA* + RADIUS = 100", ha="center", fontsize=8)
    for ax, panel, title in zip(axes, ("a", "b"), ("Expanded labels", "Time to optimality proof")):
        data = [r for r in rows if r["panel"] == panel]
        x = list(range(4))
        y = [r["relative_index_percent"] for r in data]
        ax.bar(x, y, width=.52, color=TEAL, edgecolor=TEAL, linewidth=.5, zorder=3)
        ax.axhline(100, color=GREY, linestyle=(0, (4, 3)), linewidth=.8, zorder=2)
        ax.set_ylim(0, 115)
        ax.set_yticks((0, 25, 50, 75, 100))
        ax.set_xticks(x, [str(r["m"])+"\nn = "+str(r["eligible_cases"])+"/64" for r in data])
        ax.set_xlabel("Old orders, m", labelpad=8)
        ax.set_title(title, fontsize=9, pad=12)
        ax.grid(axis="y", color="#E3E3E3", linewidth=.5, zorder=0)
        for px, py in zip(x, y):
            ax.annotate(f"{py:.1f}", (px, py), xytext=(0, 5), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)
        ax.text(0, 1, panel, transform=ax.transAxes+ScaledTranslation(-18/72, 11/72, fig.dpi_scale_trans),
                ha="left", va="bottom", fontsize=8, fontweight="bold")
    axes[0].set_ylabel("Relative index (%)")
    fig.text(.10, .065, "n = common on-time proof pairs / 64 scenarios per scale; 16 independent mothers per scale.",
             fontsize=7, ha="left")
    export(fig, out, "Fig1_Same_Kernel_Scale", 2)
    plt.close(fig)

def draw_endpoints(rows, out, plt):
    fig, ax = plt.subplots(figsize=(183/25.4, 100/25.4))
    fig.subplots_adjust(left=.32, right=.95, bottom=.24, top=.76)
    fig.suptitle("A smaller search does not improve every anytime endpoint", y=.955,
                 fontsize=10, fontweight="bold")
    fig.text(.5, .885, "Same AWA* engine | Shared-quota gate versus RADIUS alone", ha="center", fontsize=8)
    y = list(range(4))
    changes = [r["time_change_percent"] for r in rows]
    ax.barh(y, changes, height=.52, color=[ORANGE if v>0 else TEAL for v in changes],
            edgecolor="none", zorder=3)
    ax.axvline(0, color=GREY, linewidth=.8, zorder=2)
    ax.set_yticks(y, [r["label"]+"  (n = "+str(r["eligible_cases"])+")" for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(-35, 11)
    ax.set_xticks((-30, -20, -10, 0, 10))
    ax.set_xlabel("Aggregate time change (%)")
    ax.grid(axis="x", color="#E3E3E3", linewidth=.5, zorder=0)
    for py, px in zip(y, changes):
        offset = 5 if px>=0 else -5
        ax.annotate(f"{px:+.2f}%", (px, py), xytext=(offset, 0), textcoords="offset points",
                    ha="left" if px>=0 else "right", va="center", fontsize=8)
    fig.text(.32, .105, "Negative: faster    Positive: slower", fontsize=7.5)
    fig.text(.08, .045, "Endpoint-specific common cohorts; first-hit n = 256, proof n = 255 out of 256 scenarios.",
             fontsize=7, ha="left")
    export(fig, out, "Fig2_Anytime_Tradeoff", 1)
    plt.close(fig)

CAPTIONS = """# V450 static figure captions

**Figure 1. Search work and total proof time for the same search engine.**
Hansen–Zhou Anytime Weighted A* (weight 2) supplied with the common RADIUS bound and the shared-quota cutoff gate is compared with the same engine supplied with RADIUS alone. The reference is 100. Panel a reports expanded labels; panel b reports total elapsed time to proof, including common initialization and bound work. Each plotted index is 100 times the sum of candidate values divided by the sum of baseline values on the identical common cohort; timing uses each case's median of three technical repetitions before summation. Both arms must prove optimality within the one-second budget in all three repetitions. Eligible counts are 64/64, 64/64, 64/64, and 63/64 scenarios for m=6,8,10,12. Each scale contains 16 independent mother instances with four related capacity/signal variants. These are fixed-cohort descriptive ratios, without error bars or inferential tests. Expanded labels exclude internal bound work, and these four discrete sizes do not establish an asymptotic complexity law.

**Figure 2. Endpoint-specific anytime timing tradeoff.**
The same two implementations are compared using 100*(candidate time sum / baseline time sum - 1), after taking the per-case median of three technical repetitions. Negative values indicate faster attainment. The first-within-5%, first-within-10%, and first-optimum cohorts each contain all 256 scenarios; both arms must reach the endpoint within one second in all three repetitions. The proof cohort contains 255/256 scenarios satisfying the same requirement for optimality certification. The gap is (H2-H2*)/(H2*-t0), using remaining duration rather than absolute clock time; H2 denotes second-handoff completion and H2* is the independent optimum. No initial plan met any displayed quality threshold. Small increases in time to the 5% and 10% thresholds are retained. Reaching the optimum and proving it are distinct endpoints.

**Shared scope.**
The 256 scenarios arise from 64 independent mother instances, not 256 independent networks; repetitions are technical repeats. Networks use known FIFO signal calendars and synthetic orders. These figures do not establish real-city calibration, traffic-density effects, full freight-system reproduction, customer flow-time improvement, online performance, or process-memory savings. Full precision plotted data, copied source CSVs and SHA256 provenance accompany the figures.
"""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--library-root", type=Path, default=RUNTIME)
    args = parser.parse_args()
    prep = verify_preparation()
    out = args.out.resolve()
    if out.drive.upper() != "E:":
        raise ValueError("Research figure outputs must remain on E")
    out.mkdir(parents=True, exist_ok=False)
    try:
        os.environ["TEMP"] = os.environ["TMP"] = r"E:\CodexResearch-xi\temp"
        os.environ["MPLCONFIGDIR"] = str(out/"_fontcache")
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        if not (args.library_root/"matplotlib").is_dir():
            raise RuntimeError("Existing plotting runtime unavailable; do not install automatically")
        sys.path[:0] = [str(args.library_root), str(SKILL)]
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams.update({"font.family":"sans-serif", "font.sans-serif":["Arial","DejaVu Sans"],
            "font.size":8, "axes.labelsize":8, "xtick.labelsize":8, "ytick.labelsize":8,
            "legend.fontsize":8, "axes.titlesize":9, "pdf.fonttype":42, "svg.fonttype":"none",
            "axes.spines.top":False, "axes.spines.right":False, "axes.linewidth":.7,
            "figure.facecolor":"white", "savefig.facecolor":"white"})
        scale, endpoints = points()
        write_csv(out/"Fig1_Plotted_Points.csv", scale)
        write_csv(out/"Fig2_Plotted_Points.csv", endpoints)
        draw_scale(scale, out, plt)
        draw_endpoints(endpoints, out, plt)
        (out/"Captions.md").write_text(CAPTIONS, encoding="utf-8")
        dump(out/"Render_Manifest.json", {
            "status":"RENDERED_QA_PENDING", "source_sha256":sha(__file__),
            "preparation_sha256":sha(ROOT/"Preparation_Manifest.json"), "matplotlib":matplotlib.__version__,
            "source_csvs":prep["source_csvs"], "output_hashes":{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
            "physical_size_mm":{"Fig1":[183,104],"Fig2":[183,100]}, "png_dpi":600,
            "visual_inspection":"PENDING", "no_solver_called":True})
    except BaseException as exc:
        dump(out/"RENDER_FAILURE.json", {"type":type(exc).__name__,"message":str(exc)})
        raise

if __name__ == "__main__":
    main()

