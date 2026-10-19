"""One read-only command for the frozen release, data and recorded experiments."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    scripts=['tools/verify_submission.py','tools/verify_coordinated_release.py',
             'tools/verify_confirmation.py','coordinated/test_engine.py',
             'tools/test_coordinated_planning.py','tools/check_research.py','tools/check_funnel.py','tools/audit_confirmation.py']
    for script in scripts:
        run=subprocess.run([sys.executable,'-B',str(ROOT/script)],cwd=ROOT,capture_output=True,text=True)
        if run.returncode:
            print(json.dumps({'passed':False,'check':script,'detail':(run.stderr or run.stdout)[-1600:]}));return 2
    run=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','.','-p','test*.py'],cwd=ROOT/'research/starter',capture_output=True,text=True)
    if run.returncode:
        print(json.dumps({'passed':False,'check':'organizer starter regressions','detail':(run.stderr or run.stdout)[-1600:]}));return 2
    run=subprocess.run([sys.executable,'-B',str(ROOT/'tools/train_model.py'),'--verify-data'],cwd=ROOT,capture_output=True,text=True)
    if run.returncode:
        print(json.dumps({'passed':False,'check':'flat training inputs','detail':(run.stderr or run.stdout)[-1600:]}));return 2
    if any(ROOT.rglob('*.zip')):
        print(json.dumps({'passed':False,'check':'unexpected nested ZIP'}));return 2
    print(json.dumps({'passed':True,'checks':10,'nested_zips':0,'active_mode':'conservative',
                      'actual_windows':'unverified','actual_docker':'unverified',
                      'scope':'File integrity, executable unit checks and recorded evidence; does not execute Docker or repeat efficacy worlds.'}));return 0


if __name__=='__main__':raise SystemExit(main())
