"""Prepare scientific figures from V449 analysis CSV files only.
No solver import. No pyplot import until main() is explicitly executed.
"""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,math,os,statistics,subprocess,sys,traceback
P=Path(__file__).resolve().parent
METHODS=('RADIUS','RADIUS_PAIR_EAGER','RADIUS_PAIR_LAZY','RADIUS_AWA','RADIUS_PAIR_AWA','RADIUS_PAIR_AWA_GATED','NO_BOUND','DP_ADAPTER','ROUTE')
DISPLAY={'RADIUS':'Radius','RADIUS_PAIR_EAGER':'Radius + Pair (eager)','RADIUS_PAIR_LAZY':'Radius + Pair (lazy)','RADIUS_AWA':'Radius + AWA','RADIUS_PAIR_AWA':'Radius + Pair + AWA','RADIUS_PAIR_AWA_GATED':'Radius + Pair gate + AWA','NO_BOUND':'No bound','DP_ADAPTER':'Topological DP','ROUTE':'Exact Route'}
CANDIDATES=('RADIUS_PAIR_LAZY','RADIUS_PAIR_AWA','RADIUS_PAIR_AWA_GATED')
BASELINES=('RADIUS','RADIUS_AWA','DP_ADAPTER','ROUTE')
STRATA=('ALL','m6','m8','m10','m12')
SCALES=(6,8,10,12)
BUDGETS=(100,500,1000)
INPUT_FILES=('Case_Work_And_Proof.csv','Quality_Summary.csv','Pair_Time_Summary.csv')
SKILL=Path(r'C:\Users\admin\.codex\skills\nature-figure\scripts')

def require(ok,why):
    if not ok:raise AssertionError(why)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_csv(p):
    with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def number(v):
    if v in ('',None):return None
    x=float(v);require(math.isfinite(x),'non-finite CSV number');return x
def integer(v):
    x=number(v);require(x is not None and x.is_integer(),'integer CSV field');return int(x)
def boolean(v):
    if v in ('',None):return None
    require(v in ('True','False'),'boolean CSV field');return v=='True'
def div(a,b):return None if a is None or b is None or b==0 else a/b
def close(a,b):return a is None and b is None or a is not None and b is not None and math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7)
def csvwrite(p,rows):
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def inputs(folder):
    tables={name:read_csv(folder/name) for name in INPUT_FILES}
    rows=tables['Case_Work_And_Proof.csv'];keys=set();bycase={}
    require(len(rows)==3600,'Expected 400 cases x 9 methods')
    for r in rows:
        key=(r['case'],r['method']);require(key not in keys and r['method'] in METHODS,'case/method identity');keys.add(key)
        require(integer(r['planned_repeats'])==3 and sum(integer(r[k]) for k in ('ok','hard_timeouts','missing'))==3,'repeat accounting')
        require(boolean(r['all3_on_time_certified'])==(integer(r['on_time_certificates'])==3),'proof flag')
        bycase.setdefault(r['case'],[]).append(r)
    require(len(bycase)==400 and all(len(rs)==9 for rs in bycase.values()),'full 400-case coverage')
    representatives=[rs[0] for rs in bycase.values()]
    require(len({r['seed'] for r in representatives})==100,'100 independent mothers')
    require(Counter(integer(r['m']) for r in representatives)=={6:100,8:100,10:100,12:100},'four frozen scales')
    cm={(r['case'],r['method']):r for r in rows}
    return tables,rows,representatives,cm

def quality_data(tables):
    q={};source=[]
    for r in tables['Quality_Summary.csv']:
        key=(r['stratum'],r['method'],integer(r['ms']));require(key not in q,'duplicate quality summary');q[key]=r
    for m in SCALES:
        for method in METHODS:
            for ms in BUDGETS:
                r=q[(f'm{m}',method,ms)];n=integer(r['scenarios']);known=integer(r['known_oracle_cases'])
                hits=integer(r['all3_optimal']);available=integer(r['all3_feasible']);rn=integer(r['relative_regret_n'])
                require(n==100 and integer(r['independent_mothers'])==25 and 0<=hits<=min(available,known)<=n,'quality count bounds')
                value=number(r['relative_regret_median']);require((rn==0)==(value is None),'quality NA count')
                require(value is None or value>=0,'negative regret')
                source.append(dict(m=m,method=method,deadline_ms=ms,scenarios=n,independent_mothers=25,known_oracle_cases=known,
                    all3_feasible=available,all3_optimal=hits,optimal_coverage_percent=None if known==0 else 100*hits/n,
                    relative_regret_case_count=rn,relative_regret_percent=None if value is None else 100*value))
    return source

