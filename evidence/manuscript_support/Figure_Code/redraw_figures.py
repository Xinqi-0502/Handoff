"""Recreate the three manuscript figures from bundled unchanged CSVs.
Dependency: matplotlib and its normal dependencies. Run from any directory:
    python Figure_Code/redraw_figures.py --out Recreated_Figures
The destination must be fresh. No solver, simulator, private runtime,
original archive or external quality-audit package is imported.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,sys,traceback
from pathlib import Path
sys.dont_write_bytecode=True
PACKAGE=Path(__file__).resolve().parents[1]
DATA=PACKAGE/"Figure_Source_Data"
CAND="HZ_AWA_RADIUS_PAIR_GATED";BASE="HZ_AWA_RADIUS"
NAMES=("fig01_search_work_and_proof_time","fig02_anytime_timing_tradeoff","figS01_native_outcome_limits")
SIZES=((160,55),(160,45),(160,50))
def rows(name):
    with (DATA/name).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))
def check_panel_geometry(fig,path):
    """Check the unchanged comparable panel rectangles without external tools."""
    width,height=fig.get_size_inches()*72
    boxes=[(a.get_position().x0*width,a.get_position().y0*height,
            a.get_position().width*width,a.get_position().height*height) for a in fig.axes]
    status="NOT_APPLICABLE_SINGLE_PANEL"
    if len(boxes)==2:
        first,second=boxes
        for index in (1,2,3):
            if abs(first[index]-second[index])>1.5:
                raise AssertionError("Comparable panel geometry changed")
        if second[0]<=first[0]+first[2]:
            raise AssertionError("Overlapping plot rectangles")
        status="PASS"
    path.write_text(json.dumps({"status":status,"tolerance_pt":1.5,
        "plot_rectangles_pt":boxes},indent=2)+"\n",encoding="utf-8")


def require(x,msg):
    if not x:raise AssertionError(msg)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))

def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def one(rr,**keys):
    x=[r for r in rr if all(r[k]==str(v) for k,v in keys.items())];require(len(x)==1,("Unique row",keys));return x[0]

def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-10)

def data_check():
    for name, expected in load(DATA/"File_Hashes.json").items():
        require(sha(DATA/name)==expected,("Packaged CSV hash mismatch",name))
    d1=rows("fig01_points.csv");d2=rows("fig02_points.csv");dn=rows("figS01_points.csv")
    proof=rows("Directed_Proof_Pairs.csv");first=rows("Initial_Strata_First_Good_Pairs.csv")
    require(len(d1)==8 and len(d2)==4 and len(dn)==6,"Point row counts")
    for r in d1:
        source=one(proof,stratum="m",value=r["m"],candidate=CAND,baseline=BASE)
        metric="expanded" if r["panel"]=="a" else "time"
        require(int(r["eligible_cases"])==int(source["common_on_time_proved"]),"Scale cohort")
        require(int(r["available_cases"])==int(source["all_cases"])==64,"Scale planned denominator")
        require(close(r["candidate_sum"],source[f"candidate_{metric}_sum"]),"Candidate sum")
        require(close(r["baseline_sum"],source[f"baseline_{metric}_sum"]),"Baseline sum")
        require(close(r["relative_index_percent"],100*float(r["candidate_sum"])/float(r["baseline_sum"])),"Relative index")
    for r in d2:
        if r["endpoint"]=="proof":
            s=one(proof,stratum="all",value="all",candidate=CAND,baseline=BASE)
            c,b,n=s["candidate_time_sum"],s["baseline_time_sum"],s["common_on_time_proved"]
        else:
            s=one(first,stratum="all",value="all",candidate=CAND,baseline=BASE,fraction=r["gap_fraction"],initial_group="all")
            c,b,n=s["candidate_seconds"],s["baseline_seconds"],s["common_all3_reached"]
        require(int(r["eligible_cases"])==int(n),"Endpoint cohort")
        require(close(r["candidate_seconds_sum"],c) and close(r["baseline_seconds_sum"],b),"Endpoint sums")
        require(close(r["time_change_percent"],100*(float(c)/float(b)-1)),"Endpoint ratio")
    per=rows("native_per_case_points.csv");case=rows("Case_Budget_Results.csv")
    require(len(per)==384,"Native per-case coverage")
    for r in dn:
        x=[s for s in per if s["budget_ms"]==r["budget_ms"] and s["metric"]==r["metric"]]
        require(len(x)==64 and all(s["known"]=="True" for s in x),"Native full cohort")
        require(close(sum(float(s["paired_change_seconds"]) for s in x)/64,r["full64_mean_change_seconds"]),"Native mean")
        for field,letter in (("wins","W"),("ties","T"),("losses","L"),("unknown_pairs","U")):
            require(sum(s["result"]==letter for s in x)==int(r[field]),"Native WTLU")
    fallback={arm:sum(int(r["fallback_repetitions"]) for r in case if r["arm"]==arm and r["budget_ms"]=="10") for arm in ("HZ_AWA_PAIR_GATED",BASE)}
    require(fallback=={"HZ_AWA_PAIR_GATED":192,BASE:191},"10 ms fallback caption counts")
    return d1,d2,dn,{"status":"PASS","fig1_rows":8,"fig2_rows":4,"native_rows":6,"native_case_points":384,"fallback_10ms":fallback}

def render(out,d1,d2,dn):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.transforms import ScaledTranslation
    # Register available standard system Times faces; no fonts are distributed.
    windir=os.environ.get("WINDIR")
    if windir:
        for name in ("times.ttf","timesbd.ttf","timesi.ttf","timesbi.ttf"):
            candidate=Path(windir)/"Fonts"/name
            if candidate.is_file(): font_manager.fontManager.addfont(str(candidate))
    try:
        font=font_manager.findfont("Times New Roman",fallback_to_default=False)
        family="Times New Roman"
    except ValueError:
        family="DejaVu Serif"
        font=font_manager.findfont(family,fallback_to_default=False)
        print("Times New Roman unavailable: using DejaVu Serif; exact typography will differ.")
    plt.rcParams.update({"font.family":"serif","font.serif":[family],"font.size":9,
        "axes.labelsize":9,"xtick.labelsize":8.5,"ytick.labelsize":8.5,"axes.titlesize":9,
        "pdf.fonttype":42,"svg.fonttype":"none","axes.spines.top":False,"axes.spines.right":False,
        "axes.linewidth":.65,"xtick.major.width":.65,"ytick.major.width":.65,
        "figure.facecolor":"white","savefig.facecolor":"white"})
    def tag(ax,label,fig):
        ax.text(0,1,label,transform=ax.transAxes+ScaledTranslation(-12/72,5/72,fig.dpi_scale_trans),
                ha="left",va="bottom",fontsize=9,fontweight="bold")
    def save(fig,name,labels):
        fig.canvas.draw()
        check_panel_geometry(fig,out/(name+".alignment.json"))
        fig.savefig(out/(name+".pdf"));fig.savefig(out/(name+".svg"));fig.savefig(out/(name+".png"),dpi=300)
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(160/25.4,55/25.4),sharey=True)
    fig.subplots_adjust(left=.087,right=.985,bottom=.29,top=.87,wspace=.28)
    for ax,panel,title in zip(axes,("a","b"),("Expanded labels","Time to optimality proof")):
        rr=[r for r in d1 if r["panel"]==panel]
        vals=[float(r["relative_index_percent"]) for r in rr]
        ax.bar(range(4),vals,width=.55,color="#167D9A",zorder=2)
        ax.axhline(100,color="#666666",lw=.7,ls=(0,(4,3)),zorder=1)
        for x,v in enumerate(vals):
            ax.annotate(f"{v:.1f}",(x,v),xytext=(0,-3),textcoords="offset points",ha="center",va="top",color="white",fontsize=8.5)
        ax.set_ylim(0,115);ax.set_yticks([0,50,100]);ax.set_xlim(-.6,3.6)
        ax.set_xticks(range(4),[r["m"]+"\nn="+r["eligible_cases"]+"/64" for r in rr])
        ax.tick_params(axis="x",pad=2)
        ax.set_xlabel("Old orders, m",labelpad=2);ax.set_title(title,pad=5)
        tag(ax,panel,fig)
    axes[0].set_ylabel("Relative index (%)",labelpad=3)
    save(fig,NAMES[0],True)
    fig,ax=plt.subplots(figsize=(160/25.4,45/25.4))
    fig.subplots_adjust(left=.325,right=.96,bottom=.28,top=.96)
    vals=[float(r["time_change_percent"]) for r in d2]
    ax.barh(range(4),vals,height=.56,color=["#167D9A" if v<0 else "#B96B35" for v in vals],zorder=2)
    ax.axvline(0,color="#666666",lw=.7,zorder=1)
    labels=("First gap ≤5% (n=256)","First gap ≤10% (n=256)","First optimum (n=256)","Optimality proof (n=255)")
    ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.tick_params(axis="y",length=0,pad=5)
    ax.set_xlim(-36,12);ax.set_xticks([-30,-20,-10,0,10]);ax.set_xlabel("Aggregate time change (%)",labelpad=2)
    for i,v in enumerate(vals):
        ax.annotate(f"{v:+.2f}%",(v,i),xytext=(-3 if v<0 else 3,0),textcoords="offset points",
                    ha="right" if v<0 else "left",va="center",fontsize=8.5)
    save(fig,NAMES[1],False)
    fig,axes=plt.subplots(1,2,figsize=(160/25.4,50/25.4),sharey=True)
    fig.subplots_adjust(left=.087,right=.985,bottom=.25,top=.83,wspace=.28)
    for ax,metric,panel,title in zip(axes,("customer_flow_J","truck_handoff_wait"),("a","b"),("Customer-flow J","Truck handoff waiting")):
        rr=[r for r in dn if r["metric"]==metric]
        vals=[float(r["full64_mean_change_seconds"]) for r in rr]
        require(all(v==0 for v in vals),"Revisit zero-result display if source values change")
        ax.axhline(0,color="#666666",lw=.7,zorder=1)
        ax.plot(range(3),vals,"o",markersize=3.5,color="#666666",zorder=2)
        for i,r in enumerate(rr):
            ax.annotate("0.00",(i,0),xytext=(0,4),textcoords="offset points",ha="center",fontsize=8.5)
        ax.set_xlim(-.5,2.5);ax.set_ylim(-.016,.016);ax.set_yticks([-.01,0,.01])
        ax.set_xticks(range(3),[r["budget_ms"] for r in rr]);ax.set_xlabel("Planning budget (ms)",labelpad=2)
        ax.set_title(title,pad=12)
        ax.text(.5,1.015,"W/T/L/U = 0/64/0/0 at every budget",transform=ax.transAxes,ha="center",va="bottom",fontsize=8.5)
        tag(ax,panel,fig)
    axes[0].set_ylabel("Mean paired change (s)",labelpad=3)
    save(fig,NAMES[2],True)
    return {"font_family":family,"font_file_name":Path(font).name,"matplotlib_version":matplotlib.__version__,"size_mm":dict(zip(NAMES,SIZES)),"png_dpi":300}

def main():
    global DATA
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=PACKAGE/"Recreated_Figures")
    parser.add_argument("--data",type=Path,default=DATA)
    args=parser.parse_args()
    DATA=args.data.resolve()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    try:
        d1,d2,dn,check=data_check()
        dump(out/"Data_Check.json",check)
        meta=render(out,d1,d2,dn)
        dump(out/"Render_Report.json",{"status":"COMPLETE","figures":3,
            "metadata":meta,"solver_runs":0,"simulator_runs":0,
            "source_sha256":sha(__file__),
            "figure_point_csv_sha256":{n:sha(DATA/n) for n in
                ("fig01_points.csv","fig02_points.csv","figS01_points.csv")},
            "scope":"Redrawing summary data only; not raw-data analysis."})
        print(json.dumps({"status":"COMPLETE","output":str(out),"figures":3,"font":meta["font_family"]}))
    except BaseException:
        dump(out/"FAILURE.json",{"status":"FAIL","traceback":traceback.format_exc()})
        raise
if __name__=="__main__":main()

