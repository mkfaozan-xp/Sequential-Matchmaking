"""Startup-inclusive dense/sparse probes; host measurements, not container certification."""
import copy,json,os,subprocess,sys,time
try:
    import resource
except ImportError:
    resource=None
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from test_policy import feasible_state
from blackbox.storage import atomic_json

def dense(n,missing):
    state=feasible_state();base=state['members'][0];state['members']=[]
    for i in range(n):
        m=copy.deepcopy(base);m['member_id']='syn_'+f'{i:032x}'
        if missing:
            m['fields']['schedule']=None;m['field_status']['schedule']='not_asked';m['field_observed_day']['schedule']=None
        state['members'].append(m)
    return state

def main():
    rows=[]
    for shape,n,missing in [('empty',0,False),('dense',200,False),('dense_unknown',200,True)]:
        state=dense(n,missing)
        for mode in ('conservative','learned','learned_value','global'):
            for phase in ('ask','match'):
                raw=json.dumps({'schema_version':'1.0.0','phase':phase,'state':state,'memory':None});started=time.perf_counter()
                env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
                proc=subprocess.run([sys.executable,str(ROOT/'policy.py'),'--mode',mode],input=raw,text=True,capture_output=True,timeout=10,env=env)
                elapsed=time.perf_counter()-started
                if proc.returncode:raise RuntimeError(proc.stderr)
                response=json.loads(proc.stdout);diag=response['memory']['diagnostics']
                rows.append({'shape':shape,'n':n,'phase':phase,'mode':mode,'startup_seconds':elapsed,'request_bytes':len(raw.encode()),'response_bytes':len(proc.stdout.encode()),'diagnostics':diag})
                print(shape,mode,phase,round(elapsed,4),flush=True)
    atomic_json(ROOT/'results/runtime.json',{'scope':'host subprocess, not Docker, not a worst-case proof','rows':rows,'child_peak_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss if resource else None})
if __name__=='__main__':main()
