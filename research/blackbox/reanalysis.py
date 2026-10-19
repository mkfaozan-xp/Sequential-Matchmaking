"""Bind an analysis-only correction to the unchanged, originally frozen execution.

Never relabel historical episode execution as current-source execution. The
original source preimage must match the hash in its pre-outcome frozen plan.
Only reporting/gating, this verifier, tests, and paired_interval may differ.
"""
import ast
import json
from pathlib import Path
from .provenance import execution_identity,source_files
from .registry import sha
from .storage import digest,atomic_json

ROOT=Path(__file__).resolve().parent.parent
SNAPSHOT=ROOT/'evidence/v0_3_frozen_original'


def non_interval_ast(text):
    tree=ast.parse(text)
    tree.body=[node for node in tree.body if not
        (isinstance(node,ast.FunctionDef) and node.name=='paired_interval') and not
        (isinstance(node,ast.ImportFrom) and node.module=='fractions')]
    return ast.dump(tree,include_attributes=False)


def binding(root=None):
    root=Path(root) if root else ROOT
    snapshot=root/'evidence/v0_3_frozen_original'
    manifest_path=snapshot/'source_manifest.json'
    if not manifest_path.exists():return None
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    old=manifest['execution_identity'];previous=manifest['source_files'];current=execution_identity(root=root)
    plan=json.loads((snapshot/'final_test_plan.json').read_text(encoding='utf-8'))
    if digest(previous)!=old['source_sha256'] or plan['experiment']['identity']!=old or plan.get('frozen_before_results') is not True:
        raise ValueError('Original source manifest is not bound to the frozen plan')
    if old['inference_release']!=current['inference_release']:
        raise ValueError('Reanalysis cannot transfer evidence to different inference assets')
    if any(sha(snapshot/'source'/name)!=expected for name,expected in previous.items()):
        raise ValueError('Original execution source snapshot was changed')
    now={p.relative_to(root).as_posix():sha(p) for p in source_files(root)}
    changed=sorted(name for name in set(previous)|set(now) if previous.get(name)!=now.get(name))
    allowed={'blackbox/metrics.py','blackbox/reanalysis.py','scripts/release_gate.py','scripts/build_report.py','test_numeric_interval.py'}
    if not set(changed)<=allowed:raise ValueError('Changes extend beyond the declared analysis correction')
    old_metrics=(snapshot/'source/blackbox/metrics.py').read_text(encoding='utf-8')
    new_metrics=(root/'blackbox/metrics.py').read_text(encoding='utf-8')
    if non_interval_ast(old_metrics)!=non_interval_ast(new_metrics):
        raise ValueError('Metrics changes extend beyond paired_interval; episode execution evidence cannot transfer')
    return {'kind':'analysis_only_recomputation','execution_identity':old,'analysis_identity':current,
            'changed_files':changed,'original_source_manifest_sha256':sha(manifest_path),
            'original_final_sha256':sha(snapshot/'final_test.json'),'original_plan_sha256':sha(snapshot/'final_test_plan.json'),
            'note':'No policy, model, simulator, feature or episode execution code changed. Local hash evidence; not a digital signature.'}


def accepts_matrix(data):
    if not data:return False
    identity=data.get('config',{}).get('identity')
    if identity==execution_identity():return True
    try:
        proof=binding()
        if not proof or identity!=proof['execution_identity']:return False
        name='final_test.json' if data.get('scope')=='frozen final test' else 'validation.json'
        return data==json.loads((SNAPSHOT/name).read_text(encoding='utf-8'))
    except (OSError,ValueError,KeyError,TypeError):
        return False


if __name__=='__main__':
    proof=binding()
    if not proof:raise SystemExit('No frozen execution snapshot')
    from .metrics import paired_interval
    proof['recomputed_intervals']={name:paired_interval(json.loads((SNAPSHOT/(name+'.json')).read_text(encoding='utf-8'))['episodes'],'learned')
        for name in ('validation','final_test')}
    atomic_json(ROOT/'results/reanalysis.json',proof)
    print(json.dumps(proof,indent=2))
