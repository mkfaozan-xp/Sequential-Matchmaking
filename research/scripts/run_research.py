"""One bounded v0.8 build; earlier iterations remain historical evidence."""
import argparse,json,os,sys,time,uuid,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_budget import execute_phases,cleanup_docker
from blackbox.runtime import runtime_info
from blackbox.storage import atomic_json,WorkflowLock,RunBusy
from blackbox.provenance import execution_identity,source_hash

def main():
 p=argparse.ArgumentParser();p.add_argument('--minutes',type=float,default=120);p.add_argument('--bootstrap',action='store_true');p.add_argument('--skip-training',action='store_true');p.add_argument('--skip-docker',action='store_true');a=p.parse_args()
 if not 1<=a.minutes<=120:p.error('budget must be 1–120 minutes')
 runtime_info()
 try:
  with WorkflowLock(ROOT/'results/workflow.lock'):return run(a)
 except RunBusy as e:print(str(e),file=sys.stderr);return 3

def run(a):
 origin_path=ROOT/'results/workflow_origin.json';previous=ROOT/'results/budget_run.json'
 if origin_path.exists():
  origin=json.loads(origin_path.read_text());remaining=origin['deadline_unix']-time.time()
  if remaining<=60:raise ValueError('Original iteration deadline exhausted; preserve evidence rather than silently reset')
  pilot=ROOT/'results/selection_pilot.json'
  if pilot.exists() and json.loads(pilot.read_text()).get('config',{}).get('identity',{}).get('source_sha256')!=source_hash():raise ValueError('Post-pilot source change requires new declared seeds and preserved old evidence')
  if previous.exists():
   folder=ROOT/'evidence/v0_8_attempts'/json.loads(previous.read_text())['run_id'];folder.mkdir(parents=True,exist_ok=True)
   for file in (ROOT/'results').iterdir():
    if file.is_file() and file.suffix in ('.json','.log','.md'):shutil.copy2(file,folder/file.name)
 else:
  now=time.time();origin={'started_unix':now,'deadline_unix':now+a.minutes*60,'budget_seconds':a.minutes*60,'source_sha256':source_hash(),
   'scope':'New user-requested v0.8 build. Historical v0.6/v0.7 budgets are unchanged, not reset or reclassified.'};atomic_json(origin_path,origin);remaining=a.minutes*60
 started=time.monotonic();deadline=started+remaining;run_id=uuid.uuid4().hex
 env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',BLACKBOX_RUN_ID=run_id)
 record={'schema_version':7,'workflow':'v0.8 score-matched ranking and review ablations','run_id':run_id,'runtime':runtime_info(),
  'started_unix':time.time(),'budget_seconds':remaining,'origin':origin,'training_skipped':a.skip_training,'docker_skipped':a.skip_docker,
  'maximum_episode_workers':2,'new_collection_episodes':0,'status':'running','phases':[]}
 py=sys.executable;phases=[]
 if a.bootstrap:
  v=ROOT/'.venv';phases += [('create_environment',[py,'-m','venv',str(v)],180,True)];py=str(v/('Scripts/python.exe' if os.name=='nt' else 'bin/python'));phases += [('install_dependencies',[py,'-m','pip','install','-r','requirements-train.txt'],1200,True)]
 if not a.skip_docker:phases += [('docker_preflight',[py,'scripts/docker_preflight.py'],30,True),('docker_base_image',[py,'scripts/docker_preflight.py','--prepare-base'],600,True)]
 if not a.skip_training:phases += [('training',[py,'scripts/train_rankers.py'],300,True)]
 phases += [('environment_inventory',[py,'scripts/environment_report.py'],60,True),('public_training',[py,'official_data_training/train_public.py'],120,True),
  ('public_leakage_tests',[py,'official_data_training/test_leakage.py'],60,True),('tests',[py,'scripts/run_tests.py'],120,True),
  ('data_checksums',[py,'scripts/audit_data.py'],30,True),('review_audit',[py,'scripts/audit_review_v08.py'],60,True),
  ('runtime_probe',[py,'scripts/benchmark.py'],120,True),('snapshot_parity',[py,'scripts/check_snapshot_parity.py'],180,True),
  ('selection_pilot',[py,'scripts/run_matrix.py','--matrix','selection'],1800,True),('selection_freeze',[py,'scripts/select_candidate.py'],20,True)]
 if not a.skip_docker:phases += [('container',[py,'scripts/validate_policies.py'],2400,True)]
 phases += [('validation',[py,'scripts/run_matrix.py','--matrix','validation'],1200,True),('final_test',[py,'scripts/run_matrix.py','--matrix','final'],2400,True),('subprocess',[py,'scripts/run_matrix.py','--matrix','subprocess'],600,True)]
 reserves={'tests':30,'data_checksums':2,'review_audit':10,'runtime_probe':15,'snapshot_parity':45,'selection_pilot':900,'selection_freeze':2,'container':900,'validation':450,'final_test':900,'subprocess':300};record['reservations_seconds']=reserves
 try:record['status']='completed' if execute_phases(phases,deadline,record,env,reservations=reserves) else 'incomplete'
 finally:
  cleanup_docker(run_id);choice=ROOT/'results/selection.json';candidate=json.loads(choice.read_text())['selected_mode'] if choice.exists() else 'rank_tie'
  if a.skip_docker:
   for mode,name in [('conservative','container_attestation.json'),(candidate,'container_candidate.json')]:atomic_json(ROOT/'results'/name,{'identity':execution_identity(mode=mode),'mode':mode,'validated':False,'status':'unverified','episodes':[],'error':'Docker unavailable/unperformed; explicit host-only run'})
  if record['status']=='running':record['status']='interrupted'
  record.update(elapsed_seconds=time.monotonic()-started,completed_unix=time.time(),total_iteration_elapsed_seconds=time.time()-origin['started_unix']);atomic_json(ROOT/'results/budget_run.json',record)
  execute_phases([('release_gate',[sys.executable,'scripts/release_gate.py'],15,False),('report',[sys.executable,'scripts/build_report.py'],15,True)],deadline+30,record,env)
  if any(p['status']!='completed' for p in record['phases'] if p['name']=='report'):record['status']='incomplete'
  record.update(elapsed_seconds=time.monotonic()-started,completed_unix=time.time(),total_iteration_elapsed_seconds=time.time()-origin['started_unix']);atomic_json(ROOT/'results/budget_run.json',record)
 return 0 if record['status']=='completed' else 2
if __name__=='__main__':raise SystemExit(main())
