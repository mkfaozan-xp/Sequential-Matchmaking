"""Create a final-test plan before outcomes exist; no test seeds are executed here."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.seeds import reserve
from blackbox.storage import atomic_json
from blackbox.experiment import VARIANTS
from blackbox.registry import sha,load_artifact


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',required=True,help='Explicit count/range chosen from pilot variance and feasible compute')
    p.add_argument('--methods',default='conservative,hybrid')
    p.add_argument('--output',default='plans/final_test.json')
    p.add_argument('--reuse-if-matching',action='store_true',help='Reuse an identical immutable plan; never overwrite a different one')
    a=p.parse_args();seeds=[int(s) for s in a.seeds.split(',')]
    if not seeds or any(s<3101 for s in seeds) or len(set(seeds))!=len(seeds):p.error('unique final-test seeds >=3101 required')
    path=ROOT/a.output
    protocol=sha(ROOT/'plans/REVIEW_PROTOCOL.md')
    if load_artifact('model.json').get('config',{}).get('protocol_sha256')!=protocol:p.error('fitted assets must bind the exact declared protocol')
    experiment={'identity':execution_identity(),'seeds':seeds,'methods':a.methods.split(','),
        'variants':list(VARIANTS),'transport':'inprocess','decision_days':60,'follow_up_days':40,'members':200}
    if path.exists():
        existing=json.loads(path.read_text(encoding='utf-8'))
        if a.reuse_if_matching and existing.get('experiment')==experiment and existing.get('protocol_sha256')==protocol and existing.get('frozen_before_results') is True:
            reserve(seeds,existing)
            print('Reusing identical frozen plan: '+str(path));return
        p.error('plan exists with a different identity/configuration; preserve it and choose a fresh plan and unseen seeds')
    plan={'schema_version':3,'frozen_before_results':True,'experiment':experiment,'protocol_sha256':protocol,
        'note':'Commit this plan before executing. This file cannot prove that seeds were never inspected elsewhere.'}
    reserve(seeds,plan)
    atomic_json(path,plan)
    print(path)

if __name__=='__main__':main()
