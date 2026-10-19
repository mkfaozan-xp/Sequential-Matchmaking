"""Frozen whole-game comparisons; one retained budget and no post-result tuning."""
import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime,timezone
import hashlib
import json
from multiprocessing import get_context
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research'));sys.path.insert(0,str(ROOT))
from blackbox.experiment import VARIANTS,summarise
from blackbox.metrics import paired_interval,calibration
from blackbox.registry import verified_episode_snapshot
from blackbox.storage import atomic_json,digest


def subject():
    files=[* (ROOT/'coordinated').glob('*.py'),ROOT/'coordinated/model.json',ROOT/'coordinated/release.json',ROOT/'coordinated/EXPERIMENT_PLAN.json',ROOT/'policy.py']
    return digest({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)})


def job(task,expected):
    if subject()!=expected:raise ValueError('candidate source/assets changed')
    from blackbox import experiment
    from coordinated import engine
    original=experiment.decide
    def choose(request,method):
        if method.startswith('coordinated'):
            ablation={'coordinated':None,'coordinated_myopic':'myopic','coordinated_constant':'constant'}[method]
            return engine.decide(request,ablation)
        return original(request,method)
    experiment.decide=choose
    try:
        with verified_episode_snapshot():row,joint,_,_=experiment.run_episode(*task)
    finally:experiment.decide=original
    if task[2].startswith('coordinated'):
        from blackbox.ranking import project
        import math
        model=engine.load_model();head=model['reward'];pred=[];aux=[]
        for r in joint:
            if task[2]=='coordinated_constant':p=model['official_prevalence']/model['timeliness_factor']
            else:
                x=project(r['x'],'reference');z=head['intercept']+sum(w*v for w,v in zip(head['weights'],x))
                p=1/(1+math.exp(-max(-40,min(40,z))))
            pred.append({'prediction':p*model['timeliness_factor'],'label':r['label']})
            aux.append({'prediction':p,'label':r['auxiliary_label']})
        row['inherited_reference_calibration']=row['calibration'];row['calibration']=calibration(pred)
        row['auxiliary_calibration']=calibration(aux)
        row['calibration_note']='Actual coordinated reward model on its selected introduced pairs. This is selected-action calibration, not population or causal validation. Directional reference probabilities are inherited diagnostics.'
    if subject()!=expected:raise ValueError('candidate changed during episode')
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--matrix',choices=['validation','final'],required=True)
    p.add_argument('--budget-origin',type=Path,required=True)
    a=p.parse_args();plan=json.loads((ROOT/'coordinated/EXPERIMENT_PLAN.json').read_text())
    config=plan[a.matrix];expected=subject();target=ROOT/'results/coordinated'/(a.matrix+'.json')
    if target.exists():raise ValueError('matrix is already recorded; do not silently overwrite or reset')
    origin=json.loads(a.budget_origin.read_text());deadline=datetime.fromisoformat(origin['started_utc']).timestamp()+origin['budget_seconds']
    tasks=[(s,v,m) for s in config['seeds'] for v in config['variants'] for m in config['methods']]
    rows=[];started=time.monotonic();error=None;pending={};cursor=0
    def save():
        ordered=sorted(rows,key=lambda r:(r['seed'],r['variant'],r['method']))
        result={'schema_version':1,'source_and_assets_sha256':expected,'plan_sha256':hashlib.sha256((ROOT/'coordinated/EXPERIMENT_PLAN.json').read_bytes()).hexdigest(),
          'scope':'Fresh frozen full-game comparison; no candidate selection or refit from outcomes.',
          'matrix':a.matrix,'config':config,'complete':len(rows)==len(tasks),'expected_episodes':len(tasks),
          'all_valid':len(rows)==len(tasks) and all(r['valid'] for r in rows),'episodes':ordered,
          'error':error,'elapsed_seconds':time.monotonic()-started,
          'summaries':{m:summarise([r for r in rows if r['method']==m]) for m in config['methods']},
          'paired_vs_conservative':{m:paired_interval(rows,m) for m in config['methods'] if m!='conservative'},
          'budget_origin':origin,'actual_docker':False}
        atomic_json(target,result);return result
    with ProcessPoolExecutor(max_workers=2,mp_context=get_context('spawn')) as pool:
        while cursor<len(tasks) or pending:
            if time.time()>=deadline:
                error='Retained global 120-minute budget exhausted.';save();return 2
            while cursor<len(tasks) and len(pending)<2:
                task=tasks[cursor];cursor+=1;pending[pool.submit(job,task,expected)]=task
            done,_=wait(pending,timeout=1,return_when=FIRST_COMPLETED)
            for future in done:
                task=pending.pop(future)
                try:row=future.result()
                except Exception as failure:
                    row={'seed':task[0],'variant':task[1],'method':task[2],'valid':False,'error':type(failure).__name__+': '+str(failure)}
                rows.append(row);save()
                print(json.dumps({'completed':len(rows),'expected':len(tasks),'seed':task[0],'variant':task[1],
                                  'mode':task[2],'valid':row['valid'],'msmi':row.get('mutual_second_meeting_intention'),'error':row.get('error')}),flush=True)
    result=save();return 0 if result['all_valid'] else 2


if __name__=='__main__':raise SystemExit(main())
