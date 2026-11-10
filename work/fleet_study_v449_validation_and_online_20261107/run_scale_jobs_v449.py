"""Serial explicit V449 scale jobs; intended for the existing monitored launcher."""
from pathlib import Path
import gc,json,sys,traceback
from scale_sources_v449 import P,load,dump,append,require,validate_sources

def main():
    require(len(sys.argv)==2,'Supply one frozen jobs JSON')
    config_path=Path(sys.argv[1]).resolve();config=load(config_path)
    journal=(P/config['journal']).resolve();require(P in journal.parents and not journal.exists(),'Fresh job journal')
    validate_sources();journal.mkdir(parents=True);(journal/'JOB_LIST.json').write_bytes(config_path.read_bytes())
    try:
        for index,job in enumerate(config['jobs']):
            require(job['entry'] in ('check_scale_v449','run_scale_v449'),'Only declared V449 entry points')
            if job['entry']=='check_scale_v449':import check_scale_v449 as entry
            else:import run_scale_v449 as entry
            print(json.dumps(dict(job=index,status='START',entry=job['entry'],args=job['args'])),flush=True)
            sys.argv=[job['entry']+'.py',*job['args']];entry.main();gc.collect()
            append(journal/'JOBS.jsonl',dict(job=index,status='RETURNED_NORMALLY',entry=job['entry'],args=job['args']))
        dump(journal/'PROCESS_COMPLETE.json',dict(status='PASS',jobs=len(config['jobs']),note='Read each job for censoring and actual optimum coverage'))
    except BaseException as exc:
        dump(journal/'PROCESS_COMPLETE.json',dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc()));raise
if __name__=='__main__':main()