def proof_data(tables,reps,cm):
    indexed={}
    for r in tables['Pair_Time_Summary.csv']:
        key=(r['stratum'],r['left'],r['right'],r['target']);require(key not in indexed,'duplicate paired summary');indexed[key]=r
    source=[]
    for candidate in CANDIDATES:
        for baseline in BASELINES:
            for st in STRATA:
                reverse=(st,candidate,baseline,'proof') not in indexed
                key=(st,baseline,candidate,'proof') if reverse else (st,candidate,baseline,'proof')
                r=indexed[key];cs='right' if reverse else 'left';bs='left' if reverse else 'right'
                population=[x for x in reps if st=='ALL' or 'm'+x['m']==st];n=len(population)
                eligible=[x for x in population if boolean(cm[x['case'],candidate]['all3_on_time_certified']) and boolean(cm[x['case'],baseline]['all3_on_time_certified'])]
                require(integer(r['scenarios'])==n== (400 if st=='ALL' else 100) and integer(r['both_all3_on_time'])==len(eligible),'conditional denominator')
                cv=number(r[cs+'_seconds_sum']);bv=number(r[bs+'_seconds_sum']);ratio=div(cv,bv)
                ce=number(r[cs+'_expansion_sum']);be=number(r[bs+'_expansion_sum'])
                require(integer(r['expansion_pairs'])==len(eligible),'common expansion denominator')
                computed_c=sum(number(cm[x['case'],candidate]['elapsed_seconds']) for x in eligible) if eligible else None
                computed_b=sum(number(cm[x['case'],baseline]['elapsed_seconds']) for x in eligible) if eligible else None
                require(close(cv,computed_c) and close(bv,computed_b),'paired elapsed sums')
                computed_ce=sum(number(cm[x['case'],candidate]['expanded']) for x in eligible) if eligible else None
                computed_be=sum(number(cm[x['case'],baseline]['expanded']) for x in eligible) if eligible else None
                require(close(ce,computed_ce) and close(be,computed_be),'paired expansion sums')
                require(integer(r['common_mothers'])==len({x['seed'] for x in eligible}),'common mother count')
                source.append(dict(candidate=candidate,baseline=baseline,stratum=st,scenarios=n,eligible_cases=len(eligible),common_mothers=integer(r['common_mothers']),
                    candidate_only_cases=integer(r[cs+'_only']),baseline_only_cases=integer(r[bs+'_only']),neither_cases=integer(r['neither']),
                    candidate_seconds_sum=cv,baseline_seconds_sum=bv,time_ratio=ratio,candidate_expanded_sum=ce,baseline_expanded_sum=be,expanded_ratio=div(ce,be),
                    candidate_initial_optimal_in_common=integer(r[cs+'_initial_target_all3_in_common']),baseline_initial_optimal_in_common=integer(r[bs+'_initial_target_all3_in_common'])))
    return source

def mechanism_data(rows):
    source=[]
    for r in rows:
        ontime=boolean(r['all3_on_time_certified']);end=integer(r['end_certificates']);ok=integer(r['ok'])
        require(not ontime or end==3 and ok==3,'proof category')
        category='On-time proof' if ontime else 'Unavailable repeat' if ok<3 else 'Late proof' if end==3 else 'Not proved'
        d={k:r[k] for k in ('case','seed','m','Q','capacity_regime','signal','method')}
        d.update(proof_category=category,planned_repeats=3,ok=ok,hard_timeouts=integer(r['hard_timeouts']),missing=integer(r['missing']),
            expanded=number(r['expanded']),expanded_phase0=number(r['expanded_phase0']),expanded_phase1=number(r['expanded_phase1']),
            joint_checks_at_pop=number(r['joint_checks_at_pop']),joint_pruned_at_pop=number(r['joint_pruned_at_pop']),
            elapsed_seconds=number(r['elapsed_seconds']),initial_H2=number(r['initial_H2']))
        source.append(d)
    return source

