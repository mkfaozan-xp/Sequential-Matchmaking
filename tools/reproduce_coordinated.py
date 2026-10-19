"""Replay fixed recorded experiments in a new working copy, preserving this release."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve()
    if out==ROOT or ROOT in out.parents:p.error('reproduction must be outside the frozen release')
    if out.exists():p.error('choose a new directory; earlier runs are never overwritten')
    work=out/'working_copy'
    shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns('__pycache__'))
    old=out/'recorded_results';old.mkdir()
    for name in ('validation.json','final.json','confirmation.json'):
        path=work/'results/coordinated'/name
        if path.exists():shutil.move(path,old/name)
    origin=out/'new_reproduction_budget.json'
    origin.write_text(json.dumps({'started_utc':datetime.now(timezone.utc).isoformat(),'budget_seconds':7200,
         'scope':'Separate reproduction execution of already recorded seeds; not new independent evidence.'},indent=2)+'\n')
    for matrix in ('validation','final'):
        result=subprocess.run([sys.executable,'-B',str(work/'coordinated/evaluate.py'),'--matrix',matrix,
                               '--budget-origin',str(origin)],cwd=work)
        if result.returncode:return result.returncode
    # The confirmation plan anchors the exact original final evidence. Preserve
    # that reference and keep the newly executed final in a separate replay file.
    new_final=work/'results/coordinated/final.json'
    shutil.move(new_final,work/'results/coordinated/replayed_final.json')
    shutil.copyfile(old/'final.json',new_final)
    result=subprocess.run([sys.executable,'-B',str(work/'tools/confirm_coordinated.py'),
                           '--budget-origin',str(origin)],cwd=work)
    if result.returncode:return result.returncode
    (out/'REPRODUCTION_SCOPE.json').write_text(json.dumps({
       'scope':'Repeated execution of the already-recorded 684 episodes; zero new independent worlds.',
       'original_final_evidence':'working_copy/results/coordinated/final.json',
       'new_final_replay':'working_copy/results/coordinated/replayed_final.json',
       'original_recordings':'recorded_results','new_confirmation':'working_copy/results/coordinated/confirmation.json',
       'candidate_refit':False,'shared_budget_seconds':7200},indent=2)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
