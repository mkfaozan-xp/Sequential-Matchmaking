"""Verify compiled bytes, numerical predictions and source/bytecode CLI parity."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify():
    manifest=json.loads((ROOT/'compiled/cpython312/COMPILED_MANIFEST.json').read_text())
    if sys.implementation.name!='cpython' or sys.version_info[:2]!=(3,12):
        raise ValueError('Verification requires CPython 3.12.')
    for entry in manifest['files']:
        source=(ROOT/entry['source']).read_bytes()
        raw=(ROOT/'compiled/cpython312'/entry['bytecode']).read_bytes()
        if (sha(source)!=entry['source_sha256'] or sha(raw)!=entry['bytecode_sha256']
                or raw[:4]!=importlib.util.MAGIC_NUMBER
                or int.from_bytes(raw[4:8],'little')!=3
                or raw[8:16]!=importlib.util.source_hash(source)):
            raise ValueError('Compiled/source identity mismatch: '+entry['source'])
    env=dict(os.environ)
    for key in ('PYTHONPATH','PYTHONHOME','BLACKBOX_POLICY_MODE'):env.pop(key,None)
    env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    def execute(script,raw,args=(),root=ROOT):
        return subprocess.run([sys.executable,'-S','-B',str(root/script),*args],cwd=root,
                              input=raw,capture_output=True,timeout=15,env=env)
    smoke=[]
    for mode in ('conservative','rank_aux'):
        for name in ('empty_request.json','day0_request.json','refreshed_match_request.json'):
            raw=(ROOT/'runtime/examples'/name).read_bytes();args=['--mode',mode]
            source=execute('runtime/policy.py',raw,args);compiled=execute('tools/run_compiled.py',raw,args)
            if source.returncode!=0 or compiled.returncode!=0 or json.loads(source.stdout)!=json.loads(compiled.stdout):
                raise ValueError('Compiled CLI parity failed: '+mode+'/'+name+' '+compiled.stderr.decode(errors='replace')[:240])
            smoke.append({'mode':mode,'example':name,'identical':True})
    rejected=[]
    for name,raw in [('missing_contract',b'{}'),('nonfinite',b'{"x":NaN}'),('oversized',b' '*(1024**2+1))]:
        result=execute('tools/run_compiled.py',raw)
        if result.returncode!=2 or result.stdout:raise ValueError('Compiled CLI did not reject '+name)
        rejected.append(name)
    default=execute('tools/run_compiled.py',(ROOT/'runtime/examples/refreshed_match_request.json').read_bytes())
    if default.returncode!=0 or json.loads(default.stdout)['memory']['mode']!='conservative':
        raise ValueError('Compiled default mode mismatch.')
    with gzip.open(ROOT/'research/artifacts/datasets/v06_observations.json.gz','rt') as stream:
        dataset=json.load(stream)
    rows=[]
    for key in sorted(dataset['records']):
        values=dataset['records'][key]['record']['payload']['joint']
        if values:rows.append(values[0]['x'])
        if len(rows)==64:break
    if len(rows)!=64:raise ValueError('Numerical parity fixtures incomplete.')
    raw=json.dumps(rows).encode()
    source=execute('tools/model_execution_probe.py',raw)
    compiled=execute('tools/model_execution_probe.py',raw,['--compiled'])
    if source.returncode!=0 or compiled.returncode!=0:raise ValueError('Model probe failed: '+compiled.stderr.decode(errors='replace')[:240])
    left=json.loads(source.stdout);right=json.loads(compiled.stdout)
    if left['model_id']!=right['model_id'] or left['predictions']!=right['predictions']:
        raise ValueError('Compiled numerical predictions differ.')
    failures=[]
    for case in ('changed_bytecode','changed_source','missing_bytecode'):
        with tempfile.TemporaryDirectory(prefix='compiled_runtime_negative_') as td:
            root=Path(td)/'submission';(root/'tools').mkdir(parents=True)
            shutil.copytree(ROOT/'runtime',root/'runtime')
            shutil.copytree(ROOT/'compiled',root/'compiled')
            shutil.copyfile(ROOT/'tools/run_compiled.py',root/'tools/run_compiled.py')
            target=root/'compiled/cpython312/runtime/policy.pyc'
            if case=='changed_bytecode':target.write_bytes(target.read_bytes()+b'x')
            elif case=='changed_source':
                target=root/'runtime/blackbox/model.py';target.write_bytes(target.read_bytes()+b'\n# altered\n')
            else:target.unlink()
            result=execute('tools/run_compiled.py',b'{}',root=root)
            if result.returncode!=2 or result.stdout:raise ValueError('Corrupt compiled package was accepted: '+case)
            failures.append({'case':case,'rejected':True})
    return {'passed':True,'target':manifest['target'],'compiler_python':manifest['compiler_python'],
            'compiled_files_verified':len(manifest['files']),'smoke_cases':smoke,
            'invalid_requests_rejected':rejected,'default_mode':'conservative',
            'model_id':right['model_id'],'model_vectors_compared':64,
            'model_outputs_compared':640,'numerical_outputs_exactly_equal':True,
            'compiled_model_module_loaders':right['module_loaders'],'corrupt_package_checks':failures,
            'weights_retrained':False,'new_efficacy_evaluation':False,
            'actual_windows_unverified':True,'actual_docker_unverified':True}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        result=verify()
        if a.output:
            target=a.output.resolve()
            if target==ROOT or ROOT in target.parents:raise ValueError('Write new verification output outside the frozen folder.')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(json.dumps(result,sort_keys=True));return 0
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        print(json.dumps({'passed':False,'error':str(error)[:400]}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
