"""Parent controller for isolated native-memory measurements; no work on import."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time,traceback
from memory_common import *
from native_memory import observe_exit
from owned_process import owned_windows_process

def spec_hash(s):return hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
def check_gate(path,manifest,kind):
    gate=load(path);require(gate['status']=='PASS',(kind,'not PASS'))
    if kind=='safety':
        for p,h in gate['sources'].items():require(sha(p)==h,('Safety source drift',p))
    else:
        require(gate['manifest_sha256']==sha(manifest),(kind,'manifest identity'))
        for p,h in gate.get('evidence',{}).items():require(sha(p)==h,(kind,'evidence drift',p))
    return gate

def validate_row(bundle,spec,row,opt,expected_initial):
    sc,sp,dp,*_=bundle
    require(isinstance(row['H2'],int) and row['H2']>=spec['t0'],'Integer objective')
    require(row['trace'],'Missing actual incumbent trace');previous=-1;best=float('inf')
    for j,entry in enumerate(row['trace']):
        require(previous<=entry['seconds']<=row['elapsed_seconds']+1e-6,'Trace timestamp')
        require(entry['H2']<best or j==0,'Strict incumbent improvement')
        require(dp.replay_plan(spec,entry['plan'],max_seconds=15)==entry['H2'],'Independent DP-domain replay')
        require(sp.ref.replay_plan(spec,entry['plan'],sp.Watchdog(15))==entry['H2'],'Separate reference replay')
        previous=entry['seconds'];best=entry['H2']
    first=row['trace'][0];require((first['H2'],first['plan'])==expected_initial,'Shared greedy initial plan changed')
    require(row['H2']==best and row['plan']==row['trace'][-1]['plan'],'Final/trace agreement')
    lb=row['remaining_bound'];gap=row['certified_gap']
    require((lb is None and gap is None) or (lb is not None and gap==row['H2']-lb and gap>=0),'Certificate identity')
    require(row['certified_optimal']==(gap==0),'Certificate flag')
    if opt is not None:
        require(row['H2']>=opt and (lb is None or lb<=opt),'Oracle/certificate inequality')
        if row['certified_optimal']:require(row['H2']==opt,'False optimum certificate')
    total=row['setup_seconds']+row['initial_seconds']+row['search_seconds']
    require(abs(total-row['elapsed_seconds'])<.02,'Nested total timer identity')
    quality={}
    for ms in (100,500,1000):
        hits=[e for e in row['trace'] if e['seconds']<=ms/1000]
        quality[str(ms)]=min((e['H2'] for e in hits),default=None)
    return dict(status='PASS',oracle_H2=opt,initial_H2=first['H2'],literal_H2_at_ms=quality,
        certified_by_1s=bool(row['certified_optimal'] and row['elapsed_seconds']<=1),
        validation_location='Parent only, after native measurement endpoint',
        dp_oracle_shares_algorithm_with_DP_ADAPTER=True,
        trace_semantics='Generated-goal and goal-pop improvement policies allowed; no forced expansion-index convention')

def one_worker(manifest,spec,method,folder):
    folder.mkdir();pins={p:h for p,h in load(manifest)['sources'].items() if Path(p).parent==P}
    request=dict(mode='solve',worker_source_hashes=pins,manifest=str(manifest),spec=spec,spec_sha256=spec_hash(spec),method=method,wall_ms=1000,hard_seconds=15)
    dump(folder/'REQUEST.json',request);observations=[]
    def observer(stage,pid,handle):
        observations.append(observe_exit(stage,pid,handle));dump(folder/'HANDLE_OBSERVATIONS.json',observations)
    start=time.perf_counter();exit_code=None;timed=False
    with (folder/'stdout.log').open('wb') as stdout,(folder/'stderr.log').open('wb') as stderr:
        try:exit_code=owned_windows_process([sys.executable,'-B','-X','utf8',str(P/'memory_worker.py'),'--execute','--request',str(folder/'REQUEST.json')],P,stdout,stderr,60,observer)
        except subprocess.TimeoutExpired:timed=True
    envelope=dict(parent_process_seconds=time.perf_counter()-start,process_hard_seconds=60,exit_code=exit_code,handle_observations=observations)
    if timed:return dict(status='HARD_PROCESS_TIMEOUT',method=method,case=spec['case'],native_memory=None,solver_result=None,incumbent_not_recovered=True,**envelope)
    require(exit_code==0,('Worker failed',method,folder,exit_code));row=load(folder/'RESULT.json')
    require(row['method']==method and row['spec_sha256']==spec_hash(spec) and row['case']==spec['case'],'Worker identity')
    require(row['oracle_or_replay_executed_in_worker'] is False,'Worker contaminated by validation')
    if row['status']=='OK':require(row['solver_result'].get('method')==method,'Solver/public method identity')
    row.update(envelope);return row

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--job',type=Path,required=True);ap.add_argument('--execute',action='store_true');ap.add_argument('--run',type=Path);a=ap.parse_args(argv)
    require(a.execute,'Explicit --execute required');job=load(a.job);out=(a.run or Path(job['run'])).resolve();require(P in out.parents,'E memory output only');out.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();records=[];completed=[]
    os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',PYTHONDONTWRITEBYTECODE='1');sys.dont_write_bytecode=True
    try:
        manifest=Path(job['manifest']);m=verify_manifest(manifest);check_gate(job['safety_gate'],manifest,'safety')
        require(sha(m['external_gate'])==m['external_gate_sha256'] and load(m['external_gate'])['status']=='PASS','Published gate drift')
        stage=job['stage'];require(stage in ('correctness','pilot','main'),'Stage')
        if stage!='correctness':check_gate(job['correctness_gate'],manifest,'correctness')
        if stage=='main':check_gate(job['cost_approval'],manifest,'cost')
        main_methods=('RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS')
        expected_methods=list(PRIMARY+EXTERNAL) if stage=='correctness' else list(main_methods if stage=='main' else PRIMARY)
        repeats=1
        require(job['methods']==expected_methods and job['repeats']==repeats,'Frozen schedule')
        require(m['job_sha256'].get(str(a.job.resolve()))==sha(a.job),'Frozen job changed')
        inputs=load(job['inputs']);specs=inputs[job['offset']:job['offset']+job['count']]
        require(len(specs)==job['count'] and len({s['case'] for s in specs})==len(specs),'Selected case range')
        require(str(Path(job['inputs']).resolve()) in m['inputs'],'Input is not frozen')
        require(job['wall_ms']==1000 and job['hard_seconds']==15,'Shared solve limits')
        dump(out/'PROTOCOL.json',dict(job=job,job_sha256=sha(a.job),manifest_sha256=sha(manifest),sources=m['sources'],semantics=memory_semantics(),stage=stage))
        bundle=load_bundle(m);sc,sp,dp,*_=bundle;sc.validate_sources()
        oldgate=load(V449/'gates/scale_micro_all_01/GATE.json');require(oldgate['status']=='PASS','Frozen V449 correctness gate')
        for p,h in oldgate['sources'].items():require(sha(p)==h,('Old gate source drift',p))
        common_origins=None
        for case_index,spec in enumerate(specs):
            oracle=dp.solve(spec,max_seconds=15);opt=oracle['optimum_H2'] if oracle['status']=='PASS' else None
            if stage=='correctness':
                exhaustive=sp.ref.ReferenceOracle(spec,sp.Watchdog(30));truth=exhaustive.suffix(exhaustive.initial())
                require(opt==truth,'Topological DP versus independent exhaustive timed-prefix oracle')
            append(out/'ORACLES.jsonl',dict(case=spec['case'],result=oracle,used_as_incumbent=False,location='parent',small_exhaustive_checked=stage=='correctness'))
            # Parent reconstructs the canonical initial solely to validate worker output.
            ctx=sp.Context(spec,sp.Watchdog(15),False,basis='radius');initial=ctx.greedy()
            expected_initial=(initial[0],list(initial[1]));case_rows=[]
            for rep in range(repeats):
                rotation=(job['offset']+case_index+rep)%len(expected_methods);order=expected_methods[rotation:]+expected_methods[:rotation]
                for position,method in enumerate(order):
                    folder=out/f'{case_index:03d}_{rep}_{method}';row=one_worker(manifest,spec,method,folder)
                    row.update(repeat=rep,order_position=position,stage=stage,m=len(spec['old']),seed=spec['seed'],Q=spec['Q'],input_sha256=spec_hash(spec))
                    if row['status']=='OK':
                        if common_origins is None:common_origins=row['common_import_origins']
                        require(row['common_import_origins']==common_origins,'Common imports differ')
                        row['validation']=validate_row(bundle,spec,row['solver_result'],opt,expected_initial)
                        if stage=='correctness':require(row['solver_result']['certified_optimal'] and row['solver_result']['H2']==opt,'Micro not solved exactly')
                    else:
                        append(out/'FAILURES.jsonl',row)
                        if stage=='correctness':raise AssertionError(('Micro timeout',method,spec['case']))
                    append(out/'MEMORY.jsonl',row);records.append(row);case_rows.append(row)
            completed.append(spec['case']);append(out/'CASE_COMPLETE.jsonl',dict(case=spec['case'],attempts=len(case_rows),status='PASS',censored=sum(r['status']!='OK' for r in case_rows)))
        require(len(records)==len(specs)*len(expected_methods)*repeats,'Incomplete matrix');verify_manifest(manifest)
        summary=dict(status='PASS' if all(r['status']=='OK' for r in records) else 'PASS_WITH_CENSORING',stage=stage,cases=len(specs),mothers=len({s['seed'] for s in specs}),attempts=len(records),censored=sum(r['status']!='OK' for r in records),seconds=time.perf_counter()-start,case_ids=completed,manifest_sha256=sha(manifest),source_hashes=m['sources'],common_import_origins_sha256=hashlib.sha256(json.dumps(common_origins).encode()).hexdigest() if common_origins else None)
        dump(out/'SUMMARY.json',summary);dump(out/'PROCESS_COMPLETE.json',summary);print(json.dumps(summary),flush=True);return 0
    except BaseException as exc:
        failure=dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc(),completed_cases=completed,attempts=len(records),seconds=time.perf_counter()-start);dump(out/'FAILURE.json',failure);dump(out/'PROCESS_COMPLETE.json',failure);raise
if __name__=='__main__':raise SystemExit(main())

