"""Assess baseline and candidate images independently; retain both sets of evidence."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();selection=ROOT/'results/selection.json';candidate=json.loads(selection.read_text())['selected_mode'] if selection.exists() else 'hybrid';parser.add_argument('--candidate-mode',default=candidate);args=parser.parse_args()
    codes=[]
    for mode,output in (('conservative','results/container_attestation.json'),(args.candidate_mode,'results/container_candidate.json')):
        codes.append(subprocess.run([sys.executable,str(ROOT/'validate_container.py'),'--mode',mode,
            '--image','blackbox:v0.8-'+mode,'--output',output],cwd=ROOT).returncode)
    return 0 if all(code==0 for code in codes) else 2

if __name__=='__main__':raise SystemExit(main())
