"""Resumable paired validation with exact release identity and complete attempt history."""
import argparse
import json
from pathlib import Path
from blackbox.experiment import run_episode, VARIANTS, summarise
from blackbox.policy import MODES
from blackbox.storage import Ledger, atomic_json, digest, RunBusy
from blackbox.metrics import paired_interval
from blackbox.provenance import execution_identity
from blackbox.registry import identity as asset_identity

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--methods',default='baseline_greedy,baseline_no_asks,baseline_random,conservative,learned')
    parser.add_argument('--seeds',default='2101,2102,2103,2104')
    parser.add_argument('--variants',default='all')
    parser.add_argument('--transport',choices=['inprocess','subprocess'],default='inprocess')
    parser.add_argument('--output',default='results/validation.json')
    parser.add_argument('--locked-test-plan')
    args=parser.parse_args()
    seeds=[int(s) for s in args.seeds.split(',')]
    methods=args.methods.split(',')
    variants=list(VARIANTS) if args.variants=='all' else args.variants.split(',')
    allowed=set(MODES)|{'baseline_greedy','baseline_no_asks','baseline_random'}
    if not seeds or len(set(seeds))!=len(seeds) or len(set(methods))!=len(methods) or any(m not in allowed for m in methods) or len(set(variants))!=len(variants) or any(v not in VARIANTS for v in variants):
        parser.error('unique recognized methods, variants and seeds required')
    if any(1101<=s<=1150 for s in seeds):parser.error('training seeds cannot be evaluation seeds')
    identity=execution_identity()
    plan_hash=None
    if any(s>=3101 for s in seeds):
        if not args.locked_test_plan:parser.error('final-test seeds require a frozen plan')
        plan=json.loads(Path(args.locked_test_plan).read_text(encoding='utf-8'))
        expected={'identity':identity,'seeds':seeds,'methods':methods,'variants':variants,
                  'transport':args.transport,'decision_days':60,'follow_up_days':40,'members':200}
        if plan.get('experiment')!=expected or plan.get('frozen_before_results') is not True:
            parser.error('frozen plan does not match exact code/assets/configuration')
        plan_hash=digest(plan)
    path=ROOT/args.output
    path.parent.mkdir(parents=True,exist_ok=True)
    ledger=Ledger(path.with_suffix('.sqlite'))
    rows=[];run_ids=set()
    config={'identity':identity,'transport':args.transport,'members':200,'decision_days':60,'follow_up_days':40}
    expected_count=len(seeds)*len(variants)*len(methods)
    def write():
        attempts=[a for a in ledger.audit() if a['run_id'] in run_ids]
        failures=sum(a['status']=='failed' for a in attempts)
        complete=len(rows)==expected_count
        summaries={m:summarise([r for r in rows if r['method']==m]) for m in methods}
        result={'schema_version':2,'scope':'validation pilot' if plan_hash is None else 'frozen final test',
                'config':config,'plan_hash':plan_hash,'seeds':seeds,'variants':variants,'methods':methods,
                'expected_episodes':expected_count,'complete':complete,'episodes':rows,'attempt_audit':attempts,
                'failed_attempts':failures,'all_valid':complete and failures==0 and all(r['valid'] for r in rows),
                'summaries':summaries,'paired_vs_conservative':{
                    m:paired_interval(rows,m) for m in methods if m!='conservative'} if 'conservative' in methods else {}}
        atomic_json(path,result)
        return result
    try:
        for seed in seeds:
            for variant in variants:
                for method in methods:
                    key,previous=ledger.claim(dict(config,seed=seed,variant=variant,method=method))
                    run_ids.add(key)
                    if previous is not None:
                        row=previous
                    else:
                        try:
                            if execution_identity()!=identity:raise ValueError('execution identity changed before episode')
                            def progress():
                                if asset_identity()!=identity['inference_release']:raise ValueError('inference assets changed during episode')
                                ledger.heartbeat(key)
                            row,*_=run_episode(seed,variant,method,args.transport,heartbeat=progress)
                            if execution_identity()!=identity:raise ValueError('execution identity changed during episode')
                        except Exception as error:
                            row={'seed':seed,'variant':variant,'method':method,'valid':False,
                                 'error':type(error).__name__+': '+str(error)}
                        ledger.finish(key,row)
                    rows.append(row)
                    result=write()
                    print(json.dumps({k:row.get(k) for k in ('seed','variant','method','valid','mutual_second_meeting_intention','error')}),flush=True)
        return 0 if result['all_valid'] else 2
    except RunBusy as error:
        print(str(error));return 3
    finally:
        ledger.close()

if __name__=='__main__':raise SystemExit(main())
