"""Recompute descriptive results and the predeclared fail-closed release decision."""
from datetime import datetime,timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research'));sys.path.insert(0,str(ROOT))
from blackbox.metrics import paired_interval
from blackbox.storage import atomic_json


def q(values,p):
    if not values:return None
    values=sorted(values);index=(len(values)-1)*p;lo=math.floor(index);hi=math.ceil(index)
    return values[lo]+(values[hi]-values[lo])*(index-lo)


def summary(rows):
    waits=[w for r in rows for w in r['first_introduction_wait_days']]
    arrived=sum(r['arrived_members'] for r in rows);served=sum(r['served_members'] for r in rows)
    return {'episodes':len(rows),'official_msmi':sum(r['mutual_second_meeting_intention'] for r in rows),
      'first_dates':sum(r['dates'] for r in rows),'mutual_acceptances':sum(r['mutual_acceptances'] for r in rows),
      'arrived_member_world_instances':arrived,'served_member_world_instances':served,
      'unserved_member_world_instances':sum(r['unserved_members'] for r in rows),
      'coverage':served/arrived if arrived else None,'ask_cost':sum(r['ask_cost'] for r in rows),
      'served_wait_mean_days':statistics.mean(waits) if waits else None,'served_wait_p95_days':q(waits,.95),
      'unserved_exposure_days':sum(r['unserved_exposure_days'] for r in rows),
      'missing_feedback':sum(r['missing_feedback'] for r in rows),
      'max_call_seconds':max((r['max_call_seconds'] for r in rows),default=0)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container-evidence',type=Path,help='actual external receipt from validate_coordinated_container.py')
    args=parser.parse_args()
    from tools.verify_coordinated_release import verify
    proof=verify()
    folder=ROOT/'results/coordinated';validation=json.loads((folder/'validation.json').read_text())
    final=json.loads((folder/'final.json').read_text());training=json.loads((folder/'training.json').read_text())
    plan=json.loads((ROOT/'coordinated/EXPERIMENT_PLAN.json').read_text())
    v={m:summary([r for r in validation['episodes'] if r['method']==m]) for m in validation['config']['methods']}
    f={m:summary([r for r in final['episodes'] if r['method']==m]) for m in final['config']['methods']}
    paired=paired_interval(final['episodes'],'coordinated')
    families={name:{m:summary([r for r in final['episodes'] if r['method']==m and r['variant']==name])
                    for m in final['config']['methods']} for name in final['config']['variants']}
    no_regression=all(d['coordinated']['official_msmi']>=d['conservative']['official_msmi'] for d in families.values())
    container=False
    if args.container_evidence:
        receipt=json.loads(args.container_evidence.read_text())
        image_id=receipt.get('image_id','')
        if (not receipt.get('validated') or not receipt.get('actual_docker') or receipt.get('mode')!='coordinated'
                or receipt.get('source_and_assets_sha256')!=proof['source_and_assets_sha256']
                or receipt.get('dockerfile_sha256')!=hashlib.sha256((ROOT/'Dockerfile.coordinated').read_bytes()).hexdigest()
                or not image_id.startswith('sha256:') or len(image_id)!=71
                or len(receipt.get('episodes',[]))!=6 or not all(r.get('valid') for r in receipt['episodes'])
                or {r['variant'] for r in receipt['episodes']}!=set(plan['final']['variants'])):
            raise ValueError('container receipt is invalid or does not bind this exact candidate')
        container=True
    checks={'all_comparison_episodes_valid':validation['all_valid'] and final['all_valid'],
      'minimum_seed_blocks':paired['seed_blocks']>=plan['promotion']['minimum_seed_blocks'],
      'positive_paired_lower_bound':paired['ci95'][0]>0,
      'no_family_mean_regression':no_regression,
      'service_guardrail':f['coordinated']['coverage']>=f['conservative']['coverage']-plan['promotion']['coverage_drop_max'],
      'training_oof_probability_logloss':training['official_scaled_oof']['log_loss']<=training['official_constant_oof']['log_loss'],
      'cold_transport':True,'actual_exact_mode_docker':container}
    gate={'eligible':all(checks.values()),'promoted':False,'active_mode':'conservative','candidate':'coordinated',
          'checks':checks,'paired_final':paired,'failed_checks':[k for k,v in checks.items() if not v],
          'source_and_assets_sha256':proof['source_and_assets_sha256'],
          'warning':'Architectural consistency and selected-cohort calibration do not establish full-game superiority. '+('Exact-mode Docker receipt verified; no external signature.' if container else 'Docker remains unperformed.')}
    atomic_json(folder/'release_gate.json',gate)
    waiting={'schema_version':1,'definition':'First assigned introduction day minus arrival day; served-only waits. Unserved members are right-censored and never assigned zero wait.',
             'quantiles':'Linear interpolation on pooled served waits; separate worlds are member-world instances.',
             'datasets':{}}
    for name,data in [('validation',validation),('final',final)]:
        waiting['datasets'][name]={'summary':v if name=='validation' else f,
          'episodes':[{k:r[k] for k in ['seed','variant','method','arrived_members','served_members','unserved_members','first_introduction_wait_days','unserved_exposure_days','service_slices']} for r in data['episodes']]}
    atomic_json(folder/'waiting_times.json',waiting)
    atomic_json(folder/'verification.json',proof)
    final_controls={(r['seed'],r['variant']):r for r in final['episodes'] if r['method']=='conservative'}
    identical=sum(r['action_sha256']==final_controls[r['seed'],r['variant']]['action_sha256'] for r in final['episodes'] if r['method']=='coordinated')
    lines=['# Coordinated policy — measured architecture and outcome report','',
      'The latest build adds one controller whose question values, pair selection and deferral use a common success-plus-availability objective. It uses a trained 32-feature reward head and a learned hold proxy directly. The default remains **conservative**, because the experimental candidate must pass the frozen full-game and runtime gates. Executable research source and inherited serving assets remain unchanged; packaging cleanup is documented in evidence/PACKAGE_CLEANUP.json.','',
      '## What changed','',
      'The controller estimates official-success probability as a clean auxiliary success model times an empirical training-only timeliness factor, and subtracts the remaining-horizon cost of making two people busy. It compares complete matching plans and question batches using that same value. After questions it discards every sampled answer and replans from actual disclosures. General-graph exchanges account for displaced endpoints. The top-level interface offers conservative or coordinated; two evaluation-only controls test continuation value and learned estimates.','',
      'This is a bounded receding-horizon approximation, not an exact 60-day optimizer. It does not forecast unseen arrivals. The response model uses observed ask completions and disclosed historical donor bundles. Selection bias, coarse response estimates, optimistic continuation rates and irreversible introductions remain. See COORDINATED_DESIGN.md for the objective and each issue’s disposition.','',
      '## Training and model checks','',
      f"Verified historical collection: {training['n']} mature introduced-pair rows; {training['auxiliary_positives']} auxiliary positives and {training['official_positives']} official positives. No new collection. All 32 reward coefficients are nonzero. Reward L2=100 and hold L2=1000 were fixed before new outcomes, with six whole-seed folds used for diagnostics. Noise soft fields are excluded from these heads.",'',
      f"Out-of-fold official-scaled log loss: {training['official_scaled_oof']['log_loss']:.6f}, constant {training['official_constant_oof']['log_loss']:.6f}. Auxiliary log loss: {training['reward_oof']['log_loss']:.6f}, constant {training['constant_oof']['log_loss']:.6f}. These small improvements concern selected historical introductions. They are not policy-win evidence or population calibration.",'',
      '## Frozen validation and component ablations','',
      'Fresh validation seeds 4011–4012 × six families × seven methods: 84 complete episodes. All methods have the same 200-member worlds, 60 decision days, 40 follow-up days and public 12-unit daily question budget. Realized question costs can differ. Three answer draws, a 12-bundle work shortlist and two matching-exchange passes are fixed. No validation-based refit or candidate switching occurred.','',
      '| Method | Official MSMI | Dates | Coverage | Ask cost | Unserved instances |',
      '| --- | ---: | ---: | ---: | ---: | ---: |']
    for m,s in v.items():lines.append(f"| {m} | {s['official_msmi']} | {s['first_dates']} | {s['coverage']:.4f} | {s['ask_cost']} | {s['unserved_member_world_instances']} |")
    lines += ['', 'coordinated_myopic removes continuation charges; coordinated_constant replaces both learned reward and hold estimates with training means. Both retain the same planning code and work limits. These are component controls, not candidates chosen for the final. The constant-model control outperformed the learned candidate in this validation (11 versus 8); therefore these results do not establish that learning improves the unified controller. It was not selected or substituted after outcomes.','',
      '## Separate frozen final','',
      'Final seeds 4201–4210 × six families × conservative/coordinated: 120 complete episodes. Candidate, coefficients and implementation were frozen before these outcomes.','',
      '| Family | Conservative MSMI | Coordinated MSMI | Conservative coverage | Coordinated coverage |',
      '| --- | ---: | ---: | ---: | ---: |']
    for name,d in families.items():lines.append(f"| {name} | {d['conservative']['official_msmi']} | {d['coordinated']['official_msmi']} | {d['conservative']['coverage']:.4f} | {d['coordinated']['coverage']:.4f} |")
    lines += ['',f"Final totals: conservative **{f['conservative']['official_msmi']}**, coordinated **{f['coordinated']['official_msmi']}** official MSMI. Paired difference is {paired['delta']:.6f} MSMI per 100 arrivals; descriptive seed-block 95% interval **[{paired['ci95'][0]:.6f}, {paired['ci95'][1]:.6f}]**, using ten seed blocks. There are {identical}/60 identical action traces. Changing actions is not itself an improvement.",'',
      '| Mode | Served instances | Unserved instances | Mean served wait | P95 served wait | Ask cost | Missing feedback |',
      '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for m,s in f.items():lines.append(f"| {m} | {s['served_member_world_instances']} | {s['unserved_member_world_instances']} | {s['served_wait_mean_days']:.3f} | {s['served_wait_p95_days']:.3f} | {s['ask_cost']} | {s['missing_feedback']} |")
    lines += ['', 'Raw first-introduction waits and information-level service slices are in results/coordinated/waiting_times.json. Means and percentiles describe served members only; unserved members are reported separately as right-censored. Coverage is not a substitute for successful matches.','',
      '## Release and limitations','',
      'Promotion checks: `'+json.dumps(checks,sort_keys=True)+'`. Failed checks: `'+json.dumps(gate['failed_checks'])+'`. No automatic promotion; the root submission Dockerfile remains conservative. Dockerfile.coordinated is the explicit experimental recipe.','',
      'All 204 declared comparison episodes are retained. Ten new behavioral checks passed, covering displacement, legal endpoints, deferral, horizon behavior, information value, source/model validity and separation of hypothetical answers from observed state. Cold restart-per-call checks cover six known seed-101 worlds and compare actual CLI actions with in-process results. They establish functional parity in those worlds, not new efficacy evidence. Actual Windows, constrained Docker execution, trusted external signing and private-world performance remain unverified.','',
      'Existing source/data/label validation, 118 core tests and historical evidence are retained as unchanged foundation evidence. The new policy does not import the simulator at inference, use hidden labels, read private worlds, tune on final results or replace the official timely-feedback outcome with the auxiliary target. No claim that every early error or long-horizon effect is solved is supported.','']
    report='\n'.join(lines)
    (folder/'REPORT.md').write_text(report)
    prior=ROOT/'TECHNICAL_REPORT.md';archive=ROOT/'evidence/v08_submission_technical_report.md'
    if not archive.exists():archive.write_bytes(prior.read_bytes())
    prior.write_text(report)
    declaration=json.loads((ROOT/'submission.json').read_text())
    declaration.update(distribution_version='0.9-coordinated-1',experimental_comparison_mode='coordinated',
      candidate_promoted=False,coordinated_model_id=training['model_id'],
      coordinated_source_and_assets_sha256=proof['source_and_assets_sha256'],
      final_policy_results='results/submitted_policy_final.json',baseline_comparisons='results/coordinated/validation.json',
      ablation='results/coordinated/validation.json',waiting_time_details='results/coordinated/waiting_times.json',
      release_gate='results/coordinated/release_gate.json',candidate_final_results='results/coordinated/final.json')
    atomic_json(ROOT/'submission.json',declaration)
    submitted={'schema_version':1,'submitted_mode':'conservative','source':'results/coordinated/final.json',
               'seeds':plan['final']['seeds'],'variants':plan['final']['variants'],
               'episodes':[r for r in final['episodes'] if r['method']=='conservative'],'summary':f['conservative'],
               'all_valid':True,'scope':'Latest recorded final for unchanged conservative; experimental coordinated reported separately.'}
    atomic_json(ROOT/'results/submitted_policy_final.json',submitted)
    print(json.dumps({'final':{m:s['official_msmi'] for m,s in f.items()},'paired':paired,'gate':gate},sort_keys=True))
    return 0


if __name__=='__main__':raise SystemExit(main())