def panel_label(ax,letter):
    ax.annotate(letter,xy=(0,1),xycoords='axes fraction',xytext=(-14,9),textcoords='offset points',ha='left',va='bottom',weight='bold',fontsize=10)

def save(fig,name,out,exclude_axes=()):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=out/(name+'.alignment.json'),overlay_svg=out/(name+'.alignment.svg'),tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True,exclude_axes=list(exclude_axes))
    fig.savefig(out/(name+'.pdf'),format='pdf')
    fig.savefig(out/(name+'.png'),format='png',dpi=300)
    plt.close(fig)
    audits=[]
    commands=(('text',[sys.executable,'-B',str(SKILL/'audit_pdf_text.py'),str(out/(name+'.pdf')),'--min-pt','5','--json']),
        ('collision',[sys.executable,'-B',str(SKILL/'audit_figure_collisions.py'),str(out/(name+'.pdf')),'--json-out',str(out/(name+'.collision.json')),'--overlay-pdf',str(out/(name+'.collision.pdf'))]))
    for kind,cmd in commands:
        result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',check=False)
        (out/(name+'.'+kind+'-audit.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        audits.append(dict(kind=kind,returncode=result.returncode))
        require(result.returncode==0,('Rendered audit blocked delivery',name,kind,result.returncode))
    return audits

def figure_quality(data,out):
    fig,axes=plt.subplots(2,4,figsize=(12.6,8.8),sharey=True)
    fig.subplots_adjust(left=.205,right=.91,bottom=.085,top=.94,wspace=.18,hspace=.27)
    index={(r['m'],r['method'],r['deadline_ms']):r for r in data}
    regret=[r['relative_regret_percent'] for r in data if r['relative_regret_percent'] is not None]
    vmax=max([1.0]+regret)
    blue=plt.get_cmap('Blues').copy();blue.set_bad('#eeeeee')
    orange=plt.get_cmap('YlOrBr').copy();orange.set_bad('#eeeeee')
    topimage=bottomimage=None
    for col,m in enumerate(SCALES):
        for row in (0,1):
            ax=axes[row,col];metric='optimal_coverage_percent' if row==0 else 'relative_regret_percent'
            values=np.array([[np.nan if index[m,method,ms][metric] is None else index[m,method,ms][metric] for ms in BUDGETS] for method in METHODS])
            im=ax.imshow(np.ma.masked_invalid(values),aspect='auto',vmin=0,vmax=100 if row==0 else vmax,cmap=blue if row==0 else orange)
            if row==0:topimage=im
            else:bottomimage=im
            ax.set_xticks(range(3),[str(x) for x in BUDGETS]);ax.set_yticks(range(9),[DISPLAY[x] for x in METHODS])
            ax.tick_params(axis='both',length=0,labelsize=8);ax.tick_params(labelleft=col==0)
            ax.set_xlabel('Deadline (ms)',fontsize=8.5)
            if row==0:ax.set_title(f'm = {m} | 25 networks',fontsize=9,pad=12)
            else:ax.set_title(f'm = {m} | 100 paired scenarios',fontsize=9,pad=12)
            panel_label(ax,chr(97+row*4+col))
            for yi,method in enumerate(METHODS):
                for xi,ms in enumerate(BUDGETS):
                    r=index[m,method,ms];v=r[metric]
                    if row==0:label='NA' if v is None else f"{r['all3_optimal']}/100"
                    else:label='NA\n0/100' if v is None else f"{v:.1f}%\n{r['relative_regret_case_count']}/100"
                    white=v is not None and v>(60 if row==0 else .65*vmax)
                    ax.text(xi,yi,label,ha='center',va='center',fontsize=7.5,color='white' if white else '#222222')
    ca=fig.add_axes([.935,.565,.014,.35]);cb=fig.add_axes([.935,.095,.014,.35])
    fig.colorbar(topimage,cax=ca).set_label('All-three optimal coverage (%)',fontsize=8)
    fig.colorbar(bottomimage,cax=cb).set_label('Median relative regret (%)',fontsize=8)
    fig.text(.205,.012,'Top: optimal in all 3 repeats / 100 planned scenarios. Bottom: case-median regret; cell n = available cases with known optimum.',fontsize=8)
    return save(fig,'Figure_01_Budget_Quality',out,exclude_axes=(ca,cb))

def figure_proof(data,out):
    fig,axes=plt.subplots(1,3,figsize=(13.3,9.2),sharey=True)
    fig.subplots_adjust(left=.205,right=.90,bottom=.10,top=.92,wspace=.88)
    index={(r['candidate'],r['baseline'],r['stratum']):r for r in data}
    positives=[r['time_ratio'] for r in data if r['time_ratio'] is not None and r['time_ratio']>0]
    lo=min([.75]+positives)*.8;hi=max([1.25]+positives)*1.25
    labels=[DISPLAY[b]+' / '+('all' if st=='ALL' else st) for b in BASELINES for st in STRATA]
    colors=('#2878A5','#7356A0','#B56E26')
    for col,candidate in enumerate(CANDIDATES):
        ax=axes[col];ax.set_xscale('log');ax.set_xlim(lo,hi);ax.set_ylim(19.7,-.7)
        ax.axvline(1,color='#777777',lw=.8,ls='--',zorder=0)
        for y,(baseline,st) in enumerate((b,st) for b in BASELINES for st in STRATA):
            r=index[candidate,baseline,st];value=r['time_ratio'];n=r['eligible_cases'];N=r['scenarios']
            if value is not None and value>0:ax.plot(value,y,'o',ms=4.8,color=colors[col])
            value_text='NA' if value is None else f'{value:.2f}'
            ax.text(1.025,y,f'{value_text} | {n}/{N}',transform=ax.get_yaxis_transform(),ha='left',va='center',fontsize=7.7,clip_on=False)
        for edge in (4.5,9.5,14.5):ax.axhline(edge,lw=.55,color='#dddddd',zorder=0)
        ax.set_yticks(range(20),labels);ax.tick_params(axis='y',length=0,labelleft=col==0,labelsize=8)
        ax.xaxis.set_major_locator(mpl.ticker.LogLocator(base=10,subs=(1,2,5),numticks=6))
        ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda x,pos:f'{x:g}'))
        ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
        ax.set_xlabel('Candidate / baseline proof time',fontsize=8.5)
        ax.set_title(DISPLAY[candidate],fontsize=9,pad=20)
        ax.text(1.025,1.015,'Ratio | cases',transform=ax.transAxes,fontsize=7.7,ha='left',va='bottom')
        panel_label(ax,chr(97+col))
    fig.text(.205,.035,'Each ratio uses the same cases where BOTH methods proved optimal within 1 s in ALL 3 repeats. Ratio < 1 favors the candidate.',fontsize=8)
    fig.text(.205,.015,'Displayed n/N is the conditional scenario denominator. No uncertainty interval is implied; paired conditions are not independent networks.',fontsize=8)
    return save(fig,'Figure_02_Conditional_Proof_Cost',out)

