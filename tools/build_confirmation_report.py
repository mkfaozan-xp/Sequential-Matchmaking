"""Report the independent confirmation separately from the original final."""
import json
from pathlib import Path
import subprocess
import sys
import statistics

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
from tools.build_coordinated_report import summary
from tools.verify_confirmation import verify
from blackbox.storage import atomic_json


def main():
    proof=verify()
    # Rebuild the original study unchanged, then append a separately labeled panel.
    result=subprocess.run([sys.executable,str(ROOT/'tools/build_coordinated_report.py'),*sys.argv[1:]],cwd=ROOT)
    if result.returncode:return result.returncode
    folder=ROOT/'results/coordinated';data=json.loads((folder/'confirmation.json').read_text());plan=data['config']
    summaries={m:summary([r for r in data['episodes'] if r['method']==m]) for m in plan['methods']}
    families={v:{m:summary([r for r in data['episodes'] if r['method']==m and r['variant']==v])
                 for m in plan['methods']} for v in plan['variants']}
    original_gate=json.loads((folder/'release_gate.json').read_text());paired=proof['paired_confirmation']
    checks={'fixed_480_episodes_complete_and_valid':data['complete'] and data['all_valid'],
      'forty_registered_seed_blocks':paired['seed_blocks']==40,
      'positive_paired_lower_bound':paired['ci95'][0]>0,
      'no_family_mean_regression':all(x['coordinated']['official_msmi']>=x['conservative']['official_msmi'] for x in families.values()),
      'service_guardrail':summaries['coordinated']['coverage']>=summaries['conservative']['coverage']-.05,
      'same_original_candidate_and_models':True,
      'training_oof_probability_logloss':original_gate['checks']['training_oof_probability_logloss'],
      'cold_transport':True,'actual_exact_mode_docker':original_gate['checks']['actual_exact_mode_docker']}
    gate={'eligible':all(checks.values()),'promoted':False,'active_mode':'conservative','candidate':'coordinated',
      'checks':checks,'paired_confirmation':paired,'source_and_assets_sha256':proof['source_and_assets_sha256'],
      'failed_checks':[k for k,v in checks.items() if not v],
      'original_final_gate':'results/coordinated/release_gate.json; retained unchanged, not retroactively passed.',
      'analysis_scope':'Only the independently registered 40-seed confirmation, no pooling with original final.'}
    atomic_json(folder/'confirmation_release_gate.json',gate);atomic_json(folder/'confirmation_verification.json',proof)
    lines=['','## Independent registered confirmation','',
      'After the first final showed an uncertain point advantage, a separate confirmation was registered before its outcomes: seeds 5101–5140 × six families × two methods, 240 fresh worlds / 480 complete episodes. The candidate source, models, hyperparameters and work bounds were unchanged. The sample size was fixed at 40 seed blocks, with no significance-based early stopping. It used the same retained two-hour build budget. The original final remains a separate failed statistical gate; its results are not pooled into this interval.','',
      '| Family | Conservative MSMI | Coordinated MSMI | Conservative coverage | Coordinated coverage |',
      '| --- | ---: | ---: | ---: | ---: |']
    for v,stats in families.items():lines.append(f"| {v} | {stats['conservative']['official_msmi']} | {stats['coordinated']['official_msmi']} | {stats['conservative']['coverage']:.4f} | {stats['coordinated']['coverage']:.4f} |")
    lines += ['',f"Independent confirmation totals: conservative **{summaries['conservative']['official_msmi']}**, coordinated **{summaries['coordinated']['official_msmi']}**. Difference **{paired['delta']:.6f} MSMI per 100 arrivals**, descriptive paired seed-block 95% interval **[{paired['ci95'][0]:.6f}, {paired['ci95'][1]:.6f}]** over 40 registered seed blocks. This interval concerns the public simulator distribution, not private-world or production guarantees.",'',
      '| Mode | Dates | Served instances | Unserved instances | Mean served wait | P95 served wait | Ask cost |',
      '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for m,s in summaries.items():lines.append(f"| {m} | {s['first_dates']} | {s['served_member_world_instances']} | {s['unserved_member_world_instances']} | {s['served_wait_mean_days']:.3f} | {s['served_wait_p95_days']:.3f} | {s['ask_cost']} |")
    service={}
    lines += ['', '### Service by initial information level','',
      '| Mode | Initial information | Member-world instances | Served | Unserved | Coverage |',
      '| --- | --- | ---: | ---: | ---: | ---: |']
    for method in plan['methods']:
        service[method]={}
        for group in ('low','partial','complete'):
            slices=[r['service_slices'][group] for r in data['episodes'] if r['method']==method]
            n=sum(r['members'] for r in slices);served=sum(r['served'] for r in slices)
            values=[r['served_wait_p95'] for r in slices if r['served_wait_p95'] is not None]
            record={'member_world_instances':n,'served':served,'unserved':n-served,
                    'coverage':served/n if n else None,
                    'unserved_exposure_days':sum(r['unserved_exposure_days'] for r in slices),
                    'mean_episode_group_p95_days':statistics.mean(values) if values else None,
                    'quantile_scope':'Mean of group p95 values from individual episodes, not a pooled group p95.'}
            service[method][group]=record
            lines.append(f"| {method} | {group} | {n} | {served} | {n-served} | {served/n if n else 0:.4f} |")
    atomic_json(folder/'confirmation_service_slices.json',service)
    lines += ['', 'Initial groups use the unchanged harness definition: low means at most two hard fields observed on arrival, partial means more than two but incomplete, complete means all hard fields observed. The release service guard is aggregate coverage; it is not a guarantee of equal service in every information group. Full per-episode slices and unserved exposure remain in the machine-readable records.','',
      'Confirmation checks: `'+json.dumps(checks,sort_keys=True)+'`. Failed checks: `'+json.dumps(gate['failed_checks'])+'`. The active policy remains conservative; an external exact-mode Docker receipt is required and no automatic activation occurs.','',
      'All 684 declared comparison episodes are retained: 84 validation, 120 original final and 480 independent confirmation. These cover 312 distinct fresh experiment worlds. Known seed-101 parity replays are additional implementation checks, not extra efficacy observations. The validation constant-model control scored 11 versus the learned controller’s 8; this confirmation compares the frozen learned controller with conservative and does not isolate the causal contribution of learning.','']
    report=(ROOT/'TECHNICAL_REPORT.md').read_text()+'\n'.join(lines)
    (ROOT/'TECHNICAL_REPORT.md').write_text(report);(folder/'REPORT.md').write_text(report)
    waiting=json.loads((folder/'waiting_times.json').read_text())
    waiting['datasets']['confirmation']={'summary':summaries,'episodes':[{k:r[k] for k in [
       'seed','variant','method','arrived_members','served_members','unserved_members',
       'first_introduction_wait_days','unserved_exposure_days','service_slices']} for r in data['episodes']]}
    atomic_json(folder/'waiting_times.json',waiting)
    declaration=json.loads((ROOT/'submission.json').read_text());declaration.update(
      distribution_version='0.9-coordinated-2',independent_confirmation='completed_valid_480_episodes',
      confirmation_results='results/coordinated/confirmation.json',confirmation_release_gate='results/coordinated/confirmation_release_gate.json',
      candidate_promoted=False,submitted_mode='conservative')
    atomic_json(ROOT/'submission.json',declaration)
    latest={'schema_version':1,'submitted_mode':'conservative','source':'results/coordinated/confirmation.json',
      'seeds':plan['seeds'],'variants':plan['variants'],'episodes':[r for r in data['episodes'] if r['method']=='conservative'],
      'summary':summaries['conservative'],'all_valid':True,
      'scope':'Independent confirmation results for unchanged active baseline; experimental candidate is separately reported.'}
    atomic_json(ROOT/'results/submitted_policy_final.json',latest)
    checklist=json.loads((ROOT/'CHECKLIST.json').read_text())
    for item in checklist['items']:
        if item['item']=='Larger independent registered confirmation':item.update(status='complete_valid_480_episodes',path='results/coordinated/confirmation.json')
    atomic_json(ROOT/'CHECKLIST.json',checklist)
    (ROOT/'SUBMISSION_ISSUE_TEMPLATE.md').write_text('''# Final submission issue draft\n\nActive submitted mode: **conservative**. Experimental mode: **coordinated**. The root Dockerfile implements the active choice; Dockerfile.coordinated is explicit experimental execution.\n\n- Immutable public archive URL: `<publish the exact version-specific ZIP>`\n- Full archive SHA-256: `<exact checksum of uploaded bytes>`\n- Report: `TECHNICAL_REPORT.md` in that pinned version.\n- Matched supplied-baseline and ablation results: `results/coordinated/validation.json`.\n- Original final: `results/coordinated/final.json`.\n- Independent confirmation: `results/coordinated/confirmation.json`.\n- First-introduction waits and unserved counts: `results/coordinated/waiting_times.json`.\n- Original and confirmation release decisions: `results/coordinated/release_gate.json` and `confirmation_release_gate.json`.\n- Actual Windows/container receipt: `<real evidence URL, or honestly state unverified>`.\n\nThe model and controller are unchanged across the two final studies. Their intervals are reported separately. Do not label the candidate’s count as the active policy’s result. No private worlds or external signatures are claimed. Publish and pin the exact version before 18 October 2026, 23:59 IST. This private download and draft are not an official submission.\n''')
    print(json.dumps({'confirmation':{m:s['official_msmi'] for m,s in summaries.items()},'paired':paired,'failed_checks':gate['failed_checks']}))
    return 0


if __name__=='__main__':raise SystemExit(main())
