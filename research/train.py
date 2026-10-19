"""V0.6 recorded-outcome training; immutable publication never promotes a policy."""
import argparse,importlib.metadata,json,math,os,platform,time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1');os.environ.setdefault('MKL_NUM_THREADS','1')
from blackbox.fitting import fit,fit_constant,select_fit,select_duration
from blackbox.features import NAMES,DIRECTION_NAMES,FEATURE_VERSION
from blackbox.experiment import run_episode,VARIANTS
from blackbox.cache import collection_identity,load,save
from blackbox.registry import publish,select,sha,feature_digest
from blackbox.provenance import source_hash
from blackbox.storage import atomic_json,digest,WorkflowLock
ROOT=Path(__file__).resolve().parent

def bootstrap():
    """Explicit untrained assets permit non-learned collectors after schema change."""
    def head(names,p):return {'feature_names':names,'basis':'identity','weights':[0.0]*len(names),
        'intercept':math.log(p/(1-p)),'n':0,'positives':0,'training_prevalence':p,'l1':0,'l2':None,
        'estimator':'untrained_bootstrap','optimizer_converged':True}
    model={'schema_version':'1.0.0','feature_version':FEATURE_VERSION,'model_id':'untrained-v06-bootstrap',
        'basis_source_sha256':sha(ROOT/'blackbox/basis.py'),'feature_source_sha256':feature_digest(),'joint':head(NAMES,.01),'direction':head(DIRECTION_NAMES,.4),
        'auxiliary':head(NAMES,.03),'joint_ridge':head(NAMES,.01),'joint_nohistory':head(NAMES,.01),
        'duration':dict(head(NAMES,.5),kind='scheduled_hold_proxy_days',constant_days=8,use_constant=True),
        'timeliness_factor':1.0,'status':'untrained_not_evaluation_evidence'}
    _,donors,inputs=public_training()
    rid=publish(model,{'donors':donors,'public_training_inputs':inputs,'warning':'untrained model bootstrap; public train donors only'}, {'status':'untrained','source_sha256':source_hash()})
    select(rid,'conservative');return rid

def collect_one(task):
    seed,variant=task;method={0:'baseline_random',1:'baseline_greedy',2:'soft_collect',3:'explore_collect'}[seed%4]
    identity=collection_identity(seed,variant,method);key=digest(identity);path=ROOT/'artifacts/training_cache'/f'{key}.json'
    record=load(path,identity)
    if record is None:
        metrics,joint,direction,donors=run_episode(seed,variant,method,collect=True)
        record={'metrics':metrics,'joint':joint,'direction':direction,'donors':donors};save(path,identity,record)
    return key,record

def public_training():
    from official_data_training.train_public import rows_for_pool
    manifest=json.loads((ROOT/'starter/data_manifest.json').read_text());checks=json.loads((ROOT/'starter/data_checksums.json').read_text())
    splits=[set(manifest['splits'][k]) for k in ('train','validation','development_test')]
    if any(splits[i]&splits[j] for i in range(3) for j in range(i)):raise ValueError('overlapping public splits')
    rows=[];donors=[];inputs={}
    from blackbox.domain import HARD
    for pool in manifest['splits']['train']:
        name='data/'+pool+'/state.json';path=ROOT/'starter'/name
        if sha(path)!=checks[name]:raise ValueError('public training checksum mismatch')
        state=json.loads(path.read_text());actual,_=rows_for_pool(state,pool)
        rows.extend(actual);inputs[name]=sha(path)
        for m in state['members']:
            if all(m['fields'][k] is not None for k in HARD):
                donors.append({'age':m['age'],'zone':m['zone'],'fields':{k:m['fields'][k] for k in HARD}})
    return rows,donors,inputs

