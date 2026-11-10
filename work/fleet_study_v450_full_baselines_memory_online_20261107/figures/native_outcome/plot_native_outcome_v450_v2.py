"""Full64 native-outcome figure. No solver/SUMO imports. Explicit execution gate."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,shutil,subprocess,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SKILL=Path(r"C:\Users\admin\.codex\skills\nature-figure\scripts")
RUNTIME=Path(r"E:\CodexResearch-xi\workspace\research_outputs\ICTEC2027_Analysis_Figures_Extended_20261106\_Plot_Runtime")
CAND="HZ_AWA_PAIR_GATED";BASE="HZ_AWA_RADIUS";BUDGETS=(10,50,200);EPS=1e-6
NAME="Fig3_Native_Outcomes"
FILES=("Case_Budget_Results.csv","Pair_Cases.csv","Pair_Summary.csv")
def require(test,reason):
    if not test:raise AssertionError(reason)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def csvread(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def csvwrite(p,rows):
    with Path(p).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
def num(r,k):
    if r[k]=="":return None
    v=float(r[k]);require(math.isfinite(v),"Nonfinite table field");return v
def flag(r,k):
    require(r[k] in ("True","False"),"Unknown boolean");return r[k]=="True"
def sign(x):return -1 if x<-EPS else 1 if x>EPS else 0
def equal(x,y):return (x is y) if x is None or y is None else abs(x-y)<=EPS
def unique(rows,**fields):
    found=[r for r in rows if all(r[k]==str(v) for k,v in fields.items())]
    require(len(found)==1,("Expected unique source row",fields));return found[0]

def evidence(analysis,expected_summary):
    prep=load(ROOT/"Preparation_Manifest_v2.json")
    for path,h in prep["source_hashes"].items():require(sha(path)==h,("Prepared source changed",path))
    require(sha(analysis/"SUMMARY.json")==expected_summary.lower(),"Independent audit summary SHA mismatch")
    done=load(analysis/"PROCESS_COMPLETE.json");summary=load(analysis/"SUMMARY.json")
    require(done["status"]=="PASS" and done["summary_sha256"]==sha(analysis/"SUMMARY.json"),"Independent audit completion")
    require(not (analysis/"FAILURE.json").exists(),"Independent audit failure marker")
    require(summary["status"]=="PASS" and summary["cases"]==64 and summary["mothers"]==8 and summary["policy_calls"]==1728,"Require full64, reject pilot")
    require(summary["source_sha256"]==prep["audit_source_sha256"],"Audited schema source changed")
    require(summary["raw_results_changed"] is False,"Audit altered raw records")
    return summary,prep

def points(analysis):
    cases=csvread(analysis/FILES[0]);pairs=csvread(analysis/FILES[1]);sums=csvread(analysis/FILES[2])
    selected=[r for r in cases if r["arm"] in (CAND,BASE)]
    expected_cases={r["case"] for r in selected};require(len(expected_cases)==64,"Expected 64 case identities")
    require(len(selected)==64*2*3,"Case/arm/budget coverage")
    require(len({(r["case"],r["arm"],int(r["budget_ms"])) for r in selected})==384,"Duplicate case row")
    seeds={r["seed"] for r in selected};require(len(seeds)==8,"Mother count")
    for seed in seeds:
        sub=[r for r in selected if r["seed"]==seed]
        require(len({r["case"] for r in sub})==8,"Eight conditions per mother")
        require({(int(r["offset"]),int(r["people"]),int(r["slow"])) for r in sub}
                =={(o,p,s) for o in (0,24) for p in (0,10) for s in (0,2)},"Prespecified conditions")
    casepoints=[];plotpoints=[]
    for ms in BUDGETS:
        pp=[r for r in pairs if r["left"]==CAND and r["right"]==BASE and int(r["budget_ms"])==ms]
        require(len(pp)==64 and {r["case"] for r in pp}==expected_cases,"Paired case coverage")
        for r in pp:
            c=unique(selected,case=r["case"],arm=CAND,budget_ms=ms)
            b=unique(selected,case=r["case"],arm=BASE,budget_ms=ms)
            require(int(c["policy_repetitions"])==int(b["policy_repetitions"])==3,"Technical policy repetition scope")
            require(c["seed"]==b["seed"]==r["seed"],"Pair mother identity")
            known=flag(c,"complete_representative_replays") and flag(b,"complete_representative_replays")
            require(flag(r,"actual_pair_known")==known,"Physical coverage differs")
            for metric,key,delta_key in (
                ("customer_flow_J","policy_frequency_weighted_representative_replay_J","actual_delta"),
                ("truck_handoff_wait","weighted_truck_handoff_wait","weighted_truck_handoff_wait_delta")):
                cv,bv=num(c,key),num(b,key)
                require((cv is not None and bv is not None)==known,"Partial representatives were renormalized")
                delta=cv-bv if known else None
                require(equal(delta,num(r,delta_key)),"Pair difference mismatch")
                if metric=="customer_flow_J":
                    require(equal(cv,num(r,"left_actual_J")) and equal(bv,num(r,"right_actual_J")),"Pair outcome mismatch")
                    for x in (c,b):
                        j=num(x,key)
                        if j is not None:
                            require(equal(j,sum(num(x,k) for k in ("weighted_old_flow","weighted_new_a_flow","weighted_new_b_flow"))),"J decomposition")
                casepoints.append(dict(case=r["case"],seed=r["seed"],budget_ms=ms,metric=metric,
                    candidate=CAND,baseline=BASE,candidate_seconds=cv,baseline_seconds=bv,
                    paired_change_seconds=delta,known=known,result="U" if not known else ("W" if sign(delta)<0 else "L" if sign(delta)>0 else "T")))
        summary=unique(sums,stratum="ALL",budget_ms=ms,left=CAND,right=BASE)
        require(int(summary["planned_scenarios"])==64 and int(summary["mothers"])==8,"Summary denominator")
        for metric in ("customer_flow_J","truck_handoff_wait"):
            group=[r for r in casepoints if r["budget_ms"]==ms and r["metric"]==metric]
            known=[r for r in group if r["known"]]
            counts={k:sum(r["result"]==k for r in group) for k in ("W","T","L","U")}
            if metric=="customer_flow_J":
                require(int(summary["actual_known_pairs"])==len(known) and int(summary["actual_unknown_pairs"])==counts["U"],"Summary coverage")
                require([int(summary[k]) for k in ("actual_wins","actual_ties","actual_losses")]
                        ==[counts[k] for k in ("W","T","L")],"Summary W/T/L")
                km=sum(r["paired_change_seconds"] for r in known)/len(known) if known else None
                require(equal(km,num(summary,"mean_actual_delta")),"Audit mean mismatch")
            mean=sum(r["paired_change_seconds"] for r in group)/64 if len(known)==64 else None
            plotpoints.append(dict(budget_ms=ms,metric=metric,candidate=CAND,baseline=BASE,
                planned_cases=64,independent_mothers=8,known_pairs=len(known),unknown_pairs=counts["U"],
                wins=counts["W"],ties=counts["T"],losses=counts["L"],
                full64_mean_change_seconds=mean,
                mean_definition="sum of 64 matched representative-replay differences / 64; NA if any pair unknown"))
    return casepoints,plotpoints

def draw(data,out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.transforms import ScaledTranslation
    from audit_panel_alignment import require_matplotlib_panel_alignment
    plt.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial","DejaVu Sans"],"font.size":8,
        "axes.labelsize":8,"xtick.labelsize":7,"ytick.labelsize":8,"pdf.fonttype":42,"svg.fonttype":"none",
        "axes.spines.top":False,"axes.spines.right":False,"axes.linewidth":.7,
        "figure.facecolor":"white","savefig.facecolor":"white"})
    fig,axes=plt.subplots(1,2,figsize=(183/25.4,115/25.4))
    fig.subplots_adjust(left=.11,right=.97,bottom=.30,top=.74,wspace=.33)
    fig.suptitle("Native outcomes under three planning budgets",fontsize=10,fontweight="bold",y=.96)
    fig.text(.5,.89,"Same AWA* engine | Shared-quota gate minus RADIUS alone",ha="center",fontsize=8)
    fig.text(.5,.837,"10 ms mainly executes a late common-initial-plan fallback",ha="center",fontsize=7.5)
    for ax,metric,panel,title in zip(axes,("customer_flow_J","truck_handoff_wait"),("a","b"),
                                    ("Customer-flow J","Truck handoff waiting")):
        rr=[r for r in data if r["metric"]==metric];values=[r["full64_mean_change_seconds"] for r in rr]
        bound=max([abs(v) for v in values if v is not None]+[.01])*1.6
        ax.set_ylim(-bound,bound)
        ax.axhline(0,color="#707070",lw=.8,zorder=1)
        for x,v in enumerate(values):
            if v is None:
                ax.text(x,.20*bound,"NA",ha="center",va="center",fontsize=8)
            elif sign(v)==0:
                ax.plot(x,0,marker="o",markersize=4,color="#707070",zorder=3)
                ax.annotate("0.00",(x,0),xytext=(0,5),textcoords="offset points",ha="center",fontsize=8)
            else:
                ax.bar(x,v,width=.5,color="#167D9A" if v<0 else "#B96B35",zorder=3)
                ax.annotate(f"{v:+.3g}",(x,v),xytext=(0,5 if v>0 else -5),textcoords="offset points",
                            ha="center",va="bottom" if v>0 else "top",fontsize=8)
        ax.set_xlim(-.6,2.6);ax.set_xticks(range(3),[
            str(r["budget_ms"])+" ms\nW / T / L / U\n"+"/".join(str(r[k]) for k in ("wins","ties","losses","unknown_pairs")) for r in rr])
        ax.set_title(title,fontsize=9,pad=13);ax.set_ylabel("Mean paired change (s)")
        ax.text(0,1,panel,transform=ax.transAxes+ScaledTranslation(-19/72,11/72,fig.dpi_scale_trans),
                fontsize=8,fontweight="bold",ha="left",va="bottom")
    fig.text(.11,.14,"64 planned scenarios at every budget; 8 independent mothers. Negative is lower.",fontsize=7)
    fig.text(.11,.085,"W/T/L/U: lower / tied / higher / unknown. Full-64 mean is NA if any pair is unknown.",fontsize=7)
    fig.text(.11,.035,"Policy-frequency-weighted representative native replay; single decision epoch.",fontsize=7)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=out/(NAME+".alignment.json"),overlay_svg=out/(NAME+".alignment.svg"),
        tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True)
    fig.savefig(out/(NAME+".pdf"));fig.savefig(out/(NAME+".svg"));fig.savefig(out/(NAME+".png"),dpi=600)
    plt.close(fig)

CAPTION="""# Native-outcome figure caption

