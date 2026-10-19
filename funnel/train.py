"""Fixed staged models on exact observed labels; no new outcome collection."""
import gzip,hashlib,json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'));sys.path.insert(0,str(ROOT/'tools'))
from train_model import dataset
from blackbox.ranking import project,rank_names
from blackbox.fitting import fit,folds_for
from blackbox.metrics import calibration

def probability(head,x):return 1/(1+math.exp(-max(-40,min(40,head['intercept']+sum(w*v for w,v in zip(head['weights'],x))))))

def main():
 started=time.monotonic();raw,*_=dataset();names=rank_names('reference');indices=[i for i,n in enumerate(names) if n.startswith(('relationship_goal:','outcome:'))];conversion_names=[names[i] for i in indices]
 with gzip.open(ROOT/'research/artifacts/datasets/v06_observations.json.gz','rt') as f:bundle=json.load(f)
 responses={}
 for item in bundle['records'].values():
  for row in item['record']['payload']['direction']:responses.setdefault(row['row_id'].rsplit(':',1)[0],[]).append(row)
 rows=[]
 for row in raw:
  direction=responses[row['row_id']]
  if len(direction)!=2 or any(r['x'][:len(row['x'])]!=row['x'] for r in direction):raise ValueError('direction/introduced-pair alignment')
  accepted=int(all(r['label']==1 for r in direction))
  if row['auxiliary_label']>accepted:raise ValueError('positive outcome without recorded acceptance')
  rows.append(dict(row,x=project(row['x'],'reference'),accepted=accepted))
 def heads(train):
  a=fit([dict(r,label=r['accepted']) for r in train],names,l2=100)
  c=fit([dict(r,x=[r['x'][i] for i in indices],label=r['auxiliary_label']) for r in train if r['accepted']],conversion_names,l2=100)
  return a,c
 official=[];aux=[];folds=[]
 for seeds in folds_for(rows):
  train=[r for r in rows if r['seed'] not in seeds];held=[r for r in rows if r['seed'] in seeds];a,c=heads(train);factor=sum(r['label'] for r in train)/sum(r['auxiliary_label'] for r in train)
  preds=[probability(a,r['x'])*probability(c,[r['x'][i] for i in indices]) for r in held]
  official.extend({'prediction':p*factor,'label':r['label']} for p,r in zip(preds,held));aux.extend({'prediction':p,'label':r['auxiliary_label']} for p,r in zip(preds,held))
  folds.append({'held_out_seeds':seeds,'training_rows':len(train),'accepted_training_rows':sum(r['accepted'] for r in train),'acceptance_converged':a['optimizer_converged'],'conversion_converged':c['optimizer_converged']})
 a,c=heads(rows);inherited=json.loads((ROOT/'coordinated/model.json').read_text());model={'schema_version':1,'model_id':'funnel-v1','feature_names':names,'conversion_indices':indices,'acceptance':a,'conversion':c,'hold':inherited['hold'],'timeliness_factor':sum(r['label'] for r in rows)/sum(r['auxiliary_label'] for r in rows),'training_rows':len(rows),'lineage':inherited['lineage'],'plan_sha256':hashlib.sha256((ROOT/'funnel/PLAN.json').read_bytes()).hexdigest(),'scope':'Selected historical introduced pairs; observed acceptance labels; no causal/population calibration claim.'}
 model['model_id']='funnel-'+hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()[:16]
 path=ROOT/'funnel/model.json';path.write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
 result={'rows':len(rows),'accepted_pairs':sum(r['accepted'] for r in rows),'auxiliary_positive_pairs':sum(r['auxiliary_label'] for r in rows),'official_positive_pairs':sum(r['label'] for r in rows),'features':{'acceptance':len(names),'conversion':len(indices)},'official_oof':calibration(official),'auxiliary_oof':calibration(aux),'folds':folds,'elapsed_seconds':time.monotonic()-started,'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scope':'Whole-seed training-only diagnostics, not policy-win evidence.'}
 (ROOT/'results/funnel').mkdir(exist_ok=True);(ROOT/'results/funnel/training.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({k:result[k] for k in ['rows','accepted_pairs','features','elapsed_seconds']}));print('official OOF',result['official_oof']['log_loss'])

if __name__=='__main__':main()
