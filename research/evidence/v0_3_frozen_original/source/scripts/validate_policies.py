"""Assess baseline and candidate images independently; retain both sets of evidence."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]


def main():
    codes=[]
    for mode,output in (('conservative','results/container_attestation.json'),('learned','results/container_learned.json')):
        codes.append(subprocess.run([sys.executable,str(ROOT/'validate_container.py'),'--mode',mode,
            '--image','blackbox:v0.3-'+mode,'--output',output],cwd=ROOT).returncode)
    return 0 if all(code==0 for code in codes) else 2

if __name__=='__main__':raise SystemExit(main())
