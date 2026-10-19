"""Round 2 contrasts, calibration and service from complete, bound raw episodes."""
import json
from fractions import Fraction
from pathlib import Path
import random
import statistics
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blackbox.provenance import execution_identity
from blackbox.storage import atomic_json
from blackbox.metrics import paired_interval,quantile
from scripts.release_gate import valid_matrix


def pooled_calibration(records):
    records=[r for r in records if r and r.get('n',0)>0];n=sum(r['n'] for r in records)
    if not n:return {'n':0,'brier':None,'log_loss':None,'ece':None,'bins':[]}
    bins={}
    for record in records:
        for b in record['bins']:
            key=(b['lo'],b['hi']);target=bins.setdefault(key,{'n':0,'predicted_sum':0,'observed_sum':0})
            target['n']+=b['n'];target['predicted_sum']+=b['n']*b['predicted'];target['observed_sum']+=b['n']*b['observed']
    pooled=[{'lo':lo,'hi':hi,'n':b['n'],'predicted':b['predicted_sum']/b['n'],'observed':b['observed_sum']/b['n']}
        for (lo,hi),b in sorted(bins.items())]
    return {'n':n,'brier':sum(r['n']*r['brier'] for r in records)/n,
        'log_loss':sum(r['n']*r['log_loss'] for r in records)/n,
        'ece':sum(b['n']*abs(b['predicted']-b['observed']) for b in pooled)/n,'bins':pooled,
        'scope':'pooled mature selected introductions only'}


def interval(blocks):
    seeds=sorted(blocks);rng=random.Random(17)
    samples=[sum((blocks[rng.choice(seeds)] for _ in seeds),Fraction())/len(seeds) for _ in range(2000)]
    return {'seed_blocks':len(seeds),'mean':float(statistics.mean(blocks.values())),
        'ci95':[float(quantile(samples,.025)),float(quantile(samples,.975))],
        'scope':'descriptive seed-block bootstrap; small block counts do not establish reliable inference'}


def factorial(data):
    rows={(r['seed'],r['variant'],r['method']):Fraction(100*r['mutual_second_meeting_intention'],r['arrived_members']) for r in data['episodes']}
    effects={key:{} for key in ('asking_at_greedy','allocation_at_pruned','joint','interaction')}
    for seed in data['seeds']:
        values={key:[] for key in effects}
        for variant in data['variants']:
            base=rows[(seed,variant,'hybrid')];ask=rows[(seed,variant,'hybrid_pair')]
            allocation=rows[(seed,variant,'hybrid_global')];joint=rows[(seed,variant,'hybrid_pair_global')]
            values['asking_at_greedy'].append(ask-base);values['allocation_at_pruned'].append(allocation-base)
            values['joint'].append(joint-base);values['interaction'].append(joint-ask-allocation+base)
        for key in effects:effects[key][seed]=statistics.mean(values[key])
    return {key:interval(value) for key,value in effects.items()}


def method_summary(rows):
    searches=[c for r in rows for c in r.get('question_search_calls',[]) if c.get('planned',0)>0]
    solvers=[c for r in rows for c in r.get('solver_calls',[])]
    groups={}
    for group in ('low','partial','complete'):
        slices=[r['service_slices'][group] for r in rows];n=sum(s['members'] for s in slices);served=sum(s['served'] for s in slices)
        groups[group]={'members':n,'served':served,'coverage':served/n if n else None,
            'directional_calibration':pooled_calibration([r.get('directional_calibration_by_initial_info',{}).get(group) for r in rows])}
    return {'episodes':len(rows),'msmi_pairs':sum(r['mutual_second_meeting_intention'] for r in rows),
        'msmi_per_100':statistics.mean(r['msmi_per_100_arrived_members'] for r in rows),
        'coverage':statistics.mean(r['coverage'] for r in rows),'ask_cost':sum(r['ask_cost'] for r in rows),
        'soft_disclosures':sum(r.get('new_disclosures',{}).get('soft',0) for r in rows),
        'search_calls':len(searches),'search_solves':sum(c['solves'] for c in searches),
        'completed_search_calls':sum(not c['fallback'] and c['solves']==c['planned'] for c in searches),
        'search_fallbacks':sum(c['fallback'] for c in searches),'solver_fallbacks':sum(c['fallback'] for c in solvers),
        'milp_calls':sum(c['solver']=='milp' for c in solvers),'certified_optimal_calls':sum(c.get('optimal') is True for c in solvers),
        'max_call_seconds':max(r['max_call_seconds'] for r in rows),'wall_seconds':sum(r['wall_seconds'] for r in rows),
        'joint_calibration':pooled_calibration([r['calibration'] for r in rows]),
        'directional_calibration':pooled_calibration([r['directional_response_calibration'] for r in rows]),'service':groups}


def main():
    path=ROOT/'results/research.json'
    data=json.loads(path.read_text()) if path.exists() else None
    lines=['# V0.6 asking/allocation research','']
    required={'hybrid','hybrid_global','hybrid_pair','hybrid_pair_global'}
    if not valid_matrix(data) or not required<=set(data['methods']):
        lines += ['Matrix incomplete, invalid or stale. No completed research result is claimed.']
        (ROOT/'results/ROUND2.md').write_text('\n'.join(lines)+'\n')
        atomic_json(ROOT/'results/research_analysis.json',{'identity':execution_identity(),'complete':False})
        return 2
    methods={m:method_summary([r for r in data['episodes'] if r['method']==m]) for m in data['methods']}
    effects=factorial(data)
    result={'identity':execution_identity(),'complete':True,'methods':methods,'factorial':effects,
        'independent_seed_blocks':len(data['seeds']),'world_scenarios':len(data['seeds'])*len(data['variants']),
        'warning':'Two-block descriptive factorial; no powered causal or promotion claim.'}
    atomic_json(ROOT/'results/research_analysis.json',result)
    lines += [str(len(data['episodes']))+' valid executions on shared worlds; two independent seed blocks.',
        'All arms use the same fitted joint tie scorer. Asking and allocator are the declared factors.','',
        '| Mode | MSMI | Ask cost | Actual hypothetical solves | Search fallbacks | MILP fallbacks |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for m,v in methods.items():lines += [f'| {m} | {v["msmi_pairs"]} | {v["ask_cost"]} | {v["search_solves"]} | {v["search_fallbacks"]} | {v["solver_fallbacks"]} |']
    lines += ['','| Contrast | Mean per100 | Descriptive interval |','| --- | ---: | --- |']
    for k,v in effects.items():lines += [f'| {k} | {v["mean"]:.6f} | {v["ci95"]} |']
    lines += ['','Identical solve caps are not identical realized CPU work. Timing fallbacks, actual work, calibration and service slices remain in the JSON. Complementary/single/stress experiments from v0.5 are historical, not current-source proof.']
    (ROOT/'results/ROUND2.md').write_text('\n'.join(lines)+'\n')
    return 0

if __name__=='__main__':raise SystemExit(main())
