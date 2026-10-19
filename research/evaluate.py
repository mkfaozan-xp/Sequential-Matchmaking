"""Two-worker evaluation with one transactional writer and lease heartbeats."""
import argparse,json,time
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from multiprocessing import get_context
from pathlib import Path
from blackbox.experiment import run_episode,VARIANTS,summarise
from blackbox.policy import MODES
from blackbox.storage import Ledger,atomic_json,digest,RunBusy
from blackbox.metrics import paired_interval
from blackbox.provenance import execution_identity
from blackbox.runtime import runtime_info,installed_dependencies
from blackbox.seeds import reserve
from blackbox.registry import identity as asset_identity,sha,verified_episode_snapshot
ROOT=Path(__file__).resolve().parent

def episode_job(seed,variant,method,transport,identity):
    if execution_identity()!=identity:raise ValueError('execution identity changed in worker')
    def heartbeat():
        if asset_identity()!=identity['inference_release']:raise ValueError('inference assets changed in worker')
    if transport=='inprocess' and method in ('conservative','rank_tie','rank_aux','rank_ref','rank_nohistory','rank_legacy','baseline_greedy','baseline_no_asks','baseline_random'):
        with verified_episode_snapshot(identity['inference_release']):
            row,*_=run_episode(seed,variant,method,transport,heartbeat=heartbeat)
    else:row,*_=run_episode(seed,variant,method,transport,heartbeat=heartbeat)
    if execution_identity()!=identity:raise ValueError('execution identity changed during worker episode')
    return row

def main():
    p=argparse.ArgumentParser();p.add_argument('--methods',default='baseline_greedy,baseline_no_asks,baseline_random,conservative,learned')
    p.add_argument('--seeds',default='2701,2702');p.add_argument('--variants',default='all')
    p.add_argument('--transport',choices=['inprocess','subprocess'],default='inprocess');p.add_argument('--output',default='results/validation.json')
    p.add_argument('--locked-test-plan');p.add_argument('--jobs',type=int,choices=(1,2),default=2);a=p.parse_args()
    seeds=[int(s) for s in a.seeds.split(',')];methods=a.methods.split(',');variants=list(VARIANTS) if a.variants=='all' else a.variants.split(',')
    allowed=set(MODES)|{'baseline_greedy','baseline_no_asks','baseline_random'}
    if not seeds or len(set(seeds))!=len(seeds) or len(set(methods))!=len(methods) or any(m not in allowed for m in methods) or len(set(variants))!=len(variants) or any(v not in VARIANTS for v in variants):p.error('unique known seeds/methods/variants required')
    if any(1101<=s<=1150 for s in seeds):p.error('training seeds cannot be evaluation seeds')
    identity=execution_identity();plan_hash=None
    if any(s>=3101 for s in seeds):
        if not a.locked_test_plan:p.error('final seeds require a frozen plan')
        plan=json.loads(Path(a.locked_test_plan).read_text());expected={'identity':identity,'seeds':seeds,'methods':methods,'variants':variants,'transport':a.transport,'decision_days':60,'follow_up_days':40,'members':200}
        if plan.get('experiment')!=expected or plan.get('frozen_before_results') is not True:p.error('frozen subject mismatch')
        if plan.get('protocol_sha256')!=sha(ROOT/'plans/REVIEW_PROTOCOL.md'):p.error('declared protocol changed')
        plan_hash=reserve(seeds,plan)
    path=ROOT/a.output;path.parent.mkdir(parents=True,exist_ok=True);ledger=Ledger(path.with_suffix('.sqlite'))
    config={'runtime':dict(runtime_info(),dependencies=installed_dependencies()),'identity':identity,'transport':a.transport,
        'members':200,'decision_days':60,'follow_up_days':40,'host_workers':a.jobs,'numerical_threads':1,
            'asset_access':'verified episode snapshot for declared inprocess modes and supplied baselines; disk verified before/after; subprocess remains uncached'}
    tasks=[(s,v,m) for s in seeds for v in variants for m in methods];positions={t:i for i,t in enumerate(tasks)}
    rows=[];run_ids=set();expected_count=len(tasks);pending={};cursor=0
    def write():
        ordered=sorted(rows,key=lambda r:positions[(r['seed'],r['variant'],r['method'])])
        attempts=[x for x in ledger.audit() if x['run_id'] in run_ids];failures=sum(x['status']=='failed' for x in attempts)
        complete=len(ordered)==expected_count
        result={'schema_version':3,'scope':'frozen final test' if plan_hash else 'declared development study',
            'runtime':config['runtime'],'config':config,'plan_hash':plan_hash,'seeds':seeds,'variants':variants,'methods':methods,
            'expected_episodes':expected_count,'complete':complete,'episodes':ordered,'attempt_audit':attempts,
            'failed_attempts':failures,'all_valid':complete and failures==0 and all(r['valid'] for r in ordered),
            'summaries':{m:summarise([r for r in ordered if r['method']==m]) for m in methods},
            'paired_vs_conservative':{m:paired_interval(ordered,m) for m in methods if m!='conservative'} if 'conservative' in methods else {}}
        atomic_json(path,result);return result
    try:
        with ProcessPoolExecutor(max_workers=a.jobs,mp_context=get_context('spawn')) as pool:
            result=write()
            while cursor<len(tasks) or pending:
                while cursor<len(tasks) and len(pending)<a.jobs:
                    seed,variant,method=tasks[cursor];cursor+=1
                    key,previous=ledger.claim(dict(config,seed=seed,variant=variant,method=method));run_ids.add(key)
                    if previous is not None:rows.append(previous);result=write();continue
                    future=pool.submit(episode_job,seed,variant,method,a.transport,identity)
                    pending[future]=(key,seed,variant,method)
                if not pending:continue
                completed,_=wait(pending,timeout=1,return_when=FIRST_COMPLETED)
                for future,(key,seed,variant,method) in list(pending.items()):ledger.heartbeat(key)
                for future in completed:
                    key,seed,variant,method=pending.pop(future)
                    try:row=future.result()
                    except Exception as error:row={'seed':seed,'variant':variant,'method':method,'valid':False,'error':type(error).__name__+': '+str(error)}
                    ledger.finish(key,row);rows.append(row);result=write()
                    print(json.dumps({k:row.get(k) for k in ('seed','variant','method','valid','mutual_second_meeting_intention','error')}),flush=True)
        return 0 if result['all_valid'] else 2
    except RunBusy as error:print(str(error));return 3
    finally:ledger.close()

if __name__=='__main__':raise SystemExit(main())
