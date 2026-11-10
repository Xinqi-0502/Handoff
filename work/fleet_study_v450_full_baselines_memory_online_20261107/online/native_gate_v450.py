"""Small native controller/latency gate, explicitly not a policy performance trial."""
from pathlib import Path
import argparse,traceback
import published_online_v450 as published
import native_online_v450 as native
from check_online_v450 import read,put,sha,sources,validate_gate

def main():
    p=argparse.ArgumentParser();p.add_argument('--prefixes',type=Path,required=True);p.add_argument('--gate',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();validate_gate(a.gate);receipt=read(a.prefixes/'PROCESS_COMPLETE.json');inputs=read(a.prefixes/'INPUTS.json')
    assert receipt['status']=='PASS' and receipt['input_sha256']==sha(a.prefixes/'INPUTS.json') and receipt['sources']==sources()
    if (a.prefixes/'FAILURE.json').exists():raise ValueError('Failed prefix preparation')
    rows=inputs['cases'];assert len(rows)==2 and {s['seed'] for s in rows}=={4509001}
    assert {s['offset'] for s in rows}=={0,24} and all(s['people']==10 and s['slow']==2 for s in rows)
    frozen=sources();a.out.mkdir(parents=True,exist_ok=False);checks=[]
    put(a.out/'PROTOCOL.json',dict(sources=frozen,prefix_inputs_sha256=sha(a.prefixes/'INPUTS.json'),
        synthetic_latency_seconds=[.05,.21],purpose='Controller invariants at two distinct activation ticks, not measured policy performance'))
    try:
        for s in rows:
            initial=published.solve(s,'HZ_AWA_RADIUS',wall_seconds=None,node_limit=0)
            for delay in (.05,.21):
                out=a.out/f'{s["case"]}_delay{round(delay*1000)}'
                audit=native.simulate(s,initial['plan'],out,delay)
                checks.append(dict(case=s['case'],synthetic_delay_seconds=delay,folder=out.name,**audit))
        assert sources()==frozen and len(checks)==4
        put(a.out/'GATE.json',dict(status='PASS',sources=frozen,checks=checks,prefix_inputs_sha256=sha(a.prefixes/'INPUTS.json')))
        put(a.out/'PROCESS_COMPLETE.json',dict(status='PASS',gate_sha256=sha(a.out/'GATE.json')))
    except BaseException:put(a.out/'FAILURE.json',dict(error=traceback.format_exc()));raise
if __name__=='__main__':main()