def run(args):
    seeds=[int(s) for s in args.seeds.split(',')]
    if len(seeds)<3 or len(set(seeds))!=len(seeds) or any(not 1101<=s<=1150 for s in seeds):
        raise ValueError('unique training seeds 1101–1150 required')
    started=time.perf_counter();rows=[];directions=[];donors=[];episodes=[];cache_ids=[]
    tasks=[(s,v) for s in seeds for v in VARIANTS]
    with ProcessPoolExecutor(max_workers=args.jobs,mp_context=get_context('spawn')) as pool:
        for key,record in pool.map(collect_one,tasks):
            rows.extend(record['joint']);directions.extend(record['direction']);donors.extend(record['donors'])
            episodes.append(record['metrics']);cache_ids.append(key)
            print(json.dumps({'collected':len(episodes),'expected':len(tasks),'seed':record['metrics']['seed'],
                'variant':record['metrics']['variant'],'joint_rows':len(rows)}),flush=True)
    public_rows,public_donors,public_inputs=public_training();directions.extend(public_rows);donors.extend(public_donors)
    if any(r.get('auxiliary_label') is None or r.get('hold_days') is None for r in rows):
        raise ValueError('new cohort labels missing; old cache must not be padded')
    auxiliary=[dict(r,label=r['auxiliary_label']) for r in rows]
    joint,joint_cv=select_fit(rows,NAMES);direction,direction_cv=select_fit(directions,DIRECTION_NAMES)
    aux,aux_cv=select_fit(auxiliary,NAMES)
    ridge,ridge_cv=select_fit(rows,NAMES,[('identity',0,10),('identity',0,100)])
    nohistory,nohistory_cv=select_fit(rows,NAMES,[('without_outcome_history',0,10),('without_outcome_history',2,10)])
    duration,duration_cv=select_duration(rows,NAMES)
    any_yes=sum(r['label'] for r in auxiliary);timely=sum(r['label'] for r in rows)
    factor=(timely+1)/(any_yes+2)
    config={'seeds':seeds,'variants':list(VARIANTS),'feature_version':FEATURE_VERSION,'cache_ids':cache_ids,
        'protocol_sha256':sha(ROOT/'plans/REVIEW_PROTOCOL.md'),
        'data_hash':digest(rows),'direction_hash':digest(directions),'public_training_inputs':public_inputs,
        'collection':'seed mod4 supplied random / greedy / soft-fill / uniform feasible-edge',
        'selection_scope':'training seed/pool groups only','public_direction_rows':len(public_rows),'public_donors':len(public_donors)}
    lineage={'source_sha256':source_hash(),'python':platform.python_version(),'packages':{p:importlib.metadata.version(p) for p in ('numpy','scipy')},
        'platform':platform.platform(),'training':config}
    model={'schema_version':'1.0.0','feature_version':FEATURE_VERSION,'model_id':'outcome-v06-'+digest({'config':config,'lineage':lineage})[:16],
        'basis_source_sha256':sha(ROOT/'blackbox/basis.py'),'feature_source_sha256':feature_digest(),'joint':joint,'direction':direction,'auxiliary':aux,
        'joint_ridge':ridge,'joint_nohistory':nohistory,'duration':duration,'timeliness_factor':factor,'config':config,
        'status':'experimental_not_promoted','assumptions':['Auxiliary timeliness factor assumes transfer of recorded timeliness conditional on mutual Yes.',
        'Scheduled hold proxy excludes hidden exits and success-related retirement; it is not a verified optimal opportunity cost.',
        'Only selected recorded introductions are labelled; no IPS or causal claim.']}
    answers={'donors':list({digest(d):d for d in donors}.values()),'training_seeds':seeds,'public_training_inputs':public_inputs,
        'assumptions':['Disclosed bundles only, biased support; hypothetical answers never authorize real eligibility.']}
    release=publish(model,answers,lineage)
    atomic_json(ROOT/'artifacts/candidate.json',{'release_id':release,'model_id':model['model_id'],'promoted':False})
    if args.activate_candidate:select(release,'conservative')
    atomic_json(ROOT/'results/training.json',{'identity':lineage,'config':config,'episodes':episodes,'joint_rows':len(rows),
        'joint_positives':timely,'auxiliary_positives':any_yes,'direction_rows':len(directions),'donor_count':len(answers['donors']),
        'release_id':release,'wall_seconds':time.perf_counter()-started,'candidate_promoted':False})
    atomic_json(ROOT/'results/model_selection.json',{'release_id':release,'config':config,'joint':joint_cv,'direction':direction_cv,
        'auxiliary':aux_cv,'joint_ridge':ridge_cv,'joint_nohistory':nohistory_cv,'duration':duration_cv,
        'timeliness_factor':factor,'timeliness_training_counts':{'official':timely,'auxiliary':any_yes}})
    print(json.dumps({'release_id':release,'official_positives':timely,'auxiliary_positives':any_yes}),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',default=','.join(map(str,range(1101,1149))))
    p.add_argument('--jobs',type=int,choices=(1,2),default=2);p.add_argument('--activate-candidate',action='store_true')
    p.add_argument('--bootstrap-only',action='store_true');a=p.parse_args()
    with WorkflowLock(ROOT/'artifacts/training_workflow.lock'):
        if a.bootstrap_only:print(bootstrap())
        else:run(a)

if __name__=='__main__':main()
