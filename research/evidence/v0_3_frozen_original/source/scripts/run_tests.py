"""Run real suites and emit artifact-bound, machine-readable test evidence."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.storage import atomic_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--suite',choices=['project','starter'])
    parser.add_argument('--output',default='results/tests.json')
    args=parser.parse_args()
    output=Path(args.output)
    if not output.is_absolute():output=ROOT/output
    if args.suite:
        directory=ROOT if args.suite=='project' else ROOT/'starter'
        os.chdir(directory);sys.path.insert(0,str(directory))
        suite=unittest.defaultTestLoader.discover(str(directory),pattern='test_*.py',top_level_dir=str(directory))
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        atomic_json(output,{'suite':args.suite,'identity':execution_identity(),
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'skipped':len(result.skipped),'success':result.wasSuccessful()})
        return 0 if result.wasSuccessful() else 2
    parts=[]
    for name in ('project','starter'):
        path=output.with_name(output.stem+'_'+name+'.json')
        proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--suite',name,'--output',str(path)],cwd=ROOT)
        if not path.exists():raise RuntimeError('test suite failed before producing evidence')
        parts.append(json.loads(path.read_text(encoding='utf-8')))
        if proc.returncode and parts[-1]['success']:raise RuntimeError('test process/evidence mismatch')
    current=execution_identity()
    if any(p['identity']!=current for p in parts):raise ValueError('test identity changed during execution')
    result={'schema_version':2,'identity':current,'suites':parts,'tests_run':sum(p['tests_run'] for p in parts),
            'success':all(p['success'] and p['tests_run']>0 for p in parts)}
    atomic_json(output,result)
    return 0 if result['success'] else 2

if __name__=='__main__':raise SystemExit(main())
