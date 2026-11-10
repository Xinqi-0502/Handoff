"""Run explicit V448 frozen jobs serially in the supervised process."""
from pathlib import Path
import gc,json,sys,traceback
P=Path(__file__).resolve().parent

def main():
    if len(sys.argv)!=2:raise SystemExit("Supply one explicit frozen V448 job-list JSON")
    config_path=Path(sys.argv[1]).resolve()
    config=json.loads(config_path.read_text(encoding="utf-8-sig"))
    journal=(P/config["journal"]).resolve()
    if P not in journal.parents or journal.exists():raise ValueError("Fresh V448 journal required")
    journal.mkdir(parents=True)
    (journal/"JOB_LIST.json").write_bytes(config_path.read_bytes())
    try:
        import run_v448
        for index,argv in enumerate(config["jobs"]):
            print(json.dumps(dict(job=index,status="START",args=argv)),flush=True)
            sys.argv=["run_v448.py",*argv]
            run_v448.main()
            gc.collect()
            with (journal/"JOBS.jsonl").open("a",encoding="utf-8") as handle:
                handle.write(json.dumps(dict(job=index,status="PASS",args=argv))+"\n")
        (journal/"PROCESS_COMPLETE.json").write_text(json.dumps(dict(status="PASS",jobs=len(config["jobs"])),indent=2),encoding="utf-8")
        print(json.dumps(dict(status="ALL_JOBS_COMPLETE",jobs=len(config["jobs"]))),flush=True)
    except BaseException as exc:
        (journal/"PROCESS_COMPLETE.json").write_text(json.dumps(dict(status="FAIL",error=repr(exc),
             traceback=traceback.format_exc()),indent=2),encoding="utf-8")
        raise

if __name__=="__main__":
    main()

