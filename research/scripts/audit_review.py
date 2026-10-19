"""Recompute the supplied review's historical numbers without transferring evidence."""
import json,zipfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.storage import atomic_json

def main():
    old=ROOT/'evidence/v0_5/results'
    final=json.loads((old/'final_test.json').read_text());secondary=json.loads((old/'secondary_test.json').read_text())
    with zipfile.ZipFile(ROOT/'evidence/Blackbox_ML_Prototype_v0_5_0_original.zip') as z:
        pointer=json.loads(z.read('Blackbox_ML_Prototype/artifacts/deployment.json'))
        model=json.loads(z.read('Blackbox_ML_Prototype/artifacts/releases/'+pointer['release_id']+'/model.json'))
    stage=('assignments','mutual_acceptances','dates','mutual_second_meeting_intention')
    funnel={m:{k:sum(r[k] for r in final['episodes'] if r['method']==m) for k in stage} for m in final['methods']}
    families={v:{m:sum(r['mutual_acceptances'] for r in final['episodes'] if r['method']==m and r['variant']==v)
                  for m in final['methods']} for v in final['variants']}
    noise=('emotional_availability','space_for_relationship','relocate')
    soft=noise+('relationship_goal','relationship_pace','lifestyle','conversations')
    heads=list(zip(model['joint']['feature_names'],model['joint']['weights']))
    noise_l1=sum(abs(w) for n,w in heads if any(k in n for k in noise))
    soft_l1=sum(abs(w) for n,w in heads if any(k in n for k in soft));total_l1=sum(abs(w) for _,w in heads)
    by_world={}
    for r in final['episodes']:by_world.setdefault((r['seed'],r['variant']),{})[r['method']]=r
    changed=sum(v['conservative']['action_sha256']!=v['hybrid']['action_sha256'] for v in by_world.values())
    result={'historical_version':'v0.5','funnel':funnel,'family_mutual_acceptances':families,
        'joint_dimensions':len(model['joint']['weights']),'noise_named_soft_coefficient_l1':noise_l1,
        'other_soft_coefficient_l1':soft_l1-noise_l1,'fraction_of_soft_l1':noise_l1/soft_l1,
        'fraction_of_all_coefficient_l1':noise_l1/total_l1,'changed_action_worlds':changed,
        'secondary_complete':secondary['complete'],'secondary_saved':len(secondary['episodes']),
        'secondary_counts':{m:sum(r['method']==m for r in secondary['episodes']) for m in secondary['methods']},
        'corrections':['Coefficient magnitude and partial logit examples do not identify causal roots or full pair rankings.',
            'The main joint head was already trained on official MSMI, not on initial acceptance.',
            'Late positive replies are observed failures of the official deadline target, not corrupted labels or right-censoring.',
            'No-response is not a negative psychological preference; auxiliary targets explicitly mean recorded outcomes.',
            '0.36 timely probability is conditional on two answering Yes and eligible timing, not 36% of all dates.',
            'Accepted scheduled hold spans 8–27 days in development and up to39 in delayed, not universally14–27.',
            'Extra pair acceptances are not necessarily90 distinct people or demonstrated non-goal ties.',
            'Initial response history reflects selection, response rate and compatibility, not a pure latent-bias measurement.',
            'AUROC is ranking, not accuracy; two validation pools cannot establish inferiority to chance.',
            'The105/120 follow-up is incomplete with different method case counts; it cannot be called a completed final loss.',
            'Day-keyed deterministic randomness stays unchanged; fresh paired worlds and seed-block intervals address uncertainty.']}
    atomic_json(ROOT/'results/gemini_review_audit.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
