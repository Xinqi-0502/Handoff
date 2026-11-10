"""Static-only preparation: copy existing evidence, parse source AST, freeze hashes."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
V450 = ROOT.parent
SKILL = Path(r"C:\Users\admin\.codex\skills\nature-figure\scripts")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")

def main():
    if (ROOT/"Preparation_Manifest.json").exists():
        raise RuntimeError("Preserve the existing preparation manifest")
    sources = ROOT/"source_data"
    sources.mkdir(exist_ok=False)
    audit = V450/"audit_code"/"results"/"main_01"
    cross = V450/"audit_code"/"results"/"crosscheck_01"
    primary = V450/"static_comparison"/"analysis"/"main_01"
    audit_manifest = json.loads((audit/"Manifest.json").read_text())
    source_csvs = []
    for name in ("Directed_Proof_Pairs.csv","Initial_Strata_First_Good_Pairs.csv"):
        origin = audit/name
        h = sha(origin)
        if audit_manifest["outputs"][str(origin)] != h:
            raise ValueError("Audit table hash differs from its original manifest")
        shutil.copyfile(origin, sources/name)
        source_csvs.append({"original_path":str(origin),"copy_path":"source_data/"+name,"sha256":h})
    copies = [
        (primary/"PROCESS_COMPLETE.json","primary_complete.json"),
        (audit/"PROCESS_COMPLETE.json","independent_complete.json"),
        (cross/"PROCESS_COMPLETE.json","crosscheck_complete.json"),
        (cross/"Crosscheck.json","Crosscheck.json"),
        (audit/"Manifest.json","Independent_Manifest.json"),
    ]
    receipts=[]
    for origin, name in copies:
        shutil.copyfile(origin,sources/name)
        if name != "Independent_Manifest.json":
            if json.loads((sources/name).read_text())["status"] != "PASS":
                raise ValueError("Evidence receipt is not PASS")
        receipts.append({"original_path":str(origin),"copy_path":"source_data/"+name,"sha256":sha(origin)})
    ast_checks = {}
    for name in ("plot_static_v450.py","render_and_audit_static_v450.py","prepare_static_figures.py"):
        path = ROOT/name
        ast.parse(path.read_text(encoding="utf-8-sig"),filename=str(path))
        ast_checks[name] = {"status":"PASS","sha256":sha(path)}
    pin_paths = [
        ROOT/"Figure_Contract.md",ROOT/"plot_static_v450.py",ROOT/"render_and_audit_static_v450.py",
        ROOT/"Render_Static_Figures_01.ps1",ROOT/"prepare_static_figures.py",
        ROOT/"nature_figure_config.json",
        *sorted(p for p in sources.iterdir() if p.is_file()),
        *(SKILL/n for n in ("validate_figure.py","audit_pdf_text.py","audit_figure_collisions.py",
                           "audit_panel_alignment.py","nature_figure_backend.py")),
    ]
    manifest = {"status":"PREPARED_AST_ONLY","backend":"python","rendered":False,
        "solver_runs":0,"ast_checks":ast_checks,"source_csvs":source_csvs,"receipts":receipts,
        "pinned_files":[{"path":str(p),"sha256":sha(p)} for p in pin_paths],
        "runtime":r"E:\CodexResearch-xi\workspace\research_outputs\ICTEC2027_Analysis_Figures_Extended_20261106\_Plot_Runtime",
        "execution":"Run Render_Static_Figures_01.ps1 only after the serial workload window opens.",
        "visual_qa":"PENDING; no output images exist from this preparation"}
    dump(ROOT/"Preparation_Manifest.json",manifest)
    print(json.dumps({"status":"PREPARED_AST_ONLY","ast":ast_checks,
                      "manifest_sha256":sha(ROOT/"Preparation_Manifest.json")},indent=2))

if __name__ == "__main__":
    main()

