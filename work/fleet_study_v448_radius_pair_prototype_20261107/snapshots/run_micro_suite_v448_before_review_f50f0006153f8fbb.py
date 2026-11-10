"""Serialize the complete frozen micro suite in one thermally supervised process."""
from pathlib import Path
import argparse,json,hashlib,sys,time,traceback,gc,re
import check_v448 as check
P=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',default='micro_01');a=ap.parse_args()
    if not re.fullmatch('[a-z0-9_]+',a.tag):raise ValueError('Invalid tag')
    journal=P/'records'/('check_suite_'+a.tag)
    if journal.exists():raise ValueError('Fresh suite journal required')
    journal.mkdir(parents=True)
    started=time.perf_counter();allcases=json.loads(check.INPUTS.read_text(encoding='utf-8-sig'))
    runpaths=[P/'runs'/f'check_{a.tag}_{i:02d}' for i in range(24)]
    if any(p.exists() for p in runpaths):raise ValueError('One or more intended run folders already exist')
    put(journal/'PROTOCOL.json',dict(source_sha256=sha(__file__),checker_sha256=sha(check.__file__),input_sha256=sha(check.INPUTS),cases=[s['case'] for s in allcases],runs=[str(p) for p in runpaths],case_seconds=30,max_seconds_per_case_run=60,serial_same_process=True,numerical_suite_not_started_when_protocol_written=True))
    complete=[];pinsets=[]
    try:
        for i,run in enumerate(runpaths):
            sys.argv=['check_v448.py','--run',str(run),'--offset',str(i),'--limit','1','--case-seconds','30','--max-seconds','60']
            if check.main()!=0:raise RuntimeError(f'Correctness case {i} failed; dependent work stopped')
            summary=json.loads((run/'SUMMARY.json').read_text());protocol=json.loads((run/'PROTOCOL.json').read_text())
            done=json.loads((run/'PROCESS_COMPLETE.json').read_text())
            if summary['status']!='PASS' or done['status']!='PASS' or summary['case_count']!=1 or summary['offset']!=i or (run/'FAILURE.json').exists():raise AssertionError('Incomplete or failed case')
            if summary['cases'][0]['case']!=allcases[i]['case']:raise AssertionError('Case identity mismatch')
            complete.extend(summary['cases']);pinsets.append(protocol['sources'])
            with (journal/'CASE_PROGRESS.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(offset=i,case=allcases[i]['case'],run=str(run),status='PASS'))+'\n')
            gc.collect()
        if len(complete)!=24 or len({s['case'] for s in complete})!=24 or any(p!=pinsets[0] for p in pinsets):raise AssertionError('Full suite/source coverage mismatch')
        check.check_pins()
        gate=dict(status='PASS',full_micro_suite_complete=True,cases=24,independent_mothers=len({s['seed'] for s in allcases}),source_pins=pinsets[0],checker_sha256=sha(check.__file__),coordinator_sha256=sha(__file__),input_sha256=sha(check.INPUTS),runs=[str(p) for p in runpaths],case_summaries=complete,seconds=time.perf_counter()-started,integer_wait_is_prefix_sample=True,performance_claims=False)
        put(journal/'PASS.json',gate);put(journal/'PROCESS_COMPLETE.json',dict(status='PASS',cases=24,seconds=gate['seconds']))
        print(json.dumps(dict(status='MICRO_SUITE_PASS',cases=24,seconds=gate['seconds'])),flush=True)
    except BaseException as exc:
        fail=dict(status='FAIL',completed_cases=len(complete),error=repr(exc),traceback=traceback.format_exc(),seconds=time.perf_counter()-started)
        put(journal/'FAILURE.json',fail);put(journal/'PROCESS_COMPLETE.json',fail);raise
if __name__=='__main__':main()
