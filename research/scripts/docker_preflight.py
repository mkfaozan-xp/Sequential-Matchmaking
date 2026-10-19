"""Fast, read-only Docker Desktop/WSL2 engine check before spending training time."""
import json
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.docker_base import base_reference,resolve


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare-base',action='store_true',help='Fetch the Dockerfile base before training, inside the global budget')
    args=parser.parse_args()
    if not shutil.which('docker'):
        print('Docker CLI unavailable. Start Docker Desktop and enable Linux containers/WSL2.',file=sys.stderr)
        return 2
    try:
        info=json.loads(subprocess.check_output(['docker','info','--format','{{json .}}'],text=True,stderr=subprocess.PIPE,timeout=15))
        if info.get('OSType')!='linux':
            print('Switch Docker Desktop to Linux containers with its WSL2 backend.',file=sys.stderr);return 2
        print(json.dumps({k:info.get(k) for k in ('OSType','ServerVersion','NCPU','MemTotal')}))
        if args.prepare_base:
            print(json.dumps(resolve(base_reference(ROOT/'Dockerfile'))))
        return 0
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print('Docker engine not ready: '+str(error),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
