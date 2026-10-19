"""Assess the exact experimental image with the unchanged offline organizer harness."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
sys.dont_write_bytecode=True


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve()
    if out==ROOT or ROOT in out.parents or out.exists():p.error('choose a new external evidence directory')
    out.mkdir(parents=True);deadline=time.monotonic()+7200;run_id=uuid.uuid4().hex
    receipt={'schema_version':1,'mode':'coordinated','validated':False,'actual_docker':False,
             'host_windows':platform.system()=='Windows','standalone_windows_policy_unverified':True,'platform':platform.platform(),
             'started_utc':datetime.now(timezone.utc).isoformat(),'episodes':[],'status':'running',
             'proof_type':'Executed local Docker image ID and content hashes; no external digital signature.'}
    def save():
        temp=out/'container.tmp';temp.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        os.replace(temp,out/'coordinated_container.json')
    def remaining(cap=7200):
        value=min(cap,deadline-time.monotonic())
        if value<=0:raise ValueError('retained validation budget exhausted')
        return value
    def run(command,cap=120):
        proc=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=remaining(cap))
        if proc.returncode:raise ValueError(proc.stderr.decode(errors='replace')[-1000:])
        return proc.stdout
    try:
        from tools.verify_coordinated_release import verify
        proof=verify();receipt.update(source_and_assets_sha256=proof['source_and_assets_sha256'],model_id=proof['model_id'])
        receipt['dockerfile_sha256']=hashlib.sha256((ROOT/'Dockerfile.coordinated').read_bytes()).hexdigest();save()
        if not shutil.which('docker'):
            receipt['status']='unverified';raise ValueError('Docker CLI unavailable')
        info=json.loads(run(['docker','info','--format','{{json .}}'],30))
        if info.get('OSType')!='linux':raise ValueError('Linux container engine required')
        run(['docker','pull','python:3.12.14-slim'],1800)
        base=json.loads(run(['docker','image','inspect','python:3.12.14-slim'],30))[0]
        digest=base['RepoDigests'][0]
        if '@sha256:' not in digest:raise ValueError('base registry digest unavailable')
        receipt['base_registry_digest']=digest
        tag='blackbox:coordinated-'+run_id
        (out/'docker_build.log').write_bytes(run(['docker','build','-f','Dockerfile.coordinated','--build-arg','PYTHON_BASE='+digest,'-t',tag,'.'],3600))
        image=json.loads(run(['docker','image','inspect',tag],30))[0]
        if image['Size']>2*1024**3:raise ValueError('image exceeds 2 GiB')
        if image['Config'].get('User')!='65534:65534' or image['Config'].get('Entrypoint')!=['python','-B','/app/policy.py','--mode','coordinated']:
            raise ValueError('candidate image user/entrypoint mismatch')
        receipt.update(image_id=image['Id'],image_size_bytes=image['Size'],engine_version=info.get('ServerVersion'),actual_docker=True)
        sys.path.insert(0,str(ROOT/'research/starter'))
        spec=importlib.util.spec_from_file_location('coordinated_official_eval',ROOT/'research/starter/evaluate.py')
        official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
        from kit import generate
        original=official.invoke
        def bounded(command,request,timeout=10):return original(command,request,min(timeout,remaining(10)))
        official.invoke=bounded
        expected=json.loads((ROOT/'results/coordinated/transport.json').read_text())
        golden={r['variant']:r['cold_metrics'] for r in expected['rows']}
        action_hashes={r['variant']:r['official_harness_action_sha256'] for r in expected['rows']}
        receipt['constraints']={'network':'none','read_only':True,'cpus':2,'memory':'1g','memory_swap':'1g',
            'pids':64,'tmpfs':'64m','user':'65534:65534','cap_drop':'ALL','no_new_privileges':True,'timeout_seconds':10,'host_mounts':False}
        fields=('assignments','mutual_acceptances','dates','mutual_second_meeting_intention','ask_cost',
                'first_introduction_wait_days','served_members','unserved_members','coverage','missing_feedback')
        for variant in ('development','sparse','cold_start','delayed','shift','drift'):
            command=official.docker_command(image['Id'])
            command=command[:-1]+['--label','blackbox.coordinated_validation='+run_id,command[-1]]
            row=official.episode(generate(101,200,'evaluation',variant),command)
            if not row['valid'] or any(row[k]!=golden[variant][k] for k in fields) or row['action_sha256']!=action_hashes[variant]:
                raise ValueError('candidate container differs from recorded actions/outcomes: '+variant)
            row.update(seed=101,variant=variant,method='coordinated');receipt['episodes'].append(row);save()
            print(json.dumps({'completed':len(receipt['episodes']),'families':6,'variant':variant}),flush=True)
        if verify()!=proof:raise ValueError('candidate changed during container assessment')
        receipt.update(validated=True,status='completed');save();return 0
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        receipt['error']=type(error).__name__+': '+str(error)
        if receipt['status']=='running':receipt['status']='failed'
        save();print(receipt['error'],file=sys.stderr);return 2
    finally:
        if shutil.which('docker'):
            try:
                ids=subprocess.check_output(['docker','ps','-aq','--filter','label=blackbox.coordinated_validation='+run_id],timeout=10).decode().split()
                if ids:subprocess.run(['docker','rm','-f',*ids],capture_output=True,timeout=15)
            except (OSError,subprocess.SubprocessError):pass


if __name__=='__main__':raise SystemExit(main())
