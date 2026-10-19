"""Select an already verified immutable bundle for a declared offline policy mode."""
import argparse
import json
from pathlib import Path
from blackbox.registry import ROOT, select, identity
from blackbox.policy import MODES


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--release-id')
    parser.add_argument('--candidate',action='store_true')
    parser.add_argument('--mode',choices=MODES,default='conservative')
    args=parser.parse_args()
    if args.candidate == bool(args.release_id):parser.error('choose exactly one of --candidate or --release-id')
    release_id=args.release_id or json.loads((ROOT/'artifacts/candidate.json').read_text())['release_id']
    select(release_id,args.mode)
    print(json.dumps(identity(),indent=2))

if __name__=='__main__':main()
