"""Full-game bytecode/source transport parity on existing recorded check worlds."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from multiprocessing import get_context
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
RESEARCH=ROOT/'research'
sys.path.insert(0,str(RESEARCH))
sys.dont_write_bytecode=True


def replay(task):
    from blackbox import experiment
    original=experiment.invoke
    def compiled(command,request):
        return original([command[0],'-S','-B',str(ROOT/'tools/run_compiled.py'),*command[2:]],request)
    experiment.invoke=compiled
    try:return experiment.run_episode(*task,transport='subprocess')[0]
    finally:experiment.invoke=original


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve()==ROOT or ROOT in a.output.resolve().parents:
        p.error('write verification evidence outside the frozen submission')
    from blackbox.provenance import source_hash
    expected_source='65e2d14ab9d468a902af97ea79780b2523306d7b12b9414ebf7d90e9d5595bf4'
    if source_hash(RESEARCH)!=expected_source:raise ValueError('research source changed')
    record=json.loads((RESEARCH/'results/subprocess.json').read_text())
    expected={(r['seed'],r['variant'],r['method']):r for r in record['episodes']}
    fields=['action_sha256','assignments','mutual_acceptances','dates','mutual_second_meeting_intention',
            'ask_cost','served_members','unserved_members','first_introduction_wait_days','coverage',
            'unserved_exposure_days','service_slices','policy_invocations','missing_feedback',
            'max_request_bytes','max_response_bytes']
    rows=[];started=time.monotonic()
    with ProcessPoolExecutor(max_workers=2,mp_context=get_context('spawn')) as pool:
        pending={pool.submit(replay,key):key for key in expected}
        for future in as_completed(pending):
            key=pending[future];row=future.result();original=expected[key]
            if not row['valid'] or any(row[k]!=original[k] for k in fields):
                raise ValueError('Compiled full-episode parity failed: '+str(key))
            rows.append({'seed':key[0],'variant':key[1],'mode':key[2],
                         'action_sha256':row['action_sha256'],'policy_invocations':row['policy_invocations'],
                         'all_comparison_fields_identical':True,'max_call_seconds':row['max_call_seconds']})
            print(json.dumps({'completed':len(rows),'expected':len(expected),'mode':key[2],'variant':key[1]}),flush=True)
    if source_hash(RESEARCH)!=expected_source:raise ValueError('research source changed during verification')
    result={'passed':True,'episodes':len(rows),'policy_invocations':sum(r['policy_invocations'] for r in rows),
            'fields_compared':fields,'rows':sorted(rows,key=lambda r:(r['variant'],r['mode'])),
            'all_actions_and_outcomes_identical':True,'elapsed_seconds':time.monotonic()-started,
            'new_training':False,'new_efficacy_evaluation':False,
            'scope':'Replayed six seed-101 families for conservative/rank_aux through verified bytecode; transport parity only.',
            'actual_docker_unverified':True,'actual_windows_unverified':True}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