def figure_mechanism(data,out):
    fig,axes=plt.subplots(2,2,figsize=(12.6,8.8))
    fig.subplots_adjust(left=.205,right=.92,bottom=.105,top=.94,wspace=.48,hspace=.30)
    categories=('On-time proof','Late proof','Not proved','Unavailable repeat')
    colors=('#3B78A6','#D8A657','#B9BEC4','#eeeeee')
    ax=axes[0,0]
    for i,method in enumerate(METHODS):
        rs=[r for r in data if r['method']==method];require(len(rs)==400,'mechanism denominator')
        counts=Counter(r['proof_category'] for r in rs);left=0
        for j,cat in enumerate(categories):
            value=counts[cat]
            ax.barh(i,value,left=left,color=colors[j],height=.68,edgecolor='white',linewidth=.5,hatch='//' if j==3 else None,label=cat if i==0 else None)
            left+=value
        ax.text(1.025,i,f"{counts['On-time proof']}/400",transform=ax.get_yaxis_transform(),ha='left',va='center',fontsize=7.7,clip_on=False)
    ax.set_xlim(0,400);ax.set_xticks((0,100,200,300,400));ax.set_title('Proof coverage (all 3 repeats)',fontsize=9,pad=12)
    ax.set_xlabel('Planned paired scenarios',fontsize=8.5)
    panels=((axes[0,1],'expanded','End-of-run completed expansions'),(axes[1,0],'expanded_phase0','Phase 0: end-of-run expansions'),(axes[1,1],'expanded_phase1','Phase 1: end-of-run expansions'))
    for ax,key,title in panels:
        maximum=1.0
        for i,method in enumerate(METHODS):
            values=[r[key] for r in data if r['method']==method and r[key] is not None]
            require(all(v>=0 for v in values),'negative work count')
            if values:
                maximum=max(maximum,max(values))
                artists=ax.boxplot([values],positions=[i],vert=False,widths=.55,patch_artist=True,whis=(0,100),showfliers=True,manage_ticks=False,
                    boxprops=dict(facecolor='#D9E5EE',edgecolor='#45657D',linewidth=.8),medianprops=dict(color='#1D3749',linewidth=1.3),
                    whiskerprops=dict(color='#45657D',linewidth=.8),capprops=dict(color='#45657D',linewidth=.8))
            ax.text(1.025,i,f'{len(values)}/400',transform=ax.get_yaxis_transform(),ha='left',va='center',fontsize=7.7,clip_on=False)
        ax.set_xscale('symlog',linthresh=1);ax.set_xlim(0,maximum*1.3)
        ax.set_xticks([x for x in (0,1,10,100,1000,10000,100000,1000000) if x<=maximum*1.3])
        ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda x,pos:f'{x:g}'))
        ax.set_title(title,fontsize=9,pad=12);ax.set_xlabel('Completed expansions (symlog; linear 0-1)',fontsize=8)
    for idx,ax in enumerate(axes.flat):
        ax.set_ylim(8.7,-.7);ax.set_yticks(range(9),[DISPLAY[m] for m in METHODS]);ax.tick_params(axis='y',length=0,labelsize=8,labelleft=idx%2==0)
        panel_label(ax,chr(97+idx))
        ax.text(1.025,1.015,'Cases',transform=ax.transAxes,fontsize=7.7,ha='left',va='bottom')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.59,.045),ncol=4,fontsize=8,frameon=False)
    fig.text(.205,.015,'End-of-run work includes soft overruns; censored work is not full-solution work at 1 s. Smaller counts can reflect slow bounds or truncation, not efficiency.',fontsize=7.7)
    return save(fig,'Figure_03_Coverage_And_Search_Work',out)

