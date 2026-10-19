"""Fit the frozen clean outcome/hold models on verified historical observations."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research'))
sys.path.insert(0,str(ROOT))
import numpy as np
from blackbox.fitting import fit,fit_constant,predictions,folds_for
from blackbox.metrics import calibration
from blackbox.ranking import project,rank_names
from blackbox.storage import digest
from scripts.train_rankers import dataset


def sha(raw):return hashlib.sha256(raw).hexdigest()


def hold_fit(rows):
    x=np.asarray([r['x'] for r in rows]);y=np.asarray([r['hold_days']/40 for r in rows])
    center=x.mean(axis=0);mean=y.mean();xc=x-center
    w=np.linalg.solve(xc.T@xc+1000*np.eye(x.shape[1]),xc.T@(y-mean))
    return {'weights':w.tolist(),'intercept':float(mean-center@w),'constant_days':float(mean*40),
            'l2':1000,'bounds':[8,40],'target':'recorded scheduled hold proxy, not hidden true availability'}


def hold_predict(head,x):return max(8,min(40,40*(head['intercept']+sum(w*v for w,v in zip(head['weights'],x)))))


def main():
    started=time.monotonic();raw,_,_,_,lineage=dataset();names=rank_names('reference')
    rows=[dict(r,x=project(r['x'],'reference'),label=r['auxiliary_label']) for r in raw]
    reward_preds=[];constant_preds=[];official_preds=[];official_constant=[];folds=[]
    for group in folds_for(rows):
        train=[r for r in rows if r['seed'] not in group];held=[r for r in rows if r['seed'] in group]
        head=fit(train,names,l2=100);constant=fit_constant(train,names);duration=hold_fit(train)
        pp=predictions(held,head,names);cp=predictions(held,constant,names)
        reward_preds.extend(pp);constant_preds.extend(cp)
        official_by_id={r['row_id']:r['label'] for r in raw}
        timely=sum(official_by_id[r['row_id']] for r in train)/sum(r['label'] for r in train)
        official_preds.extend({'prediction':p['prediction']*timely,'label':official_by_id[r['row_id']]} for r,p in zip(held,pp))
        official_constant.extend({'prediction':constant['training_prevalence']*timely,'label':official_by_id[r['row_id']]} for r in held)
        folds.append({'held_out_seeds':group,'training_seeds':sorted({r['seed'] for r in train}),
          'reward':calibration(pp),'constant':calibration(cp),
          'hold_mse':sum((hold_predict(duration,r['x'])-r['hold_days'])**2 for r in held)/len(held),
          'constant_hold_mse':sum((duration['constant_days']-r['hold_days'])**2 for r in held)/len(held),
          'optimizer_converged':head['optimizer_converged']})
    head=fit(rows,names,l2=100);hold=hold_fit(rows)
    factor=sum(r['label'] for r in raw)/sum(r['auxiliary_label'] for r in raw)
    model={'schema_version':1,'feature_names':names,'reward':head,'hold':hold,'timeliness_factor':factor,
      'official_prevalence':sum(r['label'] for r in raw)/len(raw),
      'projection':'reference','training_rows':len(rows),'lineage':lineage,
      'plan_sha256':sha((ROOT/'coordinated/EXPERIMENT_PLAN.json').read_bytes()),
      'target_scope':'Mature selected introduced pairs; no unchosen outcomes or population/causal calibration claim.'}
    model['model_id']='coordinated-'+digest(model)[:16]
    target=ROOT/'coordinated/model.json';target.write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    release={'model_sha256':sha(target.read_bytes()),'model_id':model['model_id'],
      'runtime_source':{name:sha((ROOT/'coordinated'/name).read_bytes()) for name in ['__init__.py','engine.py']},
      'status':'experimental_not_promoted','original_inherited_artifacts_unchanged':True}
    (ROOT/'coordinated/release.json').write_text(json.dumps(release,indent=2,sort_keys=True)+'\n')
    result={'model_id':model['model_id'],'model_sha256':release['model_sha256'],'n':len(rows),
      'auxiliary_positives':sum(r['label'] for r in rows),'official_positives':sum(r['label'] for r in raw),
      'features':len(names),'nonzero_weights':head['nonzero_weights'],'new_collection_episodes':0,
      'reward_oof':calibration(reward_preds),'constant_oof':calibration(constant_preds),
      'official_scaled_oof':calibration(official_preds),'official_constant_oof':calibration(official_constant),
      'folds':folds,'selected_estimator':'Fixed ridge L2=100; no outcome-driven hyperparameter selection.',
      'elapsed_seconds':time.monotonic()-started,'python':platform.python_version(),
      'packages':{'numpy':np.__version__},'lineage':lineage}
    (ROOT/'results/coordinated/training.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ['model_id','n','features','nonzero_weights','elapsed_seconds']}))
    return 0


if __name__=='__main__':raise SystemExit(main())
