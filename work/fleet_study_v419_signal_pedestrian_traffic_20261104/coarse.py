from model_turn2 import *
from native_turn2 import simulate
from audit_turn2 import frames,get
import csv,gzip,json,traceback,statistics

R=HERE/'runs'
def summary(frs,offset):
    sig=Crossing(offset,{},False);result={}
    for edge,link in [('WC',2),('EC',0)]:
        rows=[];green=[]
        for f in frs:
            if not E-5 < f['tick']/HZ <= E:continue
            for v,x in f['vehicles'].items():
                if x[0]!=edge or x[3]&1 or not 0<=sig.length[edge]/100-x[1]<=45:continue
                row=(f['tick']/HZ,v,x[2]);rows.append(row)
                if f['signal'][link] in 'gG':green.append(row)
        speed=statistics.mean(x[2] for x in green) if green else None
        age=E-max(x[0] for x in green) if green else None
        state='unknown' if speed is None or age>4 else 'nearstop' if speed<.1 else 'slow' if speed<4 else 'moving'
        result[edge]=dict(samples=len(rows),unique=len({x[1] for x in rows}),green_samples=len(green),
            green_unique=len({x[1] for x in green}),green_latest_age=age,green_mean_mps=speed,category=state)
    return result
class ShortForecast(Crossing):
    def __init__(self,offset,obs,mode):
        super().__init__(offset,{},False)
        self.obs=obs;self.mode=mode;self.relevant=[]
    def turn_wait(self,time,link,speed):
        if self.mode=='STATIC':return 0
        edge='WC' if link in self.right_links else 'EC'
        category=self.obs[edge]['category']
        penalty=({'slow':2,'nearstop':4}.get(category,0) if time<=E+48 else 0)
        if penalty:self.relevant.append((edge,round(time,3),penalty))
        return penalty+super().turn_wait(time+penalty,link,speed)
def main():
    out=R/'coarse_freeze_01';out.mkdir()
    ds=read(R/'decisions_01/DECISIONS.json');result={};sensors={}
    for key,s in sorted(ds.items()):
        fr=frames(R/'prefix_01'/key)
        assert len(fr)==30 and fr[-1]['tick']/HZ==6
        snapshot=summary(fr,s['offset']);sensors[key]=snapshot
        choices={}
        for mode in ['COARSE','STATIC']:
            for rule in ('EXTREME_SEP','COMMON_WIT'):
                now=__import__('time').perf_counter()
                sig=ShortForecast(s['offset'],snapshot,mode);p=witness.decide(s['c'],s['wave'],s['ctx'],sig,rule)
                elapsed=__import__('time').perf_counter()-now
                assert elapsed<1 and len(p['opened'])==2 and p['opened']==s['choices']['SEP_SIGNAL']['opened']
                sig.relevant.clear();sig.forecast(s['c'],s['ctx'],s['wave'],MATRIX,p['plan'])
                choices[mode+'_'+rule]=dict(choice=p['choice'],signature=p['signature'],plan=p['plan'],opened=p['opened'],
                    secs=elapsed,pred=p['alternatives'][0]['pred']['J'],penalty_visits=sig.relevant)
        result[key]=choices
    put(out/'SENSORS.json',sensors);put(out/'CHOICES.json',result)
    old={(r['key'],r['signature']):r for sd in SEEDS for r in read(R/f'native_{sd}/PHYSICAL.json')}
    extra=read(R/'phase_extra_01/PHYSICAL_EXTRA.json')
    for r in extra:old[r['key'],r['signature']]=r
    new=[]
    for arm in ['COARSE_EXTREME_SEP','STATIC_EXTREME_SEP','COARSE_COMMON_WIT','STATIC_COMMON_WIT']:
        for key,s in sorted(result.items()):
            q=(key,s[arm]['signature'])
            if q not in old and q not in new:new.append(q)
    put(out/'FREEZE.json',dict(choices=fh(out/'CHOICES.json'),sensors=fh(out/'SENSORS.json'),protocol=fh(HERE/'COARSE_PROTOCOL.md'),
        source=fh(HERE/'coarse.py'),existing=len(old),needed=new,allowed=new[:4],omitted=new[4:]))
    print('required',len(new),'allowed',min(4,len(new)))
def replay():
    out=R/'coarse_actual_01';out.mkdir()
    src=R/'coarse_freeze_01';seal=read(src/'FREEZE.json')
    assert seal['choices']==fh(src/'CHOICES.json') and seal['source']==fh(HERE/'coarse.py')
    pol=read(src/'CHOICES.json');ds=read(R/'decisions_01/DECISIONS.json')
    known={(r['key'],r['signature']):r for sd in SEEDS for r in read(R/f'native_{sd}/PHYSICAL.json')}
    for r in read(R/'phase_extra_01/PHYSICAL_EXTRA.json'):known[r['key'],r['signature']]=r
    errors=[];rows=[]
    for key,sig in seal['allowed']:
        s=ds[key];p=next(p for p in pol[key].values() if p['signature']==sig);folder=out/(key+'_'+sig[:12])
        try:
            try:simulate(s['c'],bool(s['people']),folder,s['wave'],p['plan'],s['prefix'],s['offset'])
            except Exception:
                errors.append(dict(key=key,sig=sig,error=traceback.format_exc()))
                if not(folder/'RESULT.json').is_file():raise
            metrics=get(folder);assert metrics['prefix']==s['prefix'] and fh(folder/'old_batch.rou.xml')==s['xml']
            known[key,sig]=dict(key=key,signature=sig,folder=str(folder.relative_to(HERE)),**metrics)
        except Exception:errors.append(dict(key=key,sig=sig,validation=traceback.format_exc()))
    for key,s in ds.items():
        for arm,p in pol[key].items():
            base_arm='SEP_SIGNAL' if arm.endswith('SEP') else 'COMMON_SIGNAL'
            b=s['choices'][base_arm]
            r=known.get((key,p['signature']),{});base=known[key,b['signature']]
            row=dict(key=key,seed=s['seed'],offset=s['offset'],people=s['people'],arm=arm,choice=p['choice'],same_plan=b['signature']==p['signature'],
                status=r.get('status','budget_cap'),penalty_on_selected=len(p['penalty_visits']),seconds=p['secs'],physical=r.get('folder'))
            for col in ['J','old','new','wait','handoff']:
                row[col]=r.get(col);row['saved_vs_signal_'+col]=round(base[col]-r[col],2) if col in base and col in r else None
            rows.append(row)
    with (out/'OUTCOMES.csv').open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    put(out/'FAILURES.json',errors)
    print('rows',len(rows),'errors',len(errors))
if __name__=='__main__':
    if sys.argv[1]=='freeze':main()
    else:replay()