**Realized outcomes for the same AWA* engine with and without the shared-quota gate.**
Panel a reports customer-flow J (the sum of completion-minus-release durations over customers); panel b reports truck handoff waiting at the hub, excluding the two transfer services. Values are candidate minus baseline, averaged over all 64 matched scenarios. Negative changes mean lower outcomes. Each budget (10, 50, 200 ms) retains the same prespecified 64 scenarios and eight independent mothers, with eight related offset/pedestrian/slow-vehicle conditions per mother. No confidence interval is inferred from the 64 related conditions.

Each case-level outcome is the existing audit's policy-frequency-weighted representative native replay: selected representative plan/activation outcomes are weighted by the number of the three policy repetitions they represent, divided by three. It is not an average of three independent native replications. Planning latency and the existing activation quantization remain charged to execution. The plotted physical quantities are distinct from within-deadline forecast quality and from proving the forecast optimum.

**Deadline interpretation at 10 ms.** The shared-quota-gated arm had NO_PLAN_BY_DEADLINE in 192/192 policy repetitions, and RADIUS alone in 191/192. These calls executed the late common-initial-plan fallback. Thus the 10 ms physical outcome mainly reflects this late fallback, not a plan produced within 10 ms. The recorded planning latency and activation timing remain included in the physical replay.

