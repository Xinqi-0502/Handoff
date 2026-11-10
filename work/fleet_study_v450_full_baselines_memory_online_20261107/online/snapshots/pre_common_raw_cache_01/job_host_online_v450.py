"""Thin E-only host for a monitored online worker and all of its SUMO descendants.
The single WinAPI implementation is imported from public validation AFTER an
explicit hash check. External thermal monitor owns this host PID; terminating
it closes its non-inherited Job handle, killing only its owned process tree.
No solver or SUMO is started merely by importing this module.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,os,sys,traceback
ROOT=Path(__file__).resolve().parent
HELPER=ROOT.parents[1]/'fleet_study_v449_validation_and_online_20261107'/'validation'/'san_pablo_dam'/'run_public_validation.py'
HELPER_SHA256='c50fcb484be5261a6e710371fbe745af1c0cbabd548ff57994febc6bd8acb451'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--python',type=Path,required=True);ap.add_argument('--script',type=Path,required=True)
    ap.add_argument('--args-json',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--helper-sha256',default=HELPER_SHA256);ap.add_argument('--timeout-seconds',type=float,required=True)
    a=ap.parse_args();out=a.out.resolve();script=a.script.resolve()
    if out.drive.upper()!='E:' or out.exists() or not script.is_relative_to(ROOT):raise ValueError('Fresh E output and an online script required')
    if not math.isfinite(a.timeout_seconds) or a.timeout_seconds<=0:raise ValueError('Positive finite timeout required')
    if a.helper_sha256.lower()!=HELPER_SHA256:raise ValueError('Only the frozen reviewed helper is allowed')
    actual=hashlib.sha256(HELPER.read_bytes()).hexdigest()
    if actual.lower()!=a.helper_sha256.lower():raise ValueError('Owned-process helper hash mismatch')
    args=json.loads(a.args_json.read_text(encoding='utf-8-sig'))
    if not isinstance(args,list) or not all(isinstance(x,str) for x in args):raise ValueError('Argument JSON must be a string array, with absolute data/output paths')
    out.mkdir(parents=True,exist_ok=False)
    os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',PYTHONDONTWRITEBYTECODE='1')
    spec=importlib.util.spec_from_file_location('v449_owned_process_helper',HELPER);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    argv=[str(a.python.resolve()),'-B','-X','utf8',str(script),*args]
    def put(name,data):
        with (out/name).open('x',encoding='utf8') as f:json.dump(data,f,indent=2)
    put('COMMAND.json',{'argv':argv,'cwd':str(out),'helper':str(HELPER),'helper_sha256':actual,
        'args_sha256':hashlib.sha256(a.args_json.read_bytes()).hexdigest(),'timeout_seconds':a.timeout_seconds,
        'scope':'This worker and its native descendants only; kernel kill-on-job-close'})
    try:
        with (out/'stdout.txt').open('x',encoding='utf8') as so,(out/'stderr.txt').open('x',encoding='utf8') as se:
            code=helper.owned_windows_process(argv,out,so,se,a.timeout_seconds)
        if code:raise RuntimeError(('worker exit',code))
        put('PROCESS_COMPLETE.json',{'status':'PASS','worker_exit_code':code})
        return 0
    except BaseException:
        put('FAILURE.json',{'error':traceback.format_exc()});raise
if __name__=='__main__':raise SystemExit(main())

