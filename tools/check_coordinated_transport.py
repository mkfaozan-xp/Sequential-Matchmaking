"""Cold restart-per-call parity for the unified controller on six known worlds."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
import hashlib
from multiprocessing import get_context
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research'));sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True


def check(variant):
    from blackbox import experiment
    from blackbox.registry import verified_episode_snapshot
    from coordinated.engine import decide
    original_decide=experiment.decide;original_invoke=experiment.invoke;official_digest=hashlib.sha256()
    experiment.decide=lambda req,mode:decide(req)
    try:
        with verified_episode_snapshot():warm=experiment.run_episode(101,variant,'coordinated')[0]
        def invoke(command,request):
            response,elapsed=original_invoke([sys.executable,'-S','-B',str(ROOT/'tools/run_coordinated_compiled.py'),'--mode','coordinated'],request)
            key='asks' if request['phase']=='ask' else 'pairs'
            official_digest.update(json.dumps([request['phase'],request['state']['day'],response[key]],sort_keys=True).encode())
            return response,elapsed
        experiment.invoke=invoke
        cold=experiment.run_episode(101,variant,'coordinated',transport='subprocess')[0]
    finally:experiment.decide=original_decide;experiment.invoke=original_invoke
    fields=['action_sha256','assignments','mutual_acceptances','dates','mutual_second_meeting_intention','ask_cost',
            'first_introduction_wait_days','served_members','unserved_members','coverage','missing_feedback']
    if not cold['valid'] or any(warm[k]!=cold[k] for k in fields):
        raise ValueError('Coordinated cold/inprocess mismatch: '+variant)
    if cold['max_call_seconds']>10:raise ValueError('cold call exceeded ten seconds')
    return {'variant':variant,'seed':101,'both_views_valid':True,'all_fields_identical':True,
            'policy_invocations':cold['policy_invocations'],'cold_max_call_seconds':cold['max_call_seconds'],
            'cold_p95_call_seconds':cold['p95_call_seconds'],'cold_action_sha256':cold['action_sha256'],
            'official_harness_action_sha256':official_digest.hexdigest(),
            'cold_metrics':{k:cold[k] for k in fields if k!='action_sha256'}}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    started=time.monotonic();rows=[]
    with ProcessPoolExecutor(max_workers=2,mp_context=get_context('spawn')) as pool:
        tasks=[pool.submit(check,v) for v in ('development','sparse','cold_start','delayed','shift','drift')]
        for future in as_completed(tasks):
            rows.append(future.result());print(json.dumps({'completed':len(rows),'families':6}),flush=True)
    result={'passed':True,'families':6,'paired_views':12,'cold_cli_invocations':sum(r['policy_invocations'] for r in rows),
            'all_actions_and_outcomes_identical':True,'elapsed_seconds':time.monotonic()-started,
            'rows':sorted(rows,key=lambda r:r['variant']),'actual_docker':False,'actual_windows':False,
            'cli_entrypoint':'tools/run_coordinated_compiled.py --mode coordinated',
            'scope':'Known seed-101 compiled CLI transport checks, not new independent efficacy worlds.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