W/T/L/U counts use lower/tied/higher/unknown paired outcomes, with a 1e-6 second equality tolerance matching the independent audit. Any missing or failed representative makes its full case/arm physical aggregate unknown. If any pair is unknown, the full-64 mean for that budget is withheld as NA; unknown outcomes remain in the count denominator. No survivor, winner, same-plan, or completed-proof subset is substituted for all scenarios.

This evidence concerns a single frozen dispatch epoch in a synthetic SUMO network. Truck handoff waiting is distinct from SUMO waitingTime, general congestion delay and dispatch activation latency. The figure does not establish continuous rolling dispatch, calibration of the delivery network, real-world safety, or independent replication across 64 networks. No numerical values were selected using pilot gains. All three budgets and all unfavorable effects are retained.
"""
def command(script,args,log,env):
    result=subprocess.run([sys.executable,"-B","-X","utf8",str(script),*map(str,args)],env=env,cwd=ROOT,
                          capture_output=True,text=True,encoding="utf-8",timeout=180)
    Path(str(log)+".stdout.txt").write_text(result.stdout,encoding="utf-8")
    Path(str(log)+".stderr.txt").write_text(result.stderr,encoding="utf-8")
    require(result.returncode==0,("Retained QA failure",str(log),result.returncode))
    return json.loads(result.stdout)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analysis",type=Path,required=True);ap.add_argument("--summary-sha256",required=True)
    ap.add_argument("--out",type=Path,required=True);ap.add_argument("--execute",action="store_true");a=ap.parse_args()
    if not a.execute:raise SystemExit("Prepared only; full64 audit PASS and a released window are required.")
    summary,prep=evidence(a.analysis,a.summary_sha256)
    out=a.out.resolve();require(out.drive.upper()=="E:","E-only output");out.mkdir(parents=True,exist_ok=False)
    try:
        os.environ.update(TEMP=r"E:\CodexResearch-xi\temp",TMP=r"E:\CodexResearch-xi\temp",
            PYTHONDONTWRITEBYTECODE="1",MPLCONFIGDIR=str(out/"_fontcache"),PYTHONPATH=str(RUNTIME)+os.pathsep+str(SKILL))
        sys.path[:0]=[str(RUNTIME),str(SKILL)];env=dict(os.environ)
        qa=out/"qa";qa.mkdir();source=out/"source_data";source.mkdir()
        inputs={}
        for name in (*FILES,"SUMMARY.json","PROCESS_COMPLETE.json","Audit_Source_Hashes.json"):
            shutil.copyfile(a.analysis/name,source/name);inputs[name]=dict(original=str((a.analysis/name).resolve()),sha256=sha(source/name))
        preflight=command(SKILL/"validate_figure.py",[Path(__file__),"--backend","python","--json"],qa/"source",env)
        dump(qa/"source.json",preflight);require(preflight["summary"]["ready"],"Source preflight")
        fallback={}
        for arm in (CAND,BASE):
            rr=[r for r in csvread(source/FILES[0]) if r["arm"]==arm and int(r["budget_ms"])==10]
            fallback[arm]={"case_count":len(rr),"policy_repetitions":sum(int(r["policy_repetitions"]) for r in rr),
                           "no_plan_by_deadline":sum(int(r["fallback_repetitions"]) for r in rr)}
        require(fallback[CAND]=={"case_count":64,"policy_repetitions":192,"no_plan_by_deadline":192},"10 ms candidate annotation source changed")
        require(fallback[BASE]=={"case_count":64,"policy_repetitions":192,"no_plan_by_deadline":191},"10 ms baseline annotation source changed")
        dump(out/"Deadline_Interpretation.json",{"budget_ms":10,"counts":fallback,
             "meaning":"Primarily executes late common-initial-plan fallback; not a 10 ms on-time plan claim."})
        casepoints,plotpoints=points(source)
        csvwrite(out/"Native_Per_Case_Points.csv",casepoints);csvwrite(out/"Native_Plotted_Points.csv",plotpoints)
        draw(plotpoints,out);(out/"Caption.md").write_text(CAPTION,encoding="utf-8")
        font=command(SKILL/"audit_pdf_text.py",[out/(NAME+".pdf"),"--min-pt","5","--json"],qa/"font",env)
        dump(qa/"font.json",font);require(font["auditable"] and font["below_minimum_count"]==0,"Font QA")
        collision=command(SKILL/"audit_figure_collisions.py",[out/(NAME+".pdf"),"--json",
            "--json-out",qa/"collision.json","--overlay-pdf",qa/"collision_overlay.pdf"],qa/"collision",env)
        require(collision["auditable"] and collision["summary"]["fail"]==0,"Collision QA")
        import fitz
        from PIL import Image,ImageChops
        with fitz.open(out/(NAME+".pdf")) as doc:
            require(len(doc)==1,"PDF page count");page=doc[0]
            require(abs(page.rect.width-183/25.4*72)<.2 and abs(page.rect.height-115/25.4*72)<.2,"Physical dimensions")
            page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(qa/"pdf_preview.png")
        with Image.open(out/(NAME+".png")) as im:
            require(all(abs(x-y)<2 for x,y in zip(im.size,(183/25.4*600,115/25.4*600))),"PNG dimensions")
            box=ImageChops.difference(im.convert("RGB"),Image.new("RGB",im.size,"white")).getbbox()
            require(box and min(box[0],box[1],im.width-box[2],im.height-box[3])>4,"Canvas-edge clipping")
        require("<text" in (out/(NAME+".svg")).read_text(encoding="utf-8"),"Editable SVG")
        for name,item in inputs.items():require(sha(a.analysis/name)==item["sha256"],"Analysis changed during render")
        dump(out/"QA_Summary.json",dict(status="AUTOMATED_PASS_VISUAL_PENDING",font_min_pt=font["minimum_found_pt"],
            collision_findings=collision["findings"],source_findings=preflight["findings"],visual_inspection="PENDING"))
        dump(out/"Output_Manifest.json",dict(status="AUTOMATED_PASS_VISUAL_PENDING",source_sha256=sha(__file__),
            preparation_sha256=sha(ROOT/"Preparation_Manifest_v2.json"),input_evidence=inputs,
            outputs={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob("*")) if p.is_file() and "_fontcache" not in p.parts}))
        dump(out/"PROCESS_COMPLETE.json",dict(status="AUTOMATED_PASS_VISUAL_PENDING",cases=64,mothers=8,solver_runs=0))
    except BaseException:
        dump(out/"FAILURE.json",dict(status="FAIL",error=traceback.format_exc()));raise
if __name__=="__main__":main()

