"""Check the independently registered fixed-size confirmation without pooling."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
sys.dont_write_bytecode=True


def verify():
    from coordinated.evaluate import subject
    from blackbox.metrics import paired_interval
    plan_path=ROOT/'coordinated/CONFIRMATION_PLAN.json';plan=json.loads(plan_path.read_text())
    result=json.loads((ROOT/'results/coordinated/confirmation.json').read_text())
    if plan['source_and_assets_sha256']!=subject() or result['source_and_assets_sha256']!=subject():
        raise ValueError('confirmation candidate source or model changed')
    if result['confirmation_plan_sha256']!=hashlib.sha256(plan_path.read_bytes()).hexdigest():
        raise ValueError('registered confirmation plan changed')
    if plan['original_final_sha256']!=hashlib.sha256((ROOT/'results/coordinated/final.json').read_bytes()).hexdigest():
        raise ValueError('original final was overwritten')
    expected={(s,v,m) for s in plan['seeds'] for v in plan['variants'] for m in plan['methods']}
    actual={(r['seed'],r['variant'],r['method']) for r in result['episodes']}
    if not result['complete'] or not result['all_valid'] or len(expected)!=480 or len(result['episodes'])!=480 or expected!=actual:
        raise ValueError('confirmation incomplete or invalid')
    for row in result['episodes']:
        if (not row['valid'] or row['arrived_members']!=200 or row['policy_invocations']!=120
                or row['served_members']+row['unserved_members']!=row['arrived_members']
                or len(row['first_introduction_wait_days'])!=row['served_members']):
            raise ValueError('confirmation service/protocol record invalid')
    paired=paired_interval(result['episodes'],'coordinated')
    if paired!=result['paired_vs_conservative'] or paired['seed_blocks']!=40:
        raise ValueError('confirmation paired analysis mismatch')
    original=json.loads((ROOT/'coordinated/EXPERIMENT_PLAN.json').read_text())
    if set(plan['seeds'])&set(original['validation']['seeds']+original['final']['seeds']):
        raise ValueError('confirmation overlaps original validation/final')
    return {'passed':True,'scope':'Independent confirmation only; original final retained separately.',
            'episodes':480,'worlds':240,'seed_blocks':40,'source_and_assets_sha256':subject(),
            'paired_confirmation':paired,'actual_docker':False,'actual_windows':False}


if __name__=='__main__':
    try:print(json.dumps(verify(),sort_keys=True))
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'passed':False,'error':str(error)[:240]}),file=sys.stderr);raise SystemExit(2)
