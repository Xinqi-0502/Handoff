"""Run the frozen V450 figure export and audits after the serial window opens."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent
RUNTIME = Path(r"E:\CodexResearch-xi\workspace\research_outputs\ICTEC2027_Analysis_Figures_Extended_20261106\_Plot_Runtime")
SKILL = Path(r"C:\Users\admin\.codex\skills\nature-figure\scripts")
FIGURES = ("Fig1_Same_Kernel_Scale", "Fig2_Anytime_Tradeoff")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")

def invoke(script, args, log, env):
    command = [sys.executable, "-B", "-X", "utf8", str(script), *map(str, args)]
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, encoding="utf-8",
                            capture_output=True, timeout=180)
    Path(str(log)+".stdout.txt").write_text(result.stdout, encoding="utf-8")
    Path(str(log)+".stderr.txt").write_text(result.stderr, encoding="utf-8")
    dump(Path(str(log)+".command.json"), {"argv":command, "returncode":result.returncode})
    if result.returncode != 0:
        raise RuntimeError("Retained failing QA step: "+str(log))
    return result.stdout

def audit_geometry(exports, qa, runtime):
    sys.path.insert(0, str(runtime))
    import fitz
    from PIL import Image, ImageChops
    checks = []
    for name, height in zip(FIGURES, (104, 100)):
        with fitz.open(exports/(name+".pdf")) as doc:
            if len(doc) != 1:
                raise ValueError("Each figure must be one PDF page")
            page = doc[0]
            expected = (183/25.4*72, height/25.4*72)
            if abs(page.rect.width-expected[0])>.2 or abs(page.rect.height-expected[1])>.2:
                raise ValueError("Unexpected PDF physical dimensions")
            if not page.get_text().strip():
                raise ValueError("Editable PDF text missing")
            page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(qa/(name+".pdf_preview.png"))
        with Image.open(exports/(name+".png")) as im:
            expected_px = (183/25.4*600, height/25.4*600)
            if any(abs(actual-target)>2 for actual, target in zip(im.size, expected_px)):
                raise ValueError("Unexpected 600 dpi PNG dimensions")
            rgb = im.convert("RGB")
            content = ImageChops.difference(rgb, Image.new("RGB", im.size, "white")).getbbox()
            if content is None:
                raise ValueError("Blank figure")
            # Page-edge clipping is checked by the PDF audit as well.
            if min(content[0],content[1],im.width-content[2],im.height-content[3]) < 5:
                raise ValueError("Non-white image content reaches the canvas edge")
        svg = (exports/(name+".svg")).read_text(encoding="utf-8")
        if "<text" not in svg:
            raise ValueError("SVG text was converted to outlines")
        checks.append({"figure":name,"page_count":1,"physical_size_mm":[183,height],
                       "png_dpi":600,"svg_editable_text":True,"raster_content_bbox":content})
    return checks

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--library-root", type=Path, default=RUNTIME)
    args = parser.parse_args()
    # This import is stdlib-only. It does not import matplotlib or any solver.
    from plot_static_v450 import verify_preparation
    prep = verify_preparation()
    out = args.out.resolve()
    if out.drive.upper() != "E:":
        raise ValueError("Output directory must be on E")
    out.mkdir(parents=True, exist_ok=False)
    qa = out/"qa"
    qa.mkdir()
    exports = out/"exports"
    env = dict(os.environ)
    env.update({"TEMP":r"E:\CodexResearch-xi\temp", "TMP":r"E:\CodexResearch-xi\temp",
                "PYTHONDONTWRITEBYTECODE":"1","MPLCONFIGDIR":str(out/"_fontcache"),
                "NATURE_FIGURE_CONFIG":str(ROOT/"nature_figure_config.json"),
                "PYTHONPATH":str(args.library_root)+os.pathsep+str(SKILL)})
    try:
        source_json = invoke(SKILL/"validate_figure.py",
            [ROOT/"plot_static_v450.py","--backend","python","--json"], qa/"source", env)
        source = json.loads(source_json)
        if not source["summary"]["ready"]:
            raise ValueError("Source preflight is not ready")
        dump(qa/"source.json", source)
        invoke(ROOT/"plot_static_v450.py", ["--out",exports,"--library-root",args.library_root],
               qa/"render", env)
        warnings = []
        for name in FIGURES:
            pdf = exports/(name+".pdf")
            text_audit = json.loads(invoke(SKILL/"audit_pdf_text.py",
                [pdf,"--min-pt","5","--json"],qa/(name+".font"),env))
            dump(qa/(name+".font.json"), text_audit)
            if not text_audit["auditable"] or text_audit["below_minimum_count"]:
                raise ValueError("PDF font audit blocks completion")
            collision = json.loads(invoke(SKILL/"audit_figure_collisions.py",
                [pdf,"--json","--json-out",qa/(name+".collision.json"),
                 "--overlay-pdf",qa/(name+".collision_overlay.pdf")],
                qa/(name+".collision"),env))
            if not collision["auditable"] or collision["summary"]["fail"]:
                raise ValueError("Collision audit blocks completion")
            warnings.extend({"figure":name,**f} for f in collision["findings"] if f["severity"]=="WARN")
        geometry = audit_geometry(exports, qa, args.library_root)
        dump(qa/"Geometry.json", geometry)
        readme = """# Required visual review

Automatic export and checks have finished. Visual review is PENDING.
Inspect each exported PNG, the full PDF previews and each panel at final physical size.
Check panel alignment, page-edge clipping, labels, positive/negative signs, baselines,
cohort counts, distinction between first attainment and proof, and legibility.
Review every retained collision/source warning explicitly. Do not call this delivery
visually passed until the human/agent inspection is recorded in a separate dated QA note.
Original data and failed render directories must remain unchanged.
"""
        (out/"VISUAL_REVIEW_REQUIRED.md").write_text(readme,encoding="utf-8")
        status = "AUTOMATED_PASS_VISUAL_PENDING"
        dump(out/"QA_Summary.json",{"status":status,"collision_warnings":warnings,
             "source_findings":source["findings"],"geometry":geometry,"visual_review":"PENDING"})
        dump(out/"Output_Manifest.json",{"status":status,"source_sha256":sha(__file__),
            "preparation_sha256":sha(ROOT/"Preparation_Manifest.json"),
            "inputs":prep["source_csvs"],
            "files":{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*"))
                     if p.is_file() and "_fontcache" not in p.parts}})
        dump(out/"PROCESS_COMPLETE.json",{"status":status,"figures":2,"visual_review":"PENDING",
                                          "solver_runs":0})
    except BaseException as exc:
        dump(out/"FAILURE.json",{"type":type(exc).__name__,"message":str(exc),
                                "traceback":traceback.format_exc()})
        raise

if __name__ == "__main__":
    main()

