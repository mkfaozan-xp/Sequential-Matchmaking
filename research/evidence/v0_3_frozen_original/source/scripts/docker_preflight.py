"""Fast, read-only Docker Desktop/WSL2 engine check before spending training time."""
import json
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


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
            recipe=(Path(__file__).resolve().parents[1]/'Dockerfile').read_text()
            base=next(line.split()[1] for line in recipe.splitlines() if line.startswith('FROM '))
            try:
                subprocess.run(['docker','image','inspect',base],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
                cached=True
            except subprocess.CalledProcessError:
                subprocess.run(['docker','pull',base],check=True,timeout=540)
                cached=False
            meta=json.loads(subprocess.check_output(['docker','image','inspect',base],text=True,timeout=15))[0]
            print(json.dumps({'base':base,'base_image_id':meta['Id'],'already_cached':cached}))
        return 0
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print('Docker engine not ready: '+str(error),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
