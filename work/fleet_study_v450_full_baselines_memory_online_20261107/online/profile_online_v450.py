"""Separate small profile mode. Its instrumented times are not main policy timings."""
from pathlib import Path
import argparse,traceback
import published_online_v450 as published
from check_online_v450 import read,put,sha,sources,validate_gate

def main():
    p=argparse.ArgumentParser();p.add_argument('--prefixes',type=Path,required=True);p.add_argument('--gate',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();validate_gate(a.gate);rows=read(a.prefixes/'INPUTS.json')['cases'];frozen=sources();a.out.mkdir(parents=True,exist_ok=False)
    try:
        results=[]
        for s in rows:
            for arm in ('HZ_AWA_RADIUS','HZ_AWA_PAIR_GATED'):
                results.append(dict(case=s['case'],**published.solve(s,arm,.05,profile=True)))
        assert sources()==frozen
        put(a.out/'PROFILE.json',dict(status='PASS',sources=frozen,records=results,
            time_scope='bound_time_ns counts common lower-cost evaluations; pair_time_inclusive_ns includes its internal base recomputation; pair_time_exclusive_ns subtracts that overlap',
            main_timing=False,actual_RAM_measured=False))
        put(a.out/'PROCESS_COMPLETE.json',dict(status='PASS',profile_sha256=sha(a.out/'PROFILE.json')))
    except BaseException:put(a.out/'FAILURE.json',dict(error=traceback.format_exc()));raise
if __name__=='__main__':main()
