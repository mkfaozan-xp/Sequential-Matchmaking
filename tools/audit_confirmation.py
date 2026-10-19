"""Recompute the review's counts and distinguish facts from causal hypotheses."""
import argparse,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def audit():
 data=json.loads((ROOT/'results/coordinated/confirmation.json').read_text());rows=data['episodes']
 if len(rows)!=480 or not data['complete'] or not data['all_valid']:raise ValueError('confirmation incomplete')
 zero=[r for r in rows if r['mutual_second_meeting_intention']==0]
 partition={'no_completed_date':sum(r['dates']==0 for r in zero),'completed_dates_without_qualifying_recorded_mutual_yes':sum(r['dates']>0 and r['auxiliary_recorded_mutual_yes']==0 for r in zero),'qualifying_recorded_mutual_yes_but_late_feedback':sum(r['auxiliary_recorded_mutual_yes']>0 for r in zero)}
 if sum(partition.values())!=len(zero):raise ValueError('nonexhaustive outcome partition')
 methods={}
 for method in ('conservative','coordinated'):
  selected=[r for r in rows if r['method']==method]
  methods[method]={'episodes':len(selected),'valid':sum(r['valid'] for r in selected),'games_with_success':sum(r['mutual_second_meeting_intention']>0 for r in selected),'official_couples':sum(r['mutual_second_meeting_intention'] for r in selected),'dates':sum(r['dates'] for r in selected),'served_member_world_instances':sum(r['served_members'] for r in selected),'mean_inference_seconds':statistics.mean(r['inference_seconds'] for r in selected),'mean_episode_wall_seconds':statistics.mean(r['wall_seconds'] for r in selected)}
 return {'schema_version':1,'valid_episodes':480,'games_with_success':480-len(zero),'zero_score_games':len(zero),'zero_score_partition':partition,'no_date_subdivision':{'no_mutual_introduction_acceptance':sum(r['dates']==0 and r['mutual_acceptances']==0 for r in zero),'mutual_acceptance_but_no_completed_date':sum(r['dates']==0 and r['mutual_acceptances']>0 for r in zero)},'methods':methods,'timing_math':{'individual_timely_probability':.6,'both_timely_probability':.36,'ideal_fixed_n_at_least_one_point':{str(n):1-.64**n for n in range(1,8)},'assumptions':'Fixed number of qualifying within-window recorded mutual-Yes dates; independent uniform delays. Not a calibrated forecast of a stateful policy or random date count.'},'unsupported_causal_claims':['44 fewer dates proves waiting/continuation caused the gap','78 games are all explained by trait clash or hidden second bias','7 no-date games are explained by the 30-day scoring cutoff','dates must complete by decision day 60'],'primary_scoring':'Official qualifying-couple MSMI, not merely valid execution or games with at least one point.'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');a=p.parse_args();result=audit();target=ROOT/'results/review_audit.json'
 if a.write:target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 elif json.loads(target.read_text())!=result:raise ValueError('review audit no longer matches records')
 print(json.dumps({'passed':True,'valid_episodes':result['valid_episodes'],'successful_games':result['games_with_success'],'zero_score_partition':result['zero_score_partition']}));return 0

if __name__=='__main__':raise SystemExit(main())
