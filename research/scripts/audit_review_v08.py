"""Numerically verify review claims without modifying any fitted policy."""
import json,gzip,sys,zipfile,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.features import NAMES
from blackbox.ranking import SIGNALS,RANK_NAMES,project,contrasts,heuristic_score,rank_names
from blackbox.provenance import execution_identity
from blackbox.registry import load_artifact,sha
from blackbox.storage import atomic_json

def main():
 archive=ROOT/'evidence/Blackbox_ML_Prototype_v0_7_0_original.zip'
 if sha(archive)!='4c152ced222c8d066c26b6e6a10e707651737cdae82d5a86999f311cc8407685':raise ValueError('v0.7 archive mismatch')
 with zipfile.ZipFile(archive) as z:
  pointer=json.loads(z.read('Blackbox_ML_Prototype/artifacts/deployment.json'));old=json.loads(z.read('Blackbox_ML_Prototype/artifacts/releases/'+pointer['release_id']+'/model.json'));old_budget=json.loads(z.read('Blackbox_ML_Prototype/evidence/v0_7_preparation/budget_accounting.json'))
 model=load_artifact('model.json');legacy=model['rank_legacy_aux'];h=old['rank_auxiliary']
 amended=ROOT/'evidence/v0_8_prepackage_amendment/training.json'
 if amended.exists():
  original=json.loads(amended.read_text());before=json.loads((ROOT/'artifacts/releases'/original['release_id']/'model.json').read_text())
  for name in ('rank_official','rank_auxiliary','rank_reference','rank_nohistory'):
   if before[name]['weights']!=model[name]['weights'] or before[name]['intercept']!=model[name]['intercept']:raise ValueError('source-only packaging repair changed fitted coefficients')
 if legacy['weights']!=h['weights'] or legacy['intercept']!=h['intercept']:raise ValueError('historical control changed')
 with gzip.open(ROOT/'artifacts/datasets/v06_observations.json.gz','rt') as f:data=json.load(f)
 rows=[row for item in data['records'].values() for row in item['record']['payload']['joint']];byid={r['row_id']:r for r in rows};weights=dict(zip(RANK_NAMES,h['weights']))
 reference={n:weights[n]-(weights[n.split(':')[0]+':missing'] if n.split(':')[0] in SIGNALS else 0) for n in rank_names('reference')};shift=sum(weights[k+':missing'] for k in SIGNALS);error=0
 for row in rows:
  original=h['intercept']+sum(w*x for w,x in zip(h['weights'],project(row['x'])))
  coded=h['intercept']+shift+sum(reference[n]*x for n,x in zip(rank_names('reference'),project(row['x'],'reference')))
  error=max(error,abs(original-coded))
 if error>1e-12:raise ValueError('reference equivalence failed')
 cohorts={}
 for target in ('label','auxiliary_label'):
  unmatched=[p for p in contrasts(rows,target,same_score=False) if p['label']==1];matched=[p for p in contrasts(rows,target,same_score=True) if p['label']==1]
  if any(p['positive_heuristic_score']!=p['negative_heuristic_score'] for p in matched):raise ValueError('cross-score training pair')
  cohorts[target]={'legacy_forward_contrasts':len(unmatched),'legacy_cross_score':sum(p['positive_heuristic_score']!=p['negative_heuristic_score'] for p in unmatched),
    'matched_forward_contrasts':len(matched),'matched_positives':len({p['positive_row_id'] for p in matched}),'raw_positives':sum(r[target] for r in rows)}
 rates={}
 for value in ('agree','disagree','missing'):
  cohort=[r for r in rows if r['x'][NAMES.index('relationship_goal:'+value)]==1];rates[value]={'rows':len(cohort),'auxiliary_yes':sum(r['auxiliary_label'] for r in cohort)}
 record={'identity':execution_identity(),'observed_rows':len(rows),'historical_source':'exact v0.7 archive; no new game-performance claim',
  'reference_feature_dimensions':len(rank_names('reference')),'reference_equivalence_max_logit_error':error,
  'goal_original_weights':{s:weights['relationship_goal:'+s] for s in ('agree','disagree','missing')},
  'goal_reference_weights':{s:reference['relationship_goal:'+s] for s in ('agree','disagree')},'cohorts':cohorts,'goal_observed_auxiliary_cohorts':rates,
  'original_v07_allocation_seconds':old_budget['maximum_current_workflow_seconds'],'legacy_control_coefficients_identical':True,'packaging_amendment_coefficients_unchanged':bool(amended.exists()),
  'corrections':['Reference coding yields32 dimensions, not28.','Dropping a dummy does not enforce agreement >= missing.','Constant translation cancels in contrasts.','History rate0.5 does not imply no past date.','Retirement/selected cohorts do not prove the cause of the pilot loss.','Official late failures remain official failures; auxiliary target is separate.']}
 atomic_json(ROOT/'results/review_audit.json',record);print(json.dumps(record))
if __name__=='__main__':raise SystemExit(main())