def main():
    global plt,np,mpl,require_matplotlib_panel_alignment
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--analysis',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--library-root',type=Path,help='Optional existing Python package directory; no installation')
    args=ap.parse_args();out=(args.out if args.out.is_absolute() else P/args.out).resolve()
    folder=(args.analysis if args.analysis.is_absolute() else P/args.analysis).resolve()
    require((P/'figures').resolve() in out.parents and not out.exists(),'Fresh V449/figures child required')
    require((P/'analysis').resolve() in folder.parents,'Use a V449 analysis directory')
    out.mkdir(parents=True)
    try:
        hashes={str(folder/name):sha(folder/name) for name in INPUT_FILES}
        tables,case_rows,reps,cm=inputs(folder)
        q=quality_data(tables);p=proof_data(tables,reps,cm);m=mechanism_data(case_rows)
        csvwrite(out/'Figure_01_Source.csv',q);csvwrite(out/'Figure_02_Source.csv',p);csvwrite(out/'Figure_03_Source.csv',m)
        os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',MPLCONFIGDIR=str(out/'_mplconfig'),PYTHONDONTWRITEBYTECODE='1')
        sys.dont_write_bytecode=True
        if args.library_root:
            require(args.library_root.is_dir(),'Existing package directory required')
            sys.path.insert(0,str(args.library_root));os.environ['PYTHONPATH']=str(args.library_root)+os.pathsep+os.environ.get('PYTHONPATH','')
        import matplotlib as mpl
        mpl.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        sys.path.insert(0,str(SKILL))
        from audit_panel_alignment import require_matplotlib_panel_alignment
        mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans','Arial'],'font.size':8.5,'axes.titlesize':9,
            'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'axes.spines.top':False,'axes.spines.right':False,
            'axes.linewidth':.7,'legend.frameon':False,'pdf.fonttype':42,'svg.fonttype':'none','savefig.facecolor':'white'})
        audits={'Figure_01':figure_quality(q,out),'Figure_02':figure_proof(p,out),'Figure_03':figure_mechanism(m,out)}
        for path,value in hashes.items():require(sha(Path(path))==value,'CSV changed while plotting')
        captions='''# Figure captions and interpretation boundaries

Figure 1 | Budget quality by scale. The upper row gives the number of scenarios whose three technical repeats all reached the known optimum by each literal deadline, divided by the 100 planned scenarios at that scale. Unknown optima and unavailable incumbents do not count as hits; if no optimum is known the cell is NA. The lower row reports the median across available case medians of relative regret, (H2-optimum)/(optimum-t0), as a percentage. Each lower cell shows its actual available-case denominator. Zero is a valid regret, whereas a zero duration denominator or no available cases is NA. Each scale contains 25 independent mother networks and four related capacity/signal variants per network. Counts are descriptive, with no independence-based confidence intervals.

Figure 2 | Conditional proof cost and its denominator. Each point is candidate sum(case-median elapsed) divided by comparator sum(case-median elapsed), on exactly the same scenarios where both methods proved optimal by one second in all three repeats. The annotation gives the ratio and eligible n/planned N. N is 400 globally and 100 per scale; n is never replaced by N. Empty or zero-denominator comparisons are NA. The source CSV also retains common mother counts, one-sided eligibility, initial-optimal counts and expansion sums/ratios from the identical eligible subset. No confidence interval is implied. The figure measures proof cost, not time to a merely useful solution.

Figure 3 | Coverage and work are different outcomes. Panel a classifies all 400 scenarios per method: all-three on-time proof, all-three end-of-run proof arriving late in at least one repeat, not all-three proved among returned calls, or at least one unavailable repeat. Panels b-d show per-case medians of total, phase-0 and phase-1 completed expansions, with median/IQR boxes and full min-max whiskers. Every available case is included; n/400 is printed. The symmetric-log x-axis preserves zero (linear from zero to one). End-of-run work includes charged soft overruns and is not full-solution work at one second or equal-CPU work. Smaller counts can result from slow bound computation or truncation, including an exact quota calculation that consumes most of a budget before another expansion. A smaller label count does not itself establish pruning gains, speed or practical benefit. DP partial expansions are not miscounted as completed expansions.

All nine frozen methods remain in the quality and coverage/work views. Weighted and lazy search names identify published-policy adaptations; the new joint bound is supplied by this study. These figures use CSV tables only. They do not measure actual RAM, Python allocation bytes, whole-fleet SUMO performance, or real-world delivery gains. Three repeats are technical repeats; paired conditions are not additional independent networks. A target already achieved by the common initial plan is not a search-quality improvement.

Automated alignment, PDF text-size and collision audits were run for each final export. Every panel and assembled figure still require human visual inspection at the intended size before publication use. A collision WARN is not silently a final visual pass.
'''
        (out/'Figure_Captions.md').write_text(captions,encoding='utf-8')
        dump(out/'PROVENANCE.json',dict(source_csv_sha256=hashes,plot_script_sha256=sha(Path(__file__)),matplotlib_version=mpl.__version__,numpy_version=np.__version__,analysis_statistics_recomputed=False,plot_aggregates_checked=True,actual_RAM_measured=False))
        dump(out/'PROCESS_COMPLETE.json',dict(status='RENDERED_PENDING_VISUAL_REVIEW',figure_count=3,exports=['PNG','PDF','source CSV'],audits=audits,source_csv_count=3))
    except BaseException as exc:
        failure=dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc())
        dump(out/'FAILURE.json',failure);dump(out/'PROCESS_COMPLETE.json',failure);raise
if __name__=='__main__':main()
