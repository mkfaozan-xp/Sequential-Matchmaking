"""Recompute validation readiness from bound tests/raw episodes; promotion stays separate."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.registry import selected,sha
from blackbox.storage import atomic_json,digest
from blackbox.metrics import paired_interval
from blackbox.experiment import VARIANTS


def read(path):
    p=Path(path)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def valid_matrix(data, require_baselines=False):
    if not data or data.get('complete') is not True or data.get('config',{}).get('identity')!=execution_identity():return False
    if require_baselines and not {'baseline_greedy','baseline_no_asks','baseline_random','conservative','learned'} <= set(data.get('methods',[])):return False
    if set(data.get('variants',[]))!=set(VARIANTS):return False
    expected={(s,v,m) for s in data['seeds'] for v in VARIANTS for m in data['methods']}
    rows=data.get('episodes',[]);keys=[(r['seed'],r['variant'],r['method']) for r in rows]
    return (set(keys)==expected and len(keys)==len(expected) and all(r.get('valid') is True for r in rows)
            and not any(a['status']=='failed' for a in data.get('attempt_audit',[]))
            and all(valid_episode(r) for r in rows))


def valid_episode(row):
    try:
        n=row['arrived_members'];events=row['mutual_second_meeting_intention']
        return (type(n) is int and n==200 and type(events) is int and events>=0
            and events<=row['dates']<=row['mutual_acceptances']<=row['assignments']
            and abs(row['msmi_per_100_arrived_members']-100*events/n)<1e-10
            and 0<=row['served_members']<=n and row['unserved_members']==n-row['served_members']
            and abs(row['coverage']-row['served_members']/n)<1e-10
            and 0<=row['ask_cost']<=720 and row['max_request_bytes']<=1024**2 and row['max_response_bytes']<=1024**2)
    except (KeyError,TypeError,ZeroDivisionError):return False


def data_snapshot_valid(record,current):
    if not (record and record.get('identity')==current and record.get('verified') is True and record.get('files')==71):return False
    try:
        path=ROOT/'starter/data_checksums.json'
        if record.get('checksum_manifest_sha256')!=sha(path):return False
        checks=json.loads(path.read_text(encoding='utf-8'))
        return len(checks)==71 and all(sha(ROOT/'starter'/name)==expected for name,expected in checks.items())
    except (OSError,ValueError):return False


def container_valid(container,mode):
    expected_constraints={'network':'none','cpus':2,'memory_bytes':1024**3,'pids':64,'read_only':True,'tmpfs_bytes':64*1024**2}
    container_ok=(container is not None and container.get('identity')==execution_identity(mode=mode)
        and container.get('status')=='completed' and container.get('constraints')==expected_constraints
        and isinstance(container.get('image_id'),str) and container['image_id'].startswith('sha256:')
        and type(container.get('image_size_bytes')) is int and 0<container['image_size_bytes']<=2*1024**3)
    if container_ok:
        rows=container.get('episodes',[])
        container_ok=len(rows)==6 and {(r['seed'],r['variant']) for r in rows}=={(101,v) for v in VARIANTS} and all(r.get('valid') is True for r in rows)
    return bool(container_ok)


def assess(tests,validation,container,mode='conservative',final=None,plan=None,data_check=None,candidate_container=None):
    current=execution_identity()
    suites=(tests or {}).get('suites',[])
    test_ok=(tests is not None and tests.get('identity')==current and {s['suite'] for s in suites}=={'project','starter'}
        and len(suites)==2 and all(s.get('identity')==current and s.get('success') is True and s.get('tests_run',0)>0
        and s.get('failures')==0 and s.get('errors')==0 and s.get('skipped')==0 for s in suites))
    checks={'actual_test_suites':bool(test_ok),'complete_validation_matrix':valid_matrix(validation,require_baselines=True),
            'verified_public_snapshot':data_snapshot_valid(data_check,current),
            'exact_container_release':container_valid(container,mode)}
    promotion={'evaluated':False,'eligible':False,'reason':'No bound frozen final-test evidence'}
    if final is not None and plan is not None and valid_matrix(final) and final.get('plan_hash')==digest(plan):
        experiment=plan.get('experiment',{})
        bound=(plan.get('frozen_before_results') is True and experiment.get('identity')==current
            and experiment.get('seeds')==final['seeds'] and experiment.get('methods')==final['methods']
            and experiment.get('variants')==list(VARIANTS) and all(s>=3101 for s in final['seeds']))
        if bound and {'conservative','learned'}<=set(final['methods']):
            interval=paired_interval(final['episodes'],'learned')
            # Predeclared conservative gate: evidence across >=10 seed blocks; no family mean regression.
            scenarios={m:{} for m in ('learned','conservative')}
            for m in scenarios:
                for v in VARIANTS:
                    values=[r['msmi_per_100_arrived_members'] for r in final['episodes'] if r['method']==m and r['variant']==v]
                    scenarios[m][v]=sum(values)/len(values)
            service_ok=True
            for group in ('low','partial','complete'):
                cov={}
                for m in scenarios:
                    slices=[r['service_slices'][group] for r in final['episodes'] if r['method']==m]
                    pop=sum(s['members'] for s in slices);cov[m]=sum(s['served'] for s in slices)/pop if pop else None
                if cov['learned'] is not None and cov['conservative'] is not None and cov['learned']<cov['conservative']-.05:service_ok=False
            sufficient=interval.get('seed_blocks',0)>=10
            gain=interval.get('ci95',[0])[0]>0
            scenario_ok=all(scenarios['learned'][v]>=scenarios['conservative'][v] for v in VARIANTS)
            candidate_sandbox=container_valid(candidate_container,'learned') or (mode=='learned' and container_valid(container,'learned'))
            promotion_checks={'minimum_seed_blocks':sufficient,'positive_paired_lower_bound':gain,
                'no_family_mean_regression':scenario_ok,'service_guardrail':service_ok,
                'exact_learned_container':candidate_sandbox,'validation_readiness':all(checks.values())}
            promotion={'evaluated':True,'eligible':all(promotion_checks.values()),'checks':promotion_checks,
                'paired_interval':interval,'scenario_guardrail':scenario_ok,'service_guardrail':service_ok,
                'family_scores':scenarios,
                'reason':'Predeclared gates; 10 blocks is a minimum guardrail, not a statistical-power guarantee'}
    return {'schema_version':2,'identity':current,'mode':mode,'checks':checks,
        'status':'validation_checks_passed' if all(checks.values()) else 'blocked',
        'missing_or_failed':[k for k,v in checks.items() if not v], 'candidate_promotion':promotion,
        'warning':'Validation readiness is not production certification or private-organiser eligibility.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--validation',default='results/validation.json')
    p.add_argument('--tests',default='results/tests.json');p.add_argument('--container',default='results/container_attestation.json')
    p.add_argument('--final',default='results/final_test.json');p.add_argument('--plan',default='plans/final_test.json');p.add_argument('--mode',default='conservative')
    p.add_argument('--candidate-container',default='results/container_learned.json')
    p.add_argument('--output',default='results/release_readiness.json');a=p.parse_args()
    result=assess(read(ROOT/a.tests),read(ROOT/a.validation),read(ROOT/a.container),a.mode,
                  read(ROOT/a.final) if a.final else None,read(ROOT/a.plan) if a.plan else None,read(ROOT/'results/data_check.json'),
                  read(ROOT/a.candidate_container))
    atomic_json(ROOT/a.output,result);print(json.dumps(result,indent=2));return 0 if result['status']=='validation_checks_passed' else 2

if __name__=='__main__':raise SystemExit(main())
