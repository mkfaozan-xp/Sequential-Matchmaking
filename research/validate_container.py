"""Assess the exact immutable image and selected asset bundle; never infer a pass."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.policy import MODES
from blackbox.docker_base import base_reference,resolve
from blackbox.storage import atomic_json
sys.path.insert(0,str(ROOT/'starter'))
from kit import generate
spec=importlib.util.spec_from_file_location('official_eval',ROOT/'starter/evaluate.py')
official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
VARIANTS=('development','sparse','cold_start','delayed','shift','drift')


def cleanup(run_id):
    if not shutil.which('docker'):return
    try:
        ids=subprocess.check_output(['docker','ps','-aq','--filter','label=blackbox.run='+run_id],text=True,timeout=10).split()
        if ids:subprocess.run(['docker','rm','-f',*ids],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
    except (OSError,subprocess.SubprocessError):pass


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',default='blackbox:v0.6')
    parser.add_argument('--dockerfile',default='Dockerfile')
    parser.add_argument('--mode',choices=MODES,default='conservative')
    parser.add_argument('--output',default='results/container_attestation.json')
    args=parser.parse_args()
    if MODES[args.mode][2]=='milp' and Path(args.dockerfile).name!='Dockerfile.experimental':
        parser.error('MILP modes require Dockerfile.experimental with pinned solver dependencies')
    path=ROOT/args.output
    run_id=os.environ.get('BLACKBOX_RUN_ID') or uuid.uuid4().hex
    identity=execution_identity(mode=args.mode)
    evidence={'schema_version':2,'identity':identity,'mode':args.mode,'seed':101,'variants':list(VARIANTS),
              'expected_episodes':6,'episodes':[],'validated':False,'status':'running',
              'proof_type':'local content hashes and image ID; no digital signature or external signer',
              'timings_seconds':{}}
    atomic_json(path,evidence)
    if not shutil.which('docker'):
        evidence.update(status='unverified',error='Docker unavailable on this host')
        atomic_json(path,evidence);print(evidence['error'],file=sys.stderr);return 2
    try:
        system=json.loads(subprocess.check_output(['docker','info','--format','{{json .}}'],text=True,timeout=15))
        if system.get('OSType')!='linux':raise ValueError('Docker must use Linux containers (Docker Desktop WSL2 backend)')
        base=resolve(base_reference(ROOT/args.dockerfile));evidence['base_image']=base
        started=time.perf_counter()
        subprocess.run(['docker','build','-f',args.dockerfile,'--build-arg','PYTHON_BASE='+base['registry_digest'],'--build-arg','POLICY_MODE='+args.mode,'-t',args.image,'.'],cwd=ROOT,check=True)
        evidence['timings_seconds']['build']=time.perf_counter()-started
        meta=json.loads(subprocess.check_output(['docker','image','inspect',args.image],text=True,timeout=15))[0]
        if meta['Size']>2*1024**3:raise ValueError('image exceeds 2 GiB')
        env=dict(item.split('=',1) for item in meta['Config'].get('Env',[]) if '=' in item)
        if env.get('BLACKBOX_POLICY_MODE')!=args.mode:raise ValueError('image mode mismatch')
        if meta['Config'].get('User')!='65534:65534':raise ValueError('unexpected image user')
        evidence.update(image_id=meta['Id'],image_size_bytes=meta['Size'],engine_version=system.get('ServerVersion'),
            constraints={'network':'none','cpus':2,'memory_bytes':1024**3,'pids':64,'read_only':True,'tmpfs_bytes':64*1024**2})
        for variant in VARIANTS:
            if execution_identity(mode=args.mode)!=identity:raise ValueError('code or assets changed during container assessment')
            # Pin the immutable image ID. No source/data volumes are mounted.
            command=official.docker_command(meta['Id'])
            command=command[:-1]+['--label','blackbox.run='+run_id,command[-1]]
            started=time.perf_counter()
            row=official.episode(generate(101,200,'evaluation',variant),command)
            evidence['timings_seconds'][variant]=time.perf_counter()-started
            row.update(seed=101,variant=variant)
            evidence['episodes'].append(row);atomic_json(path,evidence)
            print(json.dumps({'variant':variant,'valid':row['valid'],'msmi':row['mutual_second_meeting_intention']}),flush=True)
        evidence.update(validated=len(evidence['episodes'])==6 and all(r['valid'] for r in evidence['episodes']),status='completed')
        atomic_json(path,evidence)
        return 0 if evidence['validated'] else 2
    except (ValueError,KeyError,OSError,subprocess.SubprocessError) as error:
        evidence.update(status='failed',error=type(error).__name__+': '+str(error),validated=False)
        atomic_json(path,evidence);print(evidence['error'],file=sys.stderr);return 2
    finally:
        cleanup(run_id)

if __name__=='__main__':raise SystemExit(main())
