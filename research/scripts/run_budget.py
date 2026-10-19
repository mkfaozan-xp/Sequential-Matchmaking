"""A bounded Windows/WSL/Linux workflow; retain partial evidence when the budget expires."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.runtime import runtime_info
from blackbox.storage import atomic_json, WorkflowLock, RunBusy


def stop_process(process):
    if process.poll() is not None:return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL)
    process.wait(timeout=10)


def run_command(command,seconds,log_path,environment):
    if seconds<=0:raise TimeoutError('No time left for another phase')
    with Path(log_path).open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=environment,
            start_new_session=os.name!='nt',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
        try:
            return process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            stop_process(process)
            raise TimeoutError('Phase exceeded its allocated wall-clock budget')
        except KeyboardInterrupt:
            stop_process(process)
            raise


def cleanup_docker(run_id):
    if not shutil.which('docker'):return
    try:
        ids=subprocess.check_output(['docker','ps','-aq','--filter','label=blackbox.run='+run_id],text=True,timeout=5).split()
        if ids:subprocess.run(['docker','rm','-f',*ids],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
    except (OSError,subprocess.SubprocessError):pass


def execute_phases(phases,deadline,record,environment,runner=run_command,clock=time.monotonic,reservations=None):
    reservations=reservations or {}
    for index,(name,command,cap,required) in enumerate(phases):
        tail_reserve=sum(reservations.get(p[0],0) for p in phases[index+1:])
        remaining=deadline-clock()-60-tail_reserve
        allowance=max(0,min(cap,remaining))
        phase={'name':name,'command':command,'status':'running','allocated_seconds':allowance,
               'downstream_reserved_seconds':tail_reserve}
        record['phases'].append(phase)
        atomic_json(ROOT/'results/budget_run.json',record)
        started=clock()
        try:
            if allowance<=0:raise TimeoutError('Downstream reservations leave no budget for this phase')
            code=runner(command,allowance,ROOT/'results'/f'{name}.log',environment)
            phase.update(status='completed' if code==0 else 'failed',exit_code=code,seconds=clock()-started)
        except (OSError,TimeoutError,subprocess.SubprocessError) as error:
            phase.update(status='timed_out' if isinstance(error,TimeoutError) else 'failed',error=str(error),seconds=clock()-started)
        atomic_json(ROOT/'results/budget_run.json',record)
        print(json.dumps(phase),flush=True)
        if required and phase['status']!='completed':
            record['phases'].extend({'name':p[0],'status':'not_run','reason':'required upstream phase incomplete'} for p in phases[index+1:])
            return False
    return True


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--minutes',type=float,default=120)
    parser.add_argument('--bootstrap',action='store_true',help='Create local .venv and install pinned NumPy/SciPy within the time budget')
    parser.add_argument('--skip-training',action='store_true',help='Reuse included candidate assets; records that training was skipped')
    parser.add_argument('--skip-docker',action='store_true',help='Host-only debugging; never produces container validation')
    args=parser.parse_args()
    if not 1<=args.minutes<=120:parser.error('wall budget must be 1-120 minutes')
    try:runtime_info()
    except ValueError as error:parser.error(str(error))
    try:
        with WorkflowLock(ROOT/'results/workflow.lock'):
            return run_workflow(args)
    except RunBusy as error:
        print(str(error),file=sys.stderr);return 3


def run_workflow(args):
    started=time.monotonic();deadline=started+args.minutes*60
    (ROOT/'results').mkdir(exist_ok=True)
    run_id=uuid.uuid4().hex
    environment=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',BLACKBOX_RUN_ID=run_id)
    record={'runtime':runtime_info(),'schema_version':3,'run_id':run_id,'budget_seconds':args.minutes*60,'phases':[],
            'status':'running','training_skipped':args.skip_training,'docker_skipped':args.skip_docker}
    phases=[]
    python=sys.executable
    if args.bootstrap:
        venv=ROOT/'.venv'
        phases.append(('create_environment',[python,'-m','venv',str(venv)],180,True))
        python=str(venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python'))
        phases.append(('install_dependencies',[python,'-m','pip','install','-r','requirements-train.txt'],1200,True))
    if not args.skip_docker:
        phases.append(('docker_preflight',[python,'scripts/docker_preflight.py'],30,True))
        phases.append(('docker_base_image',[python,'scripts/docker_preflight.py','--prepare-base'],600,True))
    if not args.skip_training:
        phases.append(('training',[python,'train.py','--activate-candidate'],1500,True))
    phases += [
        ('tests',[python,'scripts/run_tests.py'],300,True),
        ('data_checksums',[python,'scripts/audit_data.py'],30,True),
    ]
    if not args.skip_docker:
        phases.append(('container',[python,'scripts/validate_policies.py'],2400,True))
    phases.append(('validation',[python,'evaluate.py','--seeds','2401,2402','--methods',
        'baseline_greedy,baseline_no_asks,baseline_random,conservative,learned,hybrid,hybrid_soft','--variants','all','--output','results/validation.json'],2100,True))
    # Gate exit 2 can mean an honestly blocked prototype. Record it, do not call it a passed release.
    # Finalizers run even after a failed required phase; stale artifacts cannot masquerade as current.
    finalizers=[('release_gate',[python,'scripts/release_gate.py'],20,False),
                ('report',[python,'scripts/build_report.py'],20,True)]
    reservations={'container':1200,'validation':300,'tests':30,'data_checksums':5}
    record['reservations_seconds']=reservations
    try:
        completed=execute_phases(phases,deadline,record,environment,reservations=reservations)
        record['status']='completed' if completed else 'incomplete'
    finally:
        cleanup_docker(run_id)
        if args.skip_docker:
            from blackbox.provenance import execution_identity
            for mode,name in (('conservative','container_attestation.json'),('hybrid','container_candidate.json')):
                atomic_json(ROOT/'results'/name,{'schema_version':2,'identity':execution_identity(mode=mode),
                    'status':'unverified','validated':False,'episodes':[],'error':'Explicitly skipped; no Docker claim'})
        # Use the running interpreter for stdlib-only finalizers if bootstrap failed.
        for name,command,cap,required in finalizers:
            command[0]=sys.executable
        finished=execute_phases(finalizers,deadline+45,record,environment)
        if not finished and record['status']=='completed':record['status']='incomplete'
        record['elapsed_seconds']=time.monotonic()-started
        if record['status']=='running':record['status']='interrupted'
        atomic_json(ROOT/'results/budget_run.json',record)
    return 0 if record['status']=='completed' else 2

if __name__=='__main__':
    from scripts.run_research import main as current_workflow
    raise SystemExit(current_workflow())
