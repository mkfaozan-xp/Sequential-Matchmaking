"""Verify the exact shared-objective candidate and complete recorded comparisons."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
sys.dont_write_bytecode=True


def verify():
    from coordinated.engine import load_model
    from coordinated.evaluate import subject
    from blackbox.provenance import source_hash
    from blackbox.metrics import paired_interval
    model=load_model();identity=subject();plan_path=ROOT/'coordinated/EXPERIMENT_PLAN.json'
    plan=json.loads(plan_path.read_text());ph=hashlib.sha256(plan_path.read_bytes()).hexdigest()
    if source_hash(ROOT/'research')!='65e2d14ab9d468a902af97ea79780b2523306d7b12b9414ebf7d90e9d5595bf4':
        raise ValueError('historical research source changed')
    serving=[ROOT/'runtime/policy.py',ROOT/'runtime/artifacts/deployment.json']
    serving+=list((ROOT/'runtime/blackbox').glob('*.py'))
    serving+=list((ROOT/'runtime/artifacts/releases').rglob('*.json'))
    for path in serving:
        relative=path.relative_to(ROOT/'runtime')
        if path.read_bytes()!=(ROOT/'research'/relative).read_bytes():
            raise ValueError('serving dependency differs from evaluated research code/assets: '+str(relative))
    matrices={}
    for name in ('validation','final'):
        d=json.loads((ROOT/'results/coordinated'/(name+'.json')).read_text())
        if not d['complete'] or not d['all_valid'] or d['source_and_assets_sha256']!=identity or d['plan_sha256']!=ph:
            raise ValueError('incomplete or stale coordinated matrix: '+name)
        expected={(s,v,m) for s in plan[name]['seeds'] for v in plan[name]['variants'] for m in plan[name]['methods']}
        actual={(r['seed'],r['variant'],r['method']) for r in d['episodes']}
        if len(d['episodes'])!=len(expected) or actual!=expected:raise ValueError('matrix membership mismatch')
        for row in d['episodes']:
            if (not row['valid'] or len(row['first_introduction_wait_days'])!=row['served_members']
                    or row['served_members']+row['unserved_members']!=row['arrived_members']):
                raise ValueError('invalid waiting/service data')
        matrices[name]=d
    final=matrices['final'];paired=paired_interval(final['episodes'],'coordinated')
    if paired!=final['paired_vs_conservative']['coordinated']:raise ValueError('paired analysis changed')
    transport=json.loads((ROOT/'results/coordinated/transport.json').read_text())
    if not transport['passed'] or transport['cold_cli_invocations']!=720:
        raise ValueError('cold transport comparison incomplete')
    cli=json.loads((ROOT/'results/coordinated/cli_checks.json').read_text())
    if not cli['passed'] or cli['checks']!=14:raise ValueError('coordinated CLI checks incomplete')
    return {'passed':True,'model_id':model['model_id'],'source_and_assets_sha256':identity,
            'training_only_rows':model['training_rows'],'features':len(model['feature_names']),
            'inherited_serving_files_verified_identical_to_research':len(serving),
            'complete_comparison_episodes':sum(len(d['episodes']) for d in matrices.values()),
            'cold_cli_invocations':transport['cold_cli_invocations'],'cli_contract_checks':cli['checks'],'paired_final':paired,
            'active_mode':'conservative','actual_docker':False,'actual_windows':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.parse_args()
    try:print(json.dumps(verify(),sort_keys=True));return 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'passed':False,'error':str(error)[:240]}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
