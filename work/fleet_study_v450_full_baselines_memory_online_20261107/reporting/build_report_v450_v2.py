"""Build the evidence landing page from explicit audited inputs and reviewed panels.
This script performs no experiments. All optional panels must name their evidence.
"""
from pathlib import Path
import argparse, json, html, hashlib, datetime
ROOT=Path(__file__).resolve().parents[1]
def esc(x): return html.escape(str(x))
def table(headers, rows):
    return '<table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--panels',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.panels=a.panels.resolve();a.out=a.out.resolve()
    src=ROOT/'static_comparison/analysis/main_01/Analysis.json';stat=json.loads(src.read_text(encoding='utf-8-sig'))
    cross=ROOT/'audit_code/results/crosscheck_01/Crosscheck.json';cross_data=json.loads(cross.read_text(encoding='utf-8-sig'))
    assert stat['status']=='PASS' and cross_data['status']=='PASS'
    p=json.loads(a.panels.read_text(encoding='utf-8-sig'));assert p['reviewed'] is True
    evidence={str(src.relative_to(ROOT)):hashlib.sha256(src.read_bytes()).hexdigest(),str(cross.relative_to(ROOT)):hashlib.sha256(cross.read_bytes()).hexdigest(),str(a.panels.relative_to(ROOT)):hashlib.sha256(a.panels.read_bytes()).hexdigest()}
    def pair(lhs,rhs):
        direct=next((x for x in stat['pairs'] if x['lhs']==lhs and x['rhs']==rhs),None)
        if direct is not None: return direct
        reverse=next(x for x in stat['pairs'] if x['lhs']==rhs and x['rhs']==lhs)
        out=dict(reverse);out['lhs']=lhs;out['rhs']=rhs
        for field in ('seconds','expansions','faster'):
            out['lhs_'+field]=reverse['rhs_'+field]
            out['rhs_'+field]=reverse['lhs_'+field]
        out['lhs_time_change_percent']=100*(out['lhs_seconds']/out['rhs_seconds']-1)
        out['lhs_expansion_change_percent']=100*(out['lhs_expansions']/out['rhs_expansions']-1)
        for gap in (0,1,2):
            prefix='gap'+str(gap)+'_'
            out[prefix+'lhs_seconds']=reverse[prefix+'rhs_seconds']
            out[prefix+'rhs_seconds']=reverse[prefix+'lhs_seconds']
            out[prefix+'lhs_change_percent']=100*(out[prefix+'lhs_seconds']/out[prefix+'rhs_seconds']-1)
        return out
    ca='HZ_AWA_RADIUS_PAIR_GATED';comparison=[]
    for baseline,label in [('HZ_AWA_RADIUS','Complete AWA + RADIUS'),('ANA_RADIUS','Complete ANA + RADIUS')]:
        x=pair(ca,baseline);comparison.append((label,x['common_proved_cases'],f"{x['lhs_expansion_change_percent']:+.2f}%",f"{x['lhs_time_change_percent']:+.2f}%",f"{x['lhs_faster']} / {x['rhs_faster']}"))
    x=pair(ca,'HZ_AWA_RADIUS')
    sections=[('Retained version',[
        'The main deployment remains the frozen RADIUS_PAIR_AWA_GATED combination. The added check preserves the capacity relationship between two indivisible incoming orders. A common first-handoff time links their release requirements, and each old parcel can release capacity only once. A constructive upper bound on the relaxation skips added calculations that cannot reject the state.',
        'The AWA and ANA comparison implementations follow complete published search policies with declared freight-domain adapters. Their common initialization, raw-bound cache, state transitions, objectives and deadlines are held fixed. They do not reproduce the complete Hof-Schneider or Wei freight routing systems.'
    ]),('Independent search comparison',[
        'There are 256 new scenarios from 64 mother instances, with 6, 8, 10 or 12 old orders and four paired capacity/signal conditions. Four methods and three technical repetitions give 3,072 completed calls. All methods found the verified optimum within one second in every scenario and repetition. Finding that solution and finishing its optimality proof are recorded separately.',
        'The table compares the generic AWA implementation with the added check against each baseline. Both methods had to finish proof within the budget in all three repetitions for a case to enter the common-proof table. Percentages use sums of case medians on that identical subset. Negative values mean less work or time.',
    ])]
    body='<h1>Two-handoff capacity bound: evidence report</h1><p class="date">'+esc(p['date'])+'</p>'
    for title,paras in sections:
        body+='<section><h2>'+esc(title)+'</h2>'+''.join('<p>'+esc(t)+'</p>' for t in paras)+'</section>'
    body+=table(['Baseline','Common proof cases','Expanded states','Proof time','Faster / slower cases'],comparison)
    body+='<p>The same-kernel comparison isolates the added check. The selected specialized deployment has different bookkeeping costs. Its implementation advantage is reported separately.</p>'
    body+=table(['Same-kernel target','Cases','Time change'],[("First exact optimum",x['gap0_common_reached'],f"{x['gap0_lhs_change_percent']:+.2f}%"),("First 5% duration gap",x['gap1_common_reached'],f"{x['gap1_lhs_change_percent']:+.2f}%"),("First 10% duration gap",x['gap2_common_reached'],f"{x['gap2_lhs_change_percent']:+.2f}%")])
    body+='<p>The duration gap uses remaining time from the decision epoch. The slower early-quality results remain part of the evidence.</p>'
    for panel in p['panels']:
        body+='<section><h2>'+esc(panel['title'])+'</h2>'
        for text in panel.get('paragraphs',[]):body+='<p>'+esc(text)+'</p>'
        if panel.get('table'):body+=table(panel['table']['headers'],panel['table']['rows'])
        for link in panel.get('links',[]):
            target=ROOT/link['path'];assert target.exists(),str(target)
            if target.is_file():evidence[link['path']]=hashlib.sha256(target.read_bytes()).hexdigest()
            body+='<p><a href="'+esc(link['path'])+'">'+esc(link['label'])+'</a></p>'
        body+='</section>'
    for fig in p.get('figures',[]):
        target=ROOT/fig['path'];assert target.is_file();evidence[fig['path']]=hashlib.sha256(target.read_bytes()).hexdigest()
        body+='<figure><img src="'+esc(fig['path'])+'" alt="'+esc(fig['alt'])+'"><figcaption>'+esc(fig['caption'])+'</figcaption></figure>'
    body+='<section><h2>Evidence access</h2><p>All source code, frozen inputs, raw records, failures and checks are retained in this E-drive study directory. Follow the module links above for the full denominators and execution receipts.</p></section>'
    css='body{max-width:1050px;margin:42px auto;padding:0 28px 60px;font:17px/1.55 Georgia,serif;color:#20252a;background:#fff}h1{font-size:30px;line-height:1.2}h2{font-size:23px;margin-top:32px}p{margin:12px 0}table{border-collapse:collapse;width:100%;font:15px/1.45 Arial,sans-serif;margin:22px 0}th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #d3d9de}th{border-top:2px solid #333;background:#f4f6f7}a{color:#075e87}img{display:block;width:100%;height:auto}figure{margin:32px 0}figcaption{font-size:15px;color:#3b454c}.date{color:#65717a;font:14px Arial,sans-serif}@media print{body{margin:0;max-width:none}table,figure{break-inside:avoid}h2{break-after:avoid}}'
    assert not a.out.exists(),str(a.out)
    a.out.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Two-handoff capacity bound: evidence report</title><style>'+css+'</style><body>'+body+'</body></html>',encoding='utf-8')
    manifest=a.out.with_suffix('.manifest.json');manifest.write_text(json.dumps(dict(report_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(),evidence=evidence),indent=2),encoding='utf-8')
if __name__=='__main__':main()
