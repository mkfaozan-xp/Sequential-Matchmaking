"""Actual source/compiled CLI contract, privacy-boundary and refusal checks."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.resolve()==ROOT or ROOT in a.output.resolve().parents:
        p.error('write new execution evidence outside the frozen folder')
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    for key in ('PYTHONPATH','PYTHONHOME','BLACKBOX_POLICY_MODE'):env.pop(key,None)
    template=json.loads((ROOT/'runtime/examples/refreshed_match_request.json').read_text())
    bad=[('missing_contract',b'{}'),('nonfinite',b'{"x":NaN}'),('oversized',b' '*(1024**2+1))]
    hidden=copy.deepcopy(template);hidden['state']['hidden_world']={'preferences':'not observable'}
    bad.append(('hidden_state_key',json.dumps(hidden).encode()))
    future=copy.deepcopy(template);state=future['state'];ids=[m['member_id'] for m in state['members'][:2]]
    intro={'introduction_id':'future-probe','user_a':ids[0],'user_b':ids[1],'assigned_day':state['day'],
           'response_deadline_day':state['day']+7,'logging_policy':'test','propensity':None}
    state['introductions'].append(intro)
    state['feedback'].append({'introduction_id':'future-probe','member_id':ids[0],
      'event':'introduction_response','value':'yes','occurred_day':state['day']+1,'observed_day':state['day']+1})
    bad.append(('future_feedback',json.dumps(future).encode()))
    legal=[]
    empty=copy.deepcopy(template);empty['phase']='ask';empty['state']['ask_budget_remaining']=0
    legal.append(('zero_budget',empty,None))
    declined=copy.deepcopy(template);declined['phase']='ask';member=declined['state']['members'][0]
    member['fields']['age_min']=None;member['field_status']['age_min']='declined';member['field_observed_day']['age_min']=None
    legal.append(('declined_hard_field',declined,member['member_id']))
    rows=[]
    for program in ('policy.py','tools/run_coordinated_compiled.py'):
        def run(raw):
            return subprocess.run([sys.executable,'-S','-B',str(ROOT/program),'--mode','coordinated'],
                                  input=raw,capture_output=True,timeout=10,env=env,cwd=ROOT)
        for label,raw in bad:
            result=run(raw)
            if result.returncode!=2 or result.stdout:raise ValueError('invalid request accepted: '+label)
            rows.append({'program':program,'case':label,'correctly_rejected':True})
        for label,request,blocked in legal:
            result=run(json.dumps(request).encode())
            if result.returncode!=0:raise ValueError(result.stderr.decode(errors='replace'))
            response=json.loads(result.stdout)
            if label=='zero_budget' and response['asks']:raise ValueError('overspent zero question budget')
            if blocked and any(q['member_id']==blocked for q in response['asks']):raise ValueError('reasked declined constraints')
            rows.append({'program':program,'case':label,'passed':True})
    out={'passed':True,'checks':len(rows),'cases':rows,'actual_docker':False,'actual_windows':False}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'passed':True,'checks':len(rows)}));return 0


if __name__=='__main__':raise SystemExit(main())
