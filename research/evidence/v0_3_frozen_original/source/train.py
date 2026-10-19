"""Content-identified collection, regularized fitting, immutable candidate publication."""
import argparse
import importlib.metadata
import json
import math
import platform
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from blackbox.features import NAMES, DIRECTION_NAMES, FEATURE_VERSION
from blackbox.experiment import run_episode, VARIANTS
from blackbox.storage import atomic_json, digest
from blackbox.cache import collection_identity, load, save
from blackbox.registry import publish, select
from blackbox.provenance import source_hash
ROOT=Path(__file__).resolve().parent

def fit(rows,names,l2=10):
    if not rows or len({r['label'] for r in rows})<2:raise ValueError('need both label classes')
    x=np.array([r['x'] for r in rows]);y=np.array([r['label'] for r in rows],dtype=float)
    # Sum loss + L2, no class reweighting that distorts the rare-event base rate.
    def objective(theta):
        z=theta[0]+x@theta[1:];loss=np.logaddexp(0,z).sum()-y@z+(l2/2)*np.dot(theta[1:],theta[1:])
        p=1/(1+np.exp(-np.clip(z,-40,40)));g=np.r_[(p-y).sum(),x.T@(p-y)+l2*theta[1:]]
        return loss,g
    init=np.zeros(x.shape[1]+1);init[0]=math.log((y.sum()+.5)/(len(y)-y.sum()+.5))
    result=minimize(objective,init,jac=True,method='L-BFGS-B',options={'maxiter':400,'ftol':1e-10})
    if not result.success:raise RuntimeError(result.message)
    return {'feature_names':names,'intercept':float(result.x[0]),'weights':result.x[1:].tolist(),
        'n':len(rows),'positives':int(y.sum()),'training_prevalence':float(y.mean()),'l2':l2,'optimizer_converged':True}


def select_fit(rows,names):
    """Leave one whole training seed out; no validation/final outcomes enter selection."""
    from blackbox.metrics import calibration
    from blackbox.model import sigmoid
    seeds=sorted({r['seed'] for r in rows})
    if len(seeds)<3:raise ValueError('At least three training seed blocks required for regularization selection')
    candidates=[]
    for l2 in (1,10,100):
        folds=[]
        for seed in seeds:
            training=[r for r in rows if r['seed']!=seed]
            held=[r for r in rows if r['seed']==seed]
            head=fit(training,names,l2)
            predictions=[{'prediction':sigmoid(head['intercept']+sum(w*x for w,x in zip(head['weights'],r['x']))),'label':r['label']} for r in held]
            score=calibration(predictions)
            constant=calibration([{'prediction':head['training_prevalence'],'label':r['label']} for r in held])
            folds.append({'held_out_seed':seed,'training_seeds':[s for s in seeds if s!=seed],
                          'score':score,'constant_baseline':constant})
        # Equal weight per independent seed block, not per selected introduction.
        candidates.append({'l2':l2,'mean_seed_log_loss':sum(f['score']['log_loss'] for f in folds)/len(folds),'folds':folds})
    best=min(candidates,key=lambda c:(c['mean_seed_log_loss'],-c['l2']))
    head=fit(rows,names,best['l2'])
    diagnostics={'selection':'leave-one-training-seed-out log loss; stronger regularization breaks exact ties',
                 'selected_l2':best['l2'],'candidates':candidates,
                 'feature_mean':dict(zip(names,np.mean([r['x'] for r in rows],axis=0).tolist())),
                 'warning':'Selected introductions only. Predictive log loss is not evidence of policy MSMI superiority.'}
    return head,diagnostics


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seeds', default='1101,1102,1103,1104,1105,1106,1107,1108')
    parser.add_argument('--activate-candidate', action='store_true', help='Select candidate assets for offline evaluation; default policy remains conservative')
    args=parser.parse_args()
    seeds=[int(s) for s in args.seeds.split(',')]
    if len(seeds)<3 or len(set(seeds))!=len(seeds) or any(not 1101<=s<=1150 for s in seeds):
        parser.error('at least three unique training seeds 1101-1150 required')
    started=time.perf_counter()
    rows=[];directions=[];donors=[];episodes=[];cache_ids=[]
    for seed in seeds:
        for variant in VARIANTS:
            method='baseline_greedy' if seed%2 else 'baseline_random'
            identity=collection_identity(seed,variant,method)
            cache_id=digest(identity);cache_ids.append(cache_id)
            path=ROOT/'artifacts/training_cache'/f'{cache_id}.json'
            record=load(path,identity)
            if record is None:
                metrics,joint,directional,bundles=run_episode(seed,variant,method,collect=True)
                record={'metrics':metrics,'joint':joint,'direction':directional,'donors':bundles}
                save(path,identity,record)
            rows.extend(record['joint']);directions.extend(record['direction']);donors.extend(record['donors'])
            episodes.append(record['metrics'])
            print(json.dumps({'seed':seed,'variant':variant,'rows':len(rows),'positives':sum(r['label'] for r in rows),'cache_id':cache_id}),flush=True)
    joint_head,joint_selection=select_fit(rows,NAMES)
    direction_head,direction_selection=select_fit(directions,DIRECTION_NAMES)
    config={'seeds':seeds,'variants':list(VARIANTS),'l2':{'joint':joint_head['l2'],'direction':direction_head['l2']},
            'regularization_grid':[1,10,100],'selection_scope':'training seeds only','feature_version':FEATURE_VERSION,
            'data_hash':digest(rows),'direction_hash':digest(directions),'inference_seed':17,
            'selection':'odd-seed supplied greedy; even-seed supplied random','cache_ids':cache_ids}
    packages={name:importlib.metadata.version(name) for name in ('numpy','scipy')}
    lineage={'source_sha256':source_hash(),'python':platform.python_version(),'packages':packages,'platform':platform.platform(),'machine':platform.machine(),'training':config}
    model={'schema_version':'1.0.0','feature_version':FEATURE_VERSION,'model_id':'logit-'+digest({'config':config,'lineage':lineage})[:16],
           'config':config,'joint':joint_head,'direction':direction_head,
           'status':'experimental_not_promoted','selection_warning':'Selected introductions; null propensities. No unbiased IPS claims.'}
    unique={digest(d):d for d in donors}
    answers={'donors':list(unique.values()),'training_seeds':seeds,
             'assumptions':['Selected disclosed bundles; not an unbiased population model.',
             'Age offsets, own-zone transfer and retaining current observations are approximations.',
             'Stress mode changes hypothetical nondisclosure, not the true simulator.']}
    release_id=publish(model,answers,lineage)
    atomic_json(ROOT/'artifacts/candidate.json',{'release_id':release_id,'model_id':model['model_id'],'promoted':False})
    if args.activate_candidate:
        select(release_id,'conservative')
    result={'identity':lineage,'config':config,'episodes':episodes,'joint_rows':len(rows),
            'joint_positives':sum(r['label'] for r in rows),'direction_rows':len(directions),
            'donor_count':len(unique),'release_id':release_id,'wall_seconds':time.perf_counter()-started,
            'candidate_promoted':False}
    atomic_json(ROOT/'results/training.json',result)
    atomic_json(ROOT/'results/model_selection.json',{'release_id':release_id,'config':config,
        'joint':joint_selection,'direction':direction_selection})
    print(json.dumps({'model':model['model_id'],'release_id':release_id,'positives':model['joint']['positives']}))

if __name__=='__main__':main()
