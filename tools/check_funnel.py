"""Source-bound staged-scorer integrity and real CLI checks."""
import copy,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'runtime'))
from coordinated import engine
from funnel.controller import FunnelController

def main():
 before=engine.estimates;controller=FunnelController()
 assert engine.estimates is before,'shared original planner mutated'
 model=controller.model;assert model['acceptance']['optimizer_converged'] and model['conversion']['optimizer_converged']
 assert len(model['feature_names'])==32 and len(model['conversion_indices'])==18
 assert all(model['feature_names'][i].startswith(('relationship_goal:','outcome:')) for i in model['conversion_indices'])
 assert all('missing' not in n for n in model['feature_names'])
 assert 0<controller.predict_x([0.0]*32)<model['timeliness_factor']<=1
 cases=0
 env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
 def run(raw):return subprocess.run([sys.executable,'-S','-B',str(ROOT/'tools/run_funnel.py')],input=raw,capture_output=True,cwd=ROOT,timeout=10,env=env)
 for example in ('empty_request.json','day0_request.json','refreshed_match_request.json'):
  p=run((ROOT/'runtime/examples'/example).read_bytes());assert p.returncode==0,p.stderr;json.loads(p.stdout);cases+=1
 for raw in (b'{}',b'{"x":NaN}',b' '*(1024**2+1)):
  p=run(raw);assert p.returncode==2 and not p.stdout;cases+=1
 template=json.loads((ROOT/'runtime/examples/refreshed_match_request.json').read_text());template['state']['hidden_world']={}
 p=run(json.dumps(template).encode());assert p.returncode==2 and not p.stdout;cases+=1
 plan_path=ROOT/'funnel/EVALUATION_PLAN.json';plan=json.loads(plan_path.read_text());result=json.loads((ROOT/'results/funnel/pilot.json').read_text());rows=result['episodes']
 assert result['complete'] and result['all_valid'] and len(rows)==24,'fresh pilot incomplete'
 assert result['plan_sha256']==hashlib.sha256(plan_path.read_bytes()).hexdigest()
 assert result['release_sha256']==plan['release_sha256']==hashlib.sha256((ROOT/'funnel/release.json').read_bytes()).hexdigest()
 expected={(s,v,m) for s in plan['seeds'] for v in plan['families'] for m in plan['methods']}
 assert len(rows)==len(expected) and {(r['seed'],r['variant'],r['method']) for r in rows}==expected
 assert all(r['valid'] and r['arrived_members']==200 and r['policy_invocations']==120 and r['max_call_seconds']<=10 for r in rows)
 print(json.dumps({'passed':True,'cli_cases':cases,'fresh_pilot_episodes':24,'original_planner_not_mutated':True,'conditional_features':18,'promoted':False,'windows':'unverified','docker':'unverified'}));return 0

if __name__=='__main__':raise SystemExit(main())
