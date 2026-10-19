"""Replay the recorded staged pilot in a new copy; never count it as fresh evidence."""
import argparse,json,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if out.exists() or out==ROOT or ROOT in out.parents:p.error('choose a new external directory')
 work=out/'working_copy';shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns('__pycache__'))
 old=work/'results/funnel/pilot.json';shutil.move(old,out/'original_pilot.json')
 origin={'started_utc':datetime.now(timezone.utc).isoformat(),'budget_seconds':7200,'scope':'New reproduction execution of recorded seeds; not a reset of the original study or new independent evidence.'}
 (work/'evidence/coordinated/budget_origin.json').write_text(json.dumps(origin,indent=2)+'\n')
 result=subprocess.run([sys.executable,'-B',str(work/'tools/evaluate_funnel.py')],cwd=work)
 if result.returncode:return result.returncode
 data=json.loads(old.read_text());data['scope']='Repeated execution of the 24 recorded pilot episodes; not new independent evidence.';old.write_text(json.dumps(data,indent=2)+'\n')
 (out/'REPLAY_SCOPE.json').write_text(json.dumps({'candidate_refit':False,'repeated_episodes':24,'new_independent_worlds':0,'original_pilot':'original_pilot.json','replay_results':'working_copy/results/funnel/pilot.json','scope':origin['scope']},indent=2)+'\n');return 0

if __name__=='__main__':raise SystemExit(main())
