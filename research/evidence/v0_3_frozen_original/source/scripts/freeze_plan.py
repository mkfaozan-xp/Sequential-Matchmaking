"""Create a final-test plan before outcomes exist; no test seeds are executed here."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.storage import atomic_json
from blackbox.experiment import VARIANTS


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',required=True,help='Explicit count/range chosen from pilot variance and feasible compute')
    p.add_argument('--methods',default='conservative,learned')
    p.add_argument('--output',default='plans/final_test.json')
    a=p.parse_args();seeds=[int(s) for s in a.seeds.split(',')]
    if not seeds or any(s<3101 for s in seeds) or len(set(seeds))!=len(seeds):p.error('unique final-test seeds >=3101 required')
    path=ROOT/a.output
    if path.exists():p.error('plan exists; preserve it instead of overwriting')
    experiment={'identity':execution_identity(),'seeds':seeds,'methods':a.methods.split(','),
        'variants':list(VARIANTS),'transport':'inprocess','decision_days':60,'follow_up_days':40,'members':200}
    atomic_json(path,{'schema_version':2,'frozen_before_results':True,'experiment':experiment,
        'note':'Commit this plan before executing. This file cannot prove that seeds were never inspected elsewhere.'})
    print(path)

if __name__=='__main__':main()
