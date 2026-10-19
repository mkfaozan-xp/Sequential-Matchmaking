"""Fixed fresh staged-scorer pilot; no candidate switching or budget reset."""
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime
import hashlib,json,sys,time
from multiprocessing import get_context
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
from blackbox.storage import atomic_json
from coordinated.evaluate import subject

def identity():return hashlib.sha256((ROOT/'funnel/release.json').read_bytes()).hexdigest()

def job(task,expected):
 if identity()!=expected:raise ValueError('funnel release changed')
 from blackbox import experiment
 from blackbox.registry import verified_episode_snapshot
 from blackbox.metrics import calibration
 from blackbox.ranking import project
 from funnel.controller import FunnelController
 controller=FunnelController();original=experiment.decide
 experiment.decide=lambda request,method:controller.decide(request) if method=='funnel' else original(request,method)
 try:
  with verified_episode_snapshot():row,joint,_,_=experiment.run_episode(*task)
 finally:experiment.decide=original
 if task[2]=='funnel':
  row['inherited_reference_calibration']=row['calibration'];row['calibration']=calibration([{'prediction':controller.predict_x(project(r['x'],'reference')),'label':r['label']} for r in joint]);row['calibration_note']='Actual staged scorer on its selected introduced pairs; not population or causal calibration.'
 if identity()!=expected:raise ValueError('funnel release changed during episode')
 return row

def main():
 plan_path=ROOT/'funnel/EVALUATION_PLAN.json';plan=json.loads(plan_path.read_text());expected=identity()
 if expected!=plan['release_sha256'] or subject()!=plan['original_subject_sha256']:raise ValueError('evaluation subject mismatch')
 path=ROOT/'results/funnel/pilot.json'
 if path.exists():raise ValueError('do not overwrite pilot')
 origin=json.loads((ROOT/'evidence/coordinated/budget_origin.json').read_text());deadline=datetime.fromisoformat(origin['started_utc']).timestamp()+origin['budget_seconds']
 tasks=[(s,v,m) for s in plan['seeds'] for v in plan['families'] for m in plan['methods']];rows=[];started=time.monotonic();error=None
 def save():
  complete=len(rows)==len(tasks)
  result={'complete':complete,'all_valid':complete and all(r['valid'] for r in rows),'expected_episodes':24,'episodes':rows,'release_sha256':expected,'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'elapsed_seconds':time.monotonic()-started,'error':error,'budget_origin':origin,'summaries':{m:{'episodes':sum(r['method']==m for r in rows),'official_successful_pairs':sum(r.get('mutual_second_meeting_intention',0) for r in rows if r['method']==m),'episodes_with_success':sum(r.get('mutual_second_meeting_intention',0)>0 for r in rows if r['method']==m)} for m in plan['methods']},'promoted':False,'scope':'Two fresh seed blocks only, twelve paired worlds; no reliable superiority or 450/480 claim.'}
  atomic_json(path,result)
 pending={};cursor=0
 with ProcessPoolExecutor(max_workers=2,mp_context=get_context('spawn')) as pool:
  while cursor<len(tasks) or pending:
   if time.time()>=deadline:error='Original retained two-hour budget exhausted';save();return 2
   while cursor<len(tasks) and len(pending)<2:
    task=tasks[cursor];cursor+=1;pending[pool.submit(job,task,expected)]=task
   done,_=wait(pending,timeout=1,return_when=FIRST_COMPLETED)
   for future in done:
    pending.pop(future);row=future.result();
    key=(row['seed'],row['variant'],row['method'])
    if any((r['seed'],r['variant'],r['method'])==key for r in rows):raise ValueError('duplicate episode result')
    rows.append(row);save();print(json.dumps({'completed':len(rows),'method':row['method'],'valid':row['valid']}),flush=True)
 save();return 0

if __name__=='__main__':raise SystemExit(main())
