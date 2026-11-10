"""Interpret audited V450 saved outputs only. No optimizer or simulator imports."""
from pathlib import Path
import csv,json,hashlib,statistics,collections
R=Path(__file__).resolve().parents[1];A=R/'analysis/full_02';OUT=R/'analysis/interpretation_02'
C='HZ_AWA_PAIR_GATED';B='HZ_AWA_RADIUS';EPS=1e-6

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def csvread(name):
    with (A/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def num(r,k):return None if r[k]=='' else float(r[k])
def dump(name,x):
    with (OUT/name).open('x',encoding='utf8') as f:json.dump(x,f,indent=2,allow_nan=False)
def csvwrite(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('x',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
def avg(xs):return statistics.mean(xs) if xs else None

def main():
    OUT.mkdir(exist_ok=False)
    pc=read(A/'PROCESS_COMPLETE.json');summary=read(A/'SUMMARY.json')
    assert pc['status']==summary['status']=='PASS' and pc['summary_sha256']==sha(A/'SUMMARY.json')
    assert (summary['cases'],summary['mothers'],summary['policy_calls'])==(64,8,1728)
    case=csvread('Case_Budget_Results.csv');calls=csvread('Calls.csv');pairs=csvread('Pair_Cases.csv');ps=csvread('Pair_Summary.csv');mothers=csvread('Mother_Pairs.csv');native=csvread('Native_Events.csv')
    raw=[json.loads(l) for l in (R/'runs/full_02/RESULTS.jsonl').read_text(encoding='utf8').splitlines()]
    profile=read(R/'profiles/full_01/PROFILE.json');ppc=read(R/'profiles/full_01/PROCESS_COMPLETE.json')
    assert ppc['status']==profile['status']=='PASS' and ppc['profile_sha256']==sha(R/'profiles/full_01/PROFILE.json')
    assert len(raw)==1728 and len(profile['records'])==128
    mainrows=[]
    for ms in (10,50,200):
        x=next(x for x in ps if x['stratum']=='ALL' and x['left']==C and x['right']==B and int(x['budget_ms'])==ms)
        group=[x for x in pairs if x['left']==C and x['right']==B and int(x['budget_ms'])==ms]
        mm=[x for x in mothers if x['left']==C and x['right']==B and int(x['budget_ms'])==ms]
        assert len(group)==64 and len(mm)==8
        row={k:num(x,k) for k in ('mean_actual_delta','left_actual_sum','right_actual_sum','actual_wins','actual_ties','actual_losses','direct_same_plan_activation_pairs','left_sum_case_median_expanded','right_sum_case_median_expanded','left_sum_case_median_extra_cuts','both_all3_proof_pairs','proof_left_sum_case_median_ms','proof_right_sum_case_median_ms','allcase_left_sum_case_median_ms','allcase_right_sum_case_median_ms')}
        row.update(budget_ms=ms,mean_handoff_wait_delta=avg([num(q,'weighted_truck_handoff_wait_delta') for q in group]),zero_delta_mothers=sum(abs(num(q,'mean_actual_delta'))<=EPS for q in mm),forecast_actual_reversals=sum(q['strict_direction_reversal']=='True' for q in group))
        base=row['right_sum_case_median_expanded'];row['expanded_change_percent']=100*(row['left_sum_case_median_expanded']/base-1) if base else None
        base=row['proof_right_sum_case_median_ms'];row['common_proof_time_change_percent']=100*(row['proof_left_sum_case_median_ms']/base-1) if base else None
        ids={(q['case'],int(q['budget_ms']),int(q['rep']),q['arm']):(q['signature'],int(q['activation_tick'])) for q in calls}
        row['cross_arm_same_execution_rep_pairs']=sum(ids[q['case'],ms,rep,C]==ids[q['case'],ms,rep,B] for q in group for rep in range(3))
        mainrows.append(row)
    arms=[]
    for arm,ms in sorted({(q['arm'],int(q['budget_ms'])) for q in case}):
        cc=[q for q in case if q['arm']==arm and int(q['budget_ms'])==ms];rr=[q for q in calls if q['arm']==arm and int(q['budget_ms'])==ms]
        assert len(cc)==64 and len(rr)==192
        err=[num(q,'policy_frequency_weighted_representative_replay_J')-num(q,'executed_forecast_J_mean') for q in cc]
        arms.append(dict(arm=arm,budget_ms=ms,cases=64,calls=192,within_deadline_plan_calls=sum(q['deadline_fallback']=='False' for q in rr),fallback_calls=sum(q['deadline_fallback']=='True' for q in rr),all3_plan_cases=sum(int(q['plan_by_deadline_repetitions'])==3 for q in cc),all3_proof_cases=sum(int(q['proof_by_deadline_repetitions'])==3 for q in cc),proof_calls=sum(q['proof_by_deadline']=='True' for q in rr),initial_optimal_true_calls=sum(q['initial_known_optimal']=='True' for q in rr),initial_optimal_false_calls=sum(q['initial_known_optimal']=='False' for q in rr),initial_optimal_unknown_calls=sum(q['initial_known_optimal']=='' for q in rr),actual_J_sum=sum(num(q,'policy_frequency_weighted_representative_replay_J') for q in cc),actual_J_mean=avg([num(q,'policy_frequency_weighted_representative_replay_J') for q in cc]),handoff_wait_mean=avg([num(q,'weighted_truck_handoff_wait') for q in cc]),old_flow_mean=avg([num(q,'weighted_old_flow') for q in cc]),new_a_flow_mean=avg([num(q,'weighted_new_a_flow') for q in cc]),new_b_flow_mean=avg([num(q,'weighted_new_b_flow') for q in cc]),sum_case_median_ms=sum(num(q,'median_elapsed_ms') for q in cc),sum_case_median_expanded=sum(num(q,'median_expanded') for q in cc),forecast_actual_bias_mean=avg(err),forecast_actual_MAE=avg([abs(z) for z in err]),max_overrun_ms=max(num(q,'overrun_ms') for q in rr),activation_ticks=sorted({int(q['activation_tick']) for q in rr})))
    profiles=[]
    for arm in (B,C):
        rr=[q for q in profile['records'] if q['arm']==arm];assert len(rr)==64
        keys=('bound_calls','pair_calls','pair_skip_upper','pair_events','pair_loop_queries','extra_pruned','raw_bound_cache_queries','raw_bound_cache_hits','raw_bound_cache_entries','expanded')
        x=dict(arm=arm,cases=64,**{k:sum(q['counts'][k] for q in rr) for k in keys})
        x.update(elapsed_ms=sum(q['elapsed_seconds']*1000 for q in rr),common_bound_ms=sum(q['counts']['bound_time_ns'] for q in rr)/1e6,pair_inclusive_ms=sum(q['counts']['pair_time_inclusive_ns'] for q in rr)/1e6,pair_exclusive_ms=sum(q['counts']['pair_time_exclusive_ns'] for q in rr)/1e6)
        x.update(pair_exclusive_percent_of_elapsed=100*x['pair_exclusive_ms']/x['elapsed_ms'],pair_us_per_call=x['pair_exclusive_ms']*1000/x['pair_calls'] if x['pair_calls'] else None,pair_skip_fraction=x['pair_skip_upper']/x['pair_calls'] if x['pair_calls'] else None,positive_cut_cases=sum(q['counts']['extra_pruned']>0 for q in rr),cut_range=[min(q['counts']['extra_pruned'] for q in rr),max(q['counts']['extra_pruned'] for q in rr)])
        profiles.append(x)
    nsum=dict(replays=len(native),all_complete_18_customers=all(int(q['completed_customers'])==18 and int(q['unfinished_customers'])==0 for q in native),red_or_yellow_stop_exposed_replays=sum(num(q,'red_or_yellow_signal_stopped_ticks')>0 for q in native),ped_proximity_exposed_replays=sum(num(q,'ped_near_vehicle_pair_ticks')>0 for q in native),crosswalk_occupied_replays=sum(num(q,'crosswalk_occupied_ticks_after_activation')>0 for q in native),recorded_collision_elements=sum(int(q['collision_xml_element_count']) for q in native),collision_warning_lines=sum(int(q['collision_warning_line_count']) for q in native),release_command_equals_last_handoff=all(abs(num(q,'truck_release_command_seconds')-num(q,'last_handoff_seconds'))<=EPS for q in native),actual_movement_after_release_range=[min(num(q,'truck_first_moving_seconds')-num(q,'truck_release_command_seconds') for q in native),max(num(q,'truck_first_moving_seconds')-num(q,'truck_release_command_seconds') for q in native)])
    result=dict(status='PASS',main=mainrows,arms=arms,profiles=profiles,native=nsum,all_same_budget_pair_rows=len(pairs),all_same_budget_strict_forecast_actual_reversals=sum(q['strict_direction_reversal']=='True' for q in pairs),scope='8 mothers, 64 related scenarios; one frozen epoch; representative replays; no online RAM measurement')
    dump('Summary.json',result);csvwrite('Main_Same_Engine.csv',mainrows);csvwrite('Arm_Budget_Summary.csv',arms);csvwrite('Profile_Costs.csv',profiles)
    files=[A/n for n in ('SUMMARY.json','PROCESS_COMPLETE.json','Case_Budget_Results.csv','Calls.csv','Pair_Cases.csv','Pair_Summary.csv','Mother_Pairs.csv','Native_Events.csv')]+[R/'runs/full_02/RESULTS.jsonl',R/'profiles/full_01/PROFILE.json',Path(__file__)]
    dump('Source_Hashes.json',{str(p):sha(p) for p in files})
    dump('PROCESS_COMPLETE.json',dict(status='PASS',summary_sha256=sha(OUT/'Summary.json')))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
