"""Read-only native-memory analysis. Writes only a fresh analysis directory."""
from pathlib import Path
import argparse,csv,hashlib,json,statistics
P=Path(__file__).resolve().parent
METHODS=('RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def require(x,m):
    if not x:raise AssertionError(m)
def lines(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def med(a):return statistics.median(a) if a else None
def csvfile(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def summarize(rows):
    result=[]
    for scale in (None,6,8,10,12):
        for method in METHODS:
            a=[r for r in rows if r['method']==method and (scale is None or r['m']==scale)]
            n=[r for r in a if r.get('post_solve_PeakWorkingSetSize') is not None]
            x=dict(scale='all' if scale is None else scale,method=method,attempts=len(a),native_endpoints=len(n),valid_solve=sum(r['status']=='OK' for r in a),
                oracle_known=sum(r.get('oracle_H2') is not None for r in a),proof_by_1s=sum(r.get('proof_by_1s') is True for r in a),literal_feasible_1s=sum(r.get('H2_1000ms') is not None for r in a),literal_optimal_1s=sum(r.get('H2_1000ms') is not None and r.get('oracle_H2') is not None and r['H2_1000ms']==r['oracle_H2'] for r in a))
            for phase in ('pre_import','pre_solve','post_solve'):
                for metric in ('PeakWorkingSetSize','WorkingSetSize','PeakPagefileUsage','PrivateUsage'):
                    vals=[r[phase+'_'+metric] for r in n];x[phase+'_'+metric+'_median_bytes']=med(vals);x[phase+'_'+metric+'_max_bytes']=max(vals,default=None)
            vals=[r['elapsed_seconds'] for r in a if r.get('elapsed_seconds') is not None];x['memory_run_solver_seconds_sum']=sum(vals) if vals else None
            result.append(x)
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selected',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();require(P in out.parents,'Output location');out.mkdir(parents=True,exist_ok=False)
    try:
        manifest=P/'freeze_01/MANIFEST.json';m=load(manifest);pins={str(manifest):sha(manifest),str(a.selected):sha(a.selected),str(Path(__file__)):sha(__file__)}
        for f,h in m['sources'].items():require(sha(f)==h,('source drift',f))
        for f,h in m['inputs'].items():require(sha(f)==h,('input drift',f))
        frozen_jobs={h:load(f) for f,h in m['job_sha256'].items() if load(f)['stage']=='main'}
        specs=load(P/'freeze_01/INPUTS.json');bycase={s['case']:s for s in specs};selected=load(a.selected);selected=selected['runs'] if isinstance(selected,dict) else selected
        rows=[];rawrows=[];seen=set();issues=[];origin_hashes=set();completecases=[];runseconds=0
        for raw in selected:
            run=Path(raw)
            protocol=load(run/'PROTOCOL.json');job=protocol['job'];job_hash=protocol['job_sha256']
            require(job_hash in frozen_jobs and job==frozen_jobs[job_hash],'Frozen main job mismatch')
            require(protocol['manifest_sha256']==sha(manifest) and protocol['sources']==m['sources'],'Run source manifest mismatch')
            require(job['stage']=='main' and job['methods']==list(METHODS) and job['repeats']==1 and job['wall_ms']==1000 and job['hard_seconds']==15,'Main schedule/budget')
            local_specs=specs[job['offset']:job['offset']+job['count']];local_ids={x['case'] for x in local_specs}
            for name in ('PROTOCOL.json','ORACLES.jsonl','MEMORY.jsonl','CASE_COMPLETE.jsonl','SUMMARY.json','PROCESS_COMPLETE.json'):
                f=run/name
                if f.exists():pins[str(f)]=sha(f)
                else:issues.append(str(f)+' missing')
            if not (run/'MEMORY.jsonl').exists():continue
            if (run/'PROCESS_COMPLETE.json').exists():
                done=load(run/'PROCESS_COMPLETE.json')
                if done['status'] in ('PASS','PASS_WITH_CENSORING'):
                    require(done['manifest_sha256']==sha(manifest),'manifest mismatch')
                    require(load(run/'SUMMARY.json')==done,'Summary/completion disagreement')
                    require(done['stage']=='main' and done['cases']==len(local_specs) and done['attempts']==len(local_specs)*4,'Completion counts')
                    require(done['source_hashes']==m['sources'],'Completion source hashes')
                else:issues.append(str(run)+' did not complete')
                runseconds+=done.get('seconds',0)
            if (run/'CASE_COMPLETE.jsonl').exists():
                cc=lines(run/'CASE_COMPLETE.jsonl');require(all(r['status']=='PASS' and r['attempts']==4 and r['case'] in local_ids for r in cc),'Case-completion status/count')
                completecases += [r['case'] for r in cc]
            for r in lines(run/'MEMORY.jsonl'):
                key=(r['case'],r['method'],r['repeat']);require(key not in seen,'Duplicate observation');seen.add(key)
                require(r['case'] in local_ids and r['method'] in METHODS and r['repeat']==0 and r['stage']=='main','Unexpected main observation')
                spec=bycase[r['case']];require(r['seed']==spec['seed'] and r['m']==len(spec['old']) and r['Q']==spec['Q'],'Raw input metadata')
                require(r['input_sha256']==hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),'Input identity')
                flat=dict(case=r['case'],seed=spec['seed'],m=len(spec['old']),Q=spec['Q'],signal=spec.get('signal'),capacity_regime=spec.get('capacity_regime'),method=r['method'],repeat=r['repeat'],status=r['status'],parent_process_seconds=r['parent_process_seconds'])
                if r.get('post_solve'):
                    prior={k:0 for k in ('PeakWorkingSetSize','PeakPagefileUsage')}
                    for phase in ('pre_import','pre_solve','post_solve'):
                        native=r[phase];require(native['status']=='OK' and native['peak_reset_performed'] is False,'Native endpoint')
                        counter=native['counters_bytes']
                        require(all(isinstance(v,int) and v>=0 for v in counter.values()),'Non-byte counter')
                        require(counter['PeakWorkingSetSize']>=counter['WorkingSetSize'] and counter['PeakPagefileUsage']>=counter['PagefileUsage'],'Peak/current invariant')
                        for k in prior:require(counter[k]>=prior[k],'Lifetime peak reset');prior[k]=counter[k]
                        flat.update({phase+'_'+k:counter[k] for k in ('PeakWorkingSetSize','WorkingSetSize','PeakPagefileUsage','PagefileUsage','PrivateUsage')})
                    for k in prior:
                        growth=r['post_solve']['counters_bytes'][k]-r['pre_solve']['counters_bytes'][k]
                        require(growth==r['observed_peak_growth_after_baseline'][k],'Peak-growth identity');flat['observed_growth_'+k]=growth
                    origin_hashes.add(hashlib.sha256(json.dumps(r['common_import_origins']).encode()).hexdigest())
                    require(r['oracle_or_replay_executed_in_worker'] is False,'Validation contamination')
                if r['status']=='OK':
                    result=r['solver_result'];v=r['validation'];require(v['status']=='PASS','Invalid solve')
                    flat.update(elapsed_seconds=result['elapsed_seconds'],setup_seconds=result['setup_seconds'],initial_seconds=result['initial_seconds'],search_seconds=result['search_seconds'],soft_overrun_seconds=result['overrun_seconds'],H2_end=result['H2'],oracle_H2=v['oracle_H2'],proof_by_1s=v['certified_by_1s'],expanded=result['expanded'])
                    for ms in (100,500,1000):
                        quality=min((e['H2'] for e in result['trace'] if e['seconds']<=ms/1000),default=None)
                        require(quality==v['literal_H2_at_ms'][str(ms)],'Literal quality mismatch');flat['H2_'+str(ms)+'ms']=quality
                    require(v['certified_by_1s']==bool(result['certified_optimal'] and result['elapsed_seconds']<=1),'On-time certificate')
                rows.append(flat);rawrows.append(r)
        expected={(s['case'],method,0) for s in specs for method in METHODS};missing=sorted(expected-seen)
        if missing:issues.append(f'{len(missing)} planned observations missing')
        if sorted(completecases)!=sorted(bycase):issues.append('CASE_COMPLETE coverage is not exactly 32 unique cases')
        require(len(origin_hashes)<=1,'Common imports differ across measured processes')
        csvfile(out/'Observations.csv',rows);summary=summarize(rows);csvfile(out/'Method_Summary.csv',summary)
        pairs=[]
        index={(r['case'],r['method']):r for r in rows}
        for candidate,baseline in (('RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS'),('HZ_AWA_RADIUS_PAIR_GATED','HZ_AWA_RADIUS'),('RADIUS_PAIR_AWA_GATED','ANA_RADIUS'),('RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS_PAIR_GATED'),('HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS')):
            for spec in specs:
                c=index.get((spec['case'],candidate),{});b=index.get((spec['case'],baseline),{})
                pair=dict(case=spec['case'],seed=spec['seed'],m=len(spec['old']),candidate=candidate,baseline=baseline)
                for metric in ('PeakWorkingSetSize','PeakPagefileUsage','PrivateUsage'):
                    key='post_solve_'+metric;cv=c.get(key);bv=b.get(key)
                    pair[metric+'_candidate_bytes']=cv;pair[metric+'_baseline_bytes']=bv;pair[metric+'_ratio']=cv/bv if cv is not None and bv else None
                pair['both_proved_by_1s']=c.get('proof_by_1s') is True and b.get('proof_by_1s') is True
                pair['candidate_H2_1000ms']=c.get('H2_1000ms');pair['baseline_H2_1000ms']=b.get('H2_1000ms');pair['candidate_proof_by_1s']=c.get('proof_by_1s');pair['baseline_proof_by_1s']=b.get('proof_by_1s');pairs.append(pair)
        csvfile(out/'Paired_Cases.csv',pairs)
        ps=[]
        for candidate,baseline in dict.fromkeys((r['candidate'],r['baseline']) for r in pairs):
            for scale in (None,6,8,10,12):
                subset=[r for r in pairs if r['candidate']==candidate and r['baseline']==baseline and (scale is None or r['m']==scale)]
                for metric in ('PeakWorkingSetSize','PeakPagefileUsage','PrivateUsage'):
                    valid=[r for r in subset if r[metric+'_ratio'] is not None];cs=sum(r[metric+'_candidate_bytes'] for r in valid);bs=sum(r[metric+'_baseline_bytes'] for r in valid)
                    ps.append(dict(candidate=candidate,baseline=baseline,scale='all' if scale is None else scale,metric=metric,planned_cases=len(subset),paired_native_cases=len(valid),candidate_bytes_sum=cs if valid else None,baseline_bytes_sum=bs if valid else None,ratio_of_sums=cs/bs if bs else None,median_case_ratio=med([r[metric+'_ratio'] for r in valid]),lower=sum(r[metric+'_ratio']<1 for r in valid),equal=sum(r[metric+'_ratio']==1 for r in valid),higher=sum(r[metric+'_ratio']>1 for r in valid)))
        csvfile(out/'Pair_Summary.csv',ps)
        proved_pairs=[]
        for candidate,baseline in dict.fromkeys((r['candidate'],r['baseline']) for r in pairs):
            eligible=[r for r in pairs if r['candidate']==candidate and r['baseline']==baseline and r['both_proved_by_1s']]
            for metric in ('PeakWorkingSetSize','PeakPagefileUsage','PrivateUsage'):
                valid=[r for r in eligible if r[metric+'_ratio'] is not None];cs=sum(r[metric+'_candidate_bytes'] for r in valid);bs=sum(r[metric+'_baseline_bytes'] for r in valid)
                proved_pairs.append(dict(candidate=candidate,baseline=baseline,metric=metric,common_on_time_proved_cases=len(eligible),paired_native_cases=len(valid),candidate_bytes_sum=cs if valid else None,baseline_bytes_sum=bs if valid else None,ratio_of_sums=cs/bs if bs else None,median_case_ratio=med([r[metric+'_ratio'] for r in valid]),lower=sum(r[metric+'_ratio']<1 for r in valid),equal=sum(r[metric+'_ratio']==1 for r in valid),higher=sum(r[metric+'_ratio']>1 for r in valid)))
        csvfile(out/'Pair_Summary_Proved_By_1s.csv',proved_pairs)
        # The four-scenario, nine-method cost sample is diagnostic only.
        # Never merge its method denominators with the 32-scenario main sample.
        diagnostic=[];diagnostic_summary=[]
        for raw in load(P/'freeze_01/pilot_selected.json'):
            run=Path(raw);done=load(run/'PROCESS_COMPLETE.json');protocol=load(run/'PROTOCOL.json')
            require(done['status'] in ('PASS','PASS_WITH_CENSORING') and done['stage']=='pilot' and done['attempts']==9,'Pilot diagnostic completeness')
            require(done['manifest_sha256']==sha(manifest) and protocol['manifest_sha256']==sha(manifest),'Diagnostic manifest')
            rr=lines(run/'MEMORY.jsonl');require(len(rr)==9 and {r['method'] for r in rr}==set(m['primary_methods']),'Diagnostic method matrix')
            for name in ('PROTOCOL.json','MEMORY.jsonl','PROCESS_COMPLETE.json'):pins[str(run/name)]=sha(run/name)
            for r in rr:
                d=dict(case=r['case'],m=r['m'],method=r['method'],status=r['status'],scope='Four fixed pilot scenarios; diagnostic, one observation per method/case')
                if r.get('post_solve'):
                    for phase in ('pre_import','pre_solve','post_solve'):
                        for metric in ('PeakWorkingSetSize','PeakPagefileUsage','PrivateUsage'):d[phase+'_'+metric]=r[phase]['counters_bytes'][metric]
                if r['status']=='OK':
                    v=r['validation'];d.update(proof_by_1s=v['certified_by_1s'],H2_1000ms=v['literal_H2_at_ms']['1000'],oracle_H2=v['oracle_H2'])
                diagnostic.append(d)
        require(len(diagnostic)==36 and len({r['case'] for r in diagnostic})==4,'Diagnostic sample size')
        for method in m['primary_methods']:
            rr=[r for r in diagnostic if r['method']==method];d=dict(method=method,cases=4,observations=len(rr),proof_by_1s=sum(r.get('proof_by_1s') is True for r in rr),known_oracle=sum(r.get('oracle_H2') is not None for r in rr),literal_optimal_1s=sum(r.get('H2_1000ms') is not None and r.get('oracle_H2') is not None and r['H2_1000ms']==r['oracle_H2'] for r in rr))
            for phase in ('pre_import','pre_solve','post_solve'):
                for metric in ('PeakWorkingSetSize','PeakPagefileUsage','PrivateUsage'):
                    vals=[r[phase+'_'+metric] for r in rr if r.get(phase+'_'+metric) is not None];d[phase+'_'+metric+'_median_bytes']=med(vals)
            diagnostic_summary.append(d)
        csvfile(out/'Diagnostic_Pilot_Observations.csv',diagnostic);csvfile(out/'Diagnostic_Pilot_Method_Summary.csv',diagnostic_summary)
        dump(out/'Missing.json',missing);dump(out/'Source_and_Raw_Hashes.json',pins)
        result=dict(status='COMPLETE' if not issues else 'INCOMPLETE',issues=issues,observations=len(rows),expected=128,cases=len({r['case'] for r in rows}),mothers=len({r['seed'] for r in rows}),common_import_hashes=sorted(origin_hashes),all_imports_identical=len(origin_hashes)==1,failed_or_censored=sum(r['status']!='OK' for r in rows),sum_run_seconds=runseconds,manifest_sha256=sha(manifest))
        dump(out/'SUMMARY.json',result);dump(out/'PROCESS_COMPLETE.json',result)
        prose=['# Native process memory results','',f"Coverage: {len(rows)}/128 observations, {result['cases']} scenarios and {result['mothers']} mothers. One fresh process per method/scenario; no repeat-variability estimate.",'','Primary endpoints are process lifetime peaks read immediately after solve; before-import and pre-solve current/peak baselines are retained in Observations.csv. PeakPagefileUsage is peak process commit, not physical pagefile writes. PrivateUsage is current private commit, not a peak field. Working set includes shared and private resident pages.','',f"Common pre-solve module origins identical: {result['all_imports_identical']}. Censored/failed observations: {result['failed_or_censored']}. Missing endpoints remain NA.",'','| Method | Native n | Peak working set median KiB | Peak commit median KiB | Pre-solve working set median KiB | Proof by 1 s | Literal optimum by 1 s |','|---|---:|---:|---:|---:|---:|---:|']
        for r in summary:
            if r['scale']!='all':continue
            fmt=lambda x:'NA' if x is None else f'{x/1024:.2f}'
            prose.append(f"| {r['method']} | {r['native_endpoints']} | {fmt(r['post_solve_PeakWorkingSetSize_median_bytes'])} | {fmt(r['post_solve_PeakPagefileUsage_median_bytes'])} | {fmt(r['pre_solve_WorkingSetSize_median_bytes'])} | {r['proof_by_1s']}/32 | {r['literal_optimal_1s']}/{r['oracle_known']} known |")
        prose += ['','Pairs use the identical case intersection and report their own denominator. Ratios of sums and medians of case ratios are distinct. The HZ pair comparison uses the same complete engine; other engine comparisons also include implementation/container choices.','', 'Peak growth above baseline is supplemental and is not algorithm-private RAM. Peaks cannot be reset and include import/startup history. End-of-soft-run peaks include any soft overrun; they are not a maximum sampled only within the first second. These independently instrumented times are not substituted for V449 speed results. Frontier/cache counts are not RAM. This sample does not establish a general memory bound.']
        prose += ['', 'The separately labelled Diagnostic_Pilot CSV files retain native measurements for all nine original methods on the four fixed cost scenarios. Their denominator is four, with one process observation per method/case; they are not pooled with the 32-scenario main comparison or treated as broad performance confirmation.']
        if issues:prose += ['', 'Incomplete evidence: '+repr(issues)]
        (out/'Memory_Results.md').write_text('\n'.join(prose)+'\n',encoding='utf-8');print(json.dumps(result))
    except BaseException as exc:dump(out/'FAILURE.json',dict(status='FAIL',error=repr(exc)));raise
if __name__=='__main__':main()
